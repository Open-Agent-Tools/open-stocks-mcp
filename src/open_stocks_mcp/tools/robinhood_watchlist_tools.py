"""
Watchlist Management Tools for Robin Stocks MCP Server.

This module provides comprehensive watchlist management functionality including:
- Creating and managing stock watchlists
- Adding and removing symbols from watchlists
- Retrieving watchlist contents and performance
- Bulk operations for watchlist management

All functions use Robin Stocks API with proper error handling and async support.
"""

from typing import Any

import robin_stocks.robinhood as rh

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.error_handling import (
    execute_with_retry,
    handle_robin_stocks_errors,
)


@handle_robin_stocks_errors
async def get_all_watchlists() -> dict[str, Any]:
    """
    Get all user-created watchlists.

    This function retrieves all watchlists created by the user,
    including their names, symbols, and basic information.

    Returns:
        Dict containing all watchlists:
        {
            "result": {
                "watchlists": [
                    {
                        "name": "Tech Stocks",
                        "url": "watchlist_url",
                        "user": "user_url",
                        "symbols": ["AAPL", "GOOGL", "MSFT"],
                        "symbol_count": 3
                    },
                    ...
                ],
                "total_watchlists": 5,
                "status": "success"
            }
        }
    """
    logger.info("Getting all user watchlists")

    # Get all watchlists
    watchlists_data = await execute_with_retry(
        func=rh.get_all_watchlists, func_name="get_all_watchlists", max_retries=3
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

    # Process watchlists to add symbol counts
    processed_watchlists = []
    if isinstance(watchlists_data, list):
        for watchlist in watchlists_data:
            if isinstance(watchlist, dict):
                # Get symbols for this watchlist if available
                symbols = watchlist.get("symbols", [])
                processed_watchlist = {
                    **watchlist,
                    "symbol_count": len(symbols) if symbols else 0,
                }
                processed_watchlists.append(processed_watchlist)

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
    """
    Get contents of a specific watchlist by name.

    This function retrieves the complete contents of a watchlist,
    including all symbols and their current market data.

    Args:
        watchlist_name: Name of the watchlist to retrieve

    Returns:
        Dict containing watchlist contents:
        {
            "result": {
                "name": "Tech Stocks",
                "symbols": [
                    {
                        "symbol": "AAPL",
                        "name": "Apple Inc.",
                        "price": "150.00",
                        "change": "+2.50",
                        "change_percent": "+1.69%"
                    },
                    ...
                ],
                "symbol_count": 3,
                "total_value": "1250.00",
                "status": "success"
            }
        }
    """
    logger.info(f"Getting watchlist by name: {watchlist_name}")

    if not watchlist_name:
        return {"result": {"error": "Watchlist name is required", "status": "error"}}

    # Get watchlist by name
    watchlist_data = await execute_with_retry(
        func=rh.get_watchlist_by_name,
        func_name="get_watchlist_by_name",
        max_retries=3,
        name=watchlist_name,
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

    # Extract symbols if available
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
async def add_symbols_to_watchlist(
    watchlist_name: str, symbols: list[str]
) -> dict[str, Any]:
    """
    Add symbols to a specific watchlist.

    This function adds one or more stock symbols to an existing watchlist.
    If the watchlist doesn't exist, it may be created automatically.

    Args:
        watchlist_name: Name of the watchlist to add symbols to
        symbols: List of stock symbols to add (e.g., ["AAPL", "GOOGL"])

    Returns:
        Dict containing operation results:
        {
            "result": {
                "watchlist_name": "Tech Stocks",
                "symbols_added": ["AAPL", "GOOGL"],
                "symbols_count": 2,
                "success": true,
                "message": "Successfully added 2 symbols to watchlist",
                "status": "success"
            }
        }
    """
    logger.info(f"Adding symbols to watchlist '{watchlist_name}': {symbols}")

    if not watchlist_name:
        return {"result": {"error": "Watchlist name is required", "status": "error"}}

    if not symbols or len(symbols) == 0:
        return {
            "result": {"error": "At least one symbol is required", "status": "error"}
        }

    # Validate and format symbols
    formatted_symbols = []
    for symbol in symbols:
        if isinstance(symbol, str):
            formatted_symbol = symbol.upper().strip()
            if formatted_symbol:
                formatted_symbols.append(formatted_symbol)

    if not formatted_symbols:
        return {"result": {"error": "No valid symbols provided", "status": "error"}}

    # Add symbols to watchlist
    try:
        result = await execute_with_retry(
            func=rh.post_symbols_to_watchlist,
            func_name="post_symbols_to_watchlist",
            max_retries=3,
            watchlist_name=watchlist_name,
            symbols=formatted_symbols,
        )

        if result:
            logger.info(
                f"Successfully added {len(formatted_symbols)} symbols to '{watchlist_name}'"
            )
            return {
                "result": {
                    "watchlist_name": watchlist_name,
                    "symbols_added": formatted_symbols,
                    "symbols_count": len(formatted_symbols),
                    "success": True,
                    "message": f"Successfully added {len(formatted_symbols)} symbols to watchlist",
                    "operation_result": result,
                    "status": "success",
                }
            }
        else:
            logger.warning(f"Failed to add symbols to watchlist '{watchlist_name}'")
            return {
                "result": {
                    "watchlist_name": watchlist_name,
                    "symbols_attempted": formatted_symbols,
                    "success": False,
                    "error": "Failed to add symbols to watchlist",
                    "status": "error",
                }
            }

    except Exception as e:
        logger.error(f"Error adding symbols to watchlist: {e}")
        return {
            "result": {
                "watchlist_name": watchlist_name,
                "symbols_attempted": formatted_symbols,
                "success": False,
                "error": f"Error adding symbols to watchlist: {e!s}",
                "status": "error",
            }
        }


@handle_robin_stocks_errors
async def remove_symbols_from_watchlist(
    watchlist_name: str, symbols: list[str]
) -> dict[str, Any]:
    """
    Remove symbols from a specific watchlist.

    This function removes one or more stock symbols from an existing watchlist.

    Args:
        watchlist_name: Name of the watchlist to remove symbols from
        symbols: List of stock symbols to remove (e.g., ["AAPL", "GOOGL"])

    Returns:
        Dict containing operation results:
        {
            "result": {
                "watchlist_name": "Tech Stocks",
                "symbols_removed": ["AAPL", "GOOGL"],
                "symbols_count": 2,
                "success": true,
                "message": "Successfully removed 2 symbols from watchlist",
                "status": "success"
            }
        }
    """
    logger.info(f"Removing symbols from watchlist '{watchlist_name}': {symbols}")

    if not watchlist_name:
        return {"result": {"error": "Watchlist name is required", "status": "error"}}

    if not symbols or len(symbols) == 0:
        return {
            "result": {"error": "At least one symbol is required", "status": "error"}
        }

    # Validate and format symbols
    formatted_symbols = []
    for symbol in symbols:
        if isinstance(symbol, str):
            formatted_symbol = symbol.upper().strip()
            if formatted_symbol:
                formatted_symbols.append(formatted_symbol)

    if not formatted_symbols:
        return {"result": {"error": "No valid symbols provided", "status": "error"}}

    # Remove symbols from watchlist
    try:
        result = await execute_with_retry(
            func=rh.delete_symbols_from_watchlist,
            func_name="delete_symbols_from_watchlist",
            max_retries=3,
            watchlist_name=watchlist_name,
            symbols=formatted_symbols,
        )

        if result:
            logger.info(
                f"Successfully removed {len(formatted_symbols)} symbols from '{watchlist_name}'"
            )
            return {
                "result": {
                    "watchlist_name": watchlist_name,
                    "symbols_removed": formatted_symbols,
                    "symbols_count": len(formatted_symbols),
                    "success": True,
                    "message": f"Successfully removed {len(formatted_symbols)} symbols from watchlist",
                    "operation_result": result,
                    "status": "success",
                }
            }
        else:
            logger.warning(
                f"Failed to remove symbols from watchlist '{watchlist_name}'"
            )
            return {
                "result": {
                    "watchlist_name": watchlist_name,
                    "symbols_attempted": formatted_symbols,
                    "success": False,
                    "error": "Failed to remove symbols from watchlist",
                    "status": "error",
                }
            }

    except Exception as e:
        logger.error(f"Error removing symbols from watchlist: {e}")
        return {
            "result": {
                "watchlist_name": watchlist_name,
                "symbols_attempted": formatted_symbols,
                "success": False,
                "error": f"Error removing symbols from watchlist: {e!s}",
                "status": "error",
            }
        }


@handle_robin_stocks_errors
async def get_watchlist_performance(watchlist_name: str) -> dict[str, Any]:
    """
    Get performance metrics for a specific watchlist.

    This function retrieves performance data for all symbols in a watchlist,
    including current prices, changes, and aggregate performance metrics.

    Args:
        watchlist_name: Name of the watchlist to analyze

    Returns:
        Dict containing watchlist performance data:
        {
            "result": {
                "watchlist_name": "Tech Stocks",
                "symbols": [
                    {
                        "symbol": "AAPL",
                        "current_price": "150.00",
                        "change": "+2.50",
                        "change_percent": "+1.69%",
                        "volume": 50000000
                    },
                    ...
                ],
                "summary": {
                    "total_symbols": 3,
                    "gainers": 2,
                    "losers": 1,
                    "unchanged": 0,
                    "avg_change_percent": "+1.25%",
                    "total_volume": 150000000
                },
                "status": "success"
            }
        }
    """
    logger.info(f"Getting performance for watchlist: {watchlist_name}")

    if not watchlist_name:
        return {"result": {"error": "Watchlist name is required", "status": "error"}}

    # First get the watchlist to find symbols
    watchlist_data = await get_watchlist_by_name(watchlist_name)

    if watchlist_data["result"]["status"] != "success":
        return watchlist_data  # type: ignore[no-any-return]

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

    # Get current prices for all symbols
    performance_data = []
    gainers = 0
    losers = 0
    unchanged = 0
    total_volume = 0
    total_change_percent = 0.0

    for symbol in symbols:
        try:
            # Get current price data for symbol
            price_data = await execute_with_retry(
                func=rh.get_latest_price,
                func_name="get_latest_price",
                max_retries=2,
                inputSymbols=[symbol],
            )

            if price_data and len(price_data) > 0:
                current_price = price_data[0]

                # Get quote for additional data
                quote_data = await execute_with_retry(
                    func=rh.get_quote,
                    func_name="get_quote",
                    max_retries=2,
                    inputSymbols=[symbol],
                )

                if quote_data and len(quote_data) > 0:
                    quote = quote_data[0]
                    previous_close = float(quote.get("previous_close", 0))
                    volume = int(quote.get("volume", 0))

                    if previous_close > 0:
                        change = float(current_price) - previous_close
                        change_percent = (change / previous_close) * 100

                        # Categorize performance
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
                                "current_price": current_price,
                                "change": f"{change:+.2f}",
                                "change_percent": f"{change_percent:+.2f}%",
                                "volume": volume,
                            }
                        )
                    else:
                        performance_data.append(
                            {
                                "symbol": symbol,
                                "current_price": current_price,
                                "change": "N/A",
                                "change_percent": "N/A",
                                "volume": volume,
                            }
                        )

        except Exception as e:
            logger.warning(f"Could not get performance data for {symbol}: {e}")
            performance_data.append(
                {
                    "symbol": symbol,
                    "current_price": "N/A",
                    "change": "N/A",
                    "change_percent": "N/A",
                    "volume": 0,
                    "error": str(e),
                }
            )

    # Calculate summary metrics
    total_symbols = len(symbols)
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
