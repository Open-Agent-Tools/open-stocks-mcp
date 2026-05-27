"""Tests for MCP tool execution deadline enforcement."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import mcp.types
import pytest
from mcp.server.fastmcp import FastMCP

from open_stocks_mcp.server.tool_execution_limits import install_tool_execution_limit


@pytest.fixture
def slow_mcp_server() -> FastMCP:
    server = FastMCP("SlowTest")

    @server.tool()
    async def account_info() -> dict[str, Any]:
        await asyncio.sleep(10.0)
        return {"result": {"status": "ok"}}

    return server


@pytest.mark.unit
@pytest.mark.journey_system
async def test_slow_tool_returns_structured_timeout_error(
    slow_mcp_server: FastMCP,
) -> None:
    install_tool_execution_limit(slow_mcp_server, timeout_seconds=0.05)

    result = await slow_mcp_server.call_tool("account_info", {})

    assert result.isError is True
    assert len(result.content) == 1
    data = json.loads(result.content[0].text)
    assert data["error_type"] == "ToolExecutionTimeout"
    assert data["tool"] == "account_info"
    assert data["timeout_seconds"] == 0.05
    assert data["status"] == "error"
    assert data["failure_class"] == "timeout"


@pytest.mark.unit
@pytest.mark.journey_system
async def test_install_is_idempotent(slow_mcp_server: FastMCP) -> None:
    install_tool_execution_limit(slow_mcp_server, timeout_seconds=0.05)
    install_tool_execution_limit(slow_mcp_server, timeout_seconds=0.05)

    result = await slow_mcp_server.call_tool("account_info", {})

    assert result.isError is True
    content_text = result.content[0].text
    data = json.loads(content_text)
    # Exactly one timeout error, not a nested/doubled result
    assert data["error_type"] == "ToolExecutionTimeout"
    # The text should parse as flat dict, not nested
    assert "content" not in data


@pytest.mark.unit
@pytest.mark.journey_system
async def test_reinstall_updates_timeout_value(slow_mcp_server: FastMCP) -> None:
    install_tool_execution_limit(slow_mcp_server, timeout_seconds=20.0)
    install_tool_execution_limit(slow_mcp_server, timeout_seconds=0.05)

    result = await slow_mcp_server.call_tool("account_info", {})

    assert result.isError is True
    data = json.loads(result.content[0].text)
    assert data["error_type"] == "ToolExecutionTimeout"
    assert data["timeout_seconds"] == 0.05


@pytest.mark.unit
@pytest.mark.journey_system
async def test_fast_tool_completes_normally() -> None:
    server = FastMCP("FastTest")

    @server.tool()
    async def account_info() -> dict[str, Any]:
        return {"result": {"status": "ok"}}

    install_tool_execution_limit(server, timeout_seconds=5.0)

    result = await server.call_tool("account_info", {})

    # Fast tool returns the normal call_tool result (not a timeout CallToolResult)
    assert not (isinstance(result, mcp.types.CallToolResult) and result.isError is True)
