"""MCP tools for Robin Stocks trading operations."""

from typing import Any

import robin_stocks.robinhood as rh

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.batch_fetch import dedupe_preserving_order, gather_bounded
from open_stocks_mcp.tools.error_handling import (
    create_success_response,
    execute_with_retry,
    handle_robin_stocks_errors,
    log_api_call,
    sanitize_api_response,
)

# Options Order Placement Tools


@handle_robin_stocks_errors
async def order_buy_option_limit(
    instrument_id: str, quantity: int, limit_price: float
) -> dict[str, Any]:
    """
    Places a limit buy order for an option.

    Args:
        instrument_id: The option instrument ID
        quantity: The number of option contracts to buy
        limit_price: The maximum price per contract

    Returns:
        A JSON object containing order confirmation in the result field.
    """
    # Will log with actual symbol after instrument lookup

    # Validation
    if not instrument_id or not isinstance(instrument_id, str):
        return create_success_response(
            {"error": "Invalid instrument_id provided", "status": "error"}
        )

    if not isinstance(quantity, int) or quantity <= 0:
        return create_success_response(
            {"error": "Quantity must be a positive integer", "status": "error"}
        )

    if not isinstance(limit_price, int | float) or limit_price <= 0:
        return create_success_response(
            {"error": "Limit price must be a positive number", "status": "error"}
        )

    # Validate instrument exists and is tradeable
    instrument = await execute_with_retry(
        rh.get_option_instrument_data_by_id, instrument_id
    )
    if not instrument:
        return create_success_response(
            {
                "error": f"Option instrument {instrument_id} not found",
                "status": "error",
            }
        )

    if not instrument.get("tradeable", True):
        return create_success_response(
            {"error": "Option instrument is not tradeable", "status": "error"}
        )

    # Check buying power
    account = await execute_with_retry(rh.load_account_profile)
    buying_power = float(account.get("buying_power", 0))
    estimated_cost = limit_price * quantity * 100  # Options are in contracts of 100

    if buying_power < estimated_cost:
        return create_success_response(
            {
                "error": f"Insufficient buying power. Need ${estimated_cost:.2f}, have ${buying_power:.2f}",
                "status": "error",
            }
        )

    # Extract parameters needed for Robin Stocks API
    symbol = instrument.get("chain_symbol", "")
    expiration_date = instrument.get("expiration_date", "")  # Keep YYYY-MM-DD format
    strike_price = float(instrument.get("strike_price", 0))
    option_type = instrument.get("type", "")

    # Log the API call with correct parameters
    log_api_call(
        "order_buy_option_limit",
        symbol,
        quantity=quantity,
        expiration_date=expiration_date,
        strike_price=strike_price,
        option_type=option_type,
        limit_price=limit_price,
    )

    # Place order using correct Robin Stocks API parameters
    # Signature: order_buy_option_limit(positionEffect, creditOrDebit, price, symbol, quantity, expirationDate, strike, optionType)
    order_result = await execute_with_retry(
        rh.order_buy_option_limit,
        "open",  # positionEffect
        "debit",  # creditOrDebit - buying = paying debit
        limit_price,  # price
        symbol,  # symbol (e.g., 'F')
        quantity,  # quantity
        expiration_date,  # expirationDate (YYYY-MM-DD)
        strike_price,  # strike
        option_type,  # optionType ('call' or 'put')
    )

    if not order_result:
        return create_success_response(
            {"error": "Order placement failed", "status": "error"}
        )

    order_result = sanitize_api_response(order_result)

    logger.info(
        f"Option buy limit order placed for {quantity} contracts of {symbol} ${strike_price} {option_type} at ${limit_price}"
    )
    return create_success_response(
        {
            "order_id": order_result.get("id"),
            "instrument_id": instrument_id,
            "quantity": quantity,
            "limit_price": limit_price,
            "order_type": "limit",
            "side": "buy",
            "position_effect": "open",
            "state": order_result.get("state"),
            "created_at": order_result.get("created_at"),
            "status": "success",
        }
    )


