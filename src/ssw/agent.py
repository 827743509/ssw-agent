from __future__ import annotations

from deepagents import (
    GeneralPurposeSubagentProfile,
    HarnessProfile,
    create_deep_agent,
    register_harness_profile, AsyncSubAgent,
)
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from ssw.config import get_settings
from ssw.mcp_tools import _load_mcp_tools_by_name

from ssw.schemas import ExtractResult


load_dotenv()

SYSTEM_PROMPT = """
你是主控调度 Agent。你负责分析用户请求、规划步骤、分配给子 Agent，并最终汇总结论。

工作要求：
- 面向用户的回复使用简洁中文。
- 涉及发送邮件、创建日程等敏感动作时，必须等待人工审批或明确配置允许。
"""

settings = get_settings()

workspace = settings.openclaw_workspace.resolve()
data_dir = settings.openclaw_data_dir.resolve()
workspace.mkdir(parents=True, exist_ok=True)
data_dir.mkdir(parents=True, exist_ok=True)

# ttl_config = {
#     "default_ttl": 60 * 24 * 7,  # 7 天，单位为分钟
#     "refresh_on_read": True,
# }

# _checkpointer_cm = RedisSaver.from_conn_string(settings.redis_url, ttl=ttl_config)
# checkpointer = _checkpointer_cm.__enter__()
# checkpointer.setup()

tools = []
tools.extend(_load_mcp_tools_by_name('ssw'));
subagents = [

]

llm = ChatOpenAI(
    model=settings.openclaw_model,
    api_key=settings.dashscope_api_key,
    base_url=settings.dashscope_base_url,
)

# 注册一个精简 profile，限制主 Agent 只做规划、分派和汇总。
register_harness_profile(
    "openai:" + settings.openclaw_model,
    HarnessProfile(
        # 替换 DeepAgents 默认基础系统提示词。
        base_system_prompt="""
    你是一个主控规划 Agent，负责拆解任务、制定计划、分发子任务并汇总结论。
    你只做三类事情：
    1. 使用 write_todos 维护任务计划；
    2. 使用 task 把子任务分发给合适的子 Agent；
    3. 根据子 Agent 返回的结果，汇总成最终答案。



    规则：
    - 复杂任务必须先规划，再分发。
    - 不要自己执行专业任务，优先交给对应子 Agent。
    - 不要读写文件。
    - 不要使用命令行。
    - 子 Agent 返回结果后，你负责判断是否还需要继续分发或汇总。
    """,
        # 隐藏文件和沙箱相关工具。
        excluded_tools=frozenset(
            {
                "ls",
                "read_file",
                "write_file",
                "edit_file",
                "execute",
                "glob",
                "grep",
            }
        ),
        # 关闭默认 general-purpose 子 Agent，只保留显式定义的子 Agent。
        general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
    ),
)

agent = create_deep_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
    skills=[],
    subagents=subagents,
    interrupt_on={
    },
    # checkpointer=checkpointer,
    # response_format=ExtractResult,
    name="ssw-agent",
)


