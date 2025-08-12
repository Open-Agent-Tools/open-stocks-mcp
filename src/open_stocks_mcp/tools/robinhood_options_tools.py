"""
Options Trading Tools for Robin Stocks MCP Server.

This module provides comprehensive options trading analytics tools including:
- Options chains and contract discovery
- Options market data with Greeks and open interest
- Options positions and portfolio management
- Historical options pricing data

All functions use Robin Stocks API with proper error handling and async support.
"""

import contextlib
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


@handle_robin_stocks_errors
async def get_option_market_data(option_id: str) -> dict[str, Any]:
    """
    Get market data for a specific option contract by ID.

    This function retrieves comprehensive market data including Greeks,
    open interest, volume, and bid/ask spreads for a specific option.

    Args:
        option_id: Unique option contract ID

    Returns:
        Dict containing option market data:
        {
            "result": {
                "option_id": "fed6fe71-a605-4340-812a-3b0df7d1bbc3",
                "market_data": [
                    {
                        "adjusted_mark_price": "5.780000",
                        "adjusted_mark_price_round_down": "5.770000",
                        "ask_price": "5.900000",
                        "ask_size": 90,
                        "bid_price": "5.650000",
                        "bid_size": 192,
                        "break_even_price": "11.220000",
                        "high_price": "0.000000",
                        "instrument": "https://api.robinhood.com/options/instruments/fed6fe71-a605-4340-812a-3b0df7d1bbc3/",
                        "instrument_id": "fed6fe71-a605-4340-812a-3b0df7d1bbc3",
                        "last_trade_price": null,
                        "last_trade_size": null,
                        "low_price": "0.000000",
                        "mark_price": "5.775000",
                        "open_interest": 0,
                        "previous_close_date": "2025-08-08",
                        "previous_close_price": "5.650000",
                        "updated_at": "2025-08-11T16:05:11.998328415Z",
                        "volume": 0,
                        "symbol": "F",
                        "occ_symbol": "F     250912P00017000",
                        "state": "active",
                        "chance_of_profit_long": "0.000000",
                        "chance_of_profit_short": "1.000000",
                        "delta": "0.000000",
                        "gamma": "0.000000",
                        "implied_volatility": "0.000671",
                        "rho": "0.000000",
                        "theta": "0.000000",
                        "vega": "340.500000",
                        "pricing_model": "Bjerksund-Stensland 1993",
                        "high_fill_rate_buy_price": "5.842000",
                        "high_fill_rate_sell_price": "5.707000",
                        "low_fill_rate_buy_price": "5.720000",
                        "low_fill_rate_sell_price": "5.829000"
                    }
                ],
                "status": "success"
            }
        }
    """
    logger.info(f"Getting market data for option ID: {option_id}")

    if not option_id:
        return {"result": {"error": "Option ID is required", "status": "error"}}

    # Get option market data by ID
    market_data = await execute_with_retry(
        rh.options.get_option_market_data_by_id,
        option_id,
        max_retries=3,
    )

    if not market_data:
        logger.warning(f"No market data found for option ID: {option_id}")
        return {
            "result": {
                "option_id": option_id,
                "error": "No market data found for this option",
                "status": "no_data",
            }
        }

    logger.info(f"Successfully retrieved market data for option ID: {option_id}")

    return {
        "result": {
            "option_id": option_id,
            "market_data": market_data,
            "status": "success",
        }
    }


