"""Schwab trading MCP tools using schwab-py library."""

import asyncio
import datetime
from typing import Any

from schwab.orders.equities import (
    equity_buy_limit,
    equity_buy_market,
    equity_sell_limit,
    equity_sell_market,
)

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.broker_utils import get_authenticated_broker_or_error
from open_stocks_mcp.tools.error_handling import (
    create_error_response,
    create_success_response,
    handle_schwab_errors,
)


@handle_schwab_errors
async def place_schwab_order(
    account_hash: str, order_spec: dict[str, Any]
) -> dict[str, Any]:
    """Place an order with Schwab.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        order_spec: Order specification (use order builder functions)

    Returns:
        Dict with order placement result
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"place order for {account_hash}"
    )
    if error:
        return error

    try:

        def _place_order() -> Any:
            response = broker.client.place_order(account_hash, order_spec)
            return response

        response = await asyncio.to_thread(_place_order)

        # Check response status
        if response.status_code in (200, 201):
            # Extract order ID from Location header if available
            location = response.headers.get("Location", "")
            order_id = location.split("/")[-1] if location else None

            return create_success_response(
                {
                    "status": "order_placed",
                    "order_id": order_id,
                    "status_code": response.status_code,
                }
            )
        else:
            return create_error_response(
                ValueError(
                    f"Order placement failed with status {response.status_code}: {response.text}"
                )
            )

    except Exception as e:
        logger.error(f"Error placing Schwab order: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_buy_market(
    account_hash: str, symbol: str, quantity: int
) -> dict[str, Any]:
    """Place a market buy order for stock.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        symbol: Stock ticker symbol
        quantity: Number of shares to buy

    Returns:
        Dict with order placement result
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"buy {quantity} shares of {symbol}"
    )
    if error:
        return error

    try:
        # Create order spec
        order_spec = equity_buy_market(symbol.upper(), quantity)

        def _place_order() -> Any:
            response = broker.client.place_order(account_hash, order_spec)
            return response

        response = await asyncio.to_thread(_place_order)

        # Check response status
        if response.status_code in (200, 201):
            location = response.headers.get("Location", "")
            order_id = location.split("/")[-1] if location else None

            return create_success_response(
                {
                    "status": "order_placed",
                    "action": "buy",
                    "symbol": symbol.upper(),
                    "quantity": quantity,
                    "order_type": "market",
                    "order_id": order_id,
                }
            )
        else:
            return create_error_response(
                ValueError(
                    f"Buy order failed with status {response.status_code}: {response.text}"
                )
            )

    except Exception as e:
        logger.error(f"Error placing Schwab buy order for {symbol}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_sell_market(
    account_hash: str, symbol: str, quantity: int
) -> dict[str, Any]:
    """Place a market sell order for stock.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        symbol: Stock ticker symbol
        quantity: Number of shares to sell

    Returns:
        Dict with order placement result
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"sell {quantity} shares of {symbol}"
    )
    if error:
        return error

    try:
        # Create order spec
        order_spec = equity_sell_market(symbol.upper(), quantity)

        def _place_order() -> Any:
            response = broker.client.place_order(account_hash, order_spec)
            return response

        response = await asyncio.to_thread(_place_order)

        # Check response status
        if response.status_code in (200, 201):
            location = response.headers.get("Location", "")
            order_id = location.split("/")[-1] if location else None

            return create_success_response(
                {
                    "status": "order_placed",
                    "action": "sell",
                    "symbol": symbol.upper(),
                    "quantity": quantity,
                    "order_type": "market",
                    "order_id": order_id,
                }
            )
        else:
            return create_error_response(
                ValueError(
                    f"Sell order failed with status {response.status_code}: {response.text}"
                )
            )

    except Exception as e:
        logger.error(f"Error placing Schwab sell order for {symbol}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_buy_limit(
    account_hash: str, symbol: str, quantity: int, price: float
) -> dict[str, Any]:
    """Place a limit buy order for stock.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        symbol: Stock ticker symbol
        quantity: Number of shares to buy
        price: Limit price

    Returns:
        Dict with order placement result
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"buy {quantity} shares of {symbol} at ${price}"
    )
    if error:
        return error

    try:
        # Create order spec
        order_spec = equity_buy_limit(symbol.upper(), quantity, price)

        def _place_order() -> Any:
            response = broker.client.place_order(account_hash, order_spec)
            return response

        response = await asyncio.to_thread(_place_order)

        # Check response status
        if response.status_code in (200, 201):
            location = response.headers.get("Location", "")
            order_id = location.split("/")[-1] if location else None

            return create_success_response(
                {
                    "status": "order_placed",
                    "action": "buy",
                    "symbol": symbol.upper(),
                    "quantity": quantity,
                    "order_type": "limit",
                    "limit_price": price,
                    "order_id": order_id,
                }
            )
        else:
            return create_error_response(
                ValueError(
                    f"Limit buy order failed with status {response.status_code}: {response.text}"
                )
            )

    except Exception as e:
        logger.error(f"Error placing Schwab limit buy order for {symbol}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_sell_limit(
    account_hash: str, symbol: str, quantity: int, price: float
) -> dict[str, Any]:
    """Place a limit sell order for stock.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        symbol: Stock ticker symbol
        quantity: Number of shares to sell
        price: Limit price

    Returns:
        Dict with order placement result
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"sell {quantity} shares of {symbol} at ${price}"
    )
    if error:
        return error

    try:
        # Create order spec
        order_spec = equity_sell_limit(symbol.upper(), quantity, price)

        def _place_order() -> Any:
            response = broker.client.place_order(account_hash, order_spec)
            return response

        response = await asyncio.to_thread(_place_order)

        # Check response status
        if response.status_code in (200, 201):
            location = response.headers.get("Location", "")
            order_id = location.split("/")[-1] if location else None

            return create_success_response(
                {
                    "status": "order_placed",
                    "action": "sell",
                    "symbol": symbol.upper(),
                    "quantity": quantity,
                    "order_type": "limit",
                    "limit_price": price,
                    "order_id": order_id,
                }
            )
        else:
            return create_error_response(
                ValueError(
                    f"Limit sell order failed with status {response.status_code}: {response.text}"
                )
            )

    except Exception as e:
        logger.error(f"Error placing Schwab limit sell order for {symbol}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def get_schwab_orders(account_hash: str, max_results: int = 50) -> dict[str, Any]:
    """Get orders for a Schwab account.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        max_results: Maximum number of orders to return (default: 50)

    Returns:
        Dict with list of orders
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get orders for {account_hash}"
    )
    if error:
        return error

    try:

        def _get_orders() -> Any:
            response = broker.client.get_orders_for_account(
                account_hash, max_results=max_results
            )
            return response.json()

        orders_data = await asyncio.to_thread(_get_orders)

        return create_success_response(
            {
                "orders": orders_data,
                "count": len(orders_data) if isinstance(orders_data, list) else 1,
            }
        )

    except Exception as e:
        logger.error(f"Error getting Schwab orders: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def cancel_schwab_order(account_hash: str, order_id: str) -> dict[str, Any]:
    """Cancel a specific order.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        order_id: Order ID to cancel

    Returns:
        Dict with cancellation result
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"cancel order {order_id}"
    )
    if error:
        return error

    try:

        def _cancel_order() -> Any:
            response = broker.client.cancel_order(order_id, account_hash)
            return response

        response = await asyncio.to_thread(_cancel_order)

        # Check response status
        if response.status_code in (200, 204):
            return create_success_response(
                {
                    "status": "order_cancelled",
                    "order_id": order_id,
                }
            )
        else:
            return create_error_response(
                ValueError(
                    f"Order cancellation failed with status {response.status_code}: {response.text}"
                )
            )

    except Exception as e:
        logger.error(f"Error cancelling Schwab order {order_id}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def get_schwab_order_by_id(account_hash: str, order_id: str) -> dict[str, Any]:
    """Get details for a specific order.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        order_id: Order ID to retrieve

    Returns:
        Dict with order details
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get order {order_id}"
    )
    if error:
        return error

    try:

        def _get_order() -> Any:
            response = broker.client.get_order(order_id, account_hash)
            return response.json()

        order_data = await asyncio.to_thread(_get_order)

        return create_success_response(order_data)

    except Exception as e:
        logger.error(f"Error getting Schwab order {order_id}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_get_transactions(
    account_hash: str,
    start_date: str | None = None,
    end_date: str | None = None,
    transaction_types: list[str] | None = None,
    symbol: str | None = None,
) -> dict[str, Any]:
    """Get transactions for a Schwab account with optional filters."""
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get transactions for {account_hash}"
    )
    if error:
        return error

    try:
        parsed_start_date = (
            datetime.date.fromisoformat(start_date) if start_date is not None else None
        )
        parsed_end_date = (
            datetime.date.fromisoformat(end_date) if end_date is not None else None
        )

        response = await asyncio.to_thread(
            broker.client.get_transactions,
            account_hash,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            transaction_types=transaction_types,
            symbol=symbol,
        )
        transactions_data = response.json() if hasattr(response, "json") else response
        return create_success_response(
            {
                "transactions": transactions_data,
                "count": len(transactions_data)
                if isinstance(transactions_data, list)
                else 1,
            }
        )
    except Exception as e:
        logger.error(f"Error getting Schwab transactions: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_get_transactions_by_date(
    account_hash: str,
    start_date: str,
    end_date: str,
    transaction_types: list[str] | None = None,
    symbol: str | None = None,
) -> dict[str, Any]:
    """Get transactions for a Schwab account within a required date range."""
    return await schwab_get_transactions(
        account_hash,
        start_date=start_date,
        end_date=end_date,
        transaction_types=transaction_types,
        symbol=symbol,
    )
