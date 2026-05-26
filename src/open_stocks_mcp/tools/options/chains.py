"""Robinhood options chain discovery tools."""

from typing import Any

import robin_stocks.robinhood as rh

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.error_handling import (
    execute_with_retry,
    handle_robin_stocks_errors,
)


@handle_robin_stocks_errors
async def get_options_chains(symbol: str) -> dict[str, Any]:
    """
    Get option chain metadata for a stock symbol.

    This function retrieves option chain information including available expiration dates,
    trading rules, and underlying instrument details. Use find_tradable_options() to get
    individual option contracts.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "GOOGL")

    Returns:
        Dict containing option chain metadata:
        {
            "result": {
                "symbol": "AAPL",
                "chains": {
                    "id": "7dd906e5-7d4b-4161-a3fe-2c3b62038482",
                    "symbol": "AAPL",
                    "can_open_position": true,
                    "cash_component": null,
                    "expiration_dates": [
                        "2025-08-15",
                        "2025-08-22",
                        "2025-09-12",
                        ...
                    ],
                    "trade_value_multiplier": "100.0000",
                    "underlying_instruments": [
                        {
                            "id": "3b1b2528-8887-4410-bce4-b5128eac4a86",
                            "instrument": "https://api.robinhood.com/instruments/450dfc6d-5510-4d40-abfb-f633b7d9be3e/",
                            "quantity": 100
                        }
                    ],
                    "min_ticks": {
                        "above_tick": "0.05",
                        "below_tick": "0.01",
                        "cutoff_price": "3.00"
                    },
                    "min_ticks_multileg": {
                        "above_tick": "0.01",
                        "below_tick": "0.01",
                        "cutoff_price": "0.00"
                    },
                    "late_close_state": "disabled",
                    "underlyings": [
                        {
                            "type": "equity",
                            "id": "450dfc6d-5510-4d40-abfb-f633b7d9be3e",
                            "quantity": 100,
                            "symbol": "AAPL"
                        }
                    ],
                    "settle_on_open": false,
                    "sellout_time_to_expiration": 1800
                },
                "total_contracts": 1,
                "status": "success"
            }
        }
    """
    logger.info(f"Getting option chains for symbol: {symbol}")

    # Validate and format symbol
    symbol = symbol.upper().strip()
    if not symbol:
        return {"result": {"error": "Symbol is required", "status": "error"}}

    # Get option chains data
    chains_data = await execute_with_retry(rh.options.get_chains, symbol, max_retries=3)

    if not chains_data:
        logger.warning(f"No option chains found for {symbol}")
        return {
            "result": {
                "symbol": symbol,
                "chains": [],
                "total_contracts": 0,
                "message": "No option chains found",
                "status": "no_data",
            }
        }

    logger.info(f"Successfully retrieved option chains for {symbol}")

    return {
        "result": {
            "symbol": symbol,
            "chains": chains_data,
            "total_contracts": len(chains_data) if isinstance(chains_data, list) else 1,
            "status": "success",
        }
    }


@handle_robin_stocks_errors
async def find_tradable_options(
    symbol: str, expiration_date: str | None = None, option_type: str | None = None
) -> dict[str, Any]:
    """
    Find tradable options for a symbol with optional filtering.

    This function searches for specific option contracts based on expiration date
    and option type filters.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "GOOGL"). Required.
        expiration_date: Optional expiration date in YYYY-MM-DD format (e.g., "2025-09-12").
                        If provided in incorrect format, may return no results.
        option_type: Optional option type. Must be "call" or "put" (case insensitive).
                    Invalid values will return an error.

    Returns:
        Dict containing filtered option contracts:
        {
            "result": {
                "symbol": "AAPL",
                "filters": {
                    "expiration_date": "2024-01-19",
                    "option_type": "call"
                },
                "options": [
                    {
                        "chain_id": "b905e24f-f046-458c-af25-244dbe46616c",
                        "chain_symbol": "AAPL",
                        "created_at": "2025-08-01T01:04:29.754918Z",
                        "expiration_date": "2024-01-19",
                        "id": "fed6fe71-a605-4340-812a-3b0df7d1bbc3",
                        "issue_date": "2025-08-01",
                        "min_ticks": {
                            "above_tick": "0.05",
                            "below_tick": "0.01",
                            "cutoff_price": "3.00"
                        },
                        "rhs_tradability": "position_closing_only",
                        "state": "active",
                        "strike_price": "150.0000",
                        "tradability": "tradable",
                        "type": "call",
                        "updated_at": "2025-08-01T01:04:29.754932Z",
                        "url": "https://api.robinhood.com/options/instruments/fed6fe71-a605-4340-812a-3b0df7d1bbc3/",
                        "sellout_datetime": "2024-01-19T19:30:00+00:00",
                        "long_strategy_code": "fed6fe71-a605-4340-812a-3b0df7d1bbc3_L1",
                        "short_strategy_code": "fed6fe71-a605-4340-812a-3b0df7d1bbc3_S1",
                        "underlying_type": "equity"
                    },
                    ...
                ],
                "total_found": 25,
                "status": "success"
            }
        }
    """
    logger.info(
        f"Finding tradable options for {symbol} with filters: expiration={expiration_date}, type={option_type}"
    )

    # Validate and format symbol
    symbol = symbol.upper().strip()
    if not symbol:
        return {"result": {"error": "Symbol is required", "status": "error"}}

    # Validate option type if provided
    if option_type:
        option_type = option_type.lower()
        if option_type not in ["call", "put"]:
            return {
                "result": {
                    "error": "Option type must be 'call' or 'put'",
                    "status": "error",
                }
            }

    # Find tradable options using correct Robin Stocks API
    try:
        options_data = await execute_with_retry(
            rh.find_options_by_expiration,
            symbol,
            expiration_date,
            option_type,
            max_retries=3,
        )
    except AttributeError:
        # Fallback: try alternative API function names
        try:
            options_data = await execute_with_retry(
                rh.get_option_contracts_by_ticker,
                symbol,
                expiration_date,
                max_retries=3,
            )
        except AttributeError:
            logger.error("Could not find correct Robin Stocks options API function")
            return {
                "result": {
                    "symbol": symbol,
                    "error": "Options API function not available",
                    "status": "error",
                }
            }

    if not options_data:
        logger.warning(f"No tradable options found for {symbol}")
        return {
            "result": {
                "symbol": symbol,
                "filters": {
                    "expiration_date": expiration_date,
                    "option_type": option_type,
                },
                "options": [],
                "total_found": 0,
                "message": "No tradable options found",
                "status": "no_data",
            }
        }

    logger.info(
        f"Found {len(options_data) if isinstance(options_data, list) else 1} tradable options for {symbol}"
    )

    return {
        "result": {
            "symbol": symbol,
            "filters": {"expiration_date": expiration_date, "option_type": option_type},
            "options": options_data,
            "total_found": len(options_data) if isinstance(options_data, list) else 1,
            "status": "success",
        }
    }