@handle_robin_stocks_errors
async def get_option_historicals(
    symbol: str,
    expiration_date: str,
    strike_price: str,
    option_type: str,
    interval: str = "hour",
    span: str = "week",
) -> dict[str, Any]:
    """
    Get historical price data for a specific option contract.

    This function retrieves historical pricing data for an option contract
    with configurable time intervals and spans.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "GOOGL")
        expiration_date: Expiration date in YYYY-MM-DD format
        strike_price: Strike price as string
        option_type: Option type ("call" or "put")
        interval: Time interval ("5minute", "10minute", "hour", "day")
        span: Time span ("day", "week", "month", "3month", "year")

    Returns:
        Dict containing historical option price data:
        {
            "result": {
                "symbol": "AAPL",
                "expiration_date": "2024-01-19",
                "strike_price": "150.00",
                "option_type": "call",
                "interval": "hour",
                "span": "week",
                "historicals": [
                    {
                        "begins_at": "2025-08-04T00:00:00Z",
                        "open_price": "6.150000",
                        "close_price": "6.700000",
                        "high_price": "7.180000",
                        "low_price": "5.750000",
                        "volume": 0,
                        "session": "reg",
                        "interpolated": false,
                        "symbol": "F"
                    },
                    ...
                ],
                "total_data_points": 35,
                "status": "success"
            }
        }
    """
    logger.info(
        f"Getting historical data for {symbol} {strike_price} {option_type} exp: {expiration_date}"
    )

    # Validate inputs
    symbol = symbol.upper().strip()
    if not symbol:
        return {"result": {"error": "Symbol is required", "status": "error"}}

    if not expiration_date or not strike_price:
        return {
            "result": {
                "error": "Expiration date and strike price are required",
                "status": "error",
            }
        }

    option_type = option_type.lower()
    if option_type not in ["call", "put"]:
        return {
            "result": {
                "error": "Option type must be 'call' or 'put'",
                "status": "error",
            }
        }

    # Get historical option data
    historical_data = await execute_with_retry(
        rh.options.get_option_historicals,
        symbol,
        expiration_date,
        strike_price,
        option_type,
        interval,
        span,
        max_retries=3,
    )

    if not historical_data:
        logger.warning(
            f"No historical data found for {symbol} {strike_price} {option_type}"
        )
        return {
            "result": {
                "symbol": symbol,
                "expiration_date": expiration_date,
                "strike_price": strike_price,
                "option_type": option_type,
                "historicals": [],
                "total_data_points": 0,
                "message": "No historical data found",
                "status": "no_data",
            }
        }

    logger.info(
        f"Retrieved {len(historical_data) if isinstance(historical_data, list) else 1} historical data points"
    )

    return {
        "result": {
            "symbol": symbol,
            "expiration_date": expiration_date,
            "strike_price": strike_price,
            "option_type": option_type,
            "interval": interval,
            "span": span,
            "historicals": historical_data,
            "total_data_points": len(historical_data)
            if isinstance(historical_data, list)
            else 1,
            "status": "success",
        }
    }


@handle_robin_stocks_errors
async def get_aggregate_positions() -> dict[str, Any]:
    """
    Get all option positions (not actually aggregated).

    Despite the name, this function returns individual option position objects
    from Robin Stocks, not aggregated data. Each position includes detailed
    information about strategy, legs, prices, and clearing data.

    Returns:
        Dict containing array of individual option positions:
        {
            "result": {
                "positions": [
                    {
                        "id": "d97ac32e-45f6-42e9-bc2b-a4cff8c6c488",
                        "chain": "https://api.robinhood.com/options/chains/b905e24f-f046-458c-af25-244dbe46616c/",
                        "account": "https://api.robinhood.com/accounts/894785138/",
                        "account_number": "894785138",
                        "symbol": "F",
                        "strategy": "short_call",
                        "average_open_price": "29.0000",
                        "legs": [
                            {
                                "id": "c77d0bd5-bb53-4b06-a93f-0a281fb5b2bf",
                                "ratio_quantity": 1,
                                "position": "https://api.robinhood.com/options/positions/7dd81e42-0d94-4630-a668-873c38164a1b/",
                                "position_type": "short",
                                "option": "https://api.robinhood.com/options/instruments/845df489-f082-4141-9e39-e6b7654f5f75/",
                                "option_id": "845df489-f082-4141-9e39-e6b7654f5f75",
                                "expiration_date": "2025-09-12",
                                "strike_price": "11.5000",
                                "option_type": "call",
                                "settle_on_open": false
                            }
                        ],
                        "quantity": "1.0000",
                        "intraday_average_open_price": "29.0000",
                        "intraday_quantity": "1",
                        "direction": "credit",
                        "intraday_direction": "credit",
                        "trade_value_multiplier": "100.0000",
                        "created_at": "2025-08-11T13:42:16.553634Z",
                        "updated_at": "2025-08-11T13:42:16.548478Z",
                        "strategy_code": "845df489-f082-4141-9e39-e6b7654f5f75_S1",
                        "clearing_running_quantity": "1.0000",
                        "clearing_cost_basis": "29.0000",
                        "clearing_intraday_running_quantity": "1",
                        "clearing_intraday_cost_basis": "29.0000",
                        "clearing_direction": "credit",
                        "clearing_intraday_direction": "credit",
                        "underlying_type": "equity"
                    },
                    ...
                ],
                "total_positions": 15,
                "status": "success"
            }
        }
    """
    logger.info("Getting aggregated option positions")

    # Get aggregated positions
    positions_data = await execute_with_retry(
        rh.options.get_aggregate_positions,
        max_retries=3,
    )

    if not positions_data:
        logger.warning("No aggregated option positions found")
        return {
            "result": {
                "positions": {},
                "total_symbols": 0,
                "total_contracts": 0,
                "message": "No option positions found",
                "status": "no_data",
            }
        }

    # Calculate totals
    total_symbols = len(positions_data) if isinstance(positions_data, dict) else 0
    total_contracts = 0

    if isinstance(positions_data, dict):
        for symbol_data in positions_data.values():
            if isinstance(symbol_data, dict) and "positions" in symbol_data:
                total_contracts += len(symbol_data["positions"])

    logger.info(
        f"Found aggregated positions for {total_symbols} symbols with {total_contracts} contracts"
    )

    return {
        "result": {
            "positions": positions_data,
            "total_symbols": total_symbols,
            "total_contracts": total_contracts,
            "status": "success",
        }
    }


