from __future__ import annotations

import asyncio
import subprocess
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, TypeVar

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    TextBlock,
    ToolUseBlock,
    query,
)
from langgraph.types import interrupt

from ssw.config import get_settings
from ssw.subagents.code_generate.model import CodeGenerateInput


settings = get_settings()
T = TypeVar("T")


class GitCommandError(RuntimeError):
    pass


def print_claude_stderr(line: str) -> None:
    print(f"[claude stderr] {line}", file=sys.stderr)


def _claude_cli_path() -> Path | None:
    if not settings.claude_cli_path:
        return None

    cli_path = settings.claude_cli_path.strip()
    if not cli_path:
        return None

    return Path(cli_path).expanduser()


def _project_workspace(project_workspace: str | None) -> Path:
    if not project_workspace:
        raise RuntimeError("project_workspace is required before running Claude Code")

    return Path(project_workspace).resolve()


def _claude_options(project_workspace: str, permission_mode: str) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        cli_path=_claude_cli_path(),
        cwd=_project_workspace(project_workspace),
        permission_mode=permission_mode,
        stderr=print_claude_stderr,
    )


def _run_coroutine_in_isolated_loop(
    coroutine_factory: Callable[[], Awaitable[T]],
) -> T:
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()

    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coroutine_factory())
    finally:
        asyncio.set_event_loop(None)
        loop.close()


async def _run_in_isolated_loop(
    coroutine_factory: Callable[[], Awaitable[T]],
) -> T:
    return await asyncio.to_thread(_run_coroutine_in_isolated_loop, coroutine_factory)


async def create_workspace(state: CodeGenerateInput) -> dict[str, str]:
    base_dir = Path(settings.ssw_workspace or "workspace").resolve()
    code_workspace = base_dir / state.project_name

    if not code_workspace.exists():
        await asyncio.to_thread(base_dir.mkdir, parents=True, exist_ok=True)
        await run_cmd(["git", "clone", state.url, str(code_workspace)], str(base_dir))
        await run_cmd(["git", "checkout", state.branch], str(code_workspace))

    return {"project_workspace": str(code_workspace)}


def select_coding_ide(code_generate_input: CodeGenerateInput) -> str:
    return code_generate_input.code_edit


async def collect_claude_plan(question: str, project_workspace: str) -> str:
    options = _claude_options(project_workspace, "plan")

    text_parts: list[str] = []
    exit_plan: str | None = None

    async for message in query(prompt=question, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock) and block.name == "ExitPlanMode":
                    plan = block.input.get("plan")
                    if isinstance(plan, str) and plan.strip():
                        exit_plan = plan.strip()
                elif isinstance(block, TextBlock) and block.text.strip():
                    text_parts.append(block.text.strip())

    plan = exit_plan or "\n\n".join(text_parts).strip()
    if not plan:
        raise RuntimeError("Claude Code did not return a usable plan")

    return plan


async def gener_code_plan_by_claude_code(
    state: CodeGenerateInput,
) -> dict[str, Any]:
    question = state.question

    review = state.review or {}
    if review.get("action") == "revise" and review.get("feedback"):
        question = (
            f"{question}\n\n"
            f"用户对上一版计划的修改意见：\n{review['feedback']}\n\n"
            "请根据这个反馈重新生成实现计划。"
        )

    plan = await _run_in_isolated_loop(
        lambda: collect_claude_plan(question, state.project_workspace)
    )

    return {
        "plan": plan,
        "review": {},
    }


def review_plan_node(state: CodeGenerateInput) -> dict[str, Any]:
    review = interrupt(
        {
            "type": "code_plan_review",
            "plan": state.plan,
            "message": "请确认是否执行这个计划。",
            "actions": ["approve", "reject", "revise"],
        }
    )

    return {"review": review}


def route_after_review(state: CodeGenerateInput) -> str:
    review = state.review or {}
    action = review.get("action")

    if action == "approve":
        return f"execute_{state.code_edit}"

    if action == "revise":
        return f"revise_{state.code_edit}"

    return "reject"


