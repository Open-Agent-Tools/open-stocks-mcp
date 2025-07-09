"""MCP server implementation for Robin Stocks trading"""

import asyncio
import os
import sys

import click
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from open_stocks_mcp.config import ServerConfig, load_config
from open_stocks_mcp.logging_config import logger, setup_logging
from open_stocks_mcp.monitoring import MonitoredTool, get_metrics_collector
from open_stocks_mcp.tools.rate_limiter import get_rate_limiter
from open_stocks_mcp.tools.robinhood_account_tools import (
    get_account_details,
    get_account_info,
    get_portfolio,
    get_portfolio_history,
    get_positions,
)
from open_stocks_mcp.tools.robinhood_advanced_portfolio_tools import (
    get_build_holdings,
    get_build_user_profile,
    get_day_trades,
)
from open_stocks_mcp.tools.robinhood_dividend_tools import (
    get_dividends,
    get_dividends_by_instrument,
    get_interest_payments,
    get_stock_loan_payments,
    get_total_dividends,
)
from open_stocks_mcp.tools.robinhood_market_data_tools import (
    get_stock_earnings,
    get_stock_events,
    get_stock_level2_data,
    get_stock_news,
    get_stock_ratings,
    get_stock_splits,
    get_stocks_by_tag,
    get_top_100,
    get_top_movers,
    get_top_movers_sp500,
)
from open_stocks_mcp.tools.robinhood_order_tools import (
    get_options_orders,
    get_stock_orders,
)
from open_stocks_mcp.tools.robinhood_stock_tools import (
    get_market_hours,
    get_price_history,
    get_stock_info,
    get_stock_price,
    search_stocks,
)
from open_stocks_mcp.tools.robinhood_tools import list_available_tools
from open_stocks_mcp.tools.session_manager import get_session_manager

# Load environment variables from .env file
load_dotenv()

# Create global MCP server instance for Inspector
mcp = FastMCP("Open Stocks MCP")


# Register tools at module level for Inspector
@mcp.tool()
async def list_tools() -> dict:
    """Provides a list of available tools and their descriptions."""
    return await list_available_tools(mcp)


@mcp.tool()
async def account_info() -> dict:
    """Gets basic Robinhood account information."""
    return await get_account_info()


@mcp.tool()
@MonitoredTool("portfolio")
async def portfolio() -> dict:
    """Provides a high-level overview of the portfolio."""
    return await get_portfolio()


@mcp.tool()
@MonitoredTool("stock_orders")
async def stock_orders() -> dict:
    """Retrieves a list of recent stock order history and their statuses."""
    return await get_stock_orders()


@mcp.tool()
async def options_orders() -> dict:
    """Retrieves a list of recent options order history and their statuses."""
    return await get_options_orders()


@mcp.tool()
async def account_details() -> dict:
    """Gets comprehensive account details including buying power and cash balances."""
    return await get_account_details()


@mcp.tool()
async def positions() -> dict:
    """Gets current stock positions with quantities and values."""
    return await get_positions()


@mcp.tool()
async def portfolio_history(span: str = "week") -> dict:
    """Gets historical portfolio performance data.

    Args:
        span: Time span ('day', 'week', 'month', '3month', 'year', '5year', 'all')
    """
    return await get_portfolio_history(span)


# Advanced Portfolio Analytics Tools
@mcp.tool()
async def build_holdings() -> dict:
    """Builds comprehensive holdings with dividend information and performance metrics.

    Returns detailed holdings data including cost basis, equity, dividends, and performance.
    """
    return await get_build_holdings()


@mcp.tool()
async def build_user_profile() -> dict:
    """Builds comprehensive user profile with equity, cash, and dividend totals.

    Returns complete financial profile including total equity, cash balances, and dividend totals.
    """
    return await get_build_user_profile()


@mcp.tool()
async def day_trades() -> dict:
    """Gets pattern day trading information and tracking.

    Returns day trade count, remaining day trades, PDT status, and buying power information.
    """
    return await get_day_trades()


# Session Management Tools
@mcp.tool()
async def session_status() -> dict:
    """Gets current session status and authentication information."""
    session_manager = get_session_manager()
    session_info = session_manager.get_session_info()

    return {"result": {**session_info, "status": "success"}}


@mcp.tool()
async def rate_limit_status() -> dict:
    """Gets current rate limit usage and statistics."""
    rate_limiter = get_rate_limiter()
    stats = rate_limiter.get_stats()

    return {"result": {**stats, "status": "success"}}


# Monitoring Tools
@mcp.tool()
async def metrics_summary() -> dict:
    """Gets comprehensive metrics summary for monitoring."""
    metrics_collector = get_metrics_collector()
    metrics = await metrics_collector.get_metrics()

    return {"result": {**metrics, "status": "success"}}


@mcp.tool()
async def health_check() -> dict:
    """Gets health status of the MCP server."""
    metrics_collector = get_metrics_collector()
    health_status = await metrics_collector.get_health_status()

    return {"result": {**health_status, "status": "success"}}


