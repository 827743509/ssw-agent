from deepagents import create_deep_agent, CompiledSubAgent
from deepagents.backends import FilesystemBackend
from pathlib import Path
from ssw.llm import build_llm

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS_PATH = "/src/ssw/subagents/default/skills"

SYSTEM_PROMPT = """
你是一个具备 Skills 能力的智能体。

你的主要职责不是直接回答问题，而是通过发现、选择和执行合适的 Skills 来完成用户任务。

你拥有一个 Skills 库，每个 Skill 都是一个可复用的专业能力模块。
"""


default_agent = create_deep_agent(
    model=build_llm(),
    system_prompt=SYSTEM_PROMPT,
    skills=[SKILLS_PATH],
    backend=FilesystemBackend(root_dir=REPO_ROOT, virtual_mode=True),
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