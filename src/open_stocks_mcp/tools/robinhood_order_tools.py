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


def _executed_quantity(order: dict[str, Any]) -> Any:
    cumulative = order.get("cumulative_quantity")
    if cumulative not in (None, ""):
        return cumulative

    execution_total = 0.0
    has_executions = False
    for execution in order.get("executions") or []:
        if not isinstance(execution, dict):
            continue
        quantity = execution.get("quantity")
        if not isinstance(quantity, str | int | float):
            continue
        try:
            execution_total += float(quantity)
        except (TypeError, ValueError):
            continue
        has_executions = True
    if has_executions:
        return str(execution_total)
    if str(order.get("state") or "").lower() == "filled":
        return order.get("quantity")
    return None


@handle_robin_stocks_errors
async def get_stock_orders(
    start_date: str | None = None, limit: int = 100
) -> dict[str, Any]:
    """
    Retrieves a list of recent stock order history and their statuses.

    Returns:
        A JSON object containing recent stock orders in the result field.
    """
    log_api_call("get_stock_orders")

    if limit <= 0 or limit > 1000:
        return create_success_response(
            {"error": "Limit must be between 1 and 1000", "status": "error"}
        )

    if start_date:
        orders = await execute_with_retry(
            rh.get_all_stock_orders, start_date=start_date
        )
    else:
        orders = await execute_with_retry(rh.get_all_stock_orders)

    if not orders:
        return create_success_response(
            {
                "orders": [],
                "message": "No recent stock orders found.",
                "count": 0,
                "total_available": 0,
                "truncated": False,
                "start_date": start_date,
                "limit": limit,
            }
        )

    order_list = []
    for order in orders[:limit]:
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

        state = order.get("state", "N/A")
        order_data = {
            "order_id": order.get("id"),
            "symbol": symbol,
            "side": order.get("side", "N/A").upper(),
            "quantity": order.get("quantity", "N/A"),
            "requested_quantity": order.get("quantity"),
            "executed_quantity": _executed_quantity(order),
            "average_price": order.get("average_price", "N/A"),
            "price": order.get("price"),
            "order_type": order.get("type"),
            "state": state,
            "created_at": order.get("created_at", "N/A"),
            "last_transaction_at": order.get("last_transaction_at"),
            "updated_at": order.get("updated_at"),
        }
        order_list.append(order_data)

    logger.info("Successfully retrieved recent stock orders.")
    return create_success_response(
        {
            "orders": order_list,
            "count": len(order_list),
            "total_available": len(orders),
            "truncated": len(orders) > limit,
            "start_date": start_date,
            "limit": limit,
        }
    )


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
