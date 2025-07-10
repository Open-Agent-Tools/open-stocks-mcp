"""Main MCP tools for the Open Stocks MCP server."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from open_stocks_mcp.logging_config import logger


async def list_available_tools(mcp: FastMCP) -> dict[str, Any]:
    """
    Provides a list of available tools and their descriptions.

    Args:
        mcp: The FastMCP server instance.

    Returns:
        A JSON object containing the list of tools in the result field.
    """
    tools = await mcp.list_tools()
    tool_list: list[dict[str, Any]] = [
        {"name": tool.name, "description": tool.description} for tool in tools
    ]

    logger.info("Successfully listed available tools.")
    return {"result": {"tools": tool_list, "count": len(tool_list)}}
