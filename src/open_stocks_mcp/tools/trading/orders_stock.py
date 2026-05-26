"""MCP tools for stock order placement."""

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

# Stock Order Placement Tools


@handle_robin_stocks_errors
async def order_buy_market(symbol: str, quantity: int) -> dict[str, Any]:
    """
    Places a market buy order for a stock.

    Args:
        symbol: The stock symbol to buy
        quantity: The number of shares to buy

    Returns:
        A JSON object containing order confirmation in the result field.
    """
    log_api_call("order_buy_market", symbol, quantity=quantity)

    # Validation
    if not symbol or not isinstance(symbol, str):
        return create_success_response(
            {"error": "Invalid symbol provided", "status": "error"}
        )

    if not isinstance(quantity, int) or quantity <= 0:
        return create_success_response(
            {"error": "Quantity must be a positive integer", "status": "error"}
        )

    # Check if symbol exists and get quote
    quote_data = await execute_with_retry(rh.get_quotes, symbol)
    if not quote_data or not quote_data[0].get("last_trade_price"):
        return create_success_response(
            {"error": f"Symbol {symbol} not found", "status": "error"}
        )
    quote = quote_data[0]

    # Check buying power
    account = await execute_with_retry(rh.load_account_profile)
    buying_power = float(account.get("buying_power", 0))
    estimated_cost = float(quote["last_trade_price"]) * quantity

    if buying_power < estimated_cost:
        return create_success_response(
            {
                "error": f"Insufficient buying power. Need ${estimated_cost:.2f}, have ${buying_power:.2f}",
                "status": "error",
            }
        )

    # Place order
    order_result = await execute_with_retry(
        rh.order_buy_market, symbol, quantity, timeInForce="gfd"
    )

    if not order_result:
        return create_success_response(
            {"error": "Order placement failed", "status": "error"}
        )

    # Check for Robin Stocks API errors
    if isinstance(order_result, dict) and "non_field_errors" in order_result:
        error_msgs = order_result["non_field_errors"]
        return create_success_response(
            {"error": f"Order failed: {'; '.join(error_msgs)}", "status": "error"}
        )

    order_result = sanitize_api_response(order_result)

    logger.info(f"Market buy order placed for {quantity} shares of {symbol}")
    return create_success_response(
        {
            "order_id": order_result.get("id"),
            "symbol": symbol,
            "quantity": quantity,
            "price": None,  # Market orders have no set price
            "order_type": "market",
            "side": "buy",
            "state": order_result.get("state"),
            "created_at": order_result.get("created_at"),
            "status": "success",
        }
    )


@handle_robin_stocks_errors
async def order_sell_market(symbol: str, quantity: int) -> dict[str, Any]:
    """
    Places a market sell order for a stock.

    Args:
        symbol: The stock symbol to sell
        quantity: The number of shares to sell

    Returns:
        A JSON object containing order confirmation in the result field.
    """
    log_api_call("order_sell_market", symbol, quantity=quantity)

    # Validation
    if not symbol or not isinstance(symbol, str):
        return create_success_response(
            {"error": "Invalid symbol provided", "status": "error"}
        )

    if not isinstance(quantity, int) or quantity <= 0:
        return create_success_response(
            {"error": "Quantity must be a positive integer", "status": "error"}
        )

    # Check position
    positions = await execute_with_retry(rh.get_open_stock_positions)
    position = None
    for pos in positions:
        if pos.get("symbol") == symbol:
            position = pos
            break

    if not position:
        return create_success_response(
            {"error": f"No position found for {symbol}", "status": "error"}
        )

    shares_owned = float(position.get("quantity", 0))
    if shares_owned < quantity:
        return create_success_response(
            {
                "error": f"Insufficient shares. Own {shares_owned}, trying to sell {quantity}",
                "status": "error",
            }
        )

    # Place order
    order_result = await execute_with_retry(
        rh.order_sell_market, symbol, quantity, timeInForce="gfd"
    )

    if not order_result:
        return create_success_response(
            {"error": "Order placement failed", "status": "error"}
        )

    # Check for Robin Stocks API errors
    if isinstance(order_result, dict) and "non_field_errors" in order_result:
        error_msgs = order_result["non_field_errors"]
        return create_success_response(
            {"error": f"Order failed: {'; '.join(error_msgs)}", "status": "error"}
        )

    order_result = sanitize_api_response(order_result)

    logger.info(f"Market sell order placed for {quantity} shares of {symbol}")
    return create_success_response(
        {
            "order_id": order_result.get("id"),
            "symbol": symbol,
            "quantity": quantity,
            "price": None,  # Market orders have no set price
            "order_type": "market",
            "side": "sell",
            "state": order_result.get("state"),
            "created_at": order_result.get("created_at"),
            "status": "success",
        }
    )


