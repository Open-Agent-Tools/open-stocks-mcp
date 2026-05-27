"""Market mover, popularity, and tag tools for Robin Stocks integration."""

from typing import Any

import robin_stocks.robinhood as rh

from open_stocks_mcp.brokers.session_state import get_session_manager
from open_stocks_mcp.tools.error_handling import (
    create_error_response,
    create_no_data_response,
    create_success_response,
    execute_with_retry,
    handle_robin_stocks_errors,
    log_api_call,
)


@handle_robin_stocks_errors
async def get_top_movers_sp500(direction: str = "up") -> dict[str, Any]:
    """Get top S&P 500 movers for the day.

    Args:
        direction: Direction of movement, either 'up' or 'down' (default: 'up')

    Returns:
        JSON object with S&P 500 movers in "result" field:
        {
            "result": {
                "direction": "up",
                "movers": [
                    {
                        "symbol": "AAPL",
                        "instrument_url": "https://...",
                        "updated_at": "2024-07-09T16:00:00Z",
                        "price_movement": {
                            "market_hours_last_movement_pct": "2.5",
                            "market_hours_last_price": "150.00"
                        },
                        "description": "Apple Inc."
                    }
                ],
                "count": 25
            }
        }
    """
    # Validate direction parameter
    direction = direction.lower().strip()
    if direction not in ["up", "down"]:
        return create_error_response(
            ValueError("Direction must be 'up' or 'down'"), "parameter validation"
        )

    # Ensure authenticated
    session_mgr = get_session_manager()
    if not await session_mgr.ensure_authenticated():
        return create_error_response(
            ValueError("Authentication required"), "authentication"
        )

    log_api_call("get_top_movers_sp500", direction=direction)

    # Get S&P 500 movers with retry logic
    movers_data = await execute_with_retry(rh.get_top_movers_sp500, direction)

    if not movers_data:
        return create_no_data_response(
            f"No S&P 500 {direction} movers found", {"direction": direction}
        )

    # Filter out None values and ensure we have valid data
    movers = [mover for mover in movers_data if mover is not None]

    return create_success_response(
        {"direction": direction, "movers": movers, "count": len(movers)}
    )


@handle_robin_stocks_errors
async def get_top_100() -> dict[str, Any]:
    """Get top 100 most popular stocks on Robinhood with full quote data.

    Returns detailed market data for the 100 most popular stocks including
    bid/ask prices, sizes, timestamps, and trading status.

    Returns:
        JSON object with top 100 stocks in "result" field:
        {
            "result": {
                "stocks": [
                    {
                        "ask_price": "345.330000",
                        "ask_size": 103,
                        "venue_ask_time": "2025-08-11T16:14:47.706648946Z",
                        "bid_price": "345.310000",
                        "bid_size": 169,
                        "venue_bid_time": "2025-08-11T16:14:47.706648946Z",
                        "last_trade_price": "345.325000",
                        "venue_last_trade_time": "2025-08-11T16:14:48.232372322Z",
                        "last_extended_hours_trade_price": null,
                        "last_non_reg_trade_price": null,
                        "venue_last_non_reg_trade_time": null,
                        "previous_close": "329.650000",
                        "adjusted_previous_close": "329.650000",
                        "previous_close_date": "2025-08-08",
                        "symbol": "TSLA",
                        "trading_halted": false,
                        "has_traded": true,
                        "last_trade_price_source": "nls",
                        "last_non_reg_trade_price_source": "",
                        "updated_at": "2025-08-11T16:14:48Z",
                        "instrument": "https://api.robinhood.com/instruments/e39ed23a-7bd1-4587-b060-71988d9ef483/",
                        "instrument_id": "e39ed23a-7bd1-4587-b060-71988d9ef483",
                        "state": "active"
                    },
                    ...
                ],
                "count": 100
            }
        }
    """
    # Ensure authenticated
    session_mgr = get_session_manager()
    if not await session_mgr.ensure_authenticated():
        return create_error_response(
            ValueError("Authentication required"), "authentication"
        )

    log_api_call("get_top_100")

    # Get top 100 stocks with retry logic
    stocks_data = await execute_with_retry(rh.get_top_100)

    if not stocks_data:
        return create_no_data_response("No top 100 stocks data found", {})

    # Filter out None values and ensure we have valid data
    stocks = [stock for stock in stocks_data if stock is not None]

    return create_success_response({"stocks": stocks, "count": len(stocks)})