# Market Data Tools
@mcp.tool()
@MonitoredTool("stock_price")
async def stock_price(symbol: str) -> dict:
    """Gets current stock price and basic metrics.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
    """
    return await get_stock_price(symbol)


@mcp.tool()
async def stock_info(symbol: str) -> dict:
    """Gets detailed company information and fundamentals.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
    """
    return await get_stock_info(symbol)


@mcp.tool()
async def search_stocks_tool(query: str) -> dict:
    """Searches for stocks by symbol or company name.

    Args:
        query: Search query (symbol or company name)
    """
    return await search_stocks(query)


@mcp.tool()
async def market_hours() -> dict:
    """Gets current market hours and status."""
    return await get_market_hours()


@mcp.tool()
async def price_history(symbol: str, period: str = "week") -> dict:
    """Gets historical price data for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
        period: Time period ("day", "week", "month", "3month", "year", "5year")
    """
    return await get_price_history(symbol, period)


# Dividend & Income Tools
@mcp.tool()
async def dividends() -> dict:
    """Gets all dividend payment history for the account."""
    return await get_dividends()


@mcp.tool()
async def total_dividends() -> dict:
    """Gets total dividends received across all time."""
    return await get_total_dividends()


@mcp.tool()
async def dividends_by_instrument(symbol: str) -> dict:
    """Gets dividend history for a specific stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
    """
    return await get_dividends_by_instrument(symbol)


@mcp.tool()
async def interest_payments() -> dict:
    """Gets interest payment history from cash management."""
    return await get_interest_payments()


@mcp.tool()
async def stock_loan_payments() -> dict:
    """Gets stock loan payment history from the stock lending program."""
    return await get_stock_loan_payments()


# Advanced Market Data Tools
@mcp.tool()
async def top_movers_sp500(direction: str = "up") -> dict:
    """Gets top S&P 500 movers for the day.

    Args:
        direction: Direction of movement, either 'up' or 'down' (default: 'up')
    """
    return await get_top_movers_sp500(direction)


@mcp.tool()
async def top_100_stocks() -> dict:
    """Gets top 100 most popular stocks on Robinhood."""
    return await get_top_100()


@mcp.tool()
async def top_movers() -> dict:
    """Gets top 20 movers on Robinhood."""
    return await get_top_movers()


@mcp.tool()
async def stocks_by_tag(tag: str) -> dict:
    """Gets stocks filtered by market category tag.

    Args:
        tag: Market category tag (e.g., 'technology', 'biopharmaceutical', 'upcoming-earnings')
    """
    return await get_stocks_by_tag(tag)


@mcp.tool()
async def stock_ratings(symbol: str) -> dict:
    """Gets analyst ratings for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
    """
    return await get_stock_ratings(symbol)


@mcp.tool()
async def stock_earnings(symbol: str) -> dict:
    """Gets earnings reports for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
    """
    return await get_stock_earnings(symbol)


@mcp.tool()
async def stock_news(symbol: str) -> dict:
    """Gets news stories for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
    """
    return await get_stock_news(symbol)


@mcp.tool()
async def stock_splits(symbol: str) -> dict:
    """Gets stock split history for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
    """
    return await get_stock_splits(symbol)


@mcp.tool()
async def stock_events(symbol: str) -> dict:
    """Gets corporate events for a stock (for owned positions).

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
    """
    return await get_stock_events(symbol)


@mcp.tool()
async def stock_level2_data(symbol: str) -> dict:
    """Gets Level II market data for a stock (Gold subscription required).

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
    """
    return await get_stock_level2_data(symbol)


def create_mcp_server(config: ServerConfig | None = None) -> FastMCP:
    """Create and configure the MCP server instance"""
    if config is None:
        config = load_config()

    setup_logging(config)
    return mcp


def attempt_login(username: str, password: str) -> None:
    """
    Attempt to log in to Robinhood using the session manager.

    It verifies success by fetching the user profile.
    """
    try:
        logger.info(f"Attempting login for user: {username}")

        # Set credentials in session manager
        session_manager = get_session_manager()
        session_manager.set_credentials(username, password)

        # Use asyncio to run the async authentication
        async def do_auth():
            return await session_manager.ensure_authenticated()

        success = asyncio.run(do_auth())

        if success:
            logger.info(f"✅ Successfully logged into Robinhood for user: {username}")
            # Verify by getting session info
            session_info = session_manager.get_session_info()
            logger.info(f"Session info: {session_info}")
        else:
            logger.error("❌ Login failed: Could not authenticate with Robinhood.")
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
@click.option(
    "--username", help="Robinhood username.", default=os.getenv("ROBINHOOD_USERNAME")
)
@click.option(
    "--password", help="Robinhood password.", default=os.getenv("ROBINHOOD_PASSWORD")
)
def main(port: int, transport: str, username: str | None, password: str | None) -> int:
    """Run the server with specified transport and handle authentication."""
    if not username:
        username = click.prompt("Please enter your Robinhood username")
    if not password:
        password = click.prompt("Please enter your Robinhood password", hide_input=True)

    # Perform login with stored session if available
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
        # Use session manager for logout
        session_manager = get_session_manager()
        asyncio.run(session_manager.logout())
        return 0
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
