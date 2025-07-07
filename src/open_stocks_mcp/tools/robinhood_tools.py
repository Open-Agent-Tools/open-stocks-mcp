"""MCP tools for Robin Stocks."""

import robin_stocks.robinhood as rh
from mcp import types

from open_stocks_mcp.logging_config import logger


async def get_account_info() -> types.TextContent:
    """
    Retrieves basic information about the Robinhood account.

    Returns:
        A TextContent object containing account details.
    """
    try:
        # Corrected function to load user profile
        account_info = rh.load_user_profile()
        info_text = (
            f"Account Info:\n"
            f"- User: {account_info.get('username', 'N/A')}\n"
            f"- Created At: {account_info.get('created_at', 'N/A')}"
        )
        logger.info("Successfully retrieved account info.")
        return types.TextContent(type="text", text=info_text)
    except Exception as e:
        logger.error(f"Failed to retrieve account info: {e}")
        return types.TextContent(type="text", text=f"❌ Error: {e}")


async def get_portfolio() -> types.TextContent:
    """
    Provides a high-level overview of the portfolio.

    Returns:
        A TextContent object containing the portfolio overview.
    """
    try:
        portfolio = rh.load_portfolio_profile()
        # Added graceful handling for potentially missing values
        market_value = portfolio.get('market_value', 'N/A')
        equity = portfolio.get('equity', 'N/A')
        buying_power = portfolio.get('buying_power', 'N/A')

        portfolio_text = (
            f"Portfolio Overview:\n"
            f"- Market Value: ${market_value}\n"
            f"- Equity: ${equity}\n"
            f"- Buying Power: ${buying_power}"
        )
        logger.info("Successfully retrieved portfolio overview.")
        return types.TextContent(type="text", text=portfolio_text)
    except Exception as e:
        logger.error(f"Failed to retrieve portfolio overview: {e}")
        return types.TextContent(type="text", text=f"❌ Error: {e}")


async def get_orders() -> types.TextContent:
    """
    Retrieves a list of recent order history and their statuses.

    Returns:
        A TextContent object containing recent orders.
    """
    try:
        # Corrected function to get stock orders
        orders = rh.get_all_stock_orders()
        if not orders:
            return types.TextContent(type="text", text="No recent orders found.")

        orders_text = "Recent Orders:\n"
        # Limit to the 5 most recent orders and handle potential missing data
        for order in orders[:5]:
            instrument_url = order.get('instrument')
            symbol = rh.get_symbol_by_url(instrument_url) if instrument_url else 'N/A'
            created_at = order.get('last_transaction_at', order.get('created_at', 'N/A'))
            side = order.get('side', 'N/A').upper()
            quantity = order.get('quantity', 'N/A')
            avg_price = order.get('average_price', 'N/A')
            state = order.get('state', 'N/A')

            orders_text += (
                f"- {created_at} | {side} {symbol} | "
                f"Qty: {quantity} @ ${avg_price} | Status: {state}\n"
            )
        logger.info("Successfully retrieved recent orders.")
        return types.TextContent(type="text", text=orders_text)
    except Exception as e:
        logger.error(f"Failed to retrieve recent orders: {e}", exc_info=True)
        return types.TextContent(type="text", text=f"❌ Error: {e}")
