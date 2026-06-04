from functools import lru_cache
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI

from ssw.config import get_settings

settings = get_settings()


@lru_cache(maxsize=1)
def build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.ssw_model,
        api_key=settings.ssw_api_key,
        base_url=settings.ssw_base_url,
        extra_body={
            "thinking": {
                "type": "disabled",
            }
        },
    )


TRAVEL_MCP_CONNECTIONS = {
    "ssw": {
        "transport": "streamable_http",
        "url": "http://127.0.0.1:8080/ssw-mcp-server/mcp",
    },
}


_mcp_tools_cache: dict[str, list[Any]] = {}


async def load_mcp_tools_by_name(name: str) -> list[Any]:
    if name in _mcp_tools_cache:
        return _mcp_tools_cache[name]

    if name not in TRAVEL_MCP_CONNECTIONS:
        raise ValueError(f"Unknown MCP connection: {name}")

    client = MultiServerMCPClient({
        name: TRAVEL_MCP_CONNECTIONS[name],
    })

    tools = await client.get_tools()
    _mcp_tools_cache[name] = tools
    return tools