@handle_robin_stocks_errors
async def order_sell_option_limit(
    instrument_id: str, quantity: int, limit_price: float
) -> dict[str, Any]:
    """
    Places a limit sell order for an option.

    Args:
        instrument_id: The option instrument ID
        quantity: The number of option contracts to sell
        limit_price: The minimum price per contract

    Returns:
        A JSON object containing order confirmation in the result field.
    """
    # Will log with actual symbol after instrument lookup

    # Validation
    if not instrument_id or not isinstance(instrument_id, str):
        return create_success_response(
            {"error": "Invalid instrument_id provided", "status": "error"}
        )

    if not isinstance(quantity, int) or quantity <= 0:
        return create_success_response(
            {"error": "Quantity must be a positive integer", "status": "error"}
        )

    if not isinstance(limit_price, int | float) or limit_price <= 0:
        return create_success_response(
            {"error": "Limit price must be a positive number", "status": "error"}
        )

    # Validate instrument exists and is tradeable
    instrument = await execute_with_retry(
        rh.get_option_instrument_data_by_id, instrument_id
    )
    if not instrument:
        return create_success_response(
            {
                "error": f"Option instrument {instrument_id} not found",
                "status": "error",
            }
        )

    if not instrument.get("tradeable", True):
        return create_success_response(
            {"error": "Option instrument is not tradeable", "status": "error"}
        )

    # Check if we have position (for closing) or allow naked selling with margin
    try:
        positions = await execute_with_retry(rh.get_open_option_positions)
        position_quantity = 0.0

        for position in positions:
            if position.get("option") == instrument_id:
                position_quantity = float(position.get("quantity", 0))
                break

        position_effect = "close" if position_quantity >= quantity else "open"

        if position_effect == "close" and position_quantity < quantity:
            return create_success_response(
                {
                    "error": f"Insufficient position. Own {position_quantity} contracts, trying to sell {quantity}",
                    "status": "error",
                }
            )

    except Exception as e:
        logger.warning(f"Failed to check position, assuming naked sell: {e}")
        position_effect = "open"

    # Extract parameters needed for Robin Stocks API
    symbol = instrument.get("chain_symbol", "")
    expiration_date = instrument.get("expiration_date", "")  # Keep YYYY-MM-DD format
    strike_price = float(instrument.get("strike_price", 0))
    option_type = instrument.get("type", "")

    # Log the API call with correct parameters
    log_api_call(
        "order_sell_option_limit",
        symbol,
        quantity=quantity,
        expiration_date=expiration_date,
        strike_price=strike_price,
        option_type=option_type,
        limit_price=limit_price,
    )

    # Place order using correct Robin Stocks API parameters
    # Signature: order_sell_option_limit(positionEffect, creditOrDebit, price, symbol, quantity, expirationDate, strike, optionType)
    order_result = await execute_with_retry(
        rh.order_sell_option_limit,
        position_effect,  # 'open' or 'close'
        "credit",  # creditOrDebit - selling = receiving credit
        limit_price,  # price
        symbol,  # symbol (e.g., 'F')
        quantity,  # quantity
        expiration_date,  # expirationDate (YYYY-MM-DD)
        strike_price,  # strike
        option_type,  # optionType ('call' or 'put')
    )

    if not order_result:
        return create_success_response(
            {"error": "Order placement failed", "status": "error"}
        )

    order_result = sanitize_api_response(order_result)

    logger.info(
        f"Option sell limit order placed for {quantity} contracts of {symbol} ${strike_price} {option_type} at ${limit_price}"
    )
    return create_success_response(
        {
            "order_id": order_result.get("id"),
            "instrument_id": instrument_id,
            "quantity": quantity,
            "limit_price": limit_price,
            "order_type": "limit",
            "side": "sell",
            "position_effect": position_effect,
            "state": order_result.get("state"),
            "created_at": order_result.get("created_at"),
            "status": "success",
        }
    )


