"""
Options Trading Tools for Robin Stocks MCP Server.

This module provides comprehensive options trading analytics tools including:
- Options chains and contract discovery
- Options market data with Greeks and open interest
- Options positions and portfolio management
- Historical options pricing data

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
async def get_options_chains(symbol: str) -> dict[str, Any]:
    """
    Get complete option chains for a stock symbol.

    This function retrieves all available option contracts for a given stock,
    including all expiration dates, strike prices, and contract types.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "GOOGL")

    Returns:
        Dict containing option chain data:
        {
            "result": {
                "symbol": "AAPL",
                "chains": [
                    {
                        "expiration_date": "2024-01-19",
                        "strike_price": "150.00",
                        "type": "call",
                        "id": "option_id_here",
                        "tradeable": true
                    },
                    ...
                ],
                "total_contracts": 250,
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
        symbol: Stock ticker symbol (e.g., "AAPL", "GOOGL")
        expiration_date: Optional expiration date in YYYY-MM-DD format
        option_type: Optional option type ("call" or "put")

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
                        "strike_price": "150.00",
                        "expiration_date": "2024-01-19",
                        "type": "call",
                        "id": "option_id",
                        "tradeable": true
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

    # Find tradable options
    options_data = await execute_with_retry(
        rh.options.find_tradable_options,
        symbol,
        expiration_date,
        option_type,
        max_retries=3,
    )

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
                "option_id": "option_id_here",
                "symbol": "AAPL",
                "strike_price": "150.00",
                "expiration_date": "2024-01-19",
                "type": "call",
                "greeks": {
                    "delta": 0.65,
                    "gamma": 0.025,
                    "theta": -0.12,
                    "vega": 0.85,
                    "rho": 0.15
                },
                "market_data": {
                    "bid_price": "2.50",
                    "ask_price": "2.55",
                    "last_trade_price": "2.52",
                    "volume": 1250,
                    "open_interest": 5000,
                    "implied_volatility": 0.25
                },
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
                        "begins_at": "2024-01-15T09:30:00Z",
                        "open_price": "2.50",
                        "high_price": "2.65",
                        "low_price": "2.45",
                        "close_price": "2.60",
                        "volume": 150
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
    Get aggregated option positions collapsed by underlying stock.

    This function retrieves all option positions and collapses them by
    underlying stock symbol for a consolidated view.

    Returns:
        Dict containing aggregated option positions:
        {
            "result": {
                "positions": {
                    "AAPL": {
                        "total_contracts": 5,
                        "net_quantity": 3,
                        "average_price": "2.50",
                        "total_equity": "750.00",
                        "positions": [
                            {
                                "strike_price": "150.00",
                                "expiration_date": "2024-01-19",
                                "type": "call",
                                "quantity": "3",
                                "average_price": "2.50"
                            },
                            ...
                        ]
                    },
                    ...
                },
                "total_symbols": 5,
                "total_contracts": 15,
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
    Get all option positions ever held.

    This function retrieves a complete history of all option positions
    that have been held, including both open and closed positions.

    Returns:
        Dict containing all option positions:
        {
            "result": {
                "positions": [
                    {
                        "symbol": "AAPL",
                        "strike_price": "150.00",
                        "expiration_date": "2024-01-19",
                        "type": "call",
                        "quantity": "3",
                        "average_price": "2.50",
                        "current_price": "2.75",
                        "total_equity": "825.00",
                        "status": "held"
                    },
                    ...
                ],
                "total_positions": 25,
                "open_positions": 8,
                "closed_positions": 17,
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
    Get currently open option positions.

    This function retrieves only the option positions that are currently
    open and active.

    Returns:
        Dict containing open option positions:
        {
            "result": {
                "positions": [
                    {
                        "symbol": "AAPL",
                        "strike_price": "150.00",
                        "expiration_date": "2024-01-19",
                        "type": "call",
                        "quantity": "3",
                        "average_price": "2.50",
                        "current_price": "2.75",
                        "total_equity": "825.00",
                        "unrealized_pnl": "75.00",
                        "unrealized_pnl_percent": "10.00%"
                    },
                    ...
                ],
                "total_open_positions": 8,
                "total_equity": "5250.00",
                "total_unrealized_pnl": "325.00",
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
