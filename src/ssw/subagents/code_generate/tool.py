import asyncio
import os

import subprocess
import sys
from claude_agent_sdk import ClaudeAgentOptions, query, AssistantMessage, TextBlock, ToolUseBlock
from langgraph.types import interrupt
from pathlib import Path
from ssw.config import get_settings
from ssw.subagents.code_generate.model import CodeGenerateInput
from typing import Any

settings=get_settings()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

def print_claude_stderr(line: str) -> None:
    print("[claude stderr]", line, end="", file=sys.stderr)
async def create_workspace(state:CodeGenerateInput):
    base_dir = Path(settings.ssw_workspace)
    code_workspace = base_dir / state.project_name
    if not code_workspace.exists():
       await asyncio.to_thread(
            Path(code_workspace).mkdir,
            parents=True,
            exist_ok=True,
        )

       def _run():
           return subprocess.run(["git", "clone", state.url,str(code_workspace)],check=True)
       await asyncio.to_thread(_run)
       subprocess.run(
        ["git", "checkout", state.branch],
        cwd=str(code_workspace),
        check=True
     )
    return {"project_workspace":str(code_workspace)}




def select_coding_ide(code_generate_input:CodeGenerateInput):
    return code_generate_input.code_edit
CLAUDE_CLI_PATH = Path(r"C:\Users\82774\AppData\Roaming\npm\claude.cmd")
PROJECT_DIR = Path(r"D:\project\ssw-agent\workspace\ssw-blog")
async def collect_claude_plan(question: str, project_workspace: str) -> str:
    options = ClaudeAgentOptions(
        cli_path=CLAUDE_CLI_PATH,
        cwd=PROJECT_DIR,
        permission_mode="plan"
    )

    text_parts: list[str] = []
    exit_plan: str | None = None

    async for message in query(
        prompt="把首页标题的new article改为最新文章",
        options=options,
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock) and block.name == "ExitPlanMode":
                    plan = block.input.get("plan")
                    if isinstance(plan, str) and plan.strip():
                        exit_plan = plan.strip()

                elif isinstance(block, TextBlock):
                    if block.text.strip():
                        text_parts.append(block.text.strip())

    # 优先用 ExitPlanMode 的 plan；没有的话再 fallback 到文本块
    plan = exit_plan or "\n\n".join(text_parts).strip()

    if not plan:
        raise RuntimeError("Claude Code 没有返回可用的 plan")

    return plan


async def gener_code_plan_by_claude_code(state:CodeGenerateInput) -> dict[str, Any]:


    question = state.question

    # 用户要求修改计划时，把反馈拼回去让 Claude 重新生成
    review = state.review or {}
    if review.get("action") == "revise" and review.get("feedback"):
        question = (
            f"{question}\n\n"
            f"用户对上一版计划的修改意见：\n{review['feedback']}\n\n"
            "请根据这个反馈重新生成计划。"
        )
    plan=await collect_claude_plan(state.question, state.project_workspace)
    # plan = await asyncio.to_thread(
    #     _run_collect_in_new_loop,
    #     state.question,
    #     state.project_workspace,
    # )

    # 这里只返回 state，不 interrupt
    return {
        "plan": plan,
        "review": {},  # 清掉上一轮 review
    }





def review_plan_node(state: CodeGenerateInput) -> dict[str, Any]:
    # 这里才 interrupt，把 plan 返回给调用方/前端/用户
    review = interrupt(
        {
            "type": "code_plan_review",
            "plan": state.plan,
            "message": "请确认是否执行这个计划",
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




async def execute_claude_code_plan(state: CodeGenerateInput) -> dict[str, Any]:
    # 审批通过后再执行。这里按你的安全策略设置 permission_mode。
    options = ClaudeAgentOptions(
        cli_path=Path(r"C:\Users\82774\AppData\Roaming\npm\claude.cmd"),
        cwd=Path(r"D:\project\ssw-agent\workspace\ssw-blog"),
        permission_mode="acceptEdits"
    )

    prompt = f"""
用户已经批准下面的实现计划，请按计划修改项目代码。

计划：
{state.plan}
""".strip()

    outputs: list[str] = []

    async for message in query(prompt="把首页标题的new article改为最新文章", options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    outputs.append(block.text)

    return {"result": "\n".join(outputs).strip()}




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
    # 确认当前目录在 git 仓库里
    inside_repo, _, _ = await run_cmd(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=project_workspace,
    )

    if inside_repo != "true":
        raise RuntimeError(f"{project_workspace} 不是 git 仓库")

    # 获取当前分支
    branch, _, _ = await run_cmd(
        ["git", "branch", "--show-current"],
        cwd=project_workspace,
    )

    if not branch:
        raise RuntimeError("当前仓库处于 detached HEAD 状态，无法自动 push")

    # 看是否有变更
    status, _, _ = await run_cmd(
        ["git", "status", "--porcelain"],
        cwd=project_workspace,
    )

    if not status:
        return {
            "status": "no_changes",
            "message": "Claude Code 执行完成，但没有检测到 git 变更，因此没有 commit/push",
        }

    # 记录变更文件
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
        line for line in (
            changed_files_output.splitlines() + untracked_output.splitlines()
        )
        if line.strip()
    ]

    # git add
    await run_cmd(
        ["git", "add", "-A"],
        cwd=project_workspace,
    )

    # 确认暂存区是否真的有内容
    staged_status, _, _ = await run_cmd(
        ["git", "diff", "--cached", "--name-status"],
        cwd=project_workspace,
    )

    if not staged_status:
        return {
            "status": "no_staged_changes",
            "message": "检测到工作区变更，但 git add 后暂存区为空，没有 commit/push",
        }

    # commit
    commit_stdout, commit_stderr, _ = await run_cmd(
        ["git", "commit", "-m", commit_message],
        cwd=project_workspace,
    )

    commit_sha, _, _ = await run_cmd(
        ["git", "rev-parse", "HEAD"],
        cwd=project_workspace,
    )

    # 检查当前分支是否有 upstream
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

class GitCommandError(RuntimeError):
    pass

async def run_cmd(
    cmd: list[str],
    cwd: str,
    check: bool = True,
) -> tuple[str, str, int]:
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout_bytes, stderr_bytes = await process.communicate()

    stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
    stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
    returncode = process.returncode

    if check and returncode != 0:
        raise GitCommandError(
            f"命令执行失败: {' '.join(cmd)}\n"
            f"returncode: {returncode}\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        )

    return stdout, stderr, returncode