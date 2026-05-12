# map_agent.py
import asyncio
from pathlib import Path

from deepagents import create_deep_agent, register_harness_profile, HarnessProfile, GeneralPurposeSubagentProfile
from deepagents.backends import FilesystemBackend
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI


from openclaw_da.config import get_settings
from openclaw_da.subagents.map_assistant.tool.mcp_tools import load_travel_mcp_tools

_graph_cache = None
_graph_lock = asyncio.Lock()
settings = get_settings()
BASE_DIR = Path(__file__).resolve().parents[4]
PROJECT_ROOT = Path(r"D:\project\openclaw-deepagents").resolve()

backend = FilesystemBackend(
    root_dir=str(PROJECT_ROOT),
    virtual_mode=True,
)
async def agent():
  global _graph_cache
  if _graph_cache is not None:
      return _graph_cache
  llm = ChatOpenAI(
    model=settings.kimi_model,
    api_key=settings.moonshot_api_key,
    base_url=settings.moonshot_base_url,
    extra_body={
      "thinking": {
        "type": "disabled"
      }
    },
  )
  register_harness_profile(
    "openai:" + settings.openclaw_model,
    HarnessProfile(
      # 替换 DeepAgents 默认基础系统提示词。
      base_system_prompt="""
      你是百度网盘助手,只能做和百度网盘相关的文件操作。
      """,
      # 隐藏文件和沙箱相关工具。
      excluded_tools=frozenset(
        {
          "write_file",
          "edit_file",
        }
      ),
      # 关闭默认 general-purpose 子 Agent，只保留显式定义的子 Agent。
      general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
    ),
  )
  _graph_cache=create_deep_agent(
    model=llm,
    backend = backend,
    skills=["data/skills/skills_baidu_drive/"],
    system_prompt=(
      """你是百度网盘助手。
        你拥有百度网盘相关 skill。
        根据说明执行对应的bdpan命令
        """
    ),
  )
  return _graph_cache