@handle_robin_stocks_errors
async def get_top_movers() -> dict[str, Any]:
    """Get top 20 movers on Robinhood with full quote data.

    Returns detailed market data for the top 20 moving stocks including
    bid/ask prices, sizes, timestamps, and trading status.

    Returns:
        JSON object with top movers in "result" field:
        {
            "result": {
                "movers": [
                    {
                        "ask_price": "14.950000",
                        "ask_size": 776,
                        "venue_ask_time": "2025-08-11T16:09:42.253516091Z",
                        "bid_price": "14.940000",
                        "bid_size": 1968,
                        "venue_bid_time": "2025-08-11T16:09:42.253516091Z",
                        "last_trade_price": "14.941200",
                        "venue_last_trade_time": "2025-08-11T16:09:51.820785219Z",
                        "last_extended_hours_trade_price": null,
                        "last_non_reg_trade_price": null,
                        "venue_last_non_reg_trade_time": null,
                        "previous_close": "9.280000",
                        "adjusted_previous_close": "9.280000",
                        "previous_close_date": "2025-08-08",
                        "symbol": "IMXI",
                        "trading_halted": false,
                        "has_traded": true,
                        "last_trade_price_source": "nls",
                        "last_non_reg_trade_price_source": "",
                        "updated_at": "2025-08-11T16:09:51Z",
                        "instrument": "https://api.robinhood.com/instruments/25b0a9ce-e04e-4bf3-9ebf-918839ff28bc/",
                        "instrument_id": "25b0a9ce-e04e-4bf3-9ebf-918839ff28bc",
                        "state": "active"
                    },
                    ...
                ],
                "count": 20
            }
        }
    """
    # Ensure authenticated
    session_mgr = get_session_manager()
    if not await session_mgr.ensure_authenticated():
        return create_error_response(
            ValueError("Authentication required"), "authentication"
        )

    log_api_call("get_top_movers")

    # Get top movers with retry logic
    movers_data = await execute_with_retry(rh.get_top_movers)

    if not movers_data:
        return create_no_data_response("No top movers data found", {})

    # Filter out None values and ensure we have valid data
    movers = [mover for mover in movers_data if mover is not None]

    return create_success_response({"movers": movers, "count": len(movers)})


@handle_robin_stocks_errors
async def get_stocks_by_tag(tag: str) -> dict[str, Any]:
    """Get stocks filtered by market category tag.

    Args:
        tag: Market category tag (e.g., 'technology', 'biopharmaceutical', 'upcoming-earnings')

    Returns:
        JSON object with tagged stocks in "result" field:
        {
            "result": {
                "tag": "technology",
                "stocks": [
                    {
                        "symbol": "AAPL",
                        "last_trade_price": "150.00",
                        "previous_close": "149.50",
                        "ask_price": "150.10",
                        "bid_price": "149.90",
                        "updated_at": "2024-07-09T16:00:00Z"
                    }
                ],
                "count": 50
            }
        }
    """
    # Validate tag parameter
    if not tag or not isinstance(tag, str):
        return create_error_response(
            ValueError("Tag parameter is required and must be a string"),
            "parameter validation",
        )

    tag = tag.strip().lower()

    # Ensure authenticated
    session_mgr = get_session_manager()
    if not await session_mgr.ensure_authenticated():
        return create_error_response(
            ValueError("Authentication required"), "authentication"
        )

    log_api_call("get_stocks_by_tag", tag=tag)

    # Get stocks by tag with retry logic
    stocks_data = await execute_with_retry(rh.get_all_stocks_from_market_tag, tag)

    if not stocks_data or stocks_data == [None]:
        return create_no_data_response(f"No stocks found for tag: {tag}", {"tag": tag})

    # Filter out None values and ensure we have valid data
    stocks = [stock for stock in stocks_data if stock is not None]

    return create_success_response({"tag": tag, "stocks": stocks, "count": len(stocks)})
