"""Schwab trading MCP tools using schwab-py library."""

import asyncio
import datetime
from typing import Any

from schwab.orders.common import (
    Duration,
    EquityInstruction,
    OrderStrategyType,
    OrderType,
    Session,
)
from schwab.orders.equities import (
    equity_buy_limit,
    equity_buy_market,
    equity_sell_limit,
    equity_sell_market,
)
from schwab.orders.options import (
    OrderBuilder,
    bear_call_vertical_open,
    bear_put_vertical_open,
    bull_call_vertical_open,
    bull_put_vertical_open,
    option_buy_to_open_limit,
    option_sell_to_close_limit,
)

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.broker_utils import (
    execute_broker_request,
    get_authenticated_broker_or_error,
)
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

        response = await execute_broker_request(_place_order, retry_safe=False)

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

        response = await execute_broker_request(_place_order, retry_safe=False)

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

        response = await execute_broker_request(_place_order, retry_safe=False)

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

        response = await execute_broker_request(_place_order, retry_safe=False)

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

        response = await execute_broker_request(_place_order, retry_safe=False)

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

        orders_data = await execute_broker_request(_get_orders, retry_safe=True)

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

        response = await execute_broker_request(_cancel_order, retry_safe=False)

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

        order_data = await execute_broker_request(_get_order, retry_safe=True)

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


