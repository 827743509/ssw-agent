from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from openclaw_da.config import Settings

logger = logging.getLogger(__name__)


def _parse_args(value: str) -> list[str]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return [part for part in value.split() if part]

    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise ValueError("MCP 参数必须是 JSON 字符串列表或空格分隔的字符串。")
    return parsed


def _load_travel_mcp_tools_sync(settings) -> list[Any]:


    async def _load():
        client = MultiServerMCPClient({
            "12306": {
                "type": "streamable_http",
                "url": "https://mcp.api-inference.modelscope.net/e51e662717c146/mcp"
            }
        })
        client2 = MultiServerMCPClient({
            "amap_maps": {
                "type": "streamable_http",
                "url": "https://mcp.api-inference.modelscope.net/9fd0c66469144c/mcp",
                "env": {
                    "AMAP_MAPS_API_KEY": settings.amap_maps_api_key,
                }
            }
        })
        tools=await client.get_tools()
        tools.extend(await client2.get_tools())
        return tools

    return asyncio.run(_load())


async def load_travel_mcp_tools(settings) -> list[Any]:
    # 避免在 ASGI event loop 里直接执行 shutil.which / os.access
    return await asyncio.to_thread(_load_travel_mcp_tools_sync, settings)








