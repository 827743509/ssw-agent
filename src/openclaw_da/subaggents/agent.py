# map_agent.py

import os
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient

from .tool.mcp_tools import load_travel_mcp_tools
from ..config import get_settings

settings = get_settings()

amap_tools = load_travel_mcp_tools

llm = ChatOpenAI(
    model=settings.openclaw_model,
    api_key=settings.dashscope_api_key,
    base_url=settings.dashscope_base_url,
)

agent = create_agent(
    model=llm,
    tools=amap_tools,
    system_prompt=(
                "你是中国出行规划助理。"
                "需要路线规划、地理编码、距离、导航、地点或 POI 查询时，使用高德地图 MCP 工具。"
                "需要火车票余票、车次、站点、时刻表或票价查询时，使用 12306 MCP 工具。"
                "查询火车票前，要确认出发城市或车站、到达城市或车站、出行日期；"
                "如果席别、乘客类型、是否只看高铁动车等条件会影响结果，也要一并确认或说明默认假设。"
                "返回结果使用简洁中文，包含可选路线、耗时、费用或票价信息，并明确说明关键假设。"
            ),
)