@handle_robin_stocks_errors
async def order_buy_limit(
    symbol: str, quantity: int, limit_price: float
) -> dict[str, Any]:
    """
    Places a limit buy order for a stock.

    Args:
        symbol: The stock symbol to buy
        quantity: The number of shares to buy
        limit_price: The maximum price per share

    Returns:
        A JSON object containing order confirmation in the result field.
    """
    log_api_call("order_buy_limit", symbol, quantity=quantity, limit_price=limit_price)

    # Validation
    if not symbol or not isinstance(symbol, str):
        return create_success_response(
            {"error": "Invalid symbol provided", "status": "error"}
        )

    if not isinstance(quantity, int) or quantity <= 0:
        return create_success_response(
            {"error": "Quantity must be a positive integer", "status": "error"}
        )

    if not isinstance(limit_price, int | float) or limit_price <= 0:
        return create_success_response(
            {"error": "Limit price must be a positive number", "status": "error"}
        )

    # Check if symbol exists and validate limit price
    quote_data = await execute_with_retry(rh.get_quotes, symbol)
    if not quote_data or not quote_data[0].get("last_trade_price"):
        return create_success_response(
            {"error": f"Symbol {symbol} not found", "status": "error"}
        )
    quote = quote_data[0]
    current_price = float(quote["last_trade_price"])
    if (
        limit_price > current_price * 1.5
    ):  # Sanity check: limit price shouldn't be >50% above current
        return create_success_response(
            {
                "error": f"Limit price ${limit_price:.2f} too high compared to current price ${current_price:.2f}",
                "status": "error",
            }
        )

    # Check buying power
    account = await execute_with_retry(rh.load_account_profile)
    buying_power = float(account.get("buying_power", 0))
    estimated_cost = limit_price * quantity

    if buying_power < estimated_cost:
        return create_success_response(
            {
                "error": f"Insufficient buying power. Need ${estimated_cost:.2f}, have ${buying_power:.2f}",
                "status": "error",
            }
        )

    # Place order
    order_result = await execute_with_retry(
        rh.order_buy_limit, symbol, quantity, limit_price
    )

    if not order_result:
        return create_success_response(
            {"error": "Order placement failed", "status": "error"}
        )

    # Check for Robin Stocks API errors
    if isinstance(order_result, dict) and "non_field_errors" in order_result:
        error_msgs = order_result["non_field_errors"]
        return create_success_response(
            {"error": f"Order failed: {'; '.join(error_msgs)}", "status": "error"}
        )

    order_result = sanitize_api_response(order_result)

    logger.info(
        f"Limit buy order placed for {quantity} shares of {symbol} at ${limit_price}"
    )
    return create_success_response(
        {
            "order_id": order_result.get("id"),
            "symbol": symbol,
            "quantity": quantity,
            "price": limit_price,  # Limit orders have set price
            "order_type": "limit",
            "side": "buy",
            "state": order_result.get("state"),
            "created_at": order_result.get("created_at"),
            "status": "success",
        }
    )


