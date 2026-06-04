from typing import Any
from langchain_mcp_adapters.client import MultiServerMCPClient


TRAVEL_MCP_CONNECTIONS = {
    "ssw": {
        "transport": "streamable_http",
        "url": "http://127.0.0.1:8080/ssw-mcp-server/mcp",
    },
}


async def load_mcp_tools_by_name(name: str) -> list[Any]:
    if name not in TRAVEL_MCP_CONNECTIONS:
        raise ValueError(f"Unknown MCP connection: {name}")

    client = MultiServerMCPClient({
        name: TRAVEL_MCP_CONNECTIONS[name]
    })

    return await client.get_tools()