"""MCP tools for Robin Stocks order operations."""

from typing import Any

import robin_stocks.robinhood as rh

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.error_handling import (
    create_success_response,
    execute_with_retry,
    handle_robin_stocks_errors,
    log_api_call,
    sanitize_api_response,
)


@handle_robin_stocks_errors
async def get_stock_orders() -> dict[str, Any]:
    """
    Retrieves a list of recent stock order history and their statuses.

    Returns:
        A JSON object containing recent stock orders in the result field.
    """
    log_api_call("get_stock_orders")

    # Get stock orders with retry logic
    orders = await execute_with_retry(rh.get_all_stock_orders)

    if not orders:
        return create_success_response(
            {"orders": [], "message": "No recent stock orders found.", "count": 0}
        )

    # Limit to the 5 most recent orders and handle potential missing data
    order_list = []
    for order in orders[:5]:
        # Sanitize order data
        order = sanitize_api_response(order)

        instrument_url = order.get("instrument")
        symbol = "N/A"
        if instrument_url:
            try:
                symbol = await execute_with_retry(rh.get_symbol_by_url, instrument_url)
            except Exception as e:
                logger.warning(
                    f"Failed to get symbol for instrument {instrument_url}: {e}"
                )

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
    return create_success_response({"orders": order_list, "count": len(order_list)})


@handle_robin_stocks_errors
async def get_options_orders() -> dict[str, Any]:
    """
    Retrieves a list of recent options order history and their statuses.

    Returns:
        A JSON object containing recent options orders in the result field.
    """
    log_api_call("get_options_orders")

    try:
        # Try to get options orders with retry logic
        orders = await execute_with_retry(rh.get_all_option_orders)

        if not orders:
            return create_success_response(
                {"orders": [], "message": "No recent options orders found.", "count": 0}
            )

        # Limit to the 5 most recent orders
        order_list = []
        for order in orders[:5]:
            # Sanitize order data
            order = sanitize_api_response(order)

            order_data = {
                "option_type": order.get("type", "N/A"),
                "chain_symbol": order.get("chain_symbol", "N/A"),
                "side": order.get("direction", "N/A").upper(),
                "quantity": order.get("quantity", "N/A"),
                "price": order.get("price", "N/A"),
                "state": order.get("state", "N/A"),
                "created_at": order.get("created_at", "N/A"),
            }
            order_list.append(order_data)

        logger.info("Successfully retrieved recent options orders.")
        return create_success_response({"orders": order_list, "count": len(order_list)})

    except Exception as e:
        # If options orders API is not available or not implemented
        if "not found" in str(e).lower() or "not implemented" in str(e).lower():
            logger.info(
                "Options orders retrieval not yet implemented or not available."
            )
            return create_success_response(
                {
                    "message": "Options orders retrieval not yet implemented or not available. Coming soon!",
                    "status": "not_implemented",
                    "orders": [],
                    "count": 0,
                }
            )
        # Re-raise other errors to be handled by the decorator
        raise