@handle_robin_stocks_errors
async def get_all_option_positions() -> dict[str, Any]:
    """
    Get all individual option positions ever held.

    This function retrieves all option position records from Robin Stocks,
    including both long and short sides of each contract, both open and closed positions.
    Each position represents one side of an option contract.

    Returns:
        Dict containing array of individual option position records:
        {
            "result": {
                "positions": [
                    {
                        "account": "https://api.robinhood.com/accounts/894785138/",
                        "account_number": "894785138",
                        "average_price": "-29.0000",
                        "chain_id": "b905e24f-f046-458c-af25-244dbe46616c",
                        "chain_symbol": "F",
                        "id": "7dd81e42-0d94-4630-a668-873c38164a1b",
                        "option": "https://api.robinhood.com/options/instruments/845df489-f082-4141-9e39-e6b7654f5f75/",
                        "type": "short",
                        "pending_buy_quantity": "0.0000",
                        "pending_expired_quantity": "0.0000",
                        "pending_expiration_quantity": "0.0000",
                        "pending_exercise_quantity": "0.0000",
                        "pending_assignment_quantity": "0.0000",
                        "pending_sell_quantity": "0.0000",
                        "quantity": "1.0000",
                        "intraday_quantity": "1.0000",
                        "intraday_average_open_price": "-29.0000",
                        "created_at": "2025-08-09T21:06:05.831182Z",
                        "expiration_date": "2025-09-12",
                        "trade_value_multiplier": "100.0000",
                        "updated_at": "2025-08-11T13:42:16.580899Z",
                        "url": "https://api.robinhood.com/options/positions/7dd81e42-0d94-4630-a668-873c38164a1b/",
                        "option_id": "845df489-f082-4141-9e39-e6b7654f5f75",
                        "clearing_running_quantity": "1.0000",
                        "clearing_cost_basis": "29.0000",
                        "clearing_direction": "credit",
                        "clearing_intraday_running_quantity": "1.0000",
                        "clearing_intraday_cost_basis": "29.0000",
                        "clearing_intraday_direction": "credit",
                        "opened_at": "2025-08-09T21:06:05.835367Z"
                    },
                    ...
                ],
                "total_positions": 25,
                "status": "success"
            }
        }
    """
    logger.info("Getting all option positions")

    # Get all option positions
    positions_data = await execute_with_retry(
        rh.options.get_all_option_positions,
        max_retries=3,
    )

    if not positions_data:
        logger.warning("No option positions found")
        return {
            "result": {
                "positions": [],
                "total_positions": 0,
                "open_positions": 0,
                "closed_positions": 0,
                "message": "No option positions found",
                "status": "no_data",
            }
        }

    # Calculate position counts
    total_positions = len(positions_data) if isinstance(positions_data, list) else 0
    open_positions = 0
    closed_positions = 0

    if isinstance(positions_data, list):
        for position in positions_data:
            if isinstance(position, dict):
                # Check if position is open based on quantity
                quantity = position.get("quantity", "0")
                if quantity and float(quantity) > 0:
                    open_positions += 1
                else:
                    closed_positions += 1

    logger.info(
        f"Found {total_positions} total positions ({open_positions} open, {closed_positions} closed)"
    )

    return {
        "result": {
            "positions": positions_data,
            "total_positions": total_positions,
            "open_positions": open_positions,
            "closed_positions": closed_positions,
            "status": "success",
        }
    }


