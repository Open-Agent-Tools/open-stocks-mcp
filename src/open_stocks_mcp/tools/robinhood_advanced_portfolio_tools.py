"""
Advanced Portfolio Analytics Tools for Robin Stocks MCP Server.

This module provides comprehensive portfolio analytics tools including:
- Enhanced holdings with dividend information
- Complete user profile with totals
- Day trading pattern tracking

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
async def get_build_holdings() -> dict[str, Any]:
    """
    Build comprehensive holdings with dividend information.

    This function uses Robin Stocks' build_holdings() to create a comprehensive
    view of portfolio holdings including dividend information, cost basis,
    and performance metrics.

    Returns:
        Dict containing comprehensive holdings data with dividend info:
        {
            "result": {
                "AAPL": {
                    "price": "150.00",
                    "quantity": "10",
                    "average_buy_price": "145.00",
                    "equity": "1500.00",
                    "percent_change": "3.45",
                    "equity_change": "50.00",
                    "type": "stock",
                    "name": "Apple Inc",
                    "id": "450dfc6d-5510-4d40-abfb-f633b7d9be3e",
                    "pe_ratio": "25.5",
                    "percentage": "15.2"
                },
                "status": "success"
            }
        }
    """
    logger.info("Building comprehensive holdings with dividend information")

    # Execute the build_holdings function with retry logic
    holdings = await execute_with_retry(rh.build_holdings, max_retries=3)

    if not holdings:
        logger.warning("No holdings data returned from build_holdings")
        return {
            "result": {
                "holdings": {},
                "total_positions": 0,
                "message": "No holdings found",
                "status": "no_data",
            }
        }

    logger.info(f"Successfully built holdings for {len(holdings)} positions")

    return {
        "result": {
            "holdings": holdings,
            "total_positions": len(holdings),
            "status": "success",
        }
    }


@handle_robin_stocks_errors
async def get_build_user_profile() -> dict[str, Any]:
    """
    Build comprehensive user profile with equity, cash, and dividend totals.

    This function uses Robin Stocks' build_user_profile() to create a complete
    financial profile including total equity, cash balances, and dividend totals.

    Returns:
        Dict containing comprehensive user profile data:
        {
            "result": {
                "equity": "50000.00",
                "extended_hours_equity": "50100.00",
                "cash": "2500.00",
                "dividend_total": "1245.67",
                "total_return_today": "250.00",
                "total_return_today_percent": "0.50",
                "status": "success"
            }
        }
    """
    logger.info("Building comprehensive user profile with totals")

    # Execute the build_user_profile function with retry logic
    profile = await execute_with_retry(rh.build_user_profile, max_retries=3)

    if not profile:
        logger.warning("No user profile data returned from build_user_profile")
        return {
            "result": {"error": "No user profile data available", "status": "no_data"}
        }

    logger.info("Successfully built user profile with financial totals")

    return {"result": {**profile, "status": "success"}}


@handle_robin_stocks_errors
async def get_day_trades() -> dict[str, Any]:
    """
    Get pattern day trading information and tracking.

    This function retrieves information about day trading patterns,
    including day trade count, remaining day trades, and PDT status.

    Returns:
        Dict containing day trading information:
        {
            "result": {
                "day_trade_count": 2,
                "remaining_day_trades": 1,
                "pattern_day_trader": false,
                "day_trade_buying_power": "25000.00",
                "overnight_buying_power": "12500.00",
                "status": "success"
            }
        }
    """
    logger.info("Getting day trading pattern information")

    try:
        # Get account information which contains day trading data
        account_info = await execute_with_retry(rh.load_account_profile, max_retries=3)

        if not account_info:
            logger.warning("No account profile data available for day trading info")
            return {
                "result": {
                    "error": "No account profile data available",
                    "status": "no_data",
                }
            }

        # Extract day trading specific information
        day_trade_info = {
            "day_trade_count": int(account_info.get("day_trade_count", 0)),
            "remaining_day_trades": max(
                0, 3 - int(account_info.get("day_trade_count", 0))
            ),
            "pattern_day_trader": account_info.get("is_pattern_day_trader", False),
            "day_trade_buying_power": account_info.get(
                "day_trade_buying_power", "0.00"
            ),
            "overnight_buying_power": account_info.get(
                "overnight_buying_power", "0.00"
            ),
            "max_ach_early_access_amount": account_info.get(
                "max_ach_early_access_amount", "0.00"
            ),
        }

        logger.info(
            f"Day trading info: {day_trade_info['day_trade_count']} trades, "
            f"PDT: {day_trade_info['pattern_day_trader']}"
        )

        return {"result": {**day_trade_info, "status": "success"}}

    except Exception as e:
        logger.error(f"Error getting day trading information: {e}")
        return {
            "result": {
                "error": f"Failed to get day trading information: {e!s}",
                "status": "error",
            }
        }
