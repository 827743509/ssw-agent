from deepagents import create_deep_agent, CompiledSubAgent
from deepagents.backends import  LocalShellBackend
from pathlib import Path
from ssw.llm import build_llm

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS_PATH = "/src/ssw/subagents/default/skills"

SYSTEM_PROMPT = f"""
你是一个具备 Skills 能力的智能体。当前工作空间目录为: {REPO_ROOT}

你的主要职责不是直接回答问题，而是通过发现、选择和执行合适的 Skills 来完成用户任务。

你拥有一个 Skills 库，每个 Skill 都是一个可复用的专业能力模块。
重要路径规则：
1. 调用 write_file、read_file、edit_file 等 DeepAgents 文件工具时，继续使用虚拟路径，例如 /tmp/jvm-blog.md。
2. 调用 execute 执行 shell 命令时，如果命令参数需要引用文件路径，必须把虚拟路径转换为宿主机绝对路径。
3. 虚拟路径 /tmp/xxx 对应宿主机路径：{REPO_ROOT.as_posix()}/tmp/xxx。
4. execute 命令中禁止直接使用 /tmp/xxx。
5. Windows 路径在 execute 中统一使用正斜杠格式，例如：{REPO_ROOT.as_posix()}/tmp/jvm-blog.md。
"""


default_agent = create_deep_agent(
    model=build_llm(),
    system_prompt=SYSTEM_PROMPT,
    skills=[SKILLS_PATH],
    backend=LocalShellBackend(root_dir=REPO_ROOT, virtual_mode=True, inherit_env=True),
    name="default-agent",
)

default_subagent: CompiledSubAgent = {
    "name": "default-agent",
    "description": """
    通用Skills执行Agent。
    负责分析用户需求，
    自动发现、选择和组合可用Skills完成任务。
    能够处理跨领域工作流、
    标准操作流程(SOP)执行、
    通用问答以及未匹配到其它专业Agent的请求。
    当无法确定具体负责Agent时优先使用。
    """,
    "runnable": default_agent,
}
