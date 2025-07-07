"""Main MCP tools for the Open Stocks MCP server."""

from mcp.server.fastmcp import FastMCP

from open_stocks_mcp.logging_config import logger


async def list_available_tools(mcp: FastMCP) -> dict:
    """
    Provides a list of available tools and their descriptions.

    Args:
        mcp: The FastMCP server instance.

    Returns:
        A JSON object containing the list of tools in the result field.
    """
    tool_list: list[dict] = [
        {"name": tool.name, "description": tool.description}
        for tool in mcp.tools.values()
    ]

    logger.info("Successfully listed available tools.")
    return {"result": {"tools": tool_list, "count": len(tool_list)}}