@handle_robin_stocks_errors
async def order_sell_limit(
    symbol: str, quantity: int, limit_price: float
) -> dict[str, Any]:
    """
    Places a limit sell order for a stock.

    Args:
        symbol: The stock symbol to sell
        quantity: The number of shares to sell
        limit_price: The minimum price per share

    Returns:
        A JSON object containing order confirmation in the result field.
    """
    log_api_call("order_sell_limit", symbol, quantity=quantity, limit_price=limit_price)

    # Validation
    if not symbol or not isinstance(symbol, str):
        return create_success_response(
            {"error": "Invalid symbol provided", "status": "error"}
        )

    if not isinstance(quantity, int) or quantity <= 0:
        return create_success_response(
            {"error": "Quantity must be a positive integer", "status": "error"}
        )

    if not isinstance(limit_price, int | float) or limit_price <= 0:
        return create_success_response(
            {"error": "Limit price must be a positive number", "status": "error"}
        )

    # Check position
    positions = await execute_with_retry(rh.get_open_stock_positions)
    position = None
    for pos in positions:
        if pos.get("symbol") == symbol:
            position = pos
            break

    if not position:
        return create_success_response(
            {"error": f"No position found for {symbol}", "status": "error"}
        )

    shares_owned = float(position.get("quantity", 0))
    if shares_owned < quantity:
        return create_success_response(
            {
                "error": f"Insufficient shares. Own {shares_owned}, trying to sell {quantity}",
                "status": "error",
            }
        )

    # Place order
    order_result = await execute_with_retry(
        rh.order_sell_limit, symbol, quantity, limit_price
    )

    # Debug: Log the actual response
    logger.info(f"DEBUG: Raw limit sell order_result = {order_result}")
    logger.info(f"DEBUG: order_result type = {type(order_result)}")

    if not order_result:
        return create_success_response(
            {"error": "Order placement failed", "status": "error"}
        )

    # Check for Robin Stocks API errors
    if isinstance(order_result, dict) and "non_field_errors" in order_result:
        error_msgs = order_result["non_field_errors"]
        return create_success_response(
            {"error": f"Order failed: {'; '.join(error_msgs)}", "status": "error"}
        )

    order_result = sanitize_api_response(order_result)
    logger.info(f"DEBUG: Sanitized limit sell order_result = {order_result}")

    logger.info(
        f"Limit sell order placed for {quantity} shares of {symbol} at ${limit_price}"
    )
    return create_success_response(
        {
            "order_id": order_result.get("id"),
            "symbol": symbol,
            "quantity": quantity,
            "price": limit_price,  # Limit orders have set price
            "order_type": "limit",
            "side": "sell",
            "state": order_result.get("state"),
            "created_at": order_result.get("created_at"),
            "status": "success",
        }
    )


@handle_robin_stocks_errors
async def order_buy_stop_loss(
    symbol: str, quantity: int, stop_price: float
) -> dict[str, Any]:
    """
    Places a stop loss buy order for a stock.

    Args:
        symbol: The stock symbol to buy
        quantity: The number of shares to buy
        stop_price: The stop price that triggers the order

    Returns:
        A JSON object containing order confirmation in the result field.
    """
    log_api_call(
        "order_buy_stop_loss", symbol, quantity=quantity, stop_price=stop_price
    )

    # Validation
    if not symbol or not isinstance(symbol, str):
        return create_success_response(
            {"error": "Invalid symbol provided", "status": "error"}
        )

    if not isinstance(quantity, int) or quantity <= 0:
        return create_success_response(
            {"error": "Quantity must be a positive integer", "status": "error"}
        )

    if not isinstance(stop_price, int | float) or stop_price <= 0:
        return create_success_response(
            {"error": "Stop price must be a positive number", "status": "error"}
        )

    # Check if symbol exists and validate stop price
    quote_data = await execute_with_retry(rh.get_quotes, symbol)
    if not quote_data or not quote_data[0].get("last_trade_price"):
        return create_success_response(
            {"error": f"Symbol {symbol} not found", "status": "error"}
        )
    quote = quote_data[0]
    current_price = float(quote["last_trade_price"])
    if stop_price <= current_price:
        return create_success_response(
            {
                "error": f"Stop price ${stop_price:.2f} must be above current price ${current_price:.2f} for buy orders",
                "status": "error",
            }
        )

    # Place order
    order_result = await execute_with_retry(
        rh.order_buy_stop_loss, symbol, quantity, stop_price
    )

    if not order_result:
        return create_success_response(
            {"error": "Order placement failed", "status": "error"}
        )

    order_result = sanitize_api_response(order_result)

    logger.info(
        f"Stop loss buy order placed for {quantity} shares of {symbol} at stop ${stop_price}"
    )
    return create_success_response(
        {
            "order_id": order_result.get("id"),
            "symbol": symbol,
            "quantity": quantity,
            "stop_price": stop_price,
            "order_type": "stop_loss",
            "side": "buy",
            "state": order_result.get("state"),
            "created_at": order_result.get("created_at"),
            "status": "success",
        }
    )


