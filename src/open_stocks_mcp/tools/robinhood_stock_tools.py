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


@handle_robin_stocks_errors
async def get_instruments_by_symbols(symbols: list[str]) -> dict[str, Any]:
    """
    Get detailed instrument metadata for multiple symbols.

    Args:
        symbols: List of stock ticker symbols (e.g., ["AAPL", "GOOGL", "MSFT"])

    Returns:
        A JSON object containing instrument metadata for each symbol in the result field.
    """
    # Input validation
    if not symbols:
        return create_error_response(
            ValueError("Symbol list cannot be empty"), "symbol list validation"
        )

    # Validate each symbol
    for symbol in symbols:
        if not validate_symbol(symbol):
            return create_error_response(
                ValueError(f"Invalid symbol format: {symbol}"), "symbol validation"
            )

    # Clean and uppercase symbols
    clean_symbols = [symbol.strip().upper() for symbol in symbols]
    log_api_call("get_instruments_by_symbols", symbols=clean_symbols)

    # Get instruments data with retry logic
    instruments_data = await execute_with_retry(
        rh.get_instruments_by_symbols, clean_symbols
    )

    if not instruments_data:
        return create_no_data_response(
            f"No instrument data found for symbols: {clean_symbols}",
            {"symbols": clean_symbols},
        )

    # Process instruments data
    processed_instruments = []
    for instrument in instruments_data:
        if instrument:
            processed_instruments.append(
                {
                    "symbol": instrument.get("symbol", "N/A"),
                    "name": instrument.get("name", "N/A"),
                    "instrument_id": instrument.get("id", "N/A"),
                    "url": instrument.get("url", "N/A"),
                    "tradeable": instrument.get("tradeable", False),
                    "market": instrument.get("market", "N/A"),
                    "list_date": instrument.get("list_date", "N/A"),
                    "state": instrument.get("state", "N/A"),
                    "type": instrument.get("type", "N/A"),
                    "tradability": instrument.get("tradability", "N/A"),
                    "simple_name": instrument.get("simple_name", "N/A"),
                    "country": instrument.get("country", "N/A"),
                    "symbol_description": instrument.get("symbol_description", "N/A"),
                    "fractional_tradability": instrument.get(
                        "fractional_tradability", "N/A"
                    ),
                    "maintenance_ratio": instrument.get("maintenance_ratio", "N/A"),
                    "margin_initial_ratio": instrument.get(
                        "margin_initial_ratio", "N/A"
                    ),
                    "day_trade_ratio": instrument.get("day_trade_ratio", "N/A"),
                    "bloomberg_unique": instrument.get("bloomberg_unique", "N/A"),
                }
            )

    logger.info(
        f"Successfully retrieved instrument data for {len(processed_instruments)} symbols"
    )
    return create_success_response(
        {
            "instruments": processed_instruments,
            "count": len(processed_instruments),
            "requested_symbols": clean_symbols,
        }
    )


@handle_robin_stocks_errors
async def find_instrument_data(query: str) -> dict[str, Any]:
    """
    Search for instrument information by various criteria.

    Args:
        query: Search query string (can be symbol, company name, or other criteria)

    Returns:
        A JSON object containing matching instruments in the result field.
    """
    # Input validation
    if not query or not query.strip():
        return create_error_response(
            ValueError("Query cannot be empty"), "query validation"
        )

    query = query.strip()
    log_api_call("find_instrument_data", query=query)

    # Search for instruments with retry logic
    instruments_data = await execute_with_retry(rh.find_instrument_data, query)

    if not instruments_data:
        return create_no_data_response(
            f"No instrument data found for query: {query}", {"query": query}
        )

    # Process instruments data (limit to first 10 results for performance)
    processed_instruments = []
    for instrument in instruments_data[:10]:
        if instrument:
            processed_instruments.append(
                {
                    "symbol": instrument.get("symbol", "N/A"),
                    "name": instrument.get("name", "N/A"),
                    "instrument_id": instrument.get("id", "N/A"),
                    "url": instrument.get("url", "N/A"),
                    "tradeable": instrument.get("tradeable", False),
                    "market": instrument.get("market", "N/A"),
                    "list_date": instrument.get("list_date", "N/A"),
                    "state": instrument.get("state", "N/A"),
                    "type": instrument.get("type", "N/A"),
                    "tradability": instrument.get("tradability", "N/A"),
                    "simple_name": instrument.get("simple_name", "N/A"),
                    "country": instrument.get("country", "N/A"),
                    "symbol_description": instrument.get("symbol_description", "N/A"),
                    "fractional_tradability": instrument.get(
                        "fractional_tradability", "N/A"
                    ),
                }
            )

    logger.info(
        f"Successfully found {len(processed_instruments)} instruments for query: {query}"
    )
    return create_success_response(
        {
            "instruments": processed_instruments,
            "count": len(processed_instruments),
            "query": query,
            "total_results": len(instruments_data),
            "showing_results": len(processed_instruments),
        }
    )


