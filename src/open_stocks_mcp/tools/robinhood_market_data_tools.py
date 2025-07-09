"""Advanced market data tools for Robin Stocks integration."""

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
    validate_symbol,
)
from open_stocks_mcp.tools.rate_limiter import get_rate_limiter
from open_stocks_mcp.tools.session_manager import get_session_manager


@handle_robin_stocks_errors
async def get_top_movers_sp500(direction: str = "up") -> dict[str, Any]:
    """Get top S&P 500 movers for the day.

    Args:
        direction: Direction of movement, either 'up' or 'down' (default: 'up')

    Returns:
        JSON object with S&P 500 movers in "result" field:
        {
            "result": {
                "direction": "up",
                "movers": [
                    {
                        "symbol": "AAPL",
                        "instrument_url": "https://...",
                        "updated_at": "2024-07-09T16:00:00Z",
                        "price_movement": {
                            "market_hours_last_movement_pct": "2.5",
                            "market_hours_last_price": "150.00"
                        },
                        "description": "Apple Inc."
                    }
                ],
                "count": 25
            }
        }
    """
    try:
        # Validate direction parameter
        direction = direction.lower().strip()
        if direction not in ["up", "down"]:
            return create_error_response(
                ValueError("Direction must be 'up' or 'down'"), "parameter validation"
            )

        # Ensure authenticated
        session_mgr = get_session_manager()
        if not await session_mgr.ensure_authenticated():
            return create_error_response(
                ValueError("Authentication required"), "authentication"
            )

        # Apply rate limiting
        rate_limiter = get_rate_limiter()
        await rate_limiter.acquire()

        log_api_call("get_top_movers_sp500", direction=direction)

        # Get S&P 500 movers with retry logic
        movers_data = await execute_with_retry(rh.get_top_movers_sp500, direction)

        if not movers_data:
            return create_no_data_response(
                f"No S&P 500 {direction} movers found", {"direction": direction}
            )

        # Filter out None values and ensure we have valid data
        movers = [mover for mover in movers_data if mover is not None]

        return create_success_response(
            {"direction": direction, "movers": movers, "count": len(movers)}
        )

    except Exception as e:
        logger.error(f"Failed to get S&P 500 {direction} movers: {e}")
        return create_error_response(e, "get_top_movers_sp500")


@handle_robin_stocks_errors
async def get_top_100() -> dict[str, Any]:
    """Get top 100 most popular stocks on Robinhood.

    Returns:
        JSON object with top 100 stocks in "result" field:
        {
            "result": {
                "stocks": [
                    {
                        "symbol": "AAPL",
                        "last_trade_price": "150.00",
                        "previous_close": "149.50",
                        "ask_price": "150.10",
                        "bid_price": "149.90",
                        "updated_at": "2024-07-09T16:00:00Z",
                        "trading_halted": false,
                        "has_traded": true
                    }
                ],
                "count": 100
            }
        }
    """
    try:
        # Ensure authenticated
        session_mgr = get_session_manager()
        if not await session_mgr.ensure_authenticated():
            return create_error_response(
                ValueError("Authentication required"), "authentication"
            )

        # Apply rate limiting
        rate_limiter = get_rate_limiter()
        await rate_limiter.acquire()

        log_api_call("get_top_100")

        # Get top 100 stocks with retry logic
        stocks_data = await execute_with_retry(rh.get_top_100)

        if not stocks_data:
            return create_no_data_response("No top 100 stocks data found", {})

        # Filter out None values and ensure we have valid data
        stocks = [stock for stock in stocks_data if stock is not None]

        return create_success_response({"stocks": stocks, "count": len(stocks)})

    except Exception as e:
        logger.error(f"Failed to get top 100 stocks: {e}")
        return create_error_response(e, "get_top_100")


@handle_robin_stocks_errors
async def get_top_movers() -> dict[str, Any]:
    """Get top 20 movers on Robinhood.

    Returns:
        JSON object with top movers in "result" field:
        {
            "result": {
                "movers": [
                    {
                        "symbol": "TSLA",
                        "last_trade_price": "250.00",
                        "previous_close": "240.00",
                        "ask_price": "250.10",
                        "bid_price": "249.90",
                        "updated_at": "2024-07-09T16:00:00Z",
                        "trading_halted": false,
                        "has_traded": true
                    }
                ],
                "count": 20
            }
        }
    """
    try:
        # Ensure authenticated
        session_mgr = get_session_manager()
        if not await session_mgr.ensure_authenticated():
            return create_error_response(
                ValueError("Authentication required"), "authentication"
            )

        # Apply rate limiting
        rate_limiter = get_rate_limiter()
        await rate_limiter.acquire()

        log_api_call("get_top_movers")

        # Get top movers with retry logic
        movers_data = await execute_with_retry(rh.get_top_movers)

        if not movers_data:
            return create_no_data_response("No top movers data found", {})

        # Filter out None values and ensure we have valid data
        movers = [mover for mover in movers_data if mover is not None]

        return create_success_response({"movers": movers, "count": len(movers)})

    except Exception as e:
        logger.error(f"Failed to get top movers: {e}")
        return create_error_response(e, "get_top_movers")


@handle_robin_stocks_errors
async def get_stocks_by_tag(tag: str) -> dict[str, Any]:
    """Get stocks filtered by market category tag.

    Args:
        tag: Market category tag (e.g., 'technology', 'biopharmaceutical', 'upcoming-earnings')

    Returns:
        JSON object with tagged stocks in "result" field:
        {
            "result": {
                "tag": "technology",
                "stocks": [
                    {
                        "symbol": "AAPL",
                        "last_trade_price": "150.00",
                        "previous_close": "149.50",
                        "ask_price": "150.10",
                        "bid_price": "149.90",
                        "updated_at": "2024-07-09T16:00:00Z"
                    }
                ],
                "count": 50
            }
        }
    """
    try:
        # Validate tag parameter
        if not tag or not isinstance(tag, str):
            return create_error_response(
                ValueError("Tag parameter is required and must be a string"),
                "parameter validation",
            )

        tag = tag.strip().lower()

        # Ensure authenticated
        session_mgr = get_session_manager()
        if not await session_mgr.ensure_authenticated():
            return create_error_response(
                ValueError("Authentication required"), "authentication"
            )

        # Apply rate limiting
        rate_limiter = get_rate_limiter()
        await rate_limiter.acquire()

        log_api_call("get_stocks_by_tag", tag=tag)

        # Get stocks by tag with retry logic
        stocks_data = await execute_with_retry(rh.get_all_stocks_from_market_tag, tag)

        if not stocks_data or stocks_data == [None]:
            return create_no_data_response(
                f"No stocks found for tag: {tag}", {"tag": tag}
            )

        # Filter out None values and ensure we have valid data
        stocks = [stock for stock in stocks_data if stock is not None]

        return create_success_response(
            {"tag": tag, "stocks": stocks, "count": len(stocks)}
        )

    except Exception as e:
        logger.error(f"Failed to get stocks for tag {tag}: {e}")
        return create_error_response(e, "get_stocks_by_tag")


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
