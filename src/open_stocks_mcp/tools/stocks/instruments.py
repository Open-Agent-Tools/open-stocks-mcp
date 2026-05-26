"""Instrument lookup and search tools."""

import asyncio
from typing import Any

import robin_stocks.robinhood as rh

from open_stocks_mcp.config import get_config
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
from open_stocks_mcp.tools.rate_limiter import get_batcher


async def _fetch_instruments_batch(symbols: list[str]) -> dict[str, Any]:
    """Helper for batching instrument lookups."""
    instruments = await execute_with_retry(rh.get_instruments_by_symbols, symbols) or []
    return {
        inst.get("symbol", "").upper(): inst
        for inst in instruments
        if inst and inst.get("symbol")
    }


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

    # Use batching for instruments lookup
    cfg = get_config()
    batcher = get_batcher(
        "robinhood_instruments",
        batch_size=cfg.batch.batch_size,
        queue_max_wait=cfg.batch.queue_max_wait,
    )

    instruments_data = await asyncio.gather(
        *(batcher.fetch(s, _fetch_instruments_batch) for s in clean_symbols)
    )

    if not any(instruments_data):
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
        {
            "query": query,
            "results": results,
            "count": len(results),
        }
    )
