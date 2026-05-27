"""Integration coverage for production MCP tool schemas."""

from typing import Any

import pytest

from open_stocks_mcp.server.app import mcp as production_mcp

pytestmark = [pytest.mark.integration, pytest.mark.journey_system]


@pytest.mark.asyncio
async def test_production_stock_price_tool_schema_includes_symbol() -> None:
    tools = await production_mcp.list_tools()
    stock_price_tool = next(tool for tool in tools if tool.name == "stock_price")
    schema: dict[str, Any] = (
        stock_price_tool.inputSchema.model_dump()
        if hasattr(stock_price_tool.inputSchema, "model_dump")
        else stock_price_tool.inputSchema
    )
    assert schema["properties"]["symbol"]["type"] == "string"
