"""MCP tools for Robin Stocks stock market data operations."""

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
async def get_stock_price(symbol: str) -> dict[str, Any]:
    """
    Get current stock price and basic metrics.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        A JSON object containing stock price data in the result field.
    """
    # Input validation
    if not validate_symbol(symbol):
        return create_error_response(
            ValueError(f"Invalid symbol format: {symbol}"), "symbol validation"
        )

    symbol = symbol.strip().upper()
    log_api_call("get_stock_price", symbol=symbol)

    # Get latest price and quote data with retry logic
    price_data = await execute_with_retry(rh.get_latest_price, symbol, "ask_price")
    quote_data = await execute_with_retry(rh.get_quotes, symbol)

    if not price_data or not quote_data:
        return create_no_data_response(
            f"No price data found for symbol: {symbol}", {"symbol": symbol}
        )

    quote = quote_data[0] if quote_data else {}
    current_price = float(price_data[0]) if price_data and price_data[0] else 0.0

    # Calculate change and change percent
    previous_close = float(quote.get("previous_close", 0))
    change = current_price - previous_close if previous_close else 0.0
    change_percent = (change / previous_close * 100) if previous_close else 0.0

    logger.info(f"Successfully retrieved stock price for {symbol}")
    return create_success_response(
        {
            "symbol": symbol,
            "price": current_price,
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "previous_close": previous_close,
            "volume": int(quote.get("volume", 0)),
            "ask_price": float(quote.get("ask_price", 0)),
            "bid_price": float(quote.get("bid_price", 0)),
            "last_trade_price": float(quote.get("last_trade_price", 0)),
        }
    )


@handle_robin_stocks_errors
async def get_stock_info(symbol: str) -> dict[str, Any]:
    """
    Get detailed company information and fundamentals.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        A JSON object containing company information in the result field.
    """
    # Input validation
    if not validate_symbol(symbol):
        return create_error_response(
            ValueError(f"Invalid symbol format: {symbol}"), "symbol validation"
        )

    symbol = symbol.strip().upper()
    log_api_call("get_stock_info", symbol=symbol)

    # Get fundamentals and instrument data with retry logic
    fundamentals = await execute_with_retry(rh.get_fundamentals, symbol)
    instruments = await execute_with_retry(rh.get_instruments_by_symbols, symbol)

    if not fundamentals or not instruments:
        return create_no_data_response(
            f"No company information found for symbol: {symbol}", {"symbol": symbol}
        )

    fundamental = fundamentals[0] if fundamentals else {}
    instrument = instruments[0] if instruments else {}

    # Get company name with retry logic
    company_name = await execute_with_retry(rh.get_name_by_symbol, symbol)

    logger.info(f"Successfully retrieved stock info for {symbol}")
    return create_success_response(
        {
            "symbol": symbol,
            "company_name": company_name or instrument.get("simple_name", "N/A"),
            "sector": fundamental.get("sector", "N/A"),
            "industry": fundamental.get("industry", "N/A"),
            "description": fundamental.get("description", "N/A"),
            "market_cap": fundamental.get("market_cap", "N/A"),
            "pe_ratio": fundamental.get("pe_ratio", "N/A"),
            "dividend_yield": fundamental.get("dividend_yield", "N/A"),
            "high_52_weeks": fundamental.get("high_52_weeks", "N/A"),
            "low_52_weeks": fundamental.get("low_52_weeks", "N/A"),
            "average_volume": fundamental.get("average_volume", "N/A"),
            "tradeable": instrument.get("tradeable", False),
        }
    )


@handle_robin_stocks_errors
async def search_stocks(query: str) -> dict[str, Any]:
    """
    Search for stocks by symbol or company name.

    Args:
        query: Search query (symbol or company name)

    Returns:
        A JSON object containing search results in the result field.
    """
    # Input validation
    if not query or not isinstance(query, str) or len(query.strip()) == 0:
        return create_error_response(
            ValueError("Search query cannot be empty"), "query validation"
        )

    query = query.strip()
    log_api_call("search_stocks", query=query)

    # Search for instruments matching the query with retry logic
    search_results = await execute_with_retry(rh.find_instrument_data, query)

    if not search_results:
        return create_success_response(
            {
                "query": query,
                "results": [],
                "count": 0,
                "message": f"No stocks found matching query: {query}",
            }
        )

    # Process search results (limit to 10 for performance)
    results = []
    for item in search_results[:10]:
        symbol = item.get("symbol", "")
        if symbol:  # Only include results with valid symbols
            results.append(
                {
                    "symbol": symbol.upper(),
                    "name": item.get("simple_name", "N/A"),
                    "tradeable": item.get("tradeable", False),
                    "country": item.get("country", "N/A"),
                    "type": item.get("type", "N/A"),
                }
            )

    logger.info(f"Successfully searched stocks for query: {query}")
    return create_success_response(
        {"query": query, "results": results, "count": len(results)}
    )


@handle_robin_stocks_errors
async def get_market_hours() -> dict[str, Any]:
    """
    Get current market hours and status.

    Returns:
        A JSON object containing market hours information in the result field.
    """
    log_api_call("get_market_hours")

    # Get market information with retry logic
    markets = await execute_with_retry(rh.get_markets)

    if not markets:
        return create_no_data_response("No market data available")

    # Process market data - focus on main markets
    market_data = []
    for market in markets[:5]:  # Limit to top 5 markets
        market_data.append(
            {
                "name": market.get("name", "N/A"),
                "mic": market.get("mic", "N/A"),
                "operating_mic": market.get("operating_mic", "N/A"),
                "timezone": market.get("timezone", "N/A"),
                "website": market.get("website", "N/A"),
            }
        )

    logger.info("Successfully retrieved market hours information")
    return create_success_response({"markets": market_data, "count": len(market_data)})


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
