"""MCP client for tool-calling skills. Supports SSE and streamable HTTP transports."""

from __future__ import annotations

import json
import re
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

from telos.provider import ToolDefinition, ToolResult


@dataclass
class McpContext:
    """Holds connected MCP sessions and their tools."""

    tools: list[ToolDefinition]
    _tool_to_session: dict = field(default_factory=dict)

    async def call_tool(self, name: str, arguments: dict) -> ToolResult:
        """Call a tool by name, dispatching to the correct MCP session."""
        session = self._tool_to_session.get(name)
        if session is None:
            return ToolResult(
                tool_call_id="",
                content=f"Unknown tool: {name}",
                is_error=True,
            )
        result = await session.call_tool(name, arguments)
        # Extract text content from the result
        content = ""
        is_error = bool(getattr(result, "isError", False))
        if result.content:
            parts = []
            for block in result.content:
                if hasattr(block, "text"):
                    parts.append(block.text)
            content = "\n".join(parts)
        return ToolResult(tool_call_id="", content=content, is_error=is_error)


def load_mcp_config(path: Path) -> dict:
    """Parse an mcp.json file and return the config dict."""
    return json.loads(path.read_text())


def _interpolate_env(value: str, env: dict[str, str]) -> str:
    """Replace ${VAR_NAME} placeholders with values from env."""

    def replacer(match: re.Match) -> str:
        return env.get(match.group(1), "")

    return re.sub(r"\$\{(\w+)\}", replacer, value)


@asynccontextmanager
async def connect_mcp_servers(config_path: Path, env: dict[str, str]):
    """Connect to all MCP servers defined in config. Yields an McpContext.

    Supports transport types:
      - "sse": SSE transport (legacy)
      - "http" / "streamable-http": Streamable HTTP transport
      - Default (no type): uses streamable HTTP
    """
    from mcp import ClientSession

    config = load_mcp_config(config_path)
    servers = config.get("mcpServers", {})

    tools: list[ToolDefinition] = []
    tool_to_session: dict[str, ClientSession] = {}

    async with AsyncExitStack() as stack:
        for _name, server_config in servers.items():
            url = server_config["url"]
            transport_type = server_config.get("type", "http")
            headers: dict[str, str] = {}
            for key, value in server_config.get("headers", {}).items():
                headers[key] = _interpolate_env(value, env)

            if transport_type == "sse":
                from mcp.client.sse import sse_client

                read, write = await stack.enter_async_context(
                    sse_client(url=url, headers=headers)
                )
            else:
                # streamable HTTP (default)
                from mcp.client.streamable_http import streamablehttp_client

                read, write, _ = await stack.enter_async_context(
                    streamablehttp_client(url=url, headers=headers)
                )

            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()

            server_tools = await session.list_tools()
            for tool in server_tools.tools:
                td = ToolDefinition(
                    name=tool.name,
                    description=tool.description or "",
                    input_schema=tool.inputSchema,
                )
                tools.append(td)
                tool_to_session[tool.name] = session

        yield McpContext(tools=tools, _tool_to_session=tool_to_session)
