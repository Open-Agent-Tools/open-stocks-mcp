"""MCP server implementation with Echo tool"""

import asyncio
import sys

import click
from mcp import types
from mcp.server.fastmcp import FastMCP

from open_stocks_mcp.config import ServerConfig, load_config
from open_stocks_mcp.logging_config import logger, setup_logging
from open_stocks_mcp.tools.echo import echo
from open_stocks_mcp.tools.robinhood_tools import (
    login_robinhood,
)


def create_mcp_server(config: ServerConfig | None = None) -> FastMCP:
    """Create and configure the MCP server instance"""
    if config is None:
        config = load_config()

    # Set up logging first
    setup_logging(config)

    server = FastMCP(config.name)

    # Register all tools with the server
    register_tools(server)

    return server


def register_tools(mcp_server: FastMCP) -> None:
    """Register all MCP tools with the server"""

    @mcp_server.tool(
        name="echo",
        description="Echo back the input text with optional case transformation",
    )
    def echo_tool(text: str, transform: str | None = None) -> types.TextContent:
        """Wrapper around the echo tool implementation"""
        return echo(text, transform)

    @mcp_server.tool(
        name="login_robinhood",
        description="Login to Robinhood API with username, password, and SMS MFA code",
    )
    async def login_robinhood_tool(
        username: str, password: str, mfa_code: str
    ) -> types.TextContent:
        """Login to Robinhood API"""
        return await login_robinhood(username, password, mfa_code)


# Create a server instance that can be imported by the MCP CLI
server = create_mcp_server()


@click.command()
@click.option("--port", default=3001, help="Port to listen on for SSE")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport type (stdio or sse)",
)
def main(port: int, transport: str) -> int:
    """Run the server with specified transport."""
    try:
        if transport == "stdio":
            asyncio.run(server.run_stdio_async())
        else:
            server.settings.port = port
            asyncio.run(server.run_sse_async())
        return 0
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
