"""Advanced market data tools for Robin Stocks integration."""

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
from open_stocks_mcp.tools.market.movers import (
    get_stocks_by_tag,
    get_top_100,
    get_top_movers,
    get_top_movers_sp500,
)
from open_stocks_mcp.tools.rate_limiter import get_rate_limiter

__all__ = [
    "get_stock_earnings",
    "get_stock_events",
    "get_stock_level2_data",
    "get_stock_news",
    "get_stock_ratings",
    "get_stock_splits",
    "get_stocks_by_tag",
    "get_top_100",
    "get_top_movers",
    "get_top_movers_sp500",
]


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
async def get_stock_news(symbol: str) -> dict[str, Any]:
    """Get news stories for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        JSON object with news stories in "result" field:
        {
            "result": {
                "symbol": "AAPL",
                "news": [
                    {
                        "title": "Apple Reports Strong Q2 Results",
                        "author": "Tech News Reporter",
                        "published_at": "2024-07-09T14:30:00Z",
                        "source": "TechCrunch",
                        "summary": "Apple exceeded expectations...",
                        "url": "https://...",
                        "preview_image_url": "https://...",
                        "num_clicks": 1250
                    }
                ],
                "count": 20
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

        log_api_call("get_stock_news", symbol=symbol)

        # Get news with retry logic
        news_data = await execute_with_retry(rh.get_news, symbol)

        if not news_data:
            return create_no_data_response(
                f"No news data found for symbol: {symbol}", {"symbol": symbol}
            )

        return create_success_response(
            {"symbol": symbol, "news": news_data, "count": len(news_data)}
        )

    except Exception as e:
        logger.error(f"Failed to get news for {symbol}: {e}")
        return create_error_response(e, "get_stock_news")


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