@handle_robin_stocks_errors
async def get_stock_quote_by_id(instrument_id: str) -> dict[str, Any]:
    """
    Get stock quote using Robinhood's internal instrument ID.

    Args:
        instrument_id: Robinhood's internal instrument ID

    Returns:
        A JSON object containing the stock quote in the result field.
    """
    # Input validation
    if not instrument_id or not instrument_id.strip():
        return create_error_response(
            ValueError("Instrument ID cannot be empty"), "instrument_id validation"
        )

    instrument_id = instrument_id.strip()
    log_api_call("get_stock_quote_by_id", instrument_id=instrument_id)

    # Get quote by ID with retry logic
    quote_data = await execute_with_retry(rh.get_stock_quote_by_id, instrument_id)

    if not quote_data:
        return create_no_data_response(
            f"No quote data found for instrument ID: {instrument_id}",
            {"instrument_id": instrument_id},
        )

    # Process quote data
    try:
        last_trade_price = float(quote_data.get("last_trade_price", 0))
        previous_close = float(quote_data.get("previous_close", 0))

        # Calculate change and percentage change
        change = last_trade_price - previous_close if previous_close else 0
        change_percent = (change / previous_close * 100) if previous_close else 0

        processed_quote = {
            "instrument_id": instrument_id,
            "symbol": quote_data.get("symbol", "N/A"),
            "price": last_trade_price,
            "previous_close": previous_close,
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "ask_price": float(quote_data.get("ask_price", 0)),
            "bid_price": float(quote_data.get("bid_price", 0)),
            "ask_size": int(quote_data.get("ask_size", 0)),
            "bid_size": int(quote_data.get("bid_size", 0)),
            "last_extended_hours_trade_price": float(
                quote_data.get("last_extended_hours_trade_price", 0)
            ),
            "previous_close_date": quote_data.get("previous_close_date", "N/A"),
            "trading_halted": quote_data.get("trading_halted", False),
            "has_traded": quote_data.get("has_traded", False),
            "last_trade_price_source": quote_data.get("last_trade_price_source", "N/A"),
            "updated_at": quote_data.get("updated_at", "N/A"),
            "instrument_url": quote_data.get("instrument", "N/A"),
        }

        logger.info(f"Successfully retrieved quote for instrument ID: {instrument_id}")
        return create_success_response(processed_quote)

    except (ValueError, TypeError) as e:
        return create_error_response(
            ValueError(f"Error processing quote data: {e!s}"), "quote processing"
        )


@handle_robin_stocks_errors
async def get_pricebook_by_symbol(symbol: str) -> dict[str, Any]:
    """
    Get Level II order book data for a symbol (requires Gold subscription).

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        A JSON object containing Level II order book data in the result field.
    """
    # Input validation
    if not validate_symbol(symbol):
        return create_error_response(
            ValueError(f"Invalid symbol format: {symbol}"), "symbol validation"
        )

    symbol = symbol.strip().upper()
    log_api_call("get_pricebook_by_symbol", symbol=symbol)

    # Get pricebook data with retry logic
    pricebook_data = await execute_with_retry(rh.get_pricebook_by_symbol, symbol)

    if not pricebook_data:
        return create_no_data_response(
            f"No pricebook data found for symbol: {symbol}. Note: This feature requires Robinhood Gold subscription.",
            {"symbol": symbol},
        )

    # Process pricebook data
    try:
        processed_asks = []
        processed_bids = []

        # Process asks (sell orders)
        if pricebook_data.get("asks"):
            for ask in pricebook_data["asks"]:
                if ask:
                    processed_asks.append(
                        {
                            "price": float(ask.get("price", 0)),
                            "quantity": int(ask.get("quantity", 0)),
                            "side": "ask",
                        }
                    )

        # Process bids (buy orders)
        if pricebook_data.get("bids"):
            for bid in pricebook_data["bids"]:
                if bid:
                    processed_bids.append(
                        {
                            "price": float(bid.get("price", 0)),
                            "quantity": int(bid.get("quantity", 0)),
                            "side": "bid",
                        }
                    )

        # Sort asks by price (ascending) and bids by price (descending)
        processed_asks.sort(key=lambda x: x["price"])  # type: ignore[arg-type,return-value]
        processed_bids.sort(key=lambda x: x["price"], reverse=True)  # type: ignore[arg-type,return-value]

        processed_pricebook = {
            "symbol": symbol,
            "asks": processed_asks,
            "bids": processed_bids,
            "ask_count": len(processed_asks),
            "bid_count": len(processed_bids),
            "spread": (processed_asks[0]["price"] - processed_bids[0]["price"])  # type: ignore[operator]
            if processed_asks and processed_bids
            else 0.0,
            "updated_at": pricebook_data.get("updated_at", "N/A"),
            "note": "Level II data requires Robinhood Gold subscription",
        }

        logger.info(
            f"Successfully retrieved pricebook for {symbol}: {len(processed_asks)} asks, {len(processed_bids)} bids"
        )
        return create_success_response(processed_pricebook)

    except (ValueError, TypeError, KeyError) as e:
        return create_error_response(
            ValueError(f"Error processing pricebook data: {e!s}"),
            "pricebook processing",
        )