@handle_robin_stocks_errors
async def order_option_credit_spread(
    short_instrument_id: str,
    long_instrument_id: str,
    quantity: int,
    credit_price: float,
) -> dict[str, Any]:
    """
    Places a credit spread order (sell short option, buy long option).

    Args:
        short_instrument_id: The option instrument ID to sell (short leg)
        long_instrument_id: The option instrument ID to buy (long leg)
        quantity: The number of spread contracts
        credit_price: The net credit received per spread

    Returns:
        A JSON object containing order confirmation in the result field.
    """
    log_api_call(
        "order_option_credit_spread",
        short_instrument_id,
        long_instrument_id=long_instrument_id,
        quantity=quantity,
        credit_price=credit_price,
    )

    # Validation
    if not short_instrument_id or not isinstance(short_instrument_id, str):
        return create_success_response(
            {"error": "Invalid short_instrument_id provided", "status": "error"}
        )

    if not long_instrument_id or not isinstance(long_instrument_id, str):
        return create_success_response(
            {"error": "Invalid long_instrument_id provided", "status": "error"}
        )

    if not isinstance(quantity, int) or quantity <= 0:
        return create_success_response(
            {"error": "Quantity must be a positive integer", "status": "error"}
        )

    if not isinstance(credit_price, int | float) or credit_price <= 0:
        return create_success_response(
            {"error": "Credit price must be a positive number", "status": "error"}
        )

    # Validate both instruments exist and form a valid spread
    short_instrument = await execute_with_retry(
        rh.get_option_instrument_data_by_id, short_instrument_id
    )
    long_instrument = await execute_with_retry(
        rh.get_option_instrument_data_by_id, long_instrument_id
    )

    if not short_instrument or not long_instrument:
        return create_success_response(
            {"error": "One or both option instruments not found", "status": "error"}
        )

    # Basic validation - both should be same underlying and type
    if short_instrument.get("chain_symbol") != long_instrument.get("chain_symbol"):
        return create_success_response(
            {
                "error": "Options must be on the same underlying symbol",
                "status": "error",
            }
        )

    if short_instrument.get("type") != long_instrument.get("type"):
        return create_success_response(
            {"error": "Options must be same type (call or put)", "status": "error"}
        )

    # Calculate margin requirements (simplified)
    account = await execute_with_retry(rh.load_account_profile)
    buying_power = float(account.get("buying_power", 0))

    # For credit spreads, margin requirement is typically the width of strikes minus credit received
    # This is a simplified calculation
    estimated_margin = credit_price * quantity * 100  # Minimum margin estimate

    if buying_power < estimated_margin:
        return create_success_response(
            {
                "error": f"Insufficient buying power for margin requirements. Need ~${estimated_margin:.2f}, have ${buying_power:.2f}",
                "status": "error",
            }
        )

    # Place spread order
    symbol = short_instrument.get("chain_symbol")
    if not symbol:
        return create_success_response(
            {"error": "Could not extract symbol from instrument", "status": "error"}
        )

    # Create spread array with correct Robin Stocks format
    spread = [
        {
            "expirationDate": short_instrument.get("expiration_date"),
            "strike": short_instrument.get("strike_price"),
            "optionType": short_instrument.get("type"),
            "effect": "open",
            "action": "sell",  # Short leg = sell
        },
        {
            "expirationDate": long_instrument.get("expiration_date"),
            "strike": long_instrument.get("strike_price"),
            "optionType": long_instrument.get("type"),
            "effect": "open",
            "action": "buy",  # Long leg = buy
        },
    ]

    # Use correct Robin Stocks API: order_option_credit_spread(price, symbol, quantity, spread, timeInForce='gtc')
    order_result = await execute_with_retry(
        rh.order_option_credit_spread,
        credit_price,
        symbol,
        quantity,
        spread,
        timeInForce="gfd",
    )

    if not order_result:
        return create_success_response(
            {"error": "Spread order placement failed", "status": "error"}
        )

    # Check for API error responses
    if isinstance(order_result, dict) and "non_field_errors" in order_result:
        error_msgs = order_result["non_field_errors"]
        return create_success_response(
            {"error": f"Order failed: {'; '.join(error_msgs)}", "status": "error"}
        )

    order_result = sanitize_api_response(order_result)

    logger.info(
        f"Credit spread order placed for {quantity} contracts at ${credit_price} credit"
    )
    return create_success_response(
        {
            "order_id": order_result.get("id"),
            "short_instrument_id": short_instrument_id,
            "long_instrument_id": long_instrument_id,
            "quantity": quantity,
            "credit_price": credit_price,
            "order_type": "credit_spread",
            "state": order_result.get("state"),
            "created_at": order_result.get("created_at"),
            "status": "success",
        }
    )