@handle_schwab_errors
async def get_schwab_transaction(
    account_hash: str, transaction_id: str
) -> dict[str, Any]:
    """Get details for a specific transaction.

    Args:
        account_hash: Account hash from schwab_account_numbers()
        transaction_id: Transaction ID to retrieve

    Returns:
        Dict with transaction details
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get transaction {transaction_id}"
    )
    if error:
        return error

    try:

        def _get_transaction() -> Any:
            response = broker.client.get_transaction(account_hash, transaction_id)
            return response.json()

        transaction_data = await asyncio.to_thread(_get_transaction)

        return create_success_response(transaction_data)

    except Exception as e:
        logger.error(f"Error getting Schwab transaction {transaction_id}: {e}")
        return create_error_response(e)


# Open/cancellable order statuses for equity orders
_OPEN_EQUITY_STATUSES = frozenset(
    {
        "WORKING",
        "NEW",
        "QUEUED",
        "ACCEPTED",
        "AWAITING_CONDITION",
        "AWAITING_PARENT_ORDER",
        "AWAITING_RELEASE_TIME",
        "AWAITING_STOP_CONDITION",
        "PENDING_ACTIVATION",
    }
)


def _is_open_equity_order(order: dict[str, Any]) -> bool:
    """Return True when order is open and all legs are equity instruments."""
    if order.get("status") not in _OPEN_EQUITY_STATUSES:
        return False
    legs = order.get("orderLegCollection", [])
    return bool(legs) and all(
        leg.get("instrument", {}).get("assetType") == "EQUITY" for leg in legs
    )


def _is_open_option_order(order: dict[str, Any]) -> bool:
    """Return True when order is open and all legs are option instruments."""
    if order.get("status") not in _OPEN_EQUITY_STATUSES:
        return False
    legs = order.get("orderLegCollection", [])
    return bool(legs) and all(
        leg.get("instrument", {}).get("assetType") == "OPTION" for leg in legs
    )


@handle_schwab_errors
async def schwab_order_sell_stop(
    account_hash: str, symbol: str, quantity: int, stop_price: str
) -> dict[str, Any]:
    """Place a stop sell order for stock.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        symbol: Stock ticker symbol
        quantity: Number of shares to sell
        stop_price: Stop trigger price as a string (e.g. "148.00")

    Returns:
        Dict with order placement result
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"sell stop {quantity} shares of {symbol} at {stop_price}"
    )
    if error:
        return error

    try:
        order_spec = (
            OrderBuilder()
            .set_order_type(OrderType.STOP)
            .set_order_strategy_type(OrderStrategyType.SINGLE)
            .set_duration(Duration.DAY)
            .set_session(Session.NORMAL)
            .set_stop_price(stop_price)
            .add_equity_leg(EquityInstruction.SELL, symbol.upper(), quantity)
            .build()
        )

        def _place() -> Any:
            return broker.client.place_order(account_hash, order_spec)

        response = await execute_broker_request(_place, retry_safe=False)

        if response.status_code in (200, 201):
            location = response.headers.get("Location", "")
            order_id = location.split("/")[-1] if location else None
            return create_success_response(
                {
                    "status": "order_placed",
                    "action": "sell",
                    "symbol": symbol.upper(),
                    "quantity": quantity,
                    "order_type": "stop",
                    "stop_price": stop_price,
                    "order_id": order_id,
                }
            )
        else:
            return create_error_response(
                ValueError(
                    f"Stop sell order failed with status {response.status_code}: {response.text}"
                )
            )

    except Exception as e:
        logger.error(f"Error placing Schwab stop sell order for {symbol}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_get_open_stock_orders(
    account_hash: str, max_results: int = 200
) -> dict[str, Any]:
    """Get open (cancellable) equity orders for a Schwab account.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        max_results: Maximum number of orders to fetch from API before filtering

    Returns:
        Dict with list of open equity orders
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get open stock orders for {account_hash}"
    )
    if error:
        return error

    try:

        def _get_orders() -> Any:
            response = broker.client.get_orders_for_account(
                account_hash, max_results=max_results
            )
            return response.json()

        orders_data = await execute_broker_request(_get_orders, retry_safe=True)
        all_orders = orders_data if isinstance(orders_data, list) else []
        open_orders = [o for o in all_orders if _is_open_equity_order(o)]

        return create_success_response(
            {"orders": open_orders, "count": len(open_orders)}
        )

    except Exception as e:
        logger.error(f"Error getting open Schwab stock orders: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_cancel_all_stock_orders(
    account_hash: str, max_results: int = 200
) -> dict[str, Any]:
    """Cancel all open equity orders for a Schwab account.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        max_results: Maximum number of orders to fetch before filtering

    Returns:
        Dict with counts of cancelled and failed orders
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"cancel all stock orders for {account_hash}"
    )
    if error:
        return error

    try:

        def _get_orders() -> Any:
            response = broker.client.get_orders_for_account(
                account_hash, max_results=max_results
            )
            return response.json()

        orders_data = await execute_broker_request(_get_orders, retry_safe=True)
        all_orders = orders_data if isinstance(orders_data, list) else []
        open_orders = [o for o in all_orders if _is_open_equity_order(o)]

        cancelled_count = 0
        failed_count = 0
        failed_orders: list[dict[str, Any]] = []

        for order in open_orders:
            order_id = str(order.get("orderId", ""))
            try:

                def _cancel(oid: str = order_id) -> Any:
                    return broker.client.cancel_order(oid, account_hash)

                response = await execute_broker_request(_cancel, retry_safe=False)
                if response.status_code in (200, 204):
                    cancelled_count += 1
                else:
                    failed_count += 1
                    failed_orders.append(
                        {"order_id": order_id, "status_code": response.status_code}
                    )
            except Exception as cancel_exc:
                failed_count += 1
                failed_orders.append({"order_id": order_id, "error": str(cancel_exc)})

        return create_success_response(
            {
                "cancelled_count": cancelled_count,
                "failed_count": failed_count,
                "failed_orders": failed_orders,
            }
        )

    except Exception as e:
        logger.error(f"Error cancelling all Schwab stock orders: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_order_buy_option_limit(
    account_hash: str, option_symbol: str, quantity: int, price: str
) -> dict[str, Any]:
    """Place a limit buy-to-open order for an option contract.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        option_symbol: OCC option symbol (e.g. "AAPL  251219C00150000")
        quantity: Number of contracts to buy
        price: Limit price as a string (e.g. "5.50")

    Returns:
        Dict with order placement result
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"buy {quantity} {option_symbol} option contracts at {price}"
    )
    if error:
        return error

    try:
        order_spec = option_buy_to_open_limit(option_symbol, quantity, price).build()

        def _place() -> Any:
            return broker.client.place_order(account_hash, order_spec)

        response = await execute_broker_request(_place, retry_safe=False)

        if response.status_code in (200, 201):
            location = response.headers.get("Location", "")
            order_id = location.split("/")[-1] if location else None
            return create_success_response(
                {
                    "status": "order_placed",
                    "action": "buy_to_open",
                    "option_symbol": option_symbol,
                    "quantity": quantity,
                    "order_type": "limit",
                    "limit_price": price,
                    "order_id": order_id,
                }
            )
        else:
            return create_error_response(
                ValueError(
                    f"Option buy limit order failed with status {response.status_code}: {response.text}"
                )
            )

    except Exception as e:
        logger.error(f"Error placing Schwab option buy limit for {option_symbol}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_order_sell_option_limit(
    account_hash: str, option_symbol: str, quantity: int, price: str
) -> dict[str, Any]:
    """Place a limit sell-to-close order for an option contract.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        option_symbol: OCC option symbol (e.g. "AAPL  251219C00150000")
        quantity: Number of contracts to sell
        price: Limit price as a string (e.g. "4.00")

    Returns:
        Dict with order placement result
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"sell {quantity} {option_symbol} option contracts at {price}"
    )
    if error:
        return error

    try:
        order_spec = option_sell_to_close_limit(option_symbol, quantity, price).build()

        def _place() -> Any:
            return broker.client.place_order(account_hash, order_spec)

        response = await execute_broker_request(_place, retry_safe=False)

        if response.status_code in (200, 201):
            location = response.headers.get("Location", "")
            order_id = location.split("/")[-1] if location else None
            return create_success_response(
                {
                    "status": "order_placed",
                    "action": "sell_to_close",
                    "option_symbol": option_symbol,
                    "quantity": quantity,
                    "order_type": "limit",
                    "limit_price": price,
                    "order_id": order_id,
                }
            )
        else:
            return create_error_response(
                ValueError(
                    f"Option sell limit order failed with status {response.status_code}: {response.text}"
                )
            )

    except Exception as e:
        logger.error(f"Error placing Schwab option sell limit for {option_symbol}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_cancel_option_order(
    account_hash: str, order_id: str
) -> dict[str, Any]:
    """Cancel a specific option order.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        order_id: Option order ID to cancel

    Returns:
        Dict with cancellation result
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"cancel option order {order_id}"
    )
    if error:
        return error

    try:

        def _cancel() -> Any:
            return broker.client.cancel_order(order_id, account_hash)

        response = await execute_broker_request(_cancel, retry_safe=False)

        if response.status_code in (200, 204):
            return create_success_response(
                {"status": "order_cancelled", "order_id": order_id}
            )
        else:
            return create_error_response(
                ValueError(
                    f"Option order cancellation failed with status {response.status_code}: {response.text}"
                )
            )

    except Exception as e:
        logger.error(f"Error cancelling Schwab option order {order_id}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_cancel_all_option_orders(
    account_hash: str, max_results: int = 200
) -> dict[str, Any]:
    """Cancel all open option orders for a Schwab account.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        max_results: Maximum number of orders to fetch before filtering

    Returns:
        Dict with counts of cancelled and failed orders
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"cancel all option orders for {account_hash}"
    )
    if error:
        return error

    try:

        def _get_orders() -> Any:
            response = broker.client.get_orders_for_account(
                account_hash, max_results=max_results
            )
            return response.json()

        orders_data = await execute_broker_request(_get_orders, retry_safe=True)
        all_orders = orders_data if isinstance(orders_data, list) else []
        open_option_orders = [o for o in all_orders if _is_open_option_order(o)]

        cancelled_count = 0
        failed_count = 0
        failed_orders: list[dict[str, Any]] = []

        for order in open_option_orders:
            order_id = str(order.get("orderId", ""))
            try:

                def _cancel(oid: str = order_id) -> Any:
                    return broker.client.cancel_order(oid, account_hash)

                response = await execute_broker_request(_cancel, retry_safe=False)
                if response.status_code in (200, 204):
                    cancelled_count += 1
                else:
                    failed_count += 1
                    failed_orders.append(
                        {"order_id": order_id, "status_code": response.status_code}
                    )
            except Exception as cancel_exc:
                failed_count += 1
                failed_orders.append({"order_id": order_id, "error": str(cancel_exc)})

        return create_success_response(
            {
                "cancelled_count": cancelled_count,
                "failed_count": failed_count,
                "failed_orders": failed_orders,
            }
        )

    except Exception as e:
        logger.error(f"Error cancelling all Schwab option orders: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_order_option_credit_spread(
    account_hash: str,
    option_type: str,
    short_symbol: str,
    long_symbol: str,
    quantity: int,
    net_credit: str,
) -> dict[str, Any]:
    """Place a vertical credit spread order.

    For CALL: bear call spread — sell the lower strike, buy the higher strike.
    For PUT:  bull put spread — sell the higher strike, buy the lower strike.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        option_type: "CALL" or "PUT"
        short_symbol: OCC symbol for the leg you sell (collects premium)
        long_symbol: OCC symbol for the hedge/protective leg
        quantity: Number of spread contracts
        net_credit: Net credit received as a string (e.g. "2.00")

    Returns:
        Dict with order placement result
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"credit spread {option_type} {short_symbol}/{long_symbol}"
    )
    if error:
        return error

    opt = option_type.upper()
    if opt not in ("CALL", "PUT"):
        return create_error_response(
            ValueError(f"option_type must be 'CALL' or 'PUT', got '{option_type}'")
        )

    try:
        if opt == "CALL":
            order_builder = bear_call_vertical_open(
                short_symbol, long_symbol, quantity, net_credit
            )
        else:
            order_builder = bull_put_vertical_open(
                long_symbol, short_symbol, quantity, net_credit
            )

        order_spec = order_builder.build()

        def _place() -> Any:
            return broker.client.place_order(account_hash, order_spec)

        response = await execute_broker_request(_place, retry_safe=False)

        if response.status_code in (200, 201):
            location = response.headers.get("Location", "")
            order_id = location.split("/")[-1] if location else None
            return create_success_response(
                {
                    "status": "order_placed",
                    "spread_type": "credit",
                    "option_type": opt,
                    "short_symbol": short_symbol,
                    "long_symbol": long_symbol,
                    "quantity": quantity,
                    "net_credit": net_credit,
                    "order_id": order_id,
                }
            )
        else:
            return create_error_response(
                ValueError(
                    f"Credit spread order failed with status {response.status_code}: {response.text}"
                )
            )

    except Exception as e:
        logger.error(f"Error placing Schwab credit spread: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_order_option_debit_spread(
    account_hash: str,
    option_type: str,
    long_symbol: str,
    short_symbol: str,
    quantity: int,
    net_debit: str,
) -> dict[str, Any]:
    """Place a vertical debit spread order.

    For CALL: bull call spread — buy the lower strike, sell the higher strike.
    For PUT:  bear put spread — buy the higher strike, sell the lower strike.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        option_type: "CALL" or "PUT"
        long_symbol: OCC symbol for the leg you buy (main directional position)
        short_symbol: OCC symbol for the hedge/short leg
        quantity: Number of spread contracts
        net_debit: Net debit paid as a string (e.g. "3.00")

    Returns:
        Dict with order placement result
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"debit spread {option_type} {long_symbol}/{short_symbol}"
    )
    if error:
        return error

    opt = option_type.upper()
    if opt not in ("CALL", "PUT"):
        return create_error_response(
            ValueError(f"option_type must be 'CALL' or 'PUT', got '{option_type}'")
        )

    try:
        if opt == "CALL":
            order_builder = bull_call_vertical_open(
                long_symbol, short_symbol, quantity, net_debit
            )
        else:
            order_builder = bear_put_vertical_open(
                short_symbol, long_symbol, quantity, net_debit
            )

        order_spec = order_builder.build()

        def _place() -> Any:
            return broker.client.place_order(account_hash, order_spec)

        response = await execute_broker_request(_place, retry_safe=False)

        if response.status_code in (200, 201):
            location = response.headers.get("Location", "")
            order_id = location.split("/")[-1] if location else None
            return create_success_response(
                {
                    "status": "order_placed",
                    "spread_type": "debit",
                    "option_type": opt,
                    "long_symbol": long_symbol,
                    "short_symbol": short_symbol,
                    "quantity": quantity,
                    "net_debit": net_debit,
                    "order_id": order_id,
                }
            )
        else:
            return create_error_response(
                ValueError(
                    f"Debit spread order failed with status {response.status_code}: {response.text}"
                )
            )

    except Exception as e:
        logger.error(f"Error placing Schwab debit spread: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_replace_order(
    account_hash: str, order_id: str, order_spec: dict[str, Any]
) -> dict[str, Any]:
    """Replace (modify) an existing Schwab order.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        order_id: ID of the order to replace
        order_spec: New order specification dict (use order builder helpers)

    Returns:
        Dict with replacement result including the new order ID
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"replace order {order_id}"
    )
    if error:
        return error

    try:

        def _replace() -> Any:
            return broker.client.replace_order(account_hash, order_id, order_spec)

        response = await execute_broker_request(_replace, retry_safe=False)

        if response.status_code in (200, 201):
            location = response.headers.get("Location", "")
            new_order_id = location.split("/")[-1] if location else None
            return create_success_response(
                {
                    "status": "order_replaced",
                    "replaced_order_id": order_id,
                    "new_order_id": new_order_id,
                    "status_code": response.status_code,
                }
            )
        else:
            return create_error_response(
                ValueError(
                    f"Order replacement failed with status {response.status_code}: {response.text}"
                )
            )

    except Exception as e:
        logger.error(f"Error replacing Schwab order {order_id}: {e}")
        return create_error_response(e)
