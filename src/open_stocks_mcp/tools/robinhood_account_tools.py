"""MCP tools for Robin Stocks account operations."""

import robin_stocks.robinhood as rh

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.error_handling import (
    create_error_response,
    create_no_data_response,
    create_success_response,
    execute_with_retry,
    handle_robin_stocks_errors,
    log_api_call,
    sanitize_api_response,
    validate_span,
)


@handle_robin_stocks_errors
async def get_account_info() -> dict:
    """
    Retrieves basic information about the Robinhood account.

    Returns:
        A JSON object containing account details in the result field.
    """
    log_api_call("get_account_info")

    # Get account info with retry logic
    account_info = await execute_with_retry(rh.load_user_profile)

    if not account_info:
        return create_no_data_response("Account information not available")

    # Sanitize sensitive data
    account_info = sanitize_api_response(account_info)

    logger.info("Successfully retrieved account info.")
    return create_success_response(
        {
            "username": account_info.get("username", "N/A"),
            "created_at": account_info.get("created_at", "N/A"),
        }
    )


@handle_robin_stocks_errors
async def get_portfolio() -> dict:
    """
    Provides a high-level overview of the portfolio.

    Returns:
        A JSON object containing the portfolio overview in the result field.
    """
    log_api_call("get_portfolio")

    # Get portfolio data with retry logic
    portfolio = await execute_with_retry(rh.load_portfolio_profile)

    if not portfolio:
        return create_no_data_response("Portfolio data not available")

    # Sanitize sensitive data
    portfolio = sanitize_api_response(portfolio)

    logger.info("Successfully retrieved portfolio overview.")
    return create_success_response(
        {
            "market_value": portfolio.get("market_value", "N/A"),
            "equity": portfolio.get("equity", "N/A"),
            "buying_power": portfolio.get("buying_power", "N/A"),
        }
    )


@handle_robin_stocks_errors
async def get_account_details() -> dict:
    """
    Retrieves comprehensive account details including buying power and cash balances.

    Returns:
        A JSON object containing detailed account information in the result field.
    """
    log_api_call("get_account_details")

    # Get account data with retry logic
    account_data = await execute_with_retry(rh.load_phoenix_account)

    if not account_data:
        return create_no_data_response("No account data found")

    # Sanitize sensitive data
    account_data = sanitize_api_response(account_data)

    logger.info("Successfully retrieved account details.")
    return create_success_response(
        {
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
        }
    )


@handle_robin_stocks_errors
async def get_positions() -> dict:
    """
    Retrieves current stock positions with quantities and values.

    Returns:
        A JSON object containing current stock positions in the result field.
    """
    log_api_call("get_positions")

    # Get positions with retry logic
    positions = await execute_with_retry(rh.get_open_stock_positions)

    if not positions:
        return create_success_response(
            {"positions": [], "count": 0, "message": "No open stock positions found."}
        )

    position_list = []
    for position in positions:
        # Get symbol from instrument URL with retry logic
        instrument_url = position.get("instrument")
        symbol = "N/A"
        if instrument_url:
            try:
                symbol = await execute_with_retry(rh.get_symbol_by_url, instrument_url)
            except Exception as e:
                logger.warning(
                    f"Failed to get symbol for instrument {instrument_url}: {e}"
                )

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
    return create_success_response(
        {"positions": position_list, "count": len(position_list)}
    )


@handle_robin_stocks_errors
async def get_portfolio_history(span: str = "week") -> dict:
    """
    Retrieves historical portfolio performance data.

    Args:
        span: Time span for history ('day', 'week', 'month', '3month', 'year', '5year', 'all')

    Returns:
        A JSON object containing portfolio history in the result field.
    """
    # Input validation
    if not validate_span(span):
        return create_error_response(
            ValueError(
                f"Invalid span: {span}. Must be one of: day, week, month, 3month, year, 5year, all"
            ),
            "span validation",
        )

    log_api_call("get_portfolio_history", span=span)

    # Get portfolio history with retry logic
    history = await execute_with_retry(
        rh.get_historical_portfolio, None, span, "regular"
    )

    if not history:
        return create_no_data_response("No portfolio history found.", {"span": span})

    # Handle case where history is a list vs dict
    if isinstance(history, list):
        if not history:
            return create_no_data_response(
                "No portfolio history found.", {"span": span}
            )
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
    return create_success_response(
        {
            "span": span,
            "total_return": total_return,
            "data_points_count": len(historicals),
            "recent_performance": recent_data,
        }
    )