@handle_robin_stocks_errors
async def order_option_debit_spread(
    short_instrument_id: str, long_instrument_id: str, quantity: int, debit_price: float
) -> dict[str, Any]:
    """
    Places a debit spread order (buy long option, sell short option).

    Args:
        short_instrument_id: The option instrument ID to sell (short leg)
        long_instrument_id: The option instrument ID to buy (long leg)
        quantity: The number of spread contracts
        debit_price: The net debit paid per spread

    Returns:
        A JSON object containing order confirmation in the result field.
    """
    log_api_call(
        "order_option_debit_spread",
        short_instrument_id,
        long_instrument_id=long_instrument_id,
        quantity=quantity,
        debit_price=debit_price,
    )

    # Validation
    if not short_instrument_id or not isinstance(short_instrument_id, str):
        return create_success_response(
            {"error": "Invalid short_instrument_id provided", "status": "error"}
        )

    if not long_instrument_id or not isinstance(long_instrument_id, str):
        return create_success_response(
            {"error": "Invalid long_instrument_id provided", "status": "error"}
        )

    if not isinstance(quantity, int) or quantity <= 0:
        return create_success_response(
            {"error": "Quantity must be a positive integer", "status": "error"}
        )

    if not isinstance(debit_price, int | float) or debit_price <= 0:
        return create_success_response(
            {"error": "Debit price must be a positive number", "status": "error"}
        )

    # Validate both instruments exist and form a valid spread
    short_instrument = await execute_with_retry(
        rh.get_option_instrument_data_by_id, short_instrument_id
    )
    long_instrument = await execute_with_retry(
        rh.get_option_instrument_data_by_id, long_instrument_id
    )

    if not short_instrument or not long_instrument:
        return create_success_response(
            {"error": "One or both option instruments not found", "status": "error"}
        )

    # Basic validation - both should be same underlying and type
    if short_instrument.get("chain_symbol") != long_instrument.get("chain_symbol"):
        return create_success_response(
            {
                "error": "Options must be on the same underlying symbol",
                "status": "error",
            }
        )

    if short_instrument.get("type") != long_instrument.get("type"):
        return create_success_response(
            {"error": "Options must be same type (call or put)", "status": "error"}
        )

    # Check buying power for net debit
    account = await execute_with_retry(rh.load_account_profile)
    buying_power = float(account.get("buying_power", 0))
    total_debit = debit_price * quantity * 100  # Total cost

    if buying_power < total_debit:
        return create_success_response(
            {
                "error": f"Insufficient buying power. Need ${total_debit:.2f}, have ${buying_power:.2f}",
                "status": "error",
            }
        )

    # Place spread order
    symbol = short_instrument.get("chain_symbol")
    if not symbol:
        return create_success_response(
            {"error": "Could not extract symbol from instrument", "status": "error"}
        )

    # Create spread array with correct Robin Stocks format
    spread = [
        {
            "expirationDate": short_instrument.get("expiration_date"),
            "strike": short_instrument.get("strike_price"),
            "optionType": short_instrument.get("type"),
            "effect": "open",
            "action": "sell",  # Short leg = sell
        },
        {
            "expirationDate": long_instrument.get("expiration_date"),
            "strike": long_instrument.get("strike_price"),
            "optionType": long_instrument.get("type"),
            "effect": "open",
            "action": "buy",  # Long leg = buy
        },
    ]

    # Use correct Robin Stocks API: order_option_debit_spread(price, symbol, quantity, spread, timeInForce='gtc')
    order_result = await execute_with_retry(
        rh.order_option_debit_spread,
        debit_price,
        symbol,
        quantity,
        spread,
        timeInForce="gfd",
    )

    if not order_result:
        return create_success_response(
            {"error": "Spread order placement failed", "status": "error"}
        )

    # Check for API error responses
    if isinstance(order_result, dict) and "non_field_errors" in order_result:
        error_msgs = order_result["non_field_errors"]
        return create_success_response(
            {"error": f"Order failed: {'; '.join(error_msgs)}", "status": "error"}
        )

    order_result = sanitize_api_response(order_result)

    logger.info(
        f"Debit spread order placed for {quantity} contracts at ${debit_price} debit"
    )
    return create_success_response(
        {
            "order_id": order_result.get("id"),
            "short_instrument_id": short_instrument_id,
            "long_instrument_id": long_instrument_id,
            "quantity": quantity,
            "debit_price": debit_price,
            "order_type": "debit_spread",
            "state": order_result.get("state"),
            "created_at": order_result.get("created_at"),
            "status": "success",
        }
    )


