"""Historical price data tools."""

from typing import Any

import robin_stocks.robinhood as rh

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.error_handling import (
    create_error_response,
    create_no_data_response,
    create_success_response,
    execute_with_retry,
    handle_robin_stocks_errors,
    log_api_call,
    validate_period,
    validate_symbol,
)


@handle_robin_stocks_errors
async def get_price_history(symbol: str, period: str = "week") -> dict[str, Any]:
    """
    Get historical price data for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
        period: Time period ("day", "week", "month", "3month", "year", "5year")

    Returns:
        A JSON object containing historical price data in the result field.
    """
    # Input validation
    if not validate_symbol(symbol):
        return create_error_response(
            ValueError(f"Invalid symbol format: {symbol}"), "symbol validation"
        )

    if not validate_period(period):
        return create_error_response(
            ValueError(
                f"Invalid period: {period}. Must be one of: day, week, month, 3month, year, 5year"
            ),
            "period validation",
        )

    symbol = symbol.strip().upper()
    log_api_call("get_price_history", symbol=symbol, period=period)

    # Map period to interval for better data granularity
    interval_map = {
        "day": "5minute",
        "week": "hour",
        "month": "day",
        "3month": "day",
        "year": "week",
        "5year": "week",
    }

    interval = interval_map.get(period, "day")

    # Get historical data with retry logic
    historical_data = await execute_with_retry(
        rh.get_stock_historicals, symbol, interval, period, "regular"
    )

    if not historical_data:
        return create_no_data_response(
            f"No historical data found for {symbol} over {period}",
            {"symbol": symbol, "period": period},
        )

    # Process historical data (show last 20 points max for performance)
    price_points = []
    for data_point in historical_data[-20:]:
        if data_point and data_point.get("close_price"):
            price_points.append(
                {
                    "date": data_point.get("begins_at", "N/A"),
                    "open": float(data_point.get("open_price", 0)),
                    "high": float(data_point.get("high_price", 0)),
                    "low": float(data_point.get("low_price", 0)),
                    "close": float(data_point.get("close_price", 0)),
                    "volume": int(data_point.get("volume", 0)),
                }
            )

    logger.info(f"Successfully retrieved price history for {symbol} over {period}")
    return create_success_response(
        {
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "data_points": price_points,
            "count": len(price_points),
        }
    )
