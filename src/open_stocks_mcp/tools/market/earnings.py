"""Earnings and stock action tools for market research."""

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
async def get_stock_earnings(symbol: str) -> dict[str, Any]:
    """Get earnings reports for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        JSON object with earnings data in "result" field:
        {
            "result": {
                "symbol": "AAPL",
                "earnings": [
                    {
                        "year": 2024,
                        "quarter": 2,
                        "eps": {
                            "actual": "1.25",
                            "estimate": "1.20"
                        },
                        "report": {
                            "date": "2024-07-25",
                            "timing": "after_market"
                        },
                        "call": {
                            "datetime": "2024-07-25T17:00:00Z",
                            "broadcast_url": "https://..."
                        }
                    }
                ],
                "count": 8
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

        log_api_call("get_stock_earnings", symbol=symbol)

        # Get earnings with retry logic
        earnings_data = await execute_with_retry(rh.get_earnings, symbol)

        if not earnings_data:
            return create_no_data_response(
                f"No earnings data found for symbol: {symbol}", {"symbol": symbol}
            )

        return create_success_response(
            {"symbol": symbol, "earnings": earnings_data, "count": len(earnings_data)}
        )

    except Exception as e:
        logger.error(f"Failed to get earnings for {symbol}: {e}")
        return create_error_response(e, "get_stock_earnings")


@handle_robin_stocks_errors
async def get_stock_splits(symbol: str) -> dict[str, Any]:
    """Get stock split history for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        JSON object with stock splits in "result" field:
        {
            "result": {
                "symbol": "AAPL",
                "splits": [
                    {
                        "execution_date": "2020-08-31",
                        "multiplier": "4.000000",
                        "divisor": "1.000000",
                        "url": "https://...",
                        "instrument": "https://..."
                    }
                ],
                "count": 3
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

        log_api_call("get_stock_splits", symbol=symbol)

        # Get splits with retry logic
        splits_data = await execute_with_retry(rh.get_splits, symbol)

        if not splits_data:
            return create_no_data_response(
                f"No splits data found for symbol: {symbol}", {"symbol": symbol}
            )

        return create_success_response(
            {"symbol": symbol, "splits": splits_data, "count": len(splits_data)}
        )

    except Exception as e:
        logger.error(f"Failed to get splits for {symbol}: {e}")
        return create_error_response(e, "get_stock_splits")


@handle_robin_stocks_errors
async def get_stock_events(symbol: str) -> dict[str, Any]:
    """Get corporate events for a stock (for owned positions).

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        JSON object with corporate events in "result" field:
        {
            "result": {
                "symbol": "AAPL",
                "events": [
                    {
                        "type": "stock_split",
                        "event_date": "2020-08-31",
                        "state": "confirmed",
                        "direction": "debit",
                        "quantity": "300.0000",
                        "total_cash_amount": "0.00",
                        "underlying_price": "125.00",
                        "created_at": "2020-08-31T12:00:00Z"
                    }
                ],
                "count": 1
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

        log_api_call("get_stock_events", symbol=symbol)

        # Get events with retry logic
        events_data = await execute_with_retry(rh.get_events, symbol)

        if not events_data:
            return create_no_data_response(
                f"No events data found for symbol: {symbol}", {"symbol": symbol}
            )

        return create_success_response(
            {"symbol": symbol, "events": events_data, "count": len(events_data)}
        )

    except Exception as e:
        logger.error(f"Failed to get events for {symbol}: {e}")
        return create_error_response(e, "get_stock_events")
