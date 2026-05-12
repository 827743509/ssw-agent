from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from openclaw_da.config import Settings

logger = logging.getLogger(__name__)

TRAVEL_MCP_CONNECTIONS = {
    "railway_12306": {
        "transport": "streamable_http",
        "url": "https://mcp.api-inference.modelscope.net/e51e662717c146/mcp",
    },
    "amap_maps": {
        "transport": "streamable_http",
        "url": "https://mcp.api-inference.modelscope.net/99425a4337f142/mcp",
    },
}


def _log_mcp_load_error(name: str, error: BaseException) -> None:
    logger.warning(
        "加载 %s MCP 工具失败，已跳过：%s: %s",
        name,
        type(error).__name__,
        error,
    )
    logger.debug("加载 %s MCP 工具失败详情", name, exc_info=True)


def _parse_args(value: str) -> list[str]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return [part for part in value.split() if part]

    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise ValueError("MCP 参数必须是 JSON 字符串列表或空格分隔的字符串。")
    return parsed


def _load_travel_mcp_tools_sync(settings: Settings) -> list[Any]:
    async def _load():
        tools = []
        for name, connection in TRAVEL_MCP_CONNECTIONS.items():
            client = MultiServerMCPClient({name: connection})
            try:
                tools.extend(await client.get_tools())
            except BaseExceptionGroup as exc:
                _log_mcp_load_error(name, exc)
            except Exception as exc:
                _log_mcp_load_error(name, exc)

        if not tools:
            logger.warning("未加载到任何出行 MCP 工具，map_assistant 将仅使用模型能力回答。")
        return tools

    return asyncio.run(_load())


async def load_travel_mcp_tools(settings: Settings) -> list[Any]:
    # 避免在 ASGI event loop 里直接执行 shutil.which / os.access
    return await asyncio.to_thread(_load_travel_mcp_tools_sync, settings)