# Order Management Tools


@handle_robin_stocks_errors
async def cancel_stock_order(order_id: str) -> dict[str, Any]:
    """
    Cancels a specific stock order.

    Args:
        order_id: The ID of the order to cancel

    Returns:
        A JSON object containing cancellation confirmation in the result field.
    """
    log_api_call("cancel_stock_order", order_id)

    # Validation
    if not order_id or not isinstance(order_id, str):
        return create_success_response(
            {"error": "Invalid order_id provided", "status": "error"}
        )

    # Cancel order
    cancel_result = await execute_with_retry(rh.cancel_stock_order, order_id)

    if not cancel_result:
        return create_success_response(
            {"error": "Order cancellation failed", "status": "error"}
        )

    cancel_result = sanitize_api_response(cancel_result)

    logger.info(f"Stock order {order_id} cancelled")
    return create_success_response(
        {
            "order_id": order_id,
            "status": "cancelled",
            "cancelled_at": cancel_result.get("updated_at"),
            "message": "Order successfully cancelled",
        }
    )


@handle_robin_stocks_errors
async def cancel_option_order(order_id: str) -> dict[str, Any]:
    """
    Cancels a specific option order.

    Args:
        order_id: The ID of the order to cancel

    Returns:
        A JSON object containing cancellation confirmation in the result field.
    """
    log_api_call("cancel_option_order", order_id)

    # Validation
    if not order_id or not isinstance(order_id, str):
        return create_success_response(
            {"error": "Invalid order_id provided", "status": "error"}
        )

    # Cancel order
    cancel_result = await execute_with_retry(rh.cancel_option_order, order_id)

    if not cancel_result:
        return create_success_response(
            {"error": "Order cancellation failed", "status": "error"}
        )

    cancel_result = sanitize_api_response(cancel_result)

    logger.info(f"Option order {order_id} cancelled")
    return create_success_response(
        {
            "order_id": order_id,
            "status": "cancelled",
            "cancelled_at": cancel_result.get("updated_at"),
            "message": "Order successfully cancelled",
        }
    )


@handle_robin_stocks_errors
async def cancel_all_stock_orders() -> dict[str, Any]:
    """
    Cancels all open stock orders.

    Returns:
        A JSON object containing cancellation summary in the result field.
    """
    log_api_call("cancel_all_stock_orders")

    orders = await execute_with_retry(rh.get_all_open_stock_orders)

    if not orders:
        return create_success_response(
            {"cancelled_count": 0, "message": "No open stock orders to cancel"}
        )

    cancelled_count = 0
    failed_orders = []

    # Cancel each order
    for order in orders:
        try:
            order_id = order.get("id")
            if order_id:
                await execute_with_retry(rh.cancel_stock_order, order_id)
                cancelled_count += 1
        except Exception as e:
            failed_orders.append({"order_id": order.get("id"), "error": str(e)})

    logger.info(f"Cancelled {cancelled_count} stock orders")
    result = {
        "cancelled_count": cancelled_count,
        "total_orders": len(orders),
        "message": f"Successfully cancelled {cancelled_count} out of {len(orders)} stock orders",
    }

    if failed_orders:
        result["failed_orders"] = failed_orders

    return create_success_response(result)


