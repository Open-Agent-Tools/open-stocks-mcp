"""Read-only Robinhood watchlist tools."""

from typing import Any

import robin_stocks.robinhood as rh

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.error_handling import (
    execute_with_retry,
    handle_robin_stocks_errors,
)


@handle_robin_stocks_errors
async def get_all_watchlists() -> dict[str, Any]:
    """Get all user-created watchlists."""
    logger.info("Getting all user watchlists")

    watchlists_data = await execute_with_retry(
        rh.get_all_watchlists, func_name="get_all_watchlists", max_retries=3
    )

    if not watchlists_data:
        logger.warning("No watchlists found")
        return {
            "result": {
                "watchlists": [],
                "total_watchlists": 0,
                "message": "No watchlists found",
                "status": "no_data",
            }
        }

    if isinstance(watchlists_data, dict) and "results" in watchlists_data:
        watchlist_items = watchlists_data["results"]
    elif isinstance(watchlists_data, list):
        watchlist_items = watchlists_data
    else:
        logger.warning(f"Unexpected watchlists data format: {type(watchlists_data)}")
        return {
            "result": {
                "watchlists": [],
                "total_watchlists": 0,
                "message": "Unexpected data format",
                "status": "error",
            }
        }

    logger.info(f"Found {len(watchlist_items)} watchlists")

    processed_watchlists = []
    if isinstance(watchlist_items, list):
        for watchlist in watchlist_items:
            if isinstance(watchlist, dict):
                symbols = watchlist.get("symbols", [])
                processed_watchlists.append(
                    {**watchlist, "symbol_count": len(symbols) if symbols else 0}
                )

    logger.info(f"Found {len(processed_watchlists)} watchlists")

    return {
        "result": {
            "watchlists": processed_watchlists,
            "total_watchlists": len(processed_watchlists),
            "status": "success",
        }
    }


@handle_robin_stocks_errors
async def get_watchlist_by_name(watchlist_name: str) -> dict[str, Any]:
    """Get contents of a specific watchlist by name."""
    logger.info(f"Getting watchlist by name: {watchlist_name}")

    if not watchlist_name:
        return {"result": {"error": "Watchlist name is required", "status": "error"}}

    watchlist_data = await execute_with_retry(
        rh.get_watchlist_by_name,
        watchlist_name,
        func_name="get_watchlist_by_name",
        max_retries=3,
    )

    if not watchlist_data:
        logger.warning(f"Watchlist '{watchlist_name}' not found")
        return {
            "result": {
                "name": watchlist_name,
                "symbols": [],
                "symbol_count": 0,
                "message": f"Watchlist '{watchlist_name}' not found",
                "status": "not_found",
            }
        }

    symbols = watchlist_data.get("symbols", [])
    symbol_count = len(symbols) if symbols else 0

    logger.info(f"Found watchlist '{watchlist_name}' with {symbol_count} symbols")

    return {
        "result": {
            "name": watchlist_name,
            "watchlist_data": watchlist_data,
            "symbols": symbols,
            "symbol_count": symbol_count,
            "status": "success",
        }
    }


