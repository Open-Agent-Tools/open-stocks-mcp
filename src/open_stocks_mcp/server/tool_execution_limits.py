"""MCP tool execution deadline enforcement."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import mcp.types
from mcp.server.fastmcp import FastMCP

_WRAPPER_ATTR = "_tool_execution_limit_installed"


def install_tool_execution_limit(mcp_server: FastMCP, timeout_seconds: float) -> None:
    """Wrap call_tool to apply a per-call asyncio deadline.

    Idempotent: calling this more than once does not stack wrappers.
    """
    if getattr(mcp_server, _WRAPPER_ATTR, False):
        return

    original_call_tool = mcp_server.call_tool

    async def _bounded_call_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
        try:
            return await asyncio.wait_for(
                original_call_tool(tool_name, arguments),
                timeout=timeout_seconds,
            )
        except TimeoutError:
            error_data = {
                "status": "error",
                "error_type": "ToolExecutionTimeout",
                "failure_class": "timeout",
                "tool": tool_name,
                "timeout_seconds": timeout_seconds,
                "error": (
                    f"Tool '{tool_name}' exceeded the "
                    f"{timeout_seconds}s execution limit"
                ),
            }
            return mcp.types.CallToolResult(
                content=[
                    mcp.types.TextContent(
                        type="text",
                        text=json.dumps(error_data),
                    )
                ],
                isError=True,
            )

    mcp_server.call_tool = _bounded_call_tool  # type: ignore[assignment]
    setattr(mcp_server, _WRAPPER_ATTR, True)
