"""Stock ratings tools."""

from typing import Any

import robin_stocks.robinhood as rh

from open_stocks_mcp.brokers.session_state import get_session_manager
from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.error_handling import (
    create_error_response,
    create_no_data_response,
    create_success_response,
    execute_with_retry,
    handle_robin_stocks_errors,
    log_api_call,
    validate_symbol,
)
from open_stocks_mcp.tools.rate_limiter import get_rate_limiter


@handle_robin_stocks_errors
async def get_stock_ratings(symbol: str) -> dict[str, Any]:
    """Get analyst ratings for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        JSON object with analyst ratings in "result" field:
        {
            "result": {
                "symbol": "AAPL",
                "summary": {
                    "num_buy_ratings": 15,
                    "num_hold_ratings": 5,
                    "num_sell_ratings": 2
                },
                "ratings": [
                    {
                        "published_at": "2024-07-09T10:00:00Z",
                        "type": "buy",
                        "text": "Strong buy recommendation",
                        "rating": "buy"
                    }
                ],
                "ratings_published_at": "2024-07-09T10:00:00Z"
            }
        }
    """
    try:
        # Input validation
        if not validate_symbol(symbol):
            return create_error_response(
                ValueError(f"Invalid symbol format: {symbol}"), "symbol validation"
            )

        symbol = symbol.strip().upper()

        # Ensure authenticated
        session_mgr = get_session_manager()
        if not await session_mgr.ensure_authenticated():
            return create_error_response(
                ValueError("Authentication required"), "authentication"
            )

        # Apply rate limiting
        rate_limiter = get_rate_limiter()
        await rate_limiter.acquire()

        log_api_call("get_stock_ratings", symbol=symbol)

        # Get ratings with retry logic
        ratings_data = await execute_with_retry(rh.get_ratings, symbol)

        if not ratings_data:
            return create_no_data_response(
                f"No ratings data found for symbol: {symbol}", {"symbol": symbol}
            )

        # Add symbol to response for consistency
        ratings_data["symbol"] = symbol

        return create_success_response(ratings_data)

    except Exception as e:
        logger.error(f"Failed to get ratings for {symbol}: {e}")
        return create_error_response(e, "get_stock_ratings")