@handle_robin_stocks_errors
async def order_sell_stop_loss(
    symbol: str, quantity: int, stop_price: float
) -> dict[str, Any]:
    """
    Places a stop loss sell order for a stock.

    Args:
        symbol: The stock symbol to sell
        quantity: The number of shares to sell
        stop_price: The stop price that triggers the order

    Returns:
        A JSON object containing order confirmation in the result field.
    """
    log_api_call(
        "order_sell_stop_loss", symbol, quantity=quantity, stop_price=stop_price
    )

    # Validation
    if not symbol or not isinstance(symbol, str):
        return create_success_response(
            {"error": "Invalid symbol provided", "status": "error"}
        )

    if not isinstance(quantity, int) or quantity <= 0:
        return create_success_response(
            {"error": "Quantity must be a positive integer", "status": "error"}
        )

    if not isinstance(stop_price, int | float) or stop_price <= 0:
        return create_success_response(
            {"error": "Stop price must be a positive number", "status": "error"}
        )

    # Check position and validate stop price
    positions = await execute_with_retry(rh.get_open_stock_positions)
    position = None
    for pos in positions:
        if pos.get("symbol") == symbol:
            position = pos
            break

    if not position:
        return create_success_response(
            {"error": f"No position found for {symbol}", "status": "error"}
        )

    shares_owned = float(position.get("quantity", 0))
    if shares_owned < quantity:
        return create_success_response(
            {
                "error": f"Insufficient shares. Own {shares_owned}, trying to sell {quantity}",
                "status": "error",
            }
        )

    # Validate stop price
    quote_data = await execute_with_retry(rh.get_quotes, symbol)
    quote = quote_data[0]
    current_price = float(quote["last_trade_price"])
    if stop_price >= current_price:
        return create_success_response(
            {
                "error": f"Stop price ${stop_price:.2f} must be below current price ${current_price:.2f} for sell orders",
                "status": "error",
            }
        )

    # Place order
    order_result = await execute_with_retry(
        rh.order_sell_stop_loss, symbol, quantity, stop_price
    )

    if not order_result:
        return create_success_response(
            {"error": "Order placement failed", "status": "error"}
        )

    order_result = sanitize_api_response(order_result)

    logger.info(
        f"Stop loss sell order placed for {quantity} shares of {symbol} at stop ${stop_price}"
    )
    return create_success_response(
        {
            "order_id": order_result.get("id"),
            "symbol": symbol,
            "quantity": quantity,
            "stop_price": stop_price,
            "order_type": "stop_loss",
            "side": "sell",
            "state": order_result.get("state"),
            "created_at": order_result.get("created_at"),
            "status": "success",
        }
    )


@handle_robin_stocks_errors
async def order_buy_trailing_stop(
    symbol: str, quantity: int, trail_amount: float
) -> dict[str, Any]:
    """
    Places a trailing stop buy order for a stock.

    Args:
        symbol: The stock symbol to buy
        quantity: The number of shares to buy
        trail_amount: The trailing amount (percentage or dollar amount)

    Returns:
        A JSON object containing order confirmation in the result field.
    """
    log_api_call(
        "order_buy_trailing_stop", symbol, quantity=quantity, trail_amount=trail_amount
    )

    # Validation
    if not symbol or not isinstance(symbol, str):
        return create_success_response(
            {"error": "Invalid symbol provided", "status": "error"}
        )

    if not isinstance(quantity, int) or quantity <= 0:
        return create_success_response(
            {"error": "Quantity must be a positive integer", "status": "error"}
        )

    if not isinstance(trail_amount, int | float) or trail_amount <= 0:
        return create_success_response(
            {"error": "Trail amount must be a positive number", "status": "error"}
        )

    if trail_amount > 50:  # Sanity check for percentage
        return create_success_response(
            {"error": "Trail amount too high (max 50%)", "status": "error"}
        )

    # Check if symbol exists
    quote_data = await execute_with_retry(rh.get_quotes, symbol)
    if not quote_data or not quote_data[0].get("last_trade_price"):
        return create_success_response(
            {"error": f"Symbol {symbol} not found", "status": "error"}
        )

    # Place order
    order_result = await execute_with_retry(
        rh.order_buy_trailing_stop, symbol, quantity, trail_amount
    )

    if not order_result:
        return create_success_response(
            {"error": "Order placement failed", "status": "error"}
        )

    order_result = sanitize_api_response(order_result)

    logger.info(
        f"Trailing stop buy order placed for {quantity} shares of {symbol} with trail ${trail_amount}"
    )
    return create_success_response(
        {
            "order_id": order_result.get("id"),
            "symbol": symbol,
            "quantity": quantity,
            "trail_amount": trail_amount,
            "order_type": "trailing_stop",
            "side": "buy",
            "state": order_result.get("state"),
            "created_at": order_result.get("created_at"),
            "status": "success",
        }
    )


