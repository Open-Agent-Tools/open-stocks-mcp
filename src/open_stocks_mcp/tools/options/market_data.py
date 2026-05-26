"""Robinhood options market data tools."""

from typing import Any

import robin_stocks.robinhood as rh

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.error_handling import (
    execute_with_retry,
    handle_robin_stocks_errors,
)


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