async def _execute_claude_code_plan(plan: str, project_workspace: str) -> str:
    options = _claude_options(project_workspace, "acceptEdits")
    prompt = f"""
用户已经批准下面的实现计划，请按计划修改项目代码。

计划：
{plan}
""".strip()

    outputs: list[str] = []
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock) and block.text.strip():
                    outputs.append(block.text.strip())

    return "\n".join(outputs).strip()


async def execute_claude_code_plan(state: CodeGenerateInput) -> dict[str, Any]:
    result = await _run_in_isolated_loop(
        lambda: _execute_claude_code_plan(state.plan, state.project_workspace)
    )

    return {"result": result}


async def git_commit_push_node(state: CodeGenerateInput) -> dict[str, Any]:
    git_result = await git_commit_and_push(
        project_workspace=state.project_workspace,
        commit_message=getattr(
            state,
            "commit_message",
            "feat: apply Claude Code generated changes",
        ),
    )

    return {
        "git_result": git_result,
    }


async def git_commit_and_push(
    project_workspace: str,
    commit_message: str = "feat: apply Claude Code generated changes",
) -> dict[str, Any]:
    inside_repo, _, _ = await run_cmd(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=project_workspace,
    )

    if inside_repo != "true":
        raise RuntimeError(f"{project_workspace} is not a git repository")

    branch, _, _ = await run_cmd(
        ["git", "branch", "--show-current"],
        cwd=project_workspace,
    )

    if not branch:
        raise RuntimeError("Current repository is in detached HEAD state")

    status, _, _ = await run_cmd(
        ["git", "status", "--porcelain"],
        cwd=project_workspace,
    )

    if not status:
        return {
            "status": "no_changes",
            "message": "Claude Code 执行完成，但没有检测到 git 变更。",
        }

    changed_files_output, _, _ = await run_cmd(
        ["git", "diff", "--name-only"],
        cwd=project_workspace,
        check=False,
    )

    untracked_output, _, _ = await run_cmd(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=project_workspace,
        check=False,
    )

    changed_files = [
        line
        for line in changed_files_output.splitlines()
        + untracked_output.splitlines()
        if line.strip()
    ]

    await run_cmd(
        ["git", "add", "-A"],
        cwd=project_workspace,
    )

    staged_status, _, _ = await run_cmd(
        ["git", "diff", "--cached", "--name-status"],
        cwd=project_workspace,
    )

    if not staged_status:
        return {
            "status": "no_staged_changes",
            "message": "检测到 git 变更，但暂存区为空。",
        }

    commit_stdout, commit_stderr, _ = await run_cmd(
        ["git", "commit", "-m", commit_message],
        cwd=project_workspace,
    )

    commit_sha, _, _ = await run_cmd(
        ["git", "rev-parse", "HEAD"],
        cwd=project_workspace,
    )

    upstream, _, upstream_code = await run_cmd(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        cwd=project_workspace,
        check=False,
    )

    if upstream_code == 0 and upstream:
        push_cmd = ["git", "push"]
    else:
        push_cmd = ["git", "push", "-u", "origin", branch]

    push_stdout, push_stderr, _ = await run_cmd(
        push_cmd,
        cwd=project_workspace,
    )

    return {
        "status": "pushed",
        "branch": branch,
        "upstream": upstream or f"origin/{branch}",
        "commit_sha": commit_sha,
        "commit_message": commit_message,
        "changed_files": changed_files,
        "commit_stdout": commit_stdout,
        "commit_stderr": commit_stderr,
        "push_stdout": push_stdout,
        "push_stderr": push_stderr,
    }


def _run_cmd_sync(
    cmd: list[str],
    cwd: str,
    check: bool,
) -> tuple[str, str, int]:
    completed = subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    returncode = completed.returncode

    if check and returncode != 0:
        raise GitCommandError(
            f"Command failed: {' '.join(cmd)}\n"
            f"returncode: {returncode}\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        )

    return stdout, stderr, returncode


async def run_cmd(
    cmd: list[str],
    cwd: str,
    check: bool = True,
) -> tuple[str, str, int]:
    return await asyncio.to_thread(_run_cmd_sync, cmd, cwd, check)