@handle_robin_stocks_errors
async def order_sell_trailing_stop(
    symbol: str, quantity: int, trail_amount: float
) -> dict[str, Any]:
    """
    Places a trailing stop sell order for a stock.

    Args:
        symbol: The stock symbol to sell
        quantity: The number of shares to sell
        trail_amount: The trailing amount (percentage or dollar amount)

    Returns:
        A JSON object containing order confirmation in the result field.
    """
    log_api_call(
        "order_sell_trailing_stop", symbol, quantity=quantity, trail_amount=trail_amount
    )

    # Validation
    if not symbol or not isinstance(symbol, str):
        return create_success_response(
            {"error": "Invalid symbol provided", "status": "error"}
        )

    if not isinstance(quantity, int) or quantity <= 0:
        return create_success_response(
            {"error": "Quantity must be a positive integer", "status": "error"}
        )

    if not isinstance(trail_amount, int | float) or trail_amount <= 0:
        return create_success_response(
            {"error": "Trail amount must be a positive number", "status": "error"}
        )

    if trail_amount > 50:  # Sanity check for percentage
        return create_success_response(
            {"error": "Trail amount too high (max 50%)", "status": "error"}
        )

    # Check position
    positions = await execute_with_retry(rh.get_open_stock_positions)
    position = None
    for pos in positions:
        if pos.get("symbol") == symbol:
            position = pos
            break

    if not position:
        return create_success_response(
            {"error": f"No position found for {symbol}", "status": "error"}
        )

    shares_owned = float(position.get("quantity", 0))
    if shares_owned < quantity:
        return create_success_response(
            {
                "error": f"Insufficient shares. Own {shares_owned}, trying to sell {quantity}",
                "status": "error",
            }
        )

    # Place order
    order_result = await execute_with_retry(
        rh.order_sell_trailing_stop, symbol, quantity, trail_amount
    )

    if not order_result:
        return create_success_response(
            {"error": "Order placement failed", "status": "error"}
        )

    order_result = sanitize_api_response(order_result)

    logger.info(
        f"Trailing stop sell order placed for {quantity} shares of {symbol} with trail ${trail_amount}"
    )
    return create_success_response(
        {
            "order_id": order_result.get("id"),
            "symbol": symbol,
            "quantity": quantity,
            "trail_amount": trail_amount,
            "order_type": "trailing_stop",
            "side": "sell",
            "state": order_result.get("state"),
            "created_at": order_result.get("created_at"),
            "status": "success",
        }
    )


@handle_robin_stocks_errors
async def order_buy_fractional_by_price(
    symbol: str, amount_in_dollars: float
) -> dict[str, Any]:
    """
    Places a fractional share buy order using dollar amount.

    Args:
        symbol: The stock symbol to buy
        amount_in_dollars: The dollar amount to invest

    Returns:
        A JSON object containing order confirmation in the result field.
    """
    log_api_call(
        "order_buy_fractional_by_price", symbol, amount_in_dollars=amount_in_dollars
    )

    # Validation
    if not symbol or not isinstance(symbol, str):
        return create_success_response(
            {"error": "Invalid symbol provided", "status": "error"}
        )

    if not isinstance(amount_in_dollars, int | float) or amount_in_dollars <= 0:
        return create_success_response(
            {"error": "Amount must be a positive number", "status": "error"}
        )

    # Check if symbol exists
    quote_data = await execute_with_retry(rh.get_quotes, symbol)
    if not quote_data or not quote_data[0].get("last_trade_price"):
        return create_success_response(
            {"error": f"Symbol {symbol} not found", "status": "error"}
        )

    # Check buying power
    account = await execute_with_retry(rh.load_account_profile)
    buying_power = float(account.get("buying_power", 0))

    if buying_power < amount_in_dollars:
        return create_success_response(
            {
                "error": f"Insufficient buying power. Need ${amount_in_dollars:.2f}, have ${buying_power:.2f}",
                "status": "error",
            }
        )

    # Place order
    order_result = await execute_with_retry(
        rh.order_buy_fractional_by_price, symbol, amount_in_dollars
    )

    if not order_result:
        return create_success_response(
            {"error": "Order placement failed", "status": "error"}
        )

    order_result = sanitize_api_response(order_result)

    logger.info(f"Fractional buy order placed for ${amount_in_dollars} of {symbol}")
    return create_success_response(
        {
            "order_id": order_result.get("id"),
            "symbol": symbol,
            "amount_in_dollars": amount_in_dollars,
            "order_type": "fractional",
            "side": "buy",
            "state": order_result.get("state"),
            "created_at": order_result.get("created_at"),
            "status": "success",
        }
    )


