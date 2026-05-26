"""Level II market data tools for Robin Stocks integration."""

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
async def get_stock_level2_data(symbol: str) -> dict[str, Any]:
    """Get Level II market data for a stock (Gold subscription required).

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        JSON object with Level II data in "result" field:
        {
            "result": {
                "symbol": "AAPL",
                "asks": [
                    {
                        "price": "150.10",
                        "quantity": "100"
                    }
                ],
                "bids": [
                    {
                        "price": "149.90",
                        "quantity": "200"
                    }
                ],
                "updated_at": "2024-07-09T16:00:00Z"
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

        log_api_call("get_stock_level2_data", symbol=symbol)

        # Get Level II data with retry logic
        level2_data = await execute_with_retry(rh.get_pricebook_by_symbol, symbol)

        if not level2_data:
            return create_no_data_response(
                f"No Level II data found for symbol: {symbol} (Gold subscription may be required)",
                {"symbol": symbol},
            )

        # Add symbol to response for consistency
        level2_data["symbol"] = symbol

        return create_success_response(level2_data)

    except Exception as e:
        logger.error(f"Failed to get Level II data for {symbol}: {e}")
        return create_error_response(e, "get_stock_level2_data")