@handle_robin_stocks_errors
async def get_open_option_positions() -> dict[str, Any]:
    """
    Get currently open option positions with summary totals.

    This function retrieves only the option positions that are currently
    open and active, along with portfolio summary information.

    Returns:
        Dict containing open option positions:
        {
            "result": {
                "positions": [
                    {
                        "account": "https://api.robinhood.com/accounts/894785138/",
                        "account_number": "894785138",
                        "average_price": "-29.0000",
                        "chain_id": "b905e24f-f046-458c-af25-244dbe46616c",
                        "chain_symbol": "F",
                        "id": "7dd81e42-0d94-4630-a668-873c38164a1b",
                        "option": "https://api.robinhood.com/options/instruments/845df489-f082-4141-9e39-e6b7654f5f75/",
                        "type": "short",
                        "pending_buy_quantity": "0.0000",
                        "pending_expired_quantity": "0.0000",
                        "pending_expiration_quantity": "0.0000",
                        "pending_exercise_quantity": "0.0000",
                        "pending_assignment_quantity": "0.0000",
                        "pending_sell_quantity": "0.0000",
                        "quantity": "1.0000",
                        "intraday_quantity": "1.0000",
                        "intraday_average_open_price": "-29.0000",
                        "created_at": "2025-08-09T21:06:05.831182Z",
                        "expiration_date": "2025-09-12",
                        "trade_value_multiplier": "100.0000",
                        "updated_at": "2025-08-11T13:42:16.580899Z",
                        "url": "https://api.robinhood.com/options/positions/7dd81e42-0d94-4630-a668-873c38164a1b/",
                        "option_id": "845df489-f082-4141-9e39-e6b7654f5f75",
                        "clearing_running_quantity": "1.0000",
                        "clearing_cost_basis": "29.0000",
                        "clearing_direction": "credit",
                        "clearing_intraday_running_quantity": "1.0000",
                        "clearing_intraday_cost_basis": "29.0000",
                        "clearing_intraday_direction": "credit",
                        "opened_at": "2025-08-09T21:06:05.835367Z"
                    },
                    ...
                ],
                "total_open_positions": 6,
                "total_equity": "0.00",
                "total_unrealized_pnl": "0.00",
                "status": "success"
            }
        }
    """
    logger.info("Getting open option positions")

    # Get open option positions
    positions_data = await execute_with_retry(
        rh.options.get_open_option_positions,
        max_retries=3,
    )

    if not positions_data:
        logger.warning("No open option positions found")
        return {
            "result": {
                "positions": [],
                "total_open_positions": 0,
                "total_equity": "0.00",
                "total_unrealized_pnl": "0.00",
                "message": "No open option positions found",
                "status": "no_data",
            }
        }

    # Calculate totals
    total_open_positions = (
        len(positions_data) if isinstance(positions_data, list) else 0
    )
    total_equity = 0.0
    total_unrealized_pnl = 0.0

    if isinstance(positions_data, list):
        for position in positions_data:
            if isinstance(position, dict):
                equity = position.get("total_equity", "0")
                if equity:
                    total_equity += float(equity)

                pnl = position.get("unrealized_pnl", "0")
                if pnl:
                    total_unrealized_pnl += float(pnl)

    logger.info(
        f"Found {total_open_positions} open positions with total equity: ${total_equity:.2f}"
    )

    return {
        "result": {
            "positions": positions_data,
            "total_open_positions": total_open_positions,
            "total_equity": f"{total_equity:.2f}",
            "total_unrealized_pnl": f"{total_unrealized_pnl:.2f}",
            "status": "success",
        }
    }


