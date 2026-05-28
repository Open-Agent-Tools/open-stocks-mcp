"""Broker availability filter for MCP tool dispatch.

Wraps FastMCP's call_tool and list_tools to enforce ENABLED_BROKERS at
runtime: tools for disabled brokers are hidden from list_tools and return a
descriptive error when called.
"""

from __future__ import annotations

import json
from typing import Any

import mcp.types
from mcp.server.fastmcp import FastMCP

_WRAPPER_ATTR = "_broker_filter_installed"
_ENABLED_ATTR = "_broker_filter_enabled_brokers"

# Tools that operate on server state rather than a specific broker and should
# always remain accessible regardless of ENABLED_BROKERS.
_BROKER_AGNOSTIC_TOOLS: frozenset[str] = frozenset(
    {
        "list_tools",
        "session_status",
        "broker_status",
        "list_brokers",
        "rate_limit_status",
        "metrics_summary",
        "aggregated_portfolio",
        "broker_comparison",
        "health_check",
    }
)


def _tool_broker(tool_name: str) -> str | None:
    """Return the broker name required by *tool_name*, or ``None`` if agnostic.

    Mapping rules (evaluated in order):
    1. Tools in ``_BROKER_AGNOSTIC_TOOLS`` → no broker required.
    2. Tool name contains ``"schwab"`` → requires ``"schwab"``.
    3. Everything else → requires ``"robinhood"``.
    """
    if tool_name in _BROKER_AGNOSTIC_TOOLS:
        return None
    if "schwab" in tool_name:
        return "schwab"
    return "robinhood"


def install_broker_filter(mcp_server: FastMCP, enabled_brokers: list[str]) -> None:
    """Wrap *mcp_server* to enforce ``ENABLED_BROKERS`` at dispatch time.

    * ``call_tool``: tools for a disabled broker return a structured error
      instead of executing.
    * ``list_tools``: tools for disabled brokers are omitted from the listing.

    Idempotent — re-calling with a new *enabled_brokers* list updates the
    active set without stacking additional wrappers.
    """
    if getattr(mcp_server, _WRAPPER_ATTR, False):
        setattr(mcp_server, _ENABLED_ATTR, list(enabled_brokers))
        return

    setattr(mcp_server, _ENABLED_ATTR, list(enabled_brokers))
    original_call_tool = mcp_server.call_tool
    original_list_tools = mcp_server.list_tools

    async def _filtered_call_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
        active_enabled: list[str] = getattr(mcp_server, _ENABLED_ATTR, ["robinhood"])
        required = _tool_broker(tool_name)
        if required is not None and required not in active_enabled:
            error_data = {
                "status": "error",
                "error": (
                    f"Tool '{tool_name}' requires the '{required}' broker, "
                    f"which is not enabled. "
                    f"Set ENABLED_BROKERS to include '{required}' and restart the server. "
                    f"Currently enabled: {active_enabled}."
                ),
            }
            return mcp.types.CallToolResult(
                content=[
                    mcp.types.TextContent(type="text", text=json.dumps(error_data))
                ],
                isError=True,
            )
        return await original_call_tool(tool_name, arguments)

    async def _filtered_list_tools() -> list[mcp.types.Tool]:
        active_enabled: list[str] = getattr(mcp_server, _ENABLED_ATTR, ["robinhood"])
        all_tools: list[mcp.types.Tool] = await original_list_tools()
        return [
            t
            for t in all_tools
            if (req := _tool_broker(t.name)) is None or req in active_enabled
        ]

    mcp_server.call_tool = _filtered_call_tool  # type: ignore[assignment]
    mcp_server.list_tools = _filtered_list_tools  # type: ignore[method-assign]
    setattr(mcp_server, _WRAPPER_ATTR, True)
