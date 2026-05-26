"""Mutation Robinhood watchlist tools."""

from typing import Any

import robin_stocks.robinhood as rh

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.error_handling import (
    execute_with_retry,
    handle_robin_stocks_errors,
)


@handle_robin_stocks_errors
async def add_symbols_to_watchlist(
    watchlist_name: str, symbols: list[str]
) -> dict[str, Any]:
    """Add symbols to a specific watchlist."""
    logger.info(f"Adding symbols to watchlist '{watchlist_name}': {symbols}")

    if not watchlist_name:
        return {"result": {"error": "Watchlist name is required", "status": "error"}}

    if not symbols or len(symbols) == 0:
        return {
            "result": {"error": "At least one symbol is required", "status": "error"}
        }

    formatted_symbols = []
    for symbol in symbols:
        if isinstance(symbol, str):
            formatted_symbol = symbol.upper().strip()
            if formatted_symbol:
                formatted_symbols.append(formatted_symbol)

    if not formatted_symbols:
        return {"result": {"error": "No valid symbols provided", "status": "error"}}

    try:
        from functools import partial

        post_with_name = partial(rh.post_symbols_to_watchlist, name=watchlist_name)
        result = await execute_with_retry(
            post_with_name,
            formatted_symbols,
            func_name="post_symbols_to_watchlist",
            max_retries=3,
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
    """Remove symbols from a specific watchlist."""
    logger.info(f"Removing symbols from watchlist '{watchlist_name}': {symbols}")

    if not watchlist_name:
        return {"result": {"error": "Watchlist name is required", "status": "error"}}

    if not symbols or len(symbols) == 0:
        return {
            "result": {"error": "At least one symbol is required", "status": "error"}
        }

    formatted_symbols = []
    for symbol in symbols:
        if isinstance(symbol, str):
            formatted_symbol = symbol.upper().strip()
            if formatted_symbol:
                formatted_symbols.append(formatted_symbol)

    if not formatted_symbols:
        return {"result": {"error": "No valid symbols provided", "status": "error"}}

    try:
        from functools import partial

        delete_with_name = partial(
            rh.delete_symbols_from_watchlist, name=watchlist_name
        )
        result = await execute_with_retry(
            delete_with_name,
            formatted_symbols,
            func_name="delete_symbols_from_watchlist",
            max_retries=3,
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

        logger.warning(f"Failed to remove symbols from watchlist '{watchlist_name}'")
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
