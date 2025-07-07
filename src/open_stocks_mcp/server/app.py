"""MCP server implementation for Robin Stocks trading"""

import asyncio
import os
import sys

import click
import robin_stocks.robinhood as rh
from dotenv import load_dotenv
from mcp import types
from mcp.server.fastmcp import FastMCP

from open_stocks_mcp.config import ServerConfig, load_config
from open_stocks_mcp.logging_config import logger, setup_logging
from open_stocks_mcp.tools.robinhood_tools import (
    get_account_info,
    get_orders,
    get_portfolio,
)

# Load environment variables from .env file
load_dotenv()


def create_mcp_server(config: ServerConfig | None = None) -> FastMCP:
    """Create and configure the MCP server instance"""
    if config is None:
        config = load_config()

    setup_logging(config)
    server = FastMCP(config.name)
    register_tools(server)
    return server


def register_tools(mcp_server: FastMCP) -> None:
    """Register all MCP tools with the server"""

    @mcp_server.tool()
    async def account_info() -> types.TextContent:
        """Gets basic Robinhood account information."""
        return await get_account_info()

    @mcp_server.tool()
    async def portfolio() -> types.TextContent:
        """Provides a high-level overview of the portfolio."""
        return await get_portfolio()

    @mcp_server.tool()
    async def orders() -> types.TextContent:
        """Retrieves a list of recent order history and their statuses."""
        return await get_orders()


def attempt_login(username, password):
    """
    Attempt to log in to Robinhood.

    This function will prompt for MFA if required by the Robinhood API.
    It verifies success by fetching the user profile.
    """
    try:
        logger.info(f"Attempting login for user: {username}")
        # Let robin-stocks handle the MFA prompt internally
        rh.login(
            username=username,
            password=password,
            store_session=True,
        )

        # Verify login by making a test API call
        user_profile = rh.load_user_profile()
        if user_profile:
            logger.info(f"✅ Successfully logged into Robinhood for user: {username}")
        else:
            logger.error("❌ Login failed: Could not retrieve user profile after login.")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ An unexpected error occurred during login: {e}")
        sys.exit(1)


@click.command()
@click.option("--port", default=3001, help="Port to listen on for SSE")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport type (stdio or sse)",
)
@click.option("--username", help="Robinhood username.", default=os.getenv("ROBINHOOD_USERNAME"))
@click.option("--password", help="Robinhood password.", default=os.getenv("ROBINHOOD_PASSWORD"))
def main(port: int, transport: str, username, password) -> int:
    """Run the server with specified transport and handle authentication."""
    if not username:
        username = click.prompt("Please enter your Robinhood username")
    if not password:
        password = click.prompt("Please enter your Robinhood password", hide_input=True)

    # The login function will now handle MFA prompts internally when needed.
    attempt_login(username, password)

    server = create_mcp_server()

    try:
        if transport == "stdio":
            asyncio.run(server.run_stdio_async())
        else:
            server.settings.port = port
            asyncio.run(server.run_sse_async())
        return 0
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        rh.logout()
        return 0
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
