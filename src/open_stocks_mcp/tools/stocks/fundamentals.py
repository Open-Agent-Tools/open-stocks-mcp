"""Company information and market hours tools."""

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
from open_stocks_mcp.tools.stocks.instruments import _fetch_instruments_batch


@handle_robin_stocks_errors
async def get_stock_info(symbol: str) -> dict[str, Any]:
    """
    Get detailed company information and fundamentals.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        A JSON object containing company information in the result field.
    """
    # Input validation
    if not validate_symbol(symbol):
        return create_error_response(
            ValueError(f"Invalid symbol format: {symbol}"), "symbol validation"
        )

    symbol = symbol.strip().upper()
    log_api_call("get_stock_info", symbol=symbol)

    # Get fundamentals and instrument data with retry logic
    # Use batching for instruments lookup
    cfg = get_config()
    batcher = get_batcher(
        "robinhood_instruments",
        batch_size=cfg.batch.batch_size,
        queue_max_wait=cfg.batch.queue_max_wait,
    )

    fundamentals_task = execute_with_retry(rh.get_fundamentals, symbol)
    instruments_task = batcher.fetch(symbol, _fetch_instruments_batch)

    fundamentals, instrument = await asyncio.gather(fundamentals_task, instruments_task)

    if not fundamentals or not instrument:
        return create_no_data_response(
            f"No company information found for symbol: {symbol}", {"symbol": symbol}
        )

    fundamental = fundamentals[0] if fundamentals else {}

    # Get company name with retry logic
    company_name = await execute_with_retry(rh.get_name_by_symbol, symbol)

    logger.info(f"Successfully retrieved stock info for {symbol}")
    return create_success_response(
        {
            "symbol": symbol,
            "company_name": company_name or instrument.get("simple_name", "N/A"),
            "sector": fundamental.get("sector", "N/A"),
            "industry": fundamental.get("industry", "N/A"),
            "description": fundamental.get("description", "N/A"),
            "market_cap": fundamental.get("market_cap", "N/A"),
            "pe_ratio": fundamental.get("pe_ratio", "N/A"),
            "dividend_yield": fundamental.get("dividend_yield", "N/A"),
            "high_52_weeks": fundamental.get("high_52_weeks", "N/A"),
            "low_52_weeks": fundamental.get("low_52_weeks", "N/A"),
            "average_volume": fundamental.get("average_volume", "N/A"),
            "tradeable": instrument.get("tradeable", False),
        }
    )


@handle_robin_stocks_errors
async def get_market_hours() -> dict[str, Any]:
    """
    Get current market hours and status.

    Returns:
        A JSON object containing market hours information in the result field.
    """
    log_api_call("get_market_hours")

    # Get market information with retry logic
    markets = await execute_with_retry(rh.get_markets)

    if not markets:
        return create_no_data_response("No market data available")

    # Process market data - focus on main markets
    market_data = []
    for market in markets[:5]:  # Limit to top 5 markets
        market_data.append(
            {
                "name": market.get("name", "N/A"),
                "mic": market.get("mic", "N/A"),
                "operating_mic": market.get("operating_mic", "N/A"),
                "timezone": market.get("timezone", "N/A"),
                "website": market.get("website", "N/A"),
            }
        )

    logger.info("Successfully retrieved market hours information")
    return create_success_response({"markets": market_data, "count": len(market_data)})
