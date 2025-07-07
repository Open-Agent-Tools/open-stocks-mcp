"""MCP tools for Robin Stocks account operations."""

import robin_stocks.robinhood as rh

from open_stocks_mcp.logging_config import logger


async def get_account_info() -> dict:
    """
    Retrieves basic information about the Robinhood account.

    Returns:
        A JSON object containing account details in the result field.
    """
    try:
        # Corrected function to load user profile
        account_info = rh.load_user_profile()
        logger.info("Successfully retrieved account info.")
        return {
            "result": {
                "username": account_info.get("username", "N/A"),
                "created_at": account_info.get("created_at", "N/A"),
                "status": "success",
            }
        }
    except Exception as e:
        logger.error(f"Failed to retrieve account info: {e}")
        return {"result": {"error": str(e), "status": "error"}}


async def get_portfolio() -> dict:
    """
    Provides a high-level overview of the portfolio.

    Returns:
        A JSON object containing the portfolio overview in the result field.
    """
    try:
        portfolio = rh.load_portfolio_profile()
        logger.info("Successfully retrieved portfolio overview.")
        return {
            "result": {
                "market_value": portfolio.get("market_value", "N/A"),
                "equity": portfolio.get("equity", "N/A"),
                "buying_power": portfolio.get("buying_power", "N/A"),
                "status": "success",
            }
        }
    except Exception as e:
        logger.error(f"Failed to retrieve portfolio overview: {e}")
        return {"result": {"error": str(e), "status": "error"}}


async def get_account_details() -> dict:
    """
    Retrieves comprehensive account details including buying power and cash balances.

    Returns:
        A JSON object containing detailed account information in the result field.
    """
    try:
        # Use phoenix account API for unified account data
        import asyncio

        loop = asyncio.get_event_loop()
        account_data = await loop.run_in_executor(None, rh.load_phoenix_account)

        if not account_data:
            return {
                "result": {"message": "No account data found.", "status": "no_data"}
            }

        logger.info("Successfully retrieved account details.")
        return {
            "result": {
                "portfolio_equity": account_data.get("portfolio_equity", "N/A"),
                "total_equity": account_data.get("total_equity", "N/A"),
                "account_buying_power": account_data.get("account_buying_power", "N/A"),
                "options_buying_power": account_data.get("options_buying_power", "N/A"),
                "crypto_buying_power": account_data.get("crypto_buying_power", "N/A"),
                "uninvested_cash": account_data.get("uninvested_cash", "N/A"),
                "withdrawable_cash": account_data.get("withdrawable_cash", "N/A"),
                "cash_available_from_instant_deposits": account_data.get(
                    "cash_available_from_instant_deposits", "N/A"
                ),
                "cash_held_for_orders": account_data.get("cash_held_for_orders", "N/A"),
                "near_margin_call": account_data.get("near_margin_call", "N/A"),
                "status": "success",
            }
        }
    except Exception as e:
        logger.error(f"Failed to retrieve account details: {e}", exc_info=True)
        return {"result": {"error": str(e), "status": "error"}}


async def get_positions() -> dict:
    """
    Retrieves current stock positions with quantities and values.

    Returns:
        A JSON object containing current stock positions in the result field.
    """
    try:
        import asyncio

        loop = asyncio.get_event_loop()
        positions = await loop.run_in_executor(None, rh.get_open_stock_positions)

        if not positions:
            return {
                "result": {
                    "positions": [],
                    "count": 0,
                    "message": "No open stock positions found.",
                    "status": "success",
                }
            }

        position_list = []
        for position in positions:
            # Get symbol from instrument URL
            instrument_url = position.get("instrument")
            symbol = rh.get_symbol_by_url(instrument_url) if instrument_url else "N/A"

            quantity = position.get("quantity", "0")

            # Only include positions with non-zero quantity
            if float(quantity) > 0:
                position_data = {
                    "symbol": symbol,
                    "quantity": quantity,
                    "average_buy_price": position.get("average_buy_price", "0"),
                    "updated_at": position.get("updated_at", "N/A"),
                }
                position_list.append(position_data)

        logger.info("Successfully retrieved current positions.")
        return {
            "result": {
                "positions": position_list,
                "count": len(position_list),
                "status": "success",
            }
        }
    except Exception as e:
        logger.error(f"Failed to retrieve positions: {e}", exc_info=True)
        return {"result": {"error": str(e), "status": "error"}}


async def get_portfolio_history(span: str = "week") -> dict:
    """
    Retrieves historical portfolio performance data.

    Args:
        span: Time span for history ('day', 'week', 'month', '3month', 'year', '5year', 'all')

    Returns:
        A JSON object containing portfolio history in the result field.
    """
    try:
        import asyncio

        loop = asyncio.get_event_loop()
        history = await loop.run_in_executor(
            None, rh.get_historical_portfolio, None, span, "regular"
        )

        if not history:
            return {
                "result": {
                    "message": "No portfolio history found.",
                    "status": "no_data",
                }
            }

        # Handle case where history is a list vs dict
        if isinstance(history, list):
            if not history:
                return {
                    "result": {
                        "message": "No portfolio history found.",
                        "status": "no_data",
                    }
                }
            historicals = history
            total_return = "N/A"
        else:
            historicals = history.get("historicals", [])
            total_return = history.get("total_return", "N/A")

        # Show last 5 data points
        recent_data = []
        for data_point in historicals[-5:]:
            if data_point:  # Skip None entries
                recent_data.append(
                    {
                        "date": data_point.get("begins_at", "N/A"),
                        "total_equity": data_point.get("adjusted_close_equity", "N/A"),
                    }
                )

        logger.info("Successfully retrieved portfolio history.")
        return {
            "result": {
                "span": span,
                "total_return": total_return,
                "data_points_count": len(historicals),
                "recent_performance": recent_data,
                "status": "success",
            }
        }
    except Exception as e:
        logger.error(f"Failed to retrieve portfolio history: {e}", exc_info=True)
        return {"result": {"error": str(e), "status": "error"}}