@handle_robin_stocks_errors
async def get_watchlist_performance(watchlist_name: str) -> dict[str, Any]:
    """Get performance metrics for a specific watchlist."""
    logger.info(f"Getting performance for watchlist: {watchlist_name}")

    if not watchlist_name:
        return {"result": {"error": "Watchlist name is required", "status": "error"}}

    watchlist_data = await get_watchlist_by_name(watchlist_name)

    if watchlist_data["result"]["status"] != "success":
        return watchlist_data

    symbols = watchlist_data["result"].get("symbols", [])

    if not symbols:
        return {
            "result": {
                "watchlist_name": watchlist_name,
                "symbols": [],
                "summary": {
                    "total_symbols": 0,
                    "gainers": 0,
                    "losers": 0,
                    "unchanged": 0,
                },
                "message": "No symbols in watchlist",
                "status": "no_data",
            }
        }

    symbols_list = [s for s in symbols if isinstance(s, str)]

    performance_data: list[dict[str, Any]] = []
    gainers = 0
    losers = 0
    unchanged = 0
    total_volume = 0
    total_change_percent = 0.0

    try:
        price_results = await execute_with_retry(rh.get_latest_price, symbols_list)
        quote_results = await execute_with_retry(rh.get_quotes, symbols_list)

        if not isinstance(price_results, list):
            price_results = []
        if not isinstance(quote_results, list):
            quote_results = []

        quote_by_symbol = {
            str(quote["symbol"]).upper(): quote
            for quote in quote_results
            if isinstance(quote, dict) and quote.get("symbol")
        }
        quotes_have_symbols = bool(quote_by_symbol)
        prices_are_aligned = len(price_results) == len(symbols_list)

        for i, symbol in enumerate(symbols_list):
            symbol_key = symbol.upper()
            quote = quote_by_symbol.get(symbol_key)
            if quote is None and not quotes_have_symbols:
                maybe_quote = quote_results[i] if i < len(quote_results) else {}
                quote = maybe_quote if isinstance(maybe_quote, dict) else {}
            elif quote is None:
                quote = {}

            price_str = (
                quote.get("last_trade_price")
                or quote.get("last_extended_hours_trade_price")
                or quote.get("ask_price")
                or quote.get("bid_price")
            )
            if (
                price_str in (None, "")
                and prices_are_aligned
                and not quotes_have_symbols
            ):
                price_str = price_results[i]

            if price_str is not None:
                try:
                    current_price = float(price_str)
                    previous_close = float(quote.get("previous_close", 0))
                    volume = int(quote.get("volume", 0))

                    if previous_close > 0:
                        change = current_price - previous_close
                        change_percent = (change / previous_close) * 100

                        if change_percent > 0:
                            gainers += 1
                        elif change_percent < 0:
                            losers += 1
                        else:
                            unchanged += 1

                        total_change_percent += change_percent
                        total_volume += volume

                        performance_data.append(
                            {
                                "symbol": symbol,
                                "current_price": price_str,
                                "change": f"{change:+.2f}",
                                "change_percent": f"{change_percent:+.2f}%",
                                "volume": volume,
                            }
                        )
                    else:
                        total_volume += volume
                        performance_data.append(
                            {
                                "symbol": symbol,
                                "current_price": price_str,
                                "change": "N/A",
                                "change_percent": "N/A",
                                "volume": volume,
                            }
                        )
                except (ValueError, TypeError) as exc:
                    logger.warning(f"Could not parse data for {symbol}: {exc}")
                    performance_data.append(
                        {
                            "symbol": symbol,
                            "current_price": "N/A",
                            "change": "N/A",
                            "change_percent": "N/A",
                            "volume": 0,
                            "error": str(exc),
                        }
                    )
            else:
                performance_data.append(
                    {
                        "symbol": symbol,
                        "current_price": "N/A",
                        "change": "N/A",
                        "change_percent": "N/A",
                        "volume": 0,
                    }
                )

    except Exception as exc:
        logger.warning(f"Could not get performance data for watchlist: {exc}")
        for symbol in symbols_list:
            performance_data.append(
                {
                    "symbol": symbol,
                    "current_price": "N/A",
                    "change": "N/A",
                    "change_percent": "N/A",
                    "volume": 0,
                    "error": str(exc),
                }
            )

    total_symbols = len(symbols_list)
    avg_change_percent = (
        total_change_percent / total_symbols if total_symbols > 0 else 0
    )

    logger.info(
        f"Performance analysis complete for '{watchlist_name}': {gainers} gainers, {losers} losers"
    )

    return {
        "result": {
            "watchlist_name": watchlist_name,
            "symbols": performance_data,
            "summary": {
                "total_symbols": total_symbols,
                "gainers": gainers,
                "losers": losers,
                "unchanged": unchanged,
                "avg_change_percent": f"{avg_change_percent:+.2f}%",
                "total_volume": total_volume,
            },
            "status": "success",
        }
    }