@handle_robin_stocks_errors
async def get_open_option_positions_with_details() -> dict[str, Any]:
    """
    Get currently open option positions with complete option details including call/put type.

    This enhanced function retrieves open option positions and enriches each position
    with detailed option instrument data including strike price, expiration date,
    and most importantly the option type (call or put).

    Returns:
        Dict containing open option positions with enriched details:
        {
            "result": {
                "positions": [
                    {
                        "account": "https://api.robinhood.com/accounts/894785138/",
                        "account_number": "894785138",
                        "average_price": "-29.0000",
                        "chain_id": "b905e24f-f046-458c-af25-244dbe46616c",
                        "chain_symbol": "F",
                        "id": "7dd81e42-0d94-4630-a668-873c38164a1b",
                        "option": "https://api.robinhood.com/options/instruments/845df489-f082-4141-9e39-e6b7654f5f75/",
                        "type": "short",
                        "quantity": "1.0000",
                        "expiration_date": "2025-09-12",
                        "option_id": "845df489-f082-4141-9e39-e6b7654f5f75",

                        // Enhanced fields from option instrument data:
                        "option_type": "call",           // ← "call" or "put"
                        "strike_price": "11.5000",       // ← Strike price
                        "option_symbol": "F250912C00011500",  // ← OCC symbol
                        "tradability": "tradable",       // ← Trading status
                        "state": "active",               // ← Option state
                        "underlying_symbol": "F",        // ← Underlying stock

                        // ... other existing position fields
                    },
                    ...
                ],
                "total_open_positions": 6,
                "total_equity": "0.00",
                "total_unrealized_pnl": "0.00",
                "enrichment_success_rate": "100%",
                "status": "success"
            }
        }
    """
    logger.info("Getting open option positions with detailed option information")

    # Step 1: Get base open option positions
    positions_data = await execute_with_retry(
        rh.options.get_open_option_positions,
        max_retries=3,
    )

    if not positions_data:
        logger.warning("No open option positions found")
        return {
            "result": {
                "positions": [],
                "total_open_positions": 0,
                "total_equity": "0.00",
                "total_unrealized_pnl": "0.00",
                "enrichment_success_rate": "0%",
                "message": "No open option positions found",
                "status": "no_data",
            }
        }

    # Step 2: Enrich each position with option instrument details
    enriched_positions = []
    enrichment_successes = 0
    total_positions = len(positions_data) if isinstance(positions_data, list) else 0

    if isinstance(positions_data, list):
        for position in positions_data:
            if not isinstance(position, dict):
                enriched_positions.append(position)
                continue

            # Extract option_id from position
            option_id = position.get("option_id")
            if not option_id:
                # Try to extract from option URL
                option_url = position.get("option")
                if option_url and isinstance(option_url, str):
                    # Extract ID from URL like "https://api.robinhood.com/options/instruments/845df489.../""
                    url_parts = option_url.rstrip("/").split("/")
                    option_id = url_parts[-1] if url_parts else None

            # Create enriched position starting with original data
            enriched_position = position.copy()

            if option_id:
                try:
                    # Step 3: Fetch option instrument details
                    logger.debug(f"Fetching option details for ID: {option_id}")
                    option_details = await execute_with_retry(
                        rh.options.get_option_instrument_data_by_id,
                        option_id,
                        max_retries=2,
                    )

                    if option_details and isinstance(option_details, dict):
                        # Step 4: Add enriched fields to position
                        enriched_position.update(
                            {
                                "option_type": option_details.get("type", "unknown"),
                                "strike_price": option_details.get(
                                    "strike_price", "0.0000"
                                ),
                                "option_symbol": option_details.get("occ_symbol", ""),
                                "tradability": option_details.get(
                                    "tradability", "unknown"
                                ),
                                "state": option_details.get("state", "unknown"),
                                "underlying_symbol": option_details.get(
                                    "chain_symbol", ""
                                ),
                                "expiration_date": option_details.get(
                                    "expiration_date", ""
                                ),
                                "rhs_tradability": option_details.get(
                                    "rhs_tradability", "unknown"
                                ),
                            }
                        )
                        enrichment_successes += 1
                        logger.debug(f"Successfully enriched position for {option_id}")
                    else:
                        logger.warning(
                            f"No option details found for option_id: {option_id}"
                        )
                        enriched_position["option_type"] = "unknown"

                except Exception as e:
                    logger.warning(
                        f"Failed to fetch option details for {option_id}: {e}"
                    )
                    enriched_position["option_type"] = "unknown"
            else:
                logger.warning("No option_id found in position data")
                enriched_position["option_type"] = "unknown"

            enriched_positions.append(enriched_position)

    # Calculate totals (same as original function)
    total_equity = 0.0
    total_unrealized_pnl = 0.0

    for position in enriched_positions:
        if isinstance(position, dict):
            equity = position.get("total_equity", "0")
            if equity:
                with contextlib.suppress(ValueError, TypeError):
                    total_equity += float(equity)

            pnl = position.get("unrealized_pnl", "0")
            if pnl:
                with contextlib.suppress(ValueError, TypeError):
                    total_unrealized_pnl += float(pnl)

    # Calculate enrichment success rate
    enrichment_rate = (
        f"{(enrichment_successes / total_positions * 100):.0f}%"
        if total_positions > 0
        else "0%"
    )

    logger.info(
        f"Found {total_positions} open positions with total equity: ${total_equity:.2f} "
        f"(enrichment success: {enrichment_rate})"
    )

    return {
        "result": {
            "positions": enriched_positions,
            "total_open_positions": total_positions,
            "total_equity": f"{total_equity:.2f}",
            "total_unrealized_pnl": f"{total_unrealized_pnl:.2f}",
            "enrichment_success_rate": enrichment_rate,
            "status": "success",
        }
    }
