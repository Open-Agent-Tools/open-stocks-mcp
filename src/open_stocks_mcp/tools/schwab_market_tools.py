"""Schwab market data MCP tools using schwab-py library."""

import datetime
from typing import Any

from schwab.client import Client

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.broker_utils import (
    execute_broker_request,
    get_authenticated_broker_or_error,
)
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

        quote_data = await execute_broker_request(_get_quote, retry_safe=True)

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

        quotes_data = await execute_broker_request(_get_quotes, retry_safe=True)

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
        # Map period type to enum

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

        history_data = await execute_broker_request(_get_price_history, retry_safe=True)

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

        quote_data = await execute_broker_request(_get_quote, retry_safe=True)

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

        quote_data = await execute_broker_request(_get_quote, retry_safe=True)

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


@handle_schwab_errors
async def get_schwab_market_hours(
    market: str = "equity", date: str | None = None
) -> dict[str, Any]:
    """Get market hours for a given market and optional date.

    Args:
        market: Market type ('equity', 'option', 'bond', 'forex', 'future')
        date: Optional ISO date string (e.g. '2026-05-20'). Defaults to today.

    Returns:
        Dict with market hours data.
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get market hours for {market}"
    )
    if error:
        return error

    market_map = {
        "equity": Client.MarketHours.Market.EQUITY,
        "option": Client.MarketHours.Market.OPTION,
        "bond": Client.MarketHours.Market.BOND,
        "forex": Client.MarketHours.Market.FOREX,
        "future": Client.MarketHours.Market.FUTURE,
    }

    mapped_market = market_map.get(market.lower())
    if mapped_market is None:
        return create_error_response(
            ValueError(
                f"Invalid market '{market}'. Valid markets: {list(market_map.keys())}"
            )
        )

    parsed_date: datetime.date | None = None
    if date is not None:
        try:
            parsed_date = datetime.date.fromisoformat(date)
        except ValueError:
            return create_error_response(
                ValueError(f"Invalid date format '{date}'. Use ISO format: YYYY-MM-DD")
            )

    try:

        def _get_market_hours() -> Any:
            response = broker.client.get_market_hours([mapped_market], date=parsed_date)
            return response.json()

        hours_data = await execute_broker_request(_get_market_hours, retry_safe=True)

        return create_success_response(
            {
                "market": market.lower(),
                "date": date,
                "hours": hours_data,
            }
        )

    except Exception as e:
        logger.error(f"Error getting Schwab market hours for {market}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def get_schwab_movers(
    index: str,
    sort_order: str | None = None,
    frequency: int | None = None,
) -> dict[str, Any]:
    """Get market movers for a given index.

    Args:
        index: Index to query (e.g. '$DJI', '$SPX', 'NASDAQ', 'NYSE', '$COMPX',
               'EQUITY_ALL', 'INDEX_ALL', 'OPTION_ALL', 'OPTION_CALL', 'OPTION_PUT',
               'OTCBB')
        sort_order: Optional sort order ('PERCENT_CHANGE_UP', 'PERCENT_CHANGE_DOWN',
                    'VOLUME', 'TRADES')
        frequency: Optional frequency in minutes (0, 1, 5, 10, 30, 60)

    Returns:
        Dict with movers data.
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get movers for {index}"
    )
    if error:
        return error

    index_map = {
        "$compx": Client.Movers.Index.COMPX,
        "$dji": Client.Movers.Index.DJI,
        "equity_all": Client.Movers.Index.EQUITY_ALL,
        "index_all": Client.Movers.Index.INDEX_ALL,
        "nasdaq": Client.Movers.Index.NASDAQ,
        "nyse": Client.Movers.Index.NYSE,
        "option_all": Client.Movers.Index.OPTION_ALL,
        "option_call": Client.Movers.Index.OPTION_CALL,
        "option_put": Client.Movers.Index.OPTION_PUT,
        "otcbb": Client.Movers.Index.OTCBB,
        "$spx": Client.Movers.Index.SPX,
    }

    mapped_index = index_map.get(index.lower())
    if mapped_index is None:
        return create_error_response(
            ValueError(
                f"Invalid index '{index}'. Valid indexes: {list(index_map.keys())}"
            )
        )

    sort_order_map = {
        "percent_change_up": Client.Movers.SortOrder.PERCENT_CHANGE_UP,
        "percent_change_down": Client.Movers.SortOrder.PERCENT_CHANGE_DOWN,
        "volume": Client.Movers.SortOrder.VOLUME,
        "trades": Client.Movers.SortOrder.TRADES,
    }
    mapped_sort_order = None
    if sort_order is not None:
        mapped_sort_order = sort_order_map.get(sort_order.lower())
        if mapped_sort_order is None:
            return create_error_response(
                ValueError(
                    f"Invalid sort_order '{sort_order}'. Valid values: {list(sort_order_map.keys())}"
                )
            )

    frequency_map = {
        0: Client.Movers.Frequency.ZERO,
        1: Client.Movers.Frequency.ONE,
        5: Client.Movers.Frequency.FIVE,
        10: Client.Movers.Frequency.TEN,
        30: Client.Movers.Frequency.THIRTY,
        60: Client.Movers.Frequency.SIXTY,
    }
    mapped_frequency = None
    if frequency is not None:
        mapped_frequency = frequency_map.get(frequency)
        if mapped_frequency is None:
            return create_error_response(
                ValueError(
                    f"Invalid frequency {frequency}. Valid values: {list(frequency_map.keys())}"
                )
            )

    try:

        def _get_movers() -> Any:
            response = broker.client.get_movers(
                mapped_index,
                sort_order=mapped_sort_order,
                frequency=mapped_frequency,
            )
            return response.json()

        movers_data = await execute_broker_request(_get_movers, retry_safe=True)

        return create_success_response(
            {
                "index": index,
                "movers": movers_data.get("screeners", movers_data),
            }
        )

    except Exception as e:
        logger.error(f"Error getting Schwab movers for {index}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def get_schwab_movers_sp500(
    sort_order: str | None = None,
    frequency: int | None = None,
) -> dict[str, Any]:
    """Get market movers for the S&P 500 index ($SPX).

    Args:
        sort_order: Optional sort order ('PERCENT_CHANGE_UP', 'PERCENT_CHANGE_DOWN',
                    'VOLUME', 'TRADES')
        frequency: Optional frequency in minutes (0, 1, 5, 10, 30, 60)

    Returns:
        Dict with S&P 500 movers data.
    """
    return await get_schwab_movers("$SPX", sort_order=sort_order, frequency=frequency)


@handle_schwab_errors
async def get_schwab_instrument_by_cusip(cusip: str) -> dict[str, Any]:
    """Get instrument details by CUSIP identifier.

    Args:
        cusip: CUSIP identifier (leading zeros are preserved, e.g. '037833100')

    Returns:
        Dict with instrument data.
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get instrument by CUSIP {cusip}"
    )
    if error:
        return error

    cusip_clean = cusip.strip()
    if not cusip_clean:
        return create_error_response(ValueError("CUSIP cannot be empty"))

    try:

        def _get_instrument() -> Any:
            response = broker.client.get_instrument_by_cusip(cusip_clean)
            return response.json()

        instrument_data = await execute_broker_request(_get_instrument, retry_safe=True)

        return create_success_response(
            {
                "cusip": cusip_clean,
                "symbol": instrument_data.get("symbol"),
                "description": instrument_data.get("description"),
                "exchange": instrument_data.get("exchange"),
                "asset_type": instrument_data.get("assetType"),
                "data": instrument_data,
            }
        )

    except Exception as e:
        logger.error(f"Error getting Schwab instrument by CUSIP {cusip}: {e}")
        return create_error_response(e)
