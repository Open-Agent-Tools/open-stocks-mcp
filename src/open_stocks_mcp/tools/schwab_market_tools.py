"""Schwab market data MCP tools using schwab-py library."""

import asyncio
from typing import Any

from open_stocks_mcp.brokers.auth_coordinator import get_authenticated_broker_or_error
from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.error_handling import (
    create_error_response,
    create_success_response,
    handle_schwab_errors,
)


@handle_schwab_errors
async def get_schwab_quote(symbol: str) -> dict[str, Any]:
    """Get current quote for a stock symbol from Schwab.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')

    Returns:
        Dict with quote data including price, volume, bid/ask
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get quote for {symbol}"
    )
    if error:
        return error

    try:

        def _get_quote() -> Any:
            response = broker.client.get_quote(symbol.upper())
            return response.json()

        quote_data = await asyncio.to_thread(_get_quote)

        # Extract quote from response
        quote = quote_data.get(symbol.upper(), {}).get("quote", {})

        return create_success_response(
            {
                "symbol": symbol.upper(),
                "last_price": quote.get("lastPrice"),
                "bid_price": quote.get("bidPrice"),
                "ask_price": quote.get("askPrice"),
                "bid_size": quote.get("bidSize"),
                "ask_size": quote.get("askSize"),
                "volume": quote.get("totalVolume"),
                "open_price": quote.get("openPrice"),
                "high_price": quote.get("highPrice"),
                "low_price": quote.get("lowPrice"),
                "close_price": quote.get("closePrice"),
                "change": quote.get("netChange"),
                "change_percent": quote.get("netPercentChange"),
                "52_week_high": quote.get("52WkHigh"),
                "52_week_low": quote.get("52WkLow"),
                "market_cap": quote.get("marketCap"),
                "pe_ratio": quote.get("peRatio"),
                "dividend_yield": quote.get("divYield"),
            }
        )

    except Exception as e:
        logger.error(f"Error getting Schwab quote for {symbol}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def get_schwab_quotes(symbols: list[str]) -> dict[str, Any]:
    """Get current quotes for multiple stock symbols from Schwab.

    Args:
        symbols: List of stock ticker symbols (e.g., ['AAPL', 'TSLA', 'GOOGL'])

    Returns:
        Dict with quotes for all symbols
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get quotes for {len(symbols)} symbols"
    )
    if error:
        return error

    try:
        # Convert to uppercase
        symbols_upper = [s.upper() for s in symbols]

        def _get_quotes() -> Any:
            response = broker.client.get_quotes(symbols_upper)
            return response.json()

        quotes_data = await asyncio.to_thread(_get_quotes)

        # Format quotes
        quotes = {}
        for symbol in symbols_upper:
            quote_info = quotes_data.get(symbol, {})
            quote = quote_info.get("quote", {})

            quotes[symbol] = {
                "last_price": quote.get("lastPrice"),
                "change": quote.get("netChange"),
                "change_percent": quote.get("netPercentChange"),
                "volume": quote.get("totalVolume"),
                "bid_price": quote.get("bidPrice"),
                "ask_price": quote.get("askPrice"),
            }

        return create_success_response(
            {
                "quotes": quotes,
                "count": len(quotes),
            }
        )

    except Exception as e:
        logger.error(f"Error getting Schwab quotes: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def get_schwab_price_history(
    symbol: str,
    period_type: str = "day",
    period: int = 1,
    frequency_type: str = "minute",
    frequency: int = 1,
) -> dict[str, Any]:
    """Get price history for a stock symbol.

    Args:
        symbol: Stock ticker symbol
        period_type: Type of period ('day', 'month', 'year', 'ytd')
        period: Number of periods
        frequency_type: Frequency type ('minute', 'daily', 'weekly', 'monthly')
        frequency: Frequency value

    Returns:
        Dict with historical price data (candles)
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get price history for {symbol}"
    )
    if error:
        return error

    try:
        from schwab.client import Client

        # Map period types
        period_type_map = {
            "day": Client.PriceHistory.PeriodType.DAY,
            "month": Client.PriceHistory.PeriodType.MONTH,
            "year": Client.PriceHistory.PeriodType.YEAR,
            "ytd": Client.PriceHistory.PeriodType.YEAR_TO_DATE,
        }

        # Map frequency types
        frequency_type_map = {
            "minute": Client.PriceHistory.FrequencyType.MINUTE,
            "daily": Client.PriceHistory.FrequencyType.DAILY,
            "weekly": Client.PriceHistory.FrequencyType.WEEKLY,
            "monthly": Client.PriceHistory.FrequencyType.MONTHLY,
        }

        pt = period_type_map.get(period_type.lower())
        ft = frequency_type_map.get(frequency_type.lower())

        if not pt or not ft:
            return create_error_response(
                ValueError(
                    f"Invalid period_type or frequency_type. "
                    f"Valid period_types: {list(period_type_map.keys())}, "
                    f"Valid frequency_types: {list(frequency_type_map.keys())}"
                )
            )

        def _get_price_history() -> Any:
            response = broker.client.get_price_history(
                symbol.upper(),
                period_type=pt,
                period=period,
                frequency_type=ft,
                frequency=frequency,
            )
            return response.json()

        history_data = await asyncio.to_thread(_get_price_history)

        candles = history_data.get("candles", [])

        return create_success_response(
            {
                "symbol": symbol.upper(),
                "candles": candles,
                "count": len(candles),
                "empty": history_data.get("empty", False),
            }
        )

    except Exception as e:
        logger.error(f"Error getting Schwab price history for {symbol}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def get_schwab_instrument(symbol: str) -> dict[str, Any]:
    """Get instrument information for a symbol.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Dict with instrument details
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get instrument {symbol}"
    )
    if error:
        return error

    try:
        # Use quote to get instrument info
        def _get_quote() -> Any:
            response = broker.client.get_quote(symbol.upper())
            return response.json()

        quote_data = await asyncio.to_thread(_get_quote)

        symbol_data = quote_data.get(symbol.upper(), {})
        reference = symbol_data.get("reference", {})

        return create_success_response(
            {
                "symbol": symbol.upper(),
                "description": reference.get("description"),
                "exchange": reference.get("exchange"),
                "exchange_name": reference.get("exchangeName"),
                "asset_type": symbol_data.get("assetMainType"),
                "cusip": reference.get("cusip"),
            }
        )

    except Exception as e:
        logger.error(f"Error getting Schwab instrument for {symbol}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def search_schwab_instruments(query: str) -> dict[str, Any]:
    """Search for instruments by symbol or name.

    Note: Schwab API doesn't have a direct search endpoint.
    This is a simplified implementation using quote lookup.

    Args:
        query: Symbol or company name to search

    Returns:
        Dict with search results
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"search instruments {query}"
    )
    if error:
        return error

    try:
        # Try to get quote for the query (assuming it's a symbol)
        def _get_quote() -> Any:
            response = broker.client.get_quote(query.upper())
            return response.json()

        quote_data = await asyncio.to_thread(_get_quote)

        results = []
        for symbol, data in quote_data.items():
            reference = data.get("reference", {})
            results.append(
                {
                    "symbol": symbol,
                    "description": reference.get("description"),
                    "exchange": reference.get("exchangeName"),
                    "asset_type": data.get("assetMainType"),
                }
            )

        return create_success_response(
            {
                "results": results,
                "count": len(results),
            }
        )

    except Exception as e:
        logger.error(f"Error searching Schwab instruments for '{query}': {e}")
        return create_error_response(
            ValueError(
                f"No results found for '{query}'. Try using exact ticker symbol."
            )
        )
