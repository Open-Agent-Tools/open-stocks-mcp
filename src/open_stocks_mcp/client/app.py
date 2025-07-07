"""MCP client implementation for Robin Stocks tools"""

import asyncio

import click
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent


async def call_tool(tool_name: str, arguments: dict[str, str] | None = None) -> str:
    """
    Call a tool on the MCP server and get the response.

    Args:
        tool_name: The name of the tool to call
        arguments: Optional arguments for the tool

    Returns:
        The response from the server
    """
    # Create server parameters for stdio connection
    server_params = StdioServerParameters(
        command="open-stocks-mcp-server",  # Use the installed script
        args=[],  # No additional args needed
        env=None,  # Optional environment variables
    )

    async with (
        stdio_client(server_params) as (read, write),
        ClientSession(read, write) as session,
    ):
        # Initialize the connection
        await session.initialize()

        # Call the specified tool
        result = await session.call_tool(tool_name, arguments=arguments or {})

        # Extract text from the result content
        if result.content and len(result.content) > 0:
            first_content = result.content[0]
            if isinstance(first_content, TextContent):
                return first_content.text
        return str(result)


@click.command()
@click.argument("message", type=str)
def main(message: str) -> None:
    """Call a tool on the MCP server.

    Message format: 'tool_name' or 'tool_name arg1=value1 arg2=value2'

    Examples:
        get_portfolio
        get_stock_orders
        get_stock_orders status=pending
    """
    # Parse the message to extract tool name and arguments
    parts = message.split()
    tool_name = parts[0]

    # Parse arguments if provided
    arguments = {}
    for part in parts[1:]:
        if "=" in part:
            key, value = part.split("=", 1)
            arguments[key] = value

    response = asyncio.run(call_tool(tool_name, arguments))
    print(response)


if __name__ == "__main__":
    main()
