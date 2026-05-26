"""MCP server implementation for Robin Stocks trading"""

import asyncio
import os
import sys
from typing import Any

import click
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from open_stocks_mcp.brokers.auth_coordinator import attempt_broker_logins
from open_stocks_mcp.brokers.registry import get_broker_registry
from open_stocks_mcp.brokers.robinhood import RobinhoodBroker
from open_stocks_mcp.brokers.schwab import SchwabBroker
from open_stocks_mcp.config import ServerConfig, load_config
from open_stocks_mcp.logging_config import logger, setup_logging
from open_stocks_mcp.server.tool_helpers import (
    get_broker_status_data,
    get_health_check_data,
    get_list_brokers_data,
    get_list_tools_data,
    get_metrics_summary_data,
    get_rate_limit_status_data,
    get_session_status_data,
)

# Cross-Broker Tools
from open_stocks_mcp.tools.broker_comparison_tools import get_broker_comparison
from open_stocks_mcp.tools.cross_broker_tools import get_aggregated_portfolio
from open_stocks_mcp.tools.market.earnings import (
    get_stock_earnings,
    get_stock_events,
    get_stock_splits,
)
from open_stocks_mcp.tools.market.level2 import get_stock_level2_data
from open_stocks_mcp.tools.market.movers import (
    get_stocks_by_tag,
    get_top_100,
    get_top_movers,
    get_top_movers_sp500,
)
from open_stocks_mcp.tools.market.news import get_stock_news
from open_stocks_mcp.tools.market.ratings import get_stock_ratings
from open_stocks_mcp.tools.options import (
    find_tradable_options,
    get_aggregate_positions,
    get_all_option_positions,
    get_open_option_positions,
    get_open_option_positions_with_details,
    get_options_chains,
)
from open_stocks_mcp.tools.options.market_data import (
    get_option_historicals,
    get_option_market_data,
)
from open_stocks_mcp.tools.rate_limiter import configure_global_rate_limiter
from open_stocks_mcp.tools.robinhood_account_feature_summary_tools import (
    get_account_features,
)
from open_stocks_mcp.tools.robinhood_account_tools import (
    get_account_details,
    get_account_info,
    get_portfolio,
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
from open_stocks_mcp.tools.robinhood_margin_tools import (
    get_margin_calls,
    get_margin_interest,
)
from open_stocks_mcp.tools.robinhood_notification_tools import (
    get_latest_notification,
    get_notifications,
)
from open_stocks_mcp.tools.robinhood_order_tools import (
    get_options_orders,
    get_stock_orders,
)
from open_stocks_mcp.tools.robinhood_referral_tools import get_referrals
from open_stocks_mcp.tools.robinhood_stock_tools import (
    find_instrument_data,
    get_instruments_by_symbols,
    get_market_hours,
    get_price_history,
    get_pricebook_by_symbol,
    get_stock_info,
    get_stock_price,
    get_stock_quote_by_id,
    search_stocks,
)
from open_stocks_mcp.tools.robinhood_subscription_tools import get_subscription_fees

# Phase 7: Trading Capabilities Tools
from open_stocks_mcp.tools.robinhood_trading_tools import (
    cancel_all_option_orders,
    cancel_all_stock_orders,
    cancel_option_order,
    cancel_stock_order,
    get_all_open_option_orders,
    get_all_open_stock_orders,
    # order_buy_fractional_by_price,  # DEPRECATED
    order_buy_limit,
    order_buy_market,
    order_buy_option_limit,
    # order_buy_stop_loss,  # DEPRECATED
    # order_buy_trailing_stop,  # DEPRECATED
    order_option_credit_spread,
    order_option_debit_spread,
    order_sell_limit,
    order_sell_market,
    order_sell_option_limit,
    order_sell_stop_loss,
    # order_sell_trailing_stop,  # DEPRECATED
)
from open_stocks_mcp.tools.robinhood_user_profile_tools import (
    get_account_profile,
    get_account_settings,
    get_basic_profile,
    get_complete_profile,
    get_investment_profile,
    get_security_profile,
    get_user_profile,
)

# Schwab Tools
from open_stocks_mcp.tools.schwab_account_tools import (
    build_schwab_user_profile,
    get_schwab_account,
    get_schwab_account_balances,
    get_schwab_account_numbers,
    get_schwab_accounts,
    get_schwab_all_account_data,
    get_schwab_portfolio,
    get_schwab_user_preferences,
)
from open_stocks_mcp.tools.schwab_account_tools import (
    schwab_check_margin_status as schwab_check_margin_status_impl,
)
from open_stocks_mcp.tools.schwab_account_tools import (
    schwab_get_margin_interest as schwab_get_margin_interest_impl,
)
from open_stocks_mcp.tools.schwab_market_tools import (
    get_schwab_instrument,
    get_schwab_instrument_by_cusip,
    get_schwab_market_hours,
    get_schwab_movers,
    get_schwab_movers_sp500,
    get_schwab_price_history,
    get_schwab_quote,
    get_schwab_quotes,
    search_schwab_instruments,
)
from open_stocks_mcp.tools.schwab_options_tools import (
    get_schwab_option_chain,
    get_schwab_option_chain_by_expiration,
    get_schwab_option_expirations,
    get_schwab_options_positions,
)
from open_stocks_mcp.tools.schwab_options_tools import (
    schwab_find_tradable_options as _schwab_find_tradable_options_impl,
)
from open_stocks_mcp.tools.schwab_options_tools import (
    schwab_get_open_option_orders as _schwab_get_open_option_orders_impl,
)
from open_stocks_mcp.tools.schwab_options_tools import (
    schwab_option_buy_to_open as _schwab_option_buy_to_open_impl,
)
from open_stocks_mcp.tools.schwab_options_tools import (
    schwab_option_sell_to_close as _schwab_option_sell_to_close_impl,
)
from open_stocks_mcp.tools.schwab_payment_tools import (
    schwab_get_dividends as _schwab_get_dividends_impl,
)
from open_stocks_mcp.tools.schwab_payment_tools import (
    schwab_get_dividends_by_symbol as _schwab_get_dividends_by_symbol_impl,
)
from open_stocks_mcp.tools.schwab_payment_tools import (
    schwab_get_interest_payments as _schwab_get_interest_payments_impl,
)
from open_stocks_mcp.tools.schwab_payment_tools import (
    schwab_get_stock_loan_payments as _schwab_get_stock_loan_payments_impl,
)
from open_stocks_mcp.tools.schwab_payment_tools import (
    schwab_get_total_dividends as _schwab_get_total_dividends_impl,
)
from open_stocks_mcp.tools.schwab_portfolio_tools import (
    get_schwab_aggregate_positions,
    get_schwab_all_option_positions,
    get_schwab_build_holdings,
    get_schwab_day_trades,
    get_schwab_open_option_positions,
)
from open_stocks_mcp.tools.schwab_streaming_tools import (
    schwab_stream_account_activity as _schwab_stream_account_activity_impl,
)
from open_stocks_mcp.tools.schwab_streaming_tools import (
    schwab_stream_level2 as _schwab_stream_level2_impl,
)
from open_stocks_mcp.tools.schwab_streaming_tools import (
    schwab_stream_option_quotes as _schwab_stream_option_quotes_impl,
)
from open_stocks_mcp.tools.schwab_streaming_tools import (
    schwab_stream_quotes as _schwab_stream_quotes_impl,
)
from open_stocks_mcp.tools.schwab_trading_tools import (
    cancel_schwab_order,
    get_schwab_order_by_id,
    get_schwab_orders,
    get_schwab_transaction,
    place_schwab_order,
    schwab_buy_limit,
    schwab_buy_market,
    schwab_get_transactions,
    schwab_get_transactions_by_date,
    schwab_sell_limit,
    schwab_sell_market,
)
from open_stocks_mcp.tools.schwab_trading_tools import (
    schwab_cancel_all_option_orders as _schwab_cancel_all_option_orders,
)
from open_stocks_mcp.tools.schwab_trading_tools import (
    schwab_cancel_all_stock_orders as _schwab_cancel_all_stock_orders,
)
from open_stocks_mcp.tools.schwab_trading_tools import (
    schwab_cancel_option_order as _schwab_cancel_option_order,
)
from open_stocks_mcp.tools.schwab_trading_tools import (
    schwab_get_open_stock_orders as _schwab_get_open_stock_orders,
)
from open_stocks_mcp.tools.schwab_trading_tools import (
    schwab_order_buy_option_limit as _schwab_order_buy_option_limit,
)
from open_stocks_mcp.tools.schwab_trading_tools import (
    schwab_order_option_credit_spread as _schwab_order_option_credit_spread,
)
from open_stocks_mcp.tools.schwab_trading_tools import (
    schwab_order_option_debit_spread as _schwab_order_option_debit_spread,
)
from open_stocks_mcp.tools.schwab_trading_tools import (
    schwab_order_sell_option_limit as _schwab_order_sell_option_limit,
)
from open_stocks_mcp.tools.schwab_trading_tools import (
    schwab_order_sell_stop as _schwab_order_sell_stop,
)
from open_stocks_mcp.tools.schwab_trading_tools import (
    schwab_replace_order as _schwab_replace_order,
)
from open_stocks_mcp.tools.session_manager import get_session_manager
from open_stocks_mcp.tools.stocks import (
    find_instrument_data,
    get_instruments_by_symbols,
    get_market_hours,
    get_price_history,
    get_pricebook_by_symbol,
    get_stock_info,
    get_stock_price,
    get_stock_quote_by_id,
    search_stocks,
)
from open_stocks_mcp.tools.unified_watchlist_tools import (
    add_symbols_to_unified_watchlist,
    get_unified_watchlist_by_name,
    get_unified_watchlists,
    remove_symbols_from_unified_watchlist,
)
from open_stocks_mcp.tools.watchlists.read import (
    get_all_watchlists,
    get_watchlist_by_name,
    get_watchlist_performance,
)
from open_stocks_mcp.tools.watchlists.write import (
    add_symbols_to_watchlist,
    remove_symbols_from_watchlist,
)
from open_stocks_mcp.tracing import (
    instrument_mcp_tool_calls,
    setup_tracing,
    trace_tool_call,
)

# Load environment variables from .env file
load_dotenv()

# Create global MCP server instance for Inspector
mcp = FastMCP("Open Stocks MCP")


# Register tools at module level for Inspector
@mcp.tool()
async def list_tools() -> dict[str, Any]:
    """Provides a list of available tools and their descriptions."""
    return await get_list_tools_data(mcp)


@mcp.tool()
async def account_info() -> dict[str, Any]:
    """Gets basic Robinhood account information."""
    return await get_account_info()


@mcp.tool()
async def portfolio() -> dict[str, Any]:
    """Provides a high-level overview of the portfolio."""
    return await get_portfolio()


@mcp.tool()
async def stock_orders() -> dict[str, Any]:
    """Retrieves a list of recent stock order history and their statuses."""
    return await get_stock_orders()


@mcp.tool()
async def options_orders() -> dict[str, Any]:
    """Retrieves a list of recent options order history and their statuses."""
    return await get_options_orders()


@mcp.tool()
async def account_details() -> dict[str, Any]:
    """Gets comprehensive account details including buying power and cash balances."""
    return await get_account_details()


@mcp.tool()
async def positions() -> dict[str, Any]:
    """Gets current stock positions with quantities and values."""
    return await get_positions()


# Advanced Portfolio Analytics Tools
@mcp.tool()
async def build_holdings() -> dict[str, Any]:
    """Builds comprehensive holdings with dividend information and performance metrics.

    Returns detailed holdings data including cost basis, equity, dividends, and performance.
    """
    return await get_build_holdings()


@mcp.tool()
async def build_user_profile() -> dict[str, Any]:
    """Builds comprehensive user profile with equity, cash, and dividend totals.

    Returns complete financial profile including total equity, cash balances, and dividend totals.
    """
    return await get_build_user_profile()


@mcp.tool()
async def day_trades() -> dict[str, Any]:
    """Gets pattern day trading information and tracking.

    Returns day trade count, remaining day trades, PDT status, and buying power information.
    """
    return await get_day_trades()


# Session Management Tools
@mcp.tool()
async def session_status() -> dict[str, Any]:
    """Gets current session status and authentication information."""
    return await get_session_status_data()


@mcp.tool()
async def broker_status() -> dict[str, Any]:
    """Gets authentication status for all configured brokers.

    Returns information about which brokers are available, authenticated,
    or experiencing issues. Use this to troubleshoot authentication problems.

    Returns:
        Dictionary with broker authentication status for each broker
    """
    return await get_broker_status_data()


@mcp.tool()
async def list_brokers() -> dict[str, Any]:
    """Lists all registered brokers and their availability.

    Returns:
        List of broker names and their authentication status
    """
    return await get_list_brokers_data()


@mcp.tool()
async def rate_limit_status() -> dict[str, Any]:
    """Gets current rate limit usage and statistics."""
    return await get_rate_limit_status_data()


# Monitoring Tools
@mcp.tool()
async def metrics_summary() -> dict[str, Any]:
    """Gets comprehensive metrics summary for monitoring."""
    async with trace_tool_call("metrics_summary"):
        return await get_metrics_summary_data()


@mcp.tool()
async def health_check() -> dict[str, Any]:
    """Gets health status of the MCP server."""
    return await get_health_check_data()


# Market Data Tools
@mcp.tool()
async def stock_price(symbol: str) -> dict[str, Any]:
    """Gets current stock price and basic metrics.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
    """
    return await get_stock_price(symbol)


@mcp.tool()
async def stock_info(symbol: str) -> dict[str, Any]:
    """Gets detailed company information and fundamentals.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
    """
    return await get_stock_info(symbol)


@mcp.tool()
async def search_stocks_tool(query: str) -> dict[str, Any]:
    """Searches for stocks by symbol or company name.

    Args:
        query: Search query (symbol or company name)
    """
    return await search_stocks(query)


@mcp.tool()
async def market_hours() -> dict[str, Any]:
    """Gets current market hours and status."""
    return await get_market_hours()


@mcp.tool()
async def price_history(symbol: str, period: str = "week") -> dict[str, Any]:
    """Gets historical price data for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
        period: Time period ("day", "week", "month", "3month", "year", "5year")
    """
    return await get_price_history(symbol, period)


# Phase 6: Advanced Instrument Data Tools
@mcp.tool()
async def instruments_by_symbols(symbols: list[str]) -> dict[str, Any]:
    """Gets detailed instrument metadata for multiple symbols.

    Args:
        symbols: List of stock ticker symbols (e.g., ["AAPL", "GOOGL", "MSFT"])
    """
    return await get_instruments_by_symbols(symbols)


@mcp.tool()
async def find_instruments(query: str) -> dict[str, Any]:
    """Searches for instrument information by various criteria.

    Args:
        query: Search query string (can be symbol, company name, or other criteria)
    """
    return await find_instrument_data(query)


@mcp.tool()
async def stock_quote_by_id(instrument_id: str) -> dict[str, Any]:
    """Gets stock quote using Robinhood's internal instrument ID.

    Args:
        instrument_id: Robinhood's internal instrument ID
    """
    return await get_stock_quote_by_id(instrument_id)


@mcp.tool()
async def pricebook_by_symbol(symbol: str) -> dict[str, Any]:
    """Gets Level II order book data for a symbol (requires Gold subscription).

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
    """
    return await get_pricebook_by_symbol(symbol)


# Dividend & Income Tools
@mcp.tool()
async def dividends() -> dict[str, Any]:
    """Gets all dividend payment history for the account."""
    return await get_dividends()


@mcp.tool()
async def total_dividends() -> dict[str, Any]:
    """Gets total dividends received across all time."""
    return await get_total_dividends()


@mcp.tool()
async def dividends_by_instrument(symbol: str) -> dict[str, Any]:
    """Gets dividend history for a specific stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
    """
    return await get_dividends_by_instrument(symbol)


@mcp.tool()
async def interest_payments() -> dict[str, Any]:
    """Gets interest payment history from cash management."""
    return await get_interest_payments()


@mcp.tool()
async def stock_loan_payments() -> dict[str, Any]:
    """Gets stock loan payment history from the stock lending program."""
    return await get_stock_loan_payments()


# Advanced Market Data Tools
@mcp.tool()
async def top_movers_sp500(direction: str = "up") -> dict[str, Any]:
    """Gets top S&P 500 movers for the day.

    Args:
        direction: Direction of movement, either 'up' or 'down' (default: 'up')
    """
    return await get_top_movers_sp500(direction)


@mcp.tool()
async def top_100_stocks() -> dict[str, Any]:
    """Gets top 100 most popular stocks on Robinhood."""
    return await get_top_100()


@mcp.tool()
async def top_movers() -> dict[str, Any]:
    """Gets top 20 movers on Robinhood."""
    return await get_top_movers()


@mcp.tool()
async def stocks_by_tag(tag: str) -> dict[str, Any]:
    """Gets stocks filtered by market category tag.

    Args:
        tag: Market category tag (e.g., 'technology', 'biopharmaceutical', 'upcoming-earnings')
    """
    return await get_stocks_by_tag(tag)


@mcp.tool()
async def stock_ratings(symbol: str) -> dict[str, Any]:
    """Gets analyst ratings for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
    """
    return await get_stock_ratings(symbol)


@mcp.tool()
async def stock_earnings(symbol: str) -> dict[str, Any]:
    """Gets earnings reports for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
    """
    return await get_stock_earnings(symbol)


@mcp.tool()
async def stock_news(symbol: str) -> dict[str, Any]:
    """Gets news stories for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
    """
    return await get_stock_news(symbol)


@mcp.tool()
async def stock_splits(symbol: str) -> dict[str, Any]:
    """Gets stock split history for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
    """
    return await get_stock_splits(symbol)


@mcp.tool()
async def stock_events(symbol: str) -> dict[str, Any]:
    """Gets corporate events for a stock (for owned positions).

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
    """
    return await get_stock_events(symbol)


@mcp.tool()
async def stock_level2_data(symbol: str) -> dict[str, Any]:
    """Gets Level II market data for a stock (Gold subscription required).

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
    """
    return await get_stock_level2_data(symbol)


# Phase 3: Options Trading Tools
@mcp.tool()
async def options_chains(symbol: str) -> dict[str, Any]:
    """Gets complete option chains for a stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
    """
    return await get_options_chains(symbol)


@mcp.tool()
async def find_options(
    symbol: str, expiration_date: str | None = None, option_type: str | None = None
) -> dict[str, Any]:
    """Finds tradable options with optional filtering.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
        expiration_date: Optional expiration date in YYYY-MM-DD format
        option_type: Optional option type ("call" or "put")
    """
    return await find_tradable_options(symbol, expiration_date, option_type)


@mcp.tool()
async def option_market_data(option_id: str) -> dict[str, Any]:
    """Gets market data for a specific option contract.

    Args:
        option_id: Unique option contract ID
    """
    return await get_option_market_data(option_id)


@mcp.tool()
async def option_historicals(
    symbol: str,
    expiration_date: str,
    strike_price: str,
    option_type: str,
    interval: str = "hour",
    span: str = "week",
) -> dict[str, Any]:
    """Gets historical price data for an option contract.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
        expiration_date: Expiration date in YYYY-MM-DD format
        strike_price: Strike price as string
        option_type: Option type ("call" or "put")
        interval: Time interval (default: "hour")
        span: Time span (default: "week")
    """
    result = await get_option_historicals(
        symbol, expiration_date, strike_price, option_type, interval, span
    )
    return result


@mcp.tool()
async def aggregate_option_positions() -> dict[str, Any]:
    """Gets aggregated option positions collapsed by underlying stock."""
    return await get_aggregate_positions()


@mcp.tool()
async def all_option_positions() -> dict[str, Any]:
    """Gets all option positions ever held."""
    return await get_all_option_positions()


@mcp.tool()
async def open_option_positions() -> dict[str, Any]:
    """Gets currently open option positions."""
    return await get_open_option_positions()


@mcp.tool()
async def open_option_positions_with_details() -> dict[str, Any]:
    """Gets currently open option positions with enriched details including call/put type.

    This enhanced version includes complete option instrument details for each position:
    - option_type: "call" or "put"
    - strike_price: Strike price of the option
    - option_symbol: OCC option symbol
    - tradability: Trading status
    - state: Option state (active, expired, etc.)
    - underlying_symbol: Underlying stock symbol
    - enrichment_success_rate: Percentage of positions successfully enriched

    Use this instead of open_option_positions() when you need complete option details.
    """
    return await get_open_option_positions_with_details()


# Phase 3: Watchlist Management Tools
@mcp.tool()
async def all_watchlists() -> dict[str, Any]:
    """Gets all user-created watchlists."""
    return await get_all_watchlists()


@mcp.tool()
async def watchlist_by_name(watchlist_name: str) -> dict[str, Any]:
    """Gets contents of a specific watchlist by name.

    Args:
        watchlist_name: Name of the watchlist to retrieve
    """
    return await get_watchlist_by_name(watchlist_name)


@mcp.tool()
async def add_to_watchlist(watchlist_name: str, symbols: list[str]) -> dict[str, Any]:
    """Adds symbols to a watchlist.

    Args:
        watchlist_name: Name of the watchlist
        symbols: List of stock symbols to add
    """
    return await add_symbols_to_watchlist(watchlist_name, symbols)


@mcp.tool()
async def remove_from_watchlist(
    watchlist_name: str, symbols: list[str]
) -> dict[str, Any]:
    """Removes symbols from a watchlist.

    Args:
        watchlist_name: Name of the watchlist
        symbols: List of stock symbols to remove
    """
    return await remove_symbols_from_watchlist(watchlist_name, symbols)


@mcp.tool()
async def watchlist_performance(watchlist_name: str) -> dict[str, Any]:
    """Gets performance metrics for a watchlist.

    Args:
        watchlist_name: Name of the watchlist to analyze
    """
    return await get_watchlist_performance(watchlist_name)


# Unified Watchlist Tools
@mcp.tool()
async def unified_watchlists(brokers: list[str] | None = None) -> dict[str, Any]:
    """Gets all watchlists aggregated across supported brokers.

    Args:
        brokers: Optional list of broker names to include (e.g., ["robinhood", "schwab"])
    """
    return await get_unified_watchlists(brokers)


@mcp.tool()
async def unified_watchlist_by_name(
    watchlist_name: str, brokers: list[str] | None = None
) -> dict[str, Any]:
    """Gets a specific watchlist by name across supported brokers.

    Args:
        watchlist_name: Name of the watchlist
        brokers: Optional list of broker names to include
    """
    return await get_unified_watchlist_by_name(watchlist_name, brokers)


@mcp.tool()
async def unified_add_to_watchlist(
    watchlist_name: str, symbols: list[str], brokers: list[str] | None = None
) -> dict[str, Any]:
    """Adds symbols to a watchlist across supported brokers.

    Args:
        watchlist_name: Name of the watchlist
        symbols: List of stock symbols to add
        brokers: Optional list of broker names to target
    """
    return await add_symbols_to_unified_watchlist(watchlist_name, symbols, brokers)


@mcp.tool()
async def unified_remove_from_watchlist(
    watchlist_name: str, symbols: list[str], brokers: list[str] | None = None
) -> dict[str, Any]:
    """Removes symbols from a watchlist across supported brokers.

    Args:
        watchlist_name: Name of the watchlist
        symbols: List of stock symbols to remove
        brokers: Optional list of broker names to target
    """
    return await remove_symbols_from_unified_watchlist(watchlist_name, symbols, brokers)


# Phase 3: Account Features & Notifications Tools
@mcp.tool()
async def notifications(count: int = 20) -> dict[str, Any]:
    """Gets account notifications and alerts.

    Args:
        count: Number of notifications to retrieve (default: 20)
    """
    return await get_notifications(count)


@mcp.tool()
async def latest_notification() -> dict[str, Any]:
    """Gets the most recent notification."""
    return await get_latest_notification()


@mcp.tool()
async def margin_calls() -> dict[str, Any]:
    """Gets margin call information."""
    return await get_margin_calls()


@mcp.tool()
async def margin_interest() -> dict[str, Any]:
    """Gets margin interest charges and rates."""
    return await get_margin_interest()


@mcp.tool()
async def subscription_fees() -> dict[str, Any]:
    """Gets Robinhood Gold subscription fees."""
    return await get_subscription_fees()


@mcp.tool()
async def referrals() -> dict[str, Any]:
    """Gets referral program information."""
    return await get_referrals()


@mcp.tool()
async def account_features() -> dict[str, Any]:
    """Gets comprehensive account features and settings."""
    return await get_account_features()


# Phase 3: User Profile Tools
@mcp.tool()
async def account_profile() -> dict[str, Any]:
    """Gets trading account profile and configuration."""
    return await get_account_profile()


@mcp.tool()
async def basic_profile() -> dict[str, Any]:
    """Gets basic user profile information."""
    return await get_basic_profile()


@mcp.tool()
async def investment_profile() -> dict[str, Any]:
    """Gets investment profile and risk assessment."""
    return await get_investment_profile()


@mcp.tool()
async def security_profile() -> dict[str, Any]:
    """Gets security profile and settings."""
    return await get_security_profile()


@mcp.tool()
async def user_profile() -> dict[str, Any]:
    """Gets comprehensive user profile information."""
    return await get_user_profile()


@mcp.tool()
async def complete_profile() -> dict[str, Any]:
    """Gets complete user profile combining all profile types."""
    return await get_complete_profile()


@mcp.tool()
async def account_settings() -> dict[str, Any]:
    """Gets account settings and preferences."""
    return await get_account_settings()


# Phase 7: Trading Capabilities Tools


# Stock Order Placement Tools
@mcp.tool()
async def buy_stock_market(symbol: str, quantity: int) -> dict[str, Any]:
    """Places a market buy order for a stock.

    Args:
        symbol: The stock symbol to buy (e.g., "AAPL")
        quantity: The number of shares to buy
    """
    return await order_buy_market(symbol, quantity)


@mcp.tool()
async def sell_stock_market(symbol: str, quantity: int) -> dict[str, Any]:
    """Places a market sell order for a stock.

    Args:
        symbol: The stock symbol to sell (e.g., "AAPL")
        quantity: The number of shares to sell
    """
    return await order_sell_market(symbol, quantity)


@mcp.tool()
async def buy_stock_limit(
    symbol: str, quantity: int, limit_price: float
) -> dict[str, Any]:
    """Places a limit buy order for a stock.

    Args:
        symbol: The stock symbol to buy (e.g., "AAPL")
        quantity: The number of shares to buy
        limit_price: The maximum price per share
    """
    return await order_buy_limit(symbol, quantity, limit_price)


@mcp.tool()
async def sell_stock_limit(
    symbol: str, quantity: int, limit_price: float
) -> dict[str, Any]:
    """Places a limit sell order for a stock.

    Args:
        symbol: The stock symbol to sell (e.g., "AAPL")
        quantity: The number of shares to sell
        limit_price: The minimum price per share
    """
    return await order_sell_limit(symbol, quantity, limit_price)


# DEPRECATED: buy_stock_stop_loss removed - uncommon use case for most traders
# Buy stop-loss orders are primarily used for short covering or breakout trading
# which are advanced strategies not commonly used by typical retail investors
# @mcp.tool()
# async def buy_stock_stop_loss(
#     symbol: str, quantity: int, stop_price: float
# ) -> dict[str, Any]:
#     """Places a stop loss buy order for a stock.
#
#     Args:
#         symbol: The stock symbol to buy (e.g., "AAPL")
#         quantity: The number of shares to buy
#         stop_price: The stop price that triggers the order
#     """
#     return await order_buy_stop_loss(symbol, quantity, stop_price)  # type: ignore[no-any-return]


@mcp.tool()
async def sell_stock_stop_loss(
    symbol: str, quantity: int, stop_price: float
) -> dict[str, Any]:
    """Places a stop loss sell order for a stock.

    Args:
        symbol: The stock symbol to sell (e.g., "AAPL")
        quantity: The number of shares to sell
        stop_price: The stop price that triggers the order
    """
    return await order_sell_stop_loss(symbol, quantity, stop_price)


# DEPRECATED: buy_stock_trailing_stop removed - uncommon use case for most traders
# Trailing stop buy orders are advanced trading strategies primarily used for breakout trading
# which are not commonly used by typical retail investors
# @mcp.tool()
# async def buy_stock_trailing_stop(
#     symbol: str, quantity: int, trail_amount: float
# ) -> dict[str, Any]:
#     """Places a trailing stop buy order for a stock.
#
#     Args:
#         symbol: The stock symbol to buy (e.g., "AAPL")
#         quantity: The number of shares to buy
#         trail_amount: The trailing amount (percentage or dollar amount)
#     """
#     return await order_buy_trailing_stop(symbol, quantity, trail_amount)  # type: ignore[no-any-return]


# DEPRECATED: sell_stock_trailing_stop removed - uncommon use case for most traders
# Trailing stop sell orders are advanced trading strategies that require careful market timing
# and are not commonly used by typical retail investors
# @mcp.tool()
# async def sell_stock_trailing_stop(
#     symbol: str, quantity: int, trail_amount: float
# ) -> dict[str, Any]:
#     """Places a trailing stop sell order for a stock.
#
#     Args:
#         symbol: The stock symbol to sell (e.g., "AAPL")
#         quantity: The number of shares to sell
#         trail_amount: The trailing amount (percentage or dollar amount)
#     """
#     return await order_sell_trailing_stop(symbol, quantity, trail_amount)  # type: ignore[no-any-return]


# DEPRECATED: buy_fractional_stock removed - uncommon use case for most traders
# Fractional share trading is useful but represents a small subset of trading activity
# and most retail traders prefer whole share purchases for clearer position management
# @mcp.tool()
# async def buy_fractional_stock(symbol: str, amount_in_dollars: float) -> dict[str, Any]:
#     """Places a fractional share buy order using dollar amount.
#
#     Args:
#         symbol: The stock symbol to buy (e.g., "AAPL")
#         amount_in_dollars: The dollar amount to invest
#     """
#     return await order_buy_fractional_by_price(symbol, amount_in_dollars)  # type: ignore[no-any-return]


# Options Order Placement Tools
@mcp.tool()
async def buy_option_limit(
    instrument_id: str, quantity: int, limit_price: float
) -> dict[str, Any]:
    """Places a limit buy order for an option.

    Args:
        instrument_id: The option instrument ID
        quantity: The number of option contracts to buy
        limit_price: The maximum price per contract
    """
    return await order_buy_option_limit(instrument_id, quantity, limit_price)


@mcp.tool()
async def sell_option_limit(
    instrument_id: str, quantity: int, limit_price: float
) -> dict[str, Any]:
    """Places a limit sell order for an option.

    Args:
        instrument_id: The option instrument ID
        quantity: The number of option contracts to sell
        limit_price: The minimum price per contract
    """
    return await order_sell_option_limit(instrument_id, quantity, limit_price)


@mcp.tool()
async def option_credit_spread(
    short_instrument_id: str,
    long_instrument_id: str,
    quantity: int,
    credit_price: float,
) -> dict[str, Any]:
    """Places a credit spread order (sell short option, buy long option).

    Args:
        short_instrument_id: The option instrument ID to sell (short leg)
        long_instrument_id: The option instrument ID to buy (long leg)
        quantity: The number of spread contracts
        credit_price: The net credit received per spread
    """
    result: dict[str, Any] = await order_option_credit_spread(
        short_instrument_id, long_instrument_id, quantity, credit_price
    )
    return result


@mcp.tool()
async def option_debit_spread(
    short_instrument_id: str, long_instrument_id: str, quantity: int, debit_price: float
) -> dict[str, Any]:
    """Places a debit spread order (buy long option, sell short option).

    Args:
        short_instrument_id: The option instrument ID to sell (short leg)
        long_instrument_id: The option instrument ID to buy (long leg)
        quantity: The number of spread contracts
        debit_price: The net debit paid per spread
    """
    result: dict[str, Any] = await order_option_debit_spread(
        short_instrument_id, long_instrument_id, quantity, debit_price
    )
    return result


# Order Management Tools
@mcp.tool()
async def cancel_stock_order_by_id(order_id: str) -> dict[str, Any]:
    """Cancels a specific stock order.

    Args:
        order_id: The ID of the order to cancel
    """
    return await cancel_stock_order(order_id)


@mcp.tool()
async def cancel_option_order_by_id(order_id: str) -> dict[str, Any]:
    """Cancels a specific option order.

    Args:
        order_id: The ID of the order to cancel
    """
    return await cancel_option_order(order_id)


@mcp.tool()
async def cancel_all_stock_orders_tool() -> dict[str, Any]:
    """Cancels all open stock orders."""
    return await cancel_all_stock_orders()


@mcp.tool()
async def cancel_all_option_orders_tool() -> dict[str, Any]:
    """Cancels all open option orders."""
    return await cancel_all_option_orders()


@mcp.tool()
async def open_stock_orders() -> dict[str, Any]:
    """Retrieves all open stock orders."""
    return await get_all_open_stock_orders()


@mcp.tool()
async def open_option_orders() -> dict[str, Any]:
    """Retrieves all open option orders."""
    return await get_all_open_option_orders()


# Schwab Account Tools
@mcp.tool()
async def schwab_account_numbers() -> dict[str, Any]:
    """Get Schwab account numbers and their hashes."""
    return await get_schwab_account_numbers()


@mcp.tool()
async def schwab_account(
    account_hash: str, include_positions: bool = True
) -> dict[str, Any]:
    """Get Schwab account details including balances and positions.

    Args:
        account_hash: Account hash from schwab_account_numbers
        include_positions: Whether to include positions (default: True)
    """
    return await get_schwab_account(account_hash, include_positions)


@mcp.tool()
async def schwab_accounts(include_positions: bool = True) -> dict[str, Any]:
    """Get all Schwab linked accounts with balances and positions.

    Args:
        include_positions: Whether to include positions (default: True)
    """
    return await get_schwab_accounts(include_positions)


@mcp.tool()
async def schwab_portfolio(account_hash: str) -> dict[str, Any]:
    """Get Schwab portfolio positions for a specific account.

    Args:
        account_hash: Account hash from schwab_account_numbers
    """
    return await get_schwab_portfolio(account_hash)


@mcp.tool()
async def schwab_account_balances(account_hash: str) -> dict[str, Any]:
    """Get account balances for a Schwab account.

    Args:
        account_hash: Account hash from schwab_account_numbers
    """
    return await get_schwab_account_balances(account_hash)


@mcp.tool()
async def schwab_check_margin_status(account_hash: str) -> dict[str, Any]:
    """Derive margin-call status from Schwab account balances."""
    return await schwab_check_margin_status_impl(account_hash)


@mcp.tool()
async def schwab_get_margin_interest(
    account_hash: str, start_date: str | None = None, end_date: str | None = None
) -> dict[str, Any]:
    """Get Schwab margin-interest charges from transaction history."""
    return await schwab_get_margin_interest_impl(account_hash, start_date, end_date)


@mcp.tool()
async def schwab_get_user_preferences() -> dict[str, Any]:
    """Get Schwab user preferences including account list and streamer info.

    Consolidates account profile, settings, and user profile data.
    """
    return await get_schwab_user_preferences()


@mcp.tool()
async def schwab_get_all_account_data() -> dict[str, Any]:
    """Get a complete snapshot of all Schwab accounts and user preferences.

    Aggregates user preferences, account numbers, and all account data with positions.
    """
    return await get_schwab_all_account_data()


@mcp.tool()
async def schwab_build_user_profile() -> dict[str, Any]:
    """Build a normalized Schwab user profile from account and preference data.

    Returns a complete financial profile including total equity, cash balances,
    and position counts across all accounts.
    """
    return await build_schwab_user_profile()


# Cross-Broker Tools
@mcp.tool()
async def aggregated_portfolio() -> dict[str, Any]:
    """Get a unified portfolio view aggregated across all registered brokers.

    Combines positions and summary values from Robinhood and Schwab into a single
    normalized response. Brokers that are not authenticated contribute a degraded
    (status=unavailable) entry so partial information is always returned.

    Returns:
        Dict with aggregated totals, per-broker rollups, positions list,
        partial_failure flag, and unavailable_brokers list.
    """
    return await get_aggregated_portfolio()


@mcp.tool()
async def broker_comparison(
    symbols: list[str] | None = None, include_orders: bool = True, max_orders: int = 5
) -> dict[str, Any]:
    """Get side-by-side broker comparison for pricing, holdings, and orders.

    Args:
        symbols: Optional list of symbols to filter by.
        include_orders: Whether to include recent orders.
        max_orders: Maximum number of orders to return per broker.
    """
    return await get_broker_comparison(symbols, include_orders, max_orders)


# Schwab Market Data Tools
@mcp.tool()
async def schwab_quote(symbol: str) -> dict[str, Any]:
    """Get current quote for a stock symbol from Schwab.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
    """
    return await get_schwab_quote(symbol)


@mcp.tool()
async def schwab_quotes(symbols: list[str]) -> dict[str, Any]:
    """Get current quotes for multiple stock symbols from Schwab.

    Args:
        symbols: List of stock ticker symbols
    """
    return await get_schwab_quotes(symbols)


@mcp.tool()
async def schwab_price_history(
    symbol: str,
    period_type: str = "day",
    period: int = 1,
    frequency_type: str = "minute",
    frequency: int = 1,
) -> dict[str, Any]:
    """Get price history for a stock symbol.

    Args:
        symbol: Stock ticker symbol
        period_type: Type of period ('day', 'month', 'year', 'ytd')
        period: Number of periods
        frequency_type: Frequency type ('minute', 'daily', 'weekly', 'monthly')
        frequency: Frequency value
    """
    return await get_schwab_price_history(
        symbol, period_type, period, frequency_type, frequency
    )


@mcp.tool()
async def schwab_instrument(symbol: str) -> dict[str, Any]:
    """Get instrument information for a symbol.

    Args:
        symbol: Stock ticker symbol
    """
    return await get_schwab_instrument(symbol)


@mcp.tool()
async def schwab_search_instruments(query: str) -> dict[str, Any]:
    """Search for instruments by symbol or name.

    Args:
        query: Symbol or company name to search
    """
    return await search_schwab_instruments(query)


@mcp.tool()
async def schwab_get_market_hours(
    market: str = "equity", date: str | None = None
) -> dict[str, Any]:
    """Get market hours for a given market and optional date.

    Args:
        market: Market type ('equity', 'option', 'bond', 'forex', 'future')
        date: Optional ISO date string (e.g. '2026-05-20'). Defaults to today.
    """
    return await get_schwab_market_hours(market, date)


@mcp.tool()
async def schwab_get_movers(
    index: str,
    sort_order: str | None = None,
    frequency: int | None = None,
) -> dict[str, Any]:
    """Get market movers for a given index.

    Args:
        index: Index to query (e.g. '$DJI', '$SPX', 'NASDAQ', 'NYSE', '$COMPX',
               'EQUITY_ALL', 'INDEX_ALL', 'OPTION_ALL', 'OPTION_CALL', 'OPTION_PUT',
               'OTCBB')
        sort_order: Optional sort order ('PERCENT_CHANGE_UP', 'PERCENT_CHANGE_DOWN',
                    'VOLUME', 'TRADES')
        frequency: Optional frequency in minutes (0, 1, 5, 10, 30, 60)
    """
    return await get_schwab_movers(index, sort_order, frequency)


@mcp.tool()
async def schwab_get_movers_sp500(
    sort_order: str | None = None,
    frequency: int | None = None,
) -> dict[str, Any]:
    """Get market movers for the S&P 500 index ($SPX).

    Args:
        sort_order: Optional sort order ('PERCENT_CHANGE_UP', 'PERCENT_CHANGE_DOWN',
                    'VOLUME', 'TRADES')
        frequency: Optional frequency in minutes (0, 1, 5, 10, 30, 60)
    """
    return await get_schwab_movers_sp500(sort_order, frequency)


@mcp.tool()
async def schwab_get_instrument_by_cusip(cusip: str) -> dict[str, Any]:
    """Get instrument details by CUSIP identifier.

    Args:
        cusip: CUSIP identifier (leading zeros are preserved, e.g. '037833100')
    """
    return await get_schwab_instrument_by_cusip(cusip)


# Schwab Trading Tools
@mcp.tool()
async def schwab_buy_stock_market(
    account_hash: str, symbol: str, quantity: int
) -> dict[str, Any]:
    """Place a market buy order for stock.

    Args:
        account_hash: Account hash from schwab_account_numbers
        symbol: Stock ticker symbol
        quantity: Number of shares to buy
    """
    return await schwab_buy_market(account_hash, symbol, quantity)


@mcp.tool()
async def schwab_sell_stock_market(
    account_hash: str, symbol: str, quantity: int
) -> dict[str, Any]:
    """Place a market sell order for stock.

    Args:
        account_hash: Account hash from schwab_account_numbers
        symbol: Stock ticker symbol
        quantity: Number of shares to sell
    """
    return await schwab_sell_market(account_hash, symbol, quantity)


@mcp.tool()
async def schwab_buy_stock_limit(
    account_hash: str, symbol: str, quantity: int, price: float
) -> dict[str, Any]:
    """Place a limit buy order for stock.

    Args:
        account_hash: Account hash from schwab_account_numbers
        symbol: Stock ticker symbol
        quantity: Number of shares to buy
        price: Limit price
    """
    return await schwab_buy_limit(account_hash, symbol, quantity, price)


@mcp.tool()
async def schwab_sell_stock_limit(
    account_hash: str, symbol: str, quantity: int, price: float
) -> dict[str, Any]:
    """Place a limit sell order for stock.

    Args:
        account_hash: Account hash from schwab_account_numbers
        symbol: Stock ticker symbol
        quantity: Number of shares to sell
        price: Limit price
    """
    return await schwab_sell_limit(account_hash, symbol, quantity, price)


@mcp.tool()
async def schwab_place_order(
    account_hash: str, order_spec: dict[str, Any]
) -> dict[str, Any]:
    """Place a generic Schwab order using a raw order specification.

    Args:
        account_hash: Account hash from schwab_account_numbers
        order_spec: Order specification dict as accepted by the Schwab API
            (typically produced via schwab order builder helpers)
    """
    return await place_schwab_order(account_hash, order_spec)


@mcp.tool()
async def schwab_orders(account_hash: str, max_results: int = 50) -> dict[str, Any]:
    """Get orders for a Schwab account.

    Args:
        account_hash: Account hash from schwab_account_numbers
        max_results: Maximum number of orders to return (default: 50)
    """
    return await get_schwab_orders(account_hash, max_results)


@mcp.tool()
async def schwab_cancel_order(account_hash: str, order_id: str) -> dict[str, Any]:
    """Cancel a specific Schwab order.

    Args:
        account_hash: Account hash from schwab_account_numbers
        order_id: Order ID to cancel
    """
    return await cancel_schwab_order(account_hash, order_id)


@mcp.tool()
async def schwab_get_order(account_hash: str, order_id: str) -> dict[str, Any]:
    """Get details for a specific Schwab order.

    Args:
        account_hash: Account hash from schwab_account_numbers
        order_id: Order ID to retrieve
    """
    return await get_schwab_order_by_id(account_hash, order_id)


@mcp.tool()
async def schwab_transactions(
    account_hash: str,
    start_date: str | None = None,
    end_date: str | None = None,
    transaction_types: list[str] | None = None,
    symbol: str | None = None,
) -> dict[str, Any]:
    """Get Schwab transactions with optional date/type/symbol filters."""
    return await schwab_get_transactions(
        account_hash, start_date, end_date, transaction_types, symbol
    )


@mcp.tool()
async def schwab_transactions_by_date(
    account_hash: str,
    start_date: str,
    end_date: str,
    transaction_types: list[str] | None = None,
    symbol: str | None = None,
) -> dict[str, Any]:
    """Get Schwab transactions constrained by required start and end dates."""
    return await schwab_get_transactions_by_date(
        account_hash, start_date, end_date, transaction_types, symbol
    )


@mcp.tool()
async def schwab_get_transaction(
    account_hash: str, transaction_id: str
) -> dict[str, Any]:
    """Get details for a specific Schwab transaction.

    Args:
        account_hash: Account hash from schwab_account_numbers
        transaction_id: Transaction ID to retrieve
    """
    return await get_schwab_transaction(account_hash, transaction_id)


@mcp.tool()
async def schwab_get_dividends(
    account_hash: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Get dividend payments for a Schwab account.

    Args:
        account_hash: Account hash from schwab_account_numbers
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
    """
    return await _schwab_get_dividends_impl(account_hash, start_date, end_date)


@mcp.tool()
async def schwab_get_stock_loan_payments(
    account_hash: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Get stock loan (securities lending) payments for a Schwab account.

    Args:
        account_hash: Account hash from schwab_account_numbers
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
    """
    return await _schwab_get_stock_loan_payments_impl(
        account_hash, start_date, end_date
    )


@mcp.tool()
async def schwab_get_dividends_by_symbol(
    account_hash: str,
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Get dividend payments for a specific symbol in a Schwab account.

    Args:
        account_hash: Account hash from schwab_account_numbers
        symbol: Stock symbol to filter dividends by (case-insensitive)
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
    """
    return await _schwab_get_dividends_by_symbol_impl(
        account_hash, symbol, start_date, end_date
    )


@mcp.tool()
async def schwab_get_interest_payments(
    account_hash: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Get interest payments for a Schwab account.

    Args:
        account_hash: Account hash from schwab_account_numbers
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
    """
    return await _schwab_get_interest_payments_impl(account_hash, start_date, end_date)


@mcp.tool()
async def schwab_get_total_dividends(
    account_hash: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Get aggregate dividend totals with year grouping for a Schwab account.

    Args:
        account_hash: Account hash from schwab_account_numbers
        start_date: Optional start date (YYYY-MM-DD). Schwab enforces a 60-day
            default lookback; pass an explicit start_date for older history.
        end_date: Optional end date (YYYY-MM-DD)
    """
    return await _schwab_get_total_dividends_impl(account_hash, start_date, end_date)


@mcp.tool()
async def schwab_order_sell_stop(
    account_hash: str, symbol: str, quantity: int, stop_price: str
) -> dict[str, Any]:
    """Place a stop sell order for stock.

    Args:
        account_hash: Account hash from schwab_account_numbers
        symbol: Stock ticker symbol
        quantity: Number of shares to sell
        stop_price: Stop trigger price as a string (e.g. "148.00")
    """
    return await _schwab_order_sell_stop(account_hash, symbol, quantity, stop_price)


@mcp.tool()
async def schwab_get_open_stock_orders(
    account_hash: str, max_results: int = 200
) -> dict[str, Any]:
    """Get open (cancellable) equity orders for a Schwab account.

    Args:
        account_hash: Account hash from schwab_account_numbers
        max_results: Maximum orders to fetch from API before filtering
    """
    return await _schwab_get_open_stock_orders(account_hash, max_results)


@mcp.tool()
async def schwab_cancel_all_stock_orders(
    account_hash: str, max_results: int = 200
) -> dict[str, Any]:
    """Cancel all open equity orders for a Schwab account.

    Args:
        account_hash: Account hash from schwab_account_numbers
        max_results: Maximum orders to fetch before filtering
    """
    return await _schwab_cancel_all_stock_orders(account_hash, max_results)


@mcp.tool()
async def schwab_order_buy_option_limit(
    account_hash: str, option_symbol: str, quantity: int, price: str
) -> dict[str, Any]:
    """Place a limit buy-to-open order for an option contract.

    Args:
        account_hash: Account hash from schwab_account_numbers
        option_symbol: OCC option symbol (e.g. "AAPL  251219C00150000")
        quantity: Number of contracts to buy
        price: Limit price as a string (e.g. "5.50")
    """
    return await _schwab_order_buy_option_limit(
        account_hash, option_symbol, quantity, price
    )


@mcp.tool()
async def schwab_order_sell_option_limit(
    account_hash: str, option_symbol: str, quantity: int, price: str
) -> dict[str, Any]:
    """Place a limit sell-to-close order for an option contract.

    Args:
        account_hash: Account hash from schwab_account_numbers
        option_symbol: OCC option symbol (e.g. "AAPL  251219C00150000")
        quantity: Number of contracts to sell
        price: Limit price as a string (e.g. "4.00")
    """
    return await _schwab_order_sell_option_limit(
        account_hash, option_symbol, quantity, price
    )


@mcp.tool()
async def schwab_cancel_option_order(
    account_hash: str, order_id: str
) -> dict[str, Any]:
    """Cancel a specific option order.

    Args:
        account_hash: Account hash from schwab_account_numbers
        order_id: Option order ID to cancel
    """
    return await _schwab_cancel_option_order(account_hash, order_id)


@mcp.tool()
async def schwab_cancel_all_option_orders(
    account_hash: str, max_results: int = 200
) -> dict[str, Any]:
    """Cancel all open option orders for a Schwab account.

    Args:
        account_hash: Account hash from schwab_account_numbers
        max_results: Maximum orders to fetch before filtering
    """
    return await _schwab_cancel_all_option_orders(account_hash, max_results)


@mcp.tool()
async def schwab_order_option_credit_spread(
    account_hash: str,
    option_type: str,
    short_symbol: str,
    long_symbol: str,
    quantity: int,
    net_credit: str,
) -> dict[str, Any]:
    """Place a vertical credit spread option order.

    For CALL: bear call spread. For PUT: bull put spread.

    Args:
        account_hash: Account hash from schwab_account_numbers
        option_type: "CALL" or "PUT"
        short_symbol: OCC symbol for the leg you sell (collects premium)
        long_symbol: OCC symbol for the hedge/protective leg
        quantity: Number of spread contracts
        net_credit: Net credit received as a string (e.g. "2.00")
    """
    return await _schwab_order_option_credit_spread(
        account_hash, option_type, short_symbol, long_symbol, quantity, net_credit
    )


@mcp.tool()
async def schwab_order_option_debit_spread(
    account_hash: str,
    option_type: str,
    long_symbol: str,
    short_symbol: str,
    quantity: int,
    net_debit: str,
) -> dict[str, Any]:
    """Place a vertical debit spread option order.

    For CALL: bull call spread. For PUT: bear put spread.

    Args:
        account_hash: Account hash from schwab_account_numbers
        option_type: "CALL" or "PUT"
        long_symbol: OCC symbol for the leg you buy (main directional position)
        short_symbol: OCC symbol for the hedge/short leg
        quantity: Number of spread contracts
        net_debit: Net debit paid as a string (e.g. "3.00")
    """
    return await _schwab_order_option_debit_spread(
        account_hash, option_type, long_symbol, short_symbol, quantity, net_debit
    )


@mcp.tool()
async def schwab_replace_order(
    account_hash: str, order_id: str, order_spec: dict[str, Any]
) -> dict[str, Any]:
    """Replace (modify) an existing Schwab order.

    Args:
        account_hash: Account hash from schwab_account_numbers
        order_id: ID of the order to replace
        order_spec: New order specification dict (use order builder helpers)
    """
    return await _schwab_replace_order(account_hash, order_id, order_spec)


# Schwab Options Tools
@mcp.tool()
async def schwab_option_chain(
    symbol: str,
    contract_type: str | None = None,
    strike_count: int | None = None,
    include_underlying_quote: bool = True,
) -> dict[str, Any]:
    """Get option chain for a symbol.

    Args:
        symbol: Stock ticker symbol
        contract_type: Type of contracts ('CALL', 'PUT', 'ALL')
        strike_count: Number of strikes above/below at-the-money price
        include_underlying_quote: Whether to include underlying quote
    """
    return await get_schwab_option_chain(
        symbol, contract_type, strike_count, include_underlying_quote
    )


@mcp.tool()
async def schwab_option_chain_by_expiration(
    symbol: str,
    from_date: str | None = None,
    to_date: str | None = None,
    contract_type: str | None = None,
) -> dict[str, Any]:
    """Get option chain filtered by expiration dates.

    Args:
        symbol: Stock ticker symbol
        from_date: Only return expirations after this date (YYYY-MM-DD)
        to_date: Only return expirations before this date (YYYY-MM-DD)
        contract_type: Type of contracts ('CALL', 'PUT', 'ALL')
    """
    return await get_schwab_option_chain_by_expiration(
        symbol, from_date, to_date, contract_type
    )


@mcp.tool()
async def schwab_option_expirations(symbol: str) -> dict[str, Any]:
    """Get option expiration dates for a symbol.

    Args:
        symbol: Stock ticker symbol
    """
    return await get_schwab_option_expirations(symbol)


@mcp.tool()
async def schwab_options_positions(account_hash: str) -> dict[str, Any]:
    """Get current options positions for an account.

    Args:
        account_hash: Account hash from schwab_account_numbers
    """
    return await get_schwab_options_positions(account_hash)


@mcp.tool()
async def schwab_option_buy_to_open(
    account_hash: str,
    symbol: str,
    quantity: int,
    option_type: str,
    strike: float,
    expiration: str,
) -> dict[str, Any]:
    """Buy an option to open a position (Schwab)."""
    return await _schwab_option_buy_to_open_impl(
        account_hash, symbol, quantity, option_type, strike, expiration
    )


@mcp.tool()
async def schwab_option_sell_to_close(
    account_hash: str,
    symbol: str,
    quantity: int,
    option_type: str,
    strike: float,
    expiration: str,
) -> dict[str, Any]:
    """Sell an option to close a position (Schwab)."""
    return await _schwab_option_sell_to_close_impl(
        account_hash, symbol, quantity, option_type, strike, expiration
    )


@mcp.tool()
async def schwab_find_tradable_options(
    symbol: str,
    expiration_date: str | None = None,
    option_type: str | None = None,
    strike: float | None = None,
) -> dict[str, Any]:
    """Find tradable option contracts filtered by expiration, type, and strike.

    Args:
        symbol: Stock ticker symbol
        expiration_date: Filter to contracts expiring on this date (YYYY-MM-DD)
        option_type: 'call' or 'put'
        strike: Strike price to filter on
    """
    return await _schwab_find_tradable_options_impl(
        symbol, expiration_date, option_type, strike
    )


@mcp.tool()
async def schwab_get_build_holdings() -> dict[str, Any]:
    """Build enriched holdings from Schwab positions and quotes."""
    return await get_schwab_build_holdings()


@mcp.tool()
async def schwab_get_day_trades() -> dict[str, Any]:
    """Get day-trade counts derived from Schwab transaction history."""
    return await get_schwab_day_trades()


@mcp.tool()
async def schwab_get_aggregate_positions() -> dict[str, Any]:
    """Aggregate Schwab positions across all linked accounts."""
    return await get_schwab_aggregate_positions()


@mcp.tool()
async def schwab_get_all_option_positions() -> dict[str, Any]:
    """Get all Schwab option positions across linked accounts."""
    return await get_schwab_all_option_positions()


@mcp.tool()
async def schwab_get_open_option_positions() -> dict[str, Any]:
    """Get open Schwab option positions with non-zero net quantity."""
    return await get_schwab_open_option_positions()


@mcp.tool()
async def schwab_open_option_orders(
    account_hash: str, max_results: int = 50
) -> dict[str, Any]:
    """Get open option orders for a Schwab account.

    Returns only orders with at least one option leg and a working/open status
    (WORKING, PENDING_ACTIVATION, QUEUED, ACCEPTED, AWAITING_CONDITION,
    AWAITING_MANUAL_REVIEW, AWAITING_PARENT_ORDER).

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        max_results: Maximum orders to fetch before filtering (default 50)
    """
    return await _schwab_get_open_option_orders_impl(account_hash, max_results)


# Schwab Streaming Tools
@mcp.tool()
async def schwab_stream_level2(symbol: str, venue: str = "nasdaq") -> dict[str, Any]:
    """Get a Level 2 snapshot from Schwab streaming cache for a symbol."""
    return await _schwab_stream_level2_impl(symbol, venue)


@mcp.tool()
async def schwab_stream_option_quotes(symbols: list[str]) -> dict[str, Any]:
    """Get real-time option quote snapshots from Schwab streaming.

    Args:
        symbols: List of Schwab option symbols (e.g. ['AAPL  260619C00150000'])
    """
    return await _schwab_stream_option_quotes_impl(symbols)


@mcp.tool()
async def schwab_stream_quotes(symbols: list[str]) -> dict[str, Any]:
    """Get real-time equity quote snapshots from Schwab streaming.

    Args:
        symbols: List of equity ticker symbols.
    """
    return await _schwab_stream_quotes_impl(symbols)


@mcp.tool()
async def schwab_stream_account_activity() -> dict[str, Any]:
    """Get latest account activity events from Schwab streaming."""
    return await _schwab_stream_account_activity_impl()


def create_mcp_server(config: ServerConfig | None = None) -> FastMCP:
    """Create and configure the MCP server instance"""
    if config is None:
        config = load_config()

    setup_logging(config)
    configure_global_rate_limiter(
        config.rate_limits.calls_per_minute,
        config.rate_limits.calls_per_hour,
        config.rate_limits.burst_size,
    )
    setup_tracing(config)
    instrument_mcp_tool_calls(mcp)
    return mcp


async def setup_brokers(
    username: str | None,
    password: str | None,
    config: ServerConfig | None = None,
) -> None:
    """
    Setup and register all configured brokers.

    This function is NON-BLOCKING - the server will start even if
    authentication fails for all brokers.

    Args:
        username: Robinhood username (optional)
        password: Robinhood password (optional)
    """
    if config is None:
        config = load_config()

    logger.info("Setting up broker integrations...")

    # Get the global registry
    registry = await get_broker_registry()

    robinhood_enabled = config.is_feature_enabled("brokers.robinhood")
    schwab_enabled = config.is_feature_enabled("brokers.schwab")

    # Setup Robinhood broker if enabled and credentials provided
    if robinhood_enabled and username and password:
        logger.info("Configuring Robinhood broker...")
        session_manager = get_session_manager()
        robinhood_broker = RobinhoodBroker(
            username=username,
            password=password,
            session_manager=session_manager,
        )
        registry.register(robinhood_broker)
        logger.info("✓ Robinhood broker registered")
    elif robinhood_enabled:
        logger.warning(
            "⚠️  Robinhood credentials not provided - skipping Robinhood integration"
        )
        logger.info(
            "   Set ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD to enable Robinhood"
        )
    else:
        logger.info("Robinhood broker disabled by feature flag brokers.robinhood")

    # Setup Schwab broker if enabled and credentials configured
    if schwab_enabled and config.schwab_api_key and config.schwab_app_secret:
        logger.info("Configuring Schwab broker...")
        schwab_broker = SchwabBroker(
            api_key=config.schwab_api_key,
            app_secret=config.schwab_app_secret,
        )
        registry.register(schwab_broker)
        logger.info("✓ Schwab broker registered")
    elif schwab_enabled:
        logger.warning(
            "⚠️  Schwab enabled but SCHWAB_API_KEY/SCHWAB_APP_SECRET not configured"
        )
    else:
        logger.info("Schwab broker disabled by feature flag brokers.schwab")

    # Attempt to authenticate all registered brokers
    await attempt_broker_logins(require_at_least_one=False)


def attempt_login(username: str, password: str) -> None:
    """
    DEPRECATED: Legacy synchronous login function.

    This function is maintained for backward compatibility but will
    be removed in favor of async setup_brokers() function.

    Use setup_brokers() instead for graceful multi-broker authentication.
    """
    logger.warning(
        "attempt_login() is deprecated - use setup_brokers() for graceful auth"
    )

    try:
        logger.info(f"Attempting login for user: {username}")

        # Set credentials in session manager
        session_manager = get_session_manager()
        session_manager.set_credentials(username, password)

        # Use asyncio to run the async authentication
        async def do_auth() -> bool:
            return await session_manager.ensure_authenticated()

        success = asyncio.run(do_auth())

        if success:
            logger.info(f"✅ Successfully logged into Robinhood for user: {username}")
            # Verify by getting session info
            session_info = session_manager.get_session_info()
            logger.info(f"Session info: {session_info}")
        else:
            # DON'T exit - let server start anyway
            logger.error("❌ Login failed: Could not authenticate with Robinhood.")
            logger.warning(
                "   Server will start but Robinhood tools will be unavailable"
            )

    except Exception as e:
        # DON'T exit - let server start anyway
        logger.error(f"❌ An unexpected error occurred during login: {e}")
        logger.warning("   Server will start but Robinhood tools will be unavailable")


@click.command()
@click.option("--port", default=3000, help="Port to listen on for HTTP transport")
@click.option(
    "--host",
    default="127.0.0.1",
    help=(
        "Host to bind to. Defaults to 127.0.0.1 (loopback only). "
        "Non-loopback hosts (e.g. 0.0.0.0) require --api-key."
    ),
)
@click.option(
    "--transport",
    type=click.Choice(["stdio", "http"]),
    default="stdio",
    help="Transport type (stdio or http)",
)
@click.option("--debug", is_flag=True, help="Enable DEBUG logging")
@click.option(
    "--username", help="Robinhood username.", default=os.getenv("ROBINHOOD_USERNAME")
)
@click.option(
    "--password", help="Robinhood password.", default=os.getenv("ROBINHOOD_PASSWORD")
)
@click.option(
    "--api-key",
    default=os.getenv("MCP_API_KEY"),
    help=(
        "Bearer token required for /mcp and other tool-invoking endpoints. "
        "Required when --host is not a loopback address. "
        "Also read from the MCP_API_KEY environment variable."
    ),
)
@click.option(
    "--allow-trading",
    is_flag=True,
    default=False,
    help="Allow mutating trading tools over HTTP /mcp (default is read-only only)",
)
def main(
    port: int,
    host: str,
    transport: str,
    debug: bool,
    username: str | None,
    password: str | None,
    api_key: str | None,
    allow_trading: bool,
) -> int:
    """Run the server with specified transport and handle authentication.

    The server uses graceful authentication - it will start even if
    broker authentication fails. Tools will return appropriate errors
    when accessed without authentication.
    """
    # Prompt for credentials if not provided (interactive mode)
    # In non-interactive mode (Docker, systemd), credentials come from env vars
    if not username and not password and sys.stdin.isatty():
        logger.info("No credentials provided - prompting for Robinhood credentials")
        logger.info("(Press Ctrl+C to skip and start without Robinhood)")
        try:
            username = click.prompt(
                "Robinhood username (or press Ctrl+C to skip)", default=""
            )
            if username:
                password = click.prompt(
                    "Robinhood password", hide_input=True, default=""
                )
        except (KeyboardInterrupt, click.Abort):
            logger.info("\nSkipping Robinhood authentication")
            username = None
            password = None

    # Create MCP server
    config = load_config()
    if debug:
        config.log_level = "DEBUG"
    server = create_mcp_server(config)

    # Setup broker authentication (non-blocking)
    logger.info("Initializing broker authentication...")
    asyncio.run(setup_brokers(username, password, config=config))

    # Start server regardless of authentication status
    try:
        if transport == "stdio":
            logger.info("Starting MCP server with STDIO transport")
            logger.info(
                "Server ready - broker tools available based on authentication status"
            )
            asyncio.run(server.run_stdio_async())
        else:
            # Use our enhanced HTTP transport
            from open_stocks_mcp.server.http_transport import run_http_server

            logger.info(f"Starting MCP server with HTTP transport on {host}:{port}")
            logger.info(
                "Server ready - broker tools available based on authentication status"
            )
            asyncio.run(
                run_http_server(
                    server,
                    host,
                    port,
                    api_key=api_key,
                    allow_trading=allow_trading,
                )
            )
        return 0
    except KeyboardInterrupt:
        logger.info("\nServer stopped by user")
        # Logout all brokers
        from open_stocks_mcp.brokers.registry import (
            RegistryNotInitializedError,
            get_broker_registry_sync,
        )

        try:
            registry = get_broker_registry_sync()
            asyncio.run(registry.logout_all())
        except RegistryNotInitializedError:
            # Registry not initialized - no brokers to logout
            pass
        return 0
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
