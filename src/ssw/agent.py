from __future__ import annotations

from pathlib import Path
from ssw.llm import build_llm
from deepagents import (
    GeneralPurposeSubagentProfile,
    HarnessProfile,
    create_deep_agent,
    register_harness_profile, AsyncSubAgent,
)
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from ssw.config import get_settings


from ssw.subagents.text_to_sql import text_to_sql_subagent


load_dotenv()

SYSTEM_PROMPT = """
    你是一个主控规划 Agent，负责拆解任务、制定计划、分发子任务并汇总结论。
    你只做三类事情：
    1. 使用 write_todos 维护任务计划；
    2. 使用 task 把子任务分发给合适的子 Agent；
    3. 根据子 Agent 返回的结果，汇总成最终答案。
    4. 将用户问题翻译成调用子任务的参数
    规则：
    - 复杂任务必须先规划，再分发。
    - 不要自己执行专业任务，优先交给对应子 Agent。
    - 不要读写文件。
    - 不要使用命令行。
    - 子 Agent 返回结果后，你负责判断是否还需要继续分发或汇总。
    - 生成SQL相关任务直接调用text-to-sql不要拆解任务。
    """

settings = get_settings()

workspace = Path(settings.ssw_workspace).resolve()
data_dir  = Path(settings.ssw_data_dir).resolve()
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

subagents = [
    text_to_sql_subagent,
]

llm =build_llm()


agent = create_deep_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
    skills=[],
    subagents=subagents,
    interrupt_on={
    },
    # checkpointer=checkpointer,
    name="ssw-agent",
)



