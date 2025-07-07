"""MCP tools for Robin Stocks order operations."""

import robin_stocks.robinhood as rh

from open_stocks_mcp.logging_config import logger


async def get_stock_orders() -> dict:
    """
    Retrieves a list of recent stock order history and their statuses.

    Returns:
        A JSON object containing recent stock orders in the result field.
    """
    try:
        # Get stock orders specifically
        orders = rh.get_all_stock_orders()
        if not orders:
            return {
                "result": {
                    "orders": [],
                    "message": "No recent stock orders found.",
                    "status": "success",
                }
            }

        # Limit to the 5 most recent orders and handle potential missing data
        order_list = []
        for order in orders[:5]:
            instrument_url = order.get("instrument")
            symbol = rh.get_symbol_by_url(instrument_url) if instrument_url else "N/A"

            order_data = {
                "symbol": symbol,
                "side": order.get("side", "N/A").upper(),
                "quantity": order.get("quantity", "N/A"),
                "average_price": order.get("average_price", "N/A"),
                "state": order.get("state", "N/A"),
                "created_at": order.get(
                    "last_transaction_at", order.get("created_at", "N/A")
                ),
            }
            order_list.append(order_data)

        logger.info("Successfully retrieved recent stock orders.")
        return {
            "result": {
                "orders": order_list,
                "count": len(order_list),
                "status": "success",
            }
        }
    except Exception as e:
        logger.error(f"Failed to retrieve recent stock orders: {e}", exc_info=True)
        return {"result": {"error": str(e), "status": "error"}}


async def get_options_orders() -> dict:
    """
    Retrieves a list of recent options order history and their statuses.

    Returns:
        A JSON object containing recent options orders in the result field.
    """
    try:
        # TODO: Implement options orders retrieval
        # Use rh.get_all_option_orders() when implemented
        logger.info("Options orders retrieval not yet implemented.")
        return {
            "result": {
                "message": "Options orders retrieval not yet implemented. Coming soon!",
                "status": "not_implemented",
            }
        }
    except Exception as e:
        logger.error(f"Failed to retrieve options orders: {e}", exc_info=True)
        return {"result": {"error": str(e), "status": "error"}}
