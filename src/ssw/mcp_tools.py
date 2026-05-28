import asyncio
from functools import lru_cache
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

TRAVEL_MCP_CONNECTIONS = {
    "ssw": {
        "transport": "streamable_http",
        "url": "http://127.0.0.1:8080/ssw-mcp-server/mcp",
    },
}
@lru_cache(maxsize=20)
def _load_mcp_tools_by_name(name:str ) -> list[Any]:
    client = MultiServerMCPClient({name: TRAVEL_MCP_CONNECTIONS[name]})
    return asyncio.run(client.get_tools())