@handle_robin_stocks_errors
async def cancel_all_option_orders() -> dict[str, Any]:
    """
    Cancels all open option orders.

    Returns:
        A JSON object containing cancellation summary in the result field.
    """
    log_api_call("cancel_all_option_orders")

    orders = await execute_with_retry(rh.get_all_open_option_orders)

    if not orders:
        return create_success_response(
            {"cancelled_count": 0, "message": "No open option orders to cancel"}
        )

    cancelled_count = 0
    failed_orders = []

    # Cancel each order
    for order in orders:
        try:
            order_id = order.get("id")
            if order_id:
                await execute_with_retry(rh.cancel_option_order, order_id)
                cancelled_count += 1
        except Exception as e:
            failed_orders.append({"order_id": order.get("id"), "error": str(e)})

    logger.info(f"Cancelled {cancelled_count} option orders")
    result = {
        "cancelled_count": cancelled_count,
        "total_orders": len(orders),
        "message": f"Successfully cancelled {cancelled_count} out of {len(orders)} option orders",
    }

    if failed_orders:
        result["failed_orders"] = failed_orders

    return create_success_response(result)


@handle_robin_stocks_errors
async def get_all_open_stock_orders() -> dict[str, Any]:
    """
    Retrieves all open stock orders.

    Returns:
        A JSON object containing open stock orders in the result field.
    """
    log_api_call("get_all_open_stock_orders")

    orders = await execute_with_retry(rh.get_all_open_stock_orders)

    if not orders:
        return create_success_response(
            {"orders": [], "count": 0, "message": "No open stock orders found"}
        )

    sanitized_orders = [sanitize_api_response(order) for order in orders]

    # Resolve every distinct instrument URL once, concurrently — multiple open
    # orders for the same ticker would otherwise repeat the same lookup.
    instrument_urls = dedupe_preserving_order(
        order.get("instrument") for order in sanitized_orders
    )
    url_to_symbol: dict[str, str] = {}
    if instrument_urls:
        symbol_results = await gather_bounded(
            [execute_with_retry(rh.get_symbol_by_url, url) for url in instrument_urls]
        )
        for url, value in zip(instrument_urls, symbol_results, strict=True):
            if isinstance(value, BaseException):
                logger.warning(f"Failed to get symbol for instrument {url}: {value}")
                continue
            if isinstance(value, str) and value:
                url_to_symbol[url] = value

    order_list = []
    for order in sanitized_orders:
        instrument_url = order.get("instrument")
        symbol = url_to_symbol.get(instrument_url, "N/A") if instrument_url else "N/A"

        order_data = {
            "order_id": order.get("id"),
            "symbol": symbol,
            "side": order.get("side", "N/A").upper(),
            "quantity": order.get("quantity"),
            "price": order.get("price"),
            "order_type": order.get("type"),
            "state": order.get("state"),
            "created_at": order.get("created_at"),
            "updated_at": order.get("updated_at"),
        }
        order_list.append(order_data)

    logger.info(f"Retrieved {len(order_list)} open stock orders")
    return create_success_response({"orders": order_list, "count": len(order_list)})


@handle_robin_stocks_errors
async def get_all_open_option_orders() -> dict[str, Any]:
    """
    Retrieves all open option orders.

    Returns:
        A JSON object containing open option orders in the result field.
    """
    log_api_call("get_all_open_option_orders")

    orders = await execute_with_retry(rh.get_all_open_option_orders)

    if not orders:
        return create_success_response(
            {"orders": [], "count": 0, "message": "No open option orders found"}
        )

    order_list = []
    for order in orders:
        order = sanitize_api_response(order)

        order_data = {
            "order_id": order.get("id"),
            "chain_symbol": order.get("chain_symbol"),
            "side": order.get("direction", "N/A").upper(),
            "quantity": order.get("quantity"),
            "price": order.get("price"),
            "order_type": order.get("type"),
            "state": order.get("state"),
            "created_at": order.get("created_at"),
            "updated_at": order.get("updated_at"),
        }
        order_list.append(order_data)

    logger.info(f"Retrieved {len(order_list)} open option orders")
    return create_success_response({"orders": order_list, "count": len(order_list)})
