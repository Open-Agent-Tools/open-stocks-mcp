"""Tools for Schwab real-time streaming data."""

from typing import Any

from open_stocks_mcp.tools.broker_utils import (
    get_authenticated_broker_or_error,
)
from open_stocks_mcp.tools.error_handling import (
    create_success_response,
)


async def schwab_stream_level2(symbol: str, venue: str = "nasdaq") -> dict[str, Any]:
    """Get real-time Level 2 order-book snapshot from Schwab streaming.

    Args:
        symbol: Ticker symbol (e.g. 'AAPL')
        venue: 'nasdaq' or 'nyse' (default: 'nasdaq')
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"stream Level 2 book for {symbol}"
    )
    if error:
        return error

    # Check streaming capability
    health = broker.get_health_status()
    if not health.get("capabilities", {}).get("streaming_quotes"):
        return create_success_response(
            {
                "status": "stream_unavailable",
                "symbol": symbol,
                "reason": "streaming capability disabled",
            }
        )

    # Check stream manager readiness
    manager = getattr(broker, "stream_manager", None)
    if manager is None:
        return create_success_response(
            {
                "status": "stream_unavailable",
                "symbol": symbol,
                "reason": "stream manager unavailable",
            }
        )

    if not manager.is_running:
        return create_success_response(
            {
                "status": "stream_unavailable",
                "symbol": symbol,
                "reason": "stream manager stopped",
            }
        )

    # Subscribe to Level 2
    sub_success = await manager.subscribe_level2(symbol, venue)
    if not sub_success:
        return create_success_response(
            {
                "status": "stream_unavailable",
                "symbol": symbol,
                "reason": "Level 2 subscription failed",
            }
        )

    # Retrieve cached snapshot
    snapshot = manager.get_latest_level2(symbol)
    if not snapshot:
        return create_success_response(
            {
                "status": "stream_unavailable",
                "symbol": symbol,
                "reason": "no cached Level 2 snapshot",
            }
        )

    return create_success_response(
        {
            "status": "success",
            "symbol": symbol.upper(),
            "venue": venue.lower(),
            "snapshot": snapshot,
        }
    )


async def schwab_stream_option_quotes(symbols: list[str]) -> dict[str, Any]:
    """Get real-time option quote snapshots from Schwab streaming.

    Args:
        symbols: List of Schwab option symbols (e.g. ['AAPL  260619C00150000'])
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", "stream option quotes"
    )
    if error:
        return error

    # Check streaming capability
    health = broker.get_health_status()
    if not health.get("capabilities", {}).get("streaming_quotes"):
        return create_success_response(
            {
                "status": "stream_unavailable",
                "symbols": symbols,
                "reason": "streaming capability disabled",
            }
        )

    # Check stream manager readiness
    manager = getattr(broker, "stream_manager", None)
    if manager is None:
        return create_success_response(
            {
                "status": "stream_unavailable",
                "symbols": symbols,
                "reason": "stream manager unavailable",
            }
        )

    if not manager.is_running:
        return create_success_response(
            {
                "status": "stream_unavailable",
                "symbols": symbols,
                "reason": "stream manager stopped",
            }
        )

    # Subscribe to option symbols
    sub_success = await manager.subscribe_option_quotes(symbols)
    if not sub_success:
        return create_success_response(
            {
                "status": "stream_unavailable",
                "symbols": symbols,
                "reason": "option quote subscription failed",
            }
        )

    # Retrieve cached snapshots
    quotes = {}
    for symbol in symbols:
        quote = manager.get_latest_option_quote(symbol)
        if quote:
            quotes[symbol] = quote

    if not quotes:
        return create_success_response(
            {
                "status": "stream_unavailable",
                "symbols": symbols,
                "reason": "no cached option quote snapshot",
            }
        )

    return create_success_response(
        {
            "status": "success",
            "quotes": quotes,
            "count": len(quotes),
        }
    )


async def schwab_stream_level2(symbol: str, venue: str = "nasdaq") -> dict[str, Any]:
    """Get a Level 2 snapshot from Schwab streaming cache for a symbol.

    Note: this endpoint follows a subscribe-then-read pattern; the first call may
    return `stream_unavailable` until an async book update arrives and is cached.
    """
    symbol_upper = symbol.upper()
    venue_lower = venue.lower()

    if venue_lower not in {"nasdaq", "nyse"}:
        return create_success_response(
            {
                "status": "stream_unavailable",
                "symbol": symbol_upper,
                "venue": venue_lower,
                "reason": "unsupported venue",
            }
        )

    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"stream level2 for {symbol_upper}"
    )
    if error:
        return error

    health = broker.get_health_status()
    if not health.get("capabilities", {}).get("streaming_quotes"):
        return create_success_response(
            {
                "status": "stream_unavailable",
                "symbol": symbol_upper,
                "venue": venue_lower,
                "reason": "streaming capability disabled",
            }
        )

    manager = getattr(broker, "stream_manager", None)
    if manager is None:
        return create_success_response(
            {
                "status": "stream_unavailable",
                "symbol": symbol_upper,
                "venue": venue_lower,
                "reason": "stream manager unavailable",
            }
        )

    if not manager.is_running:
        return create_success_response(
            {
                "status": "stream_unavailable",
                "symbol": symbol_upper,
                "venue": venue_lower,
                "reason": "stream manager stopped",
            }
        )

    subscribed = await manager.subscribe_level2(symbol_upper, venue_lower)
    if not subscribed:
        return create_success_response(
            {
                "status": "stream_unavailable",
                "symbol": symbol_upper,
                "venue": venue_lower,
                "reason": "subscription failed",
            }
        )

    snapshot = manager.get_latest_level2(symbol_upper, venue_lower)
    if snapshot is None:
        return create_success_response(
            {
                "status": "stream_unavailable",
                "symbol": symbol_upper,
                "venue": venue_lower,
                "reason": "no snapshot available",
            }
        )

    return create_success_response(
        {
            "status": "success",
            "symbol": symbol_upper,
            "venue": venue_lower,
            "snapshot": snapshot,
        }
    )


async def schwab_stream_account_activity() -> dict[str, Any]:
    """Get latest account activity events from Schwab streaming."""
    broker, error = await get_authenticated_broker_or_error(
        "schwab", "stream account activity"
    )
    if error:
        return error

    # Check streaming capability
    health = broker.get_health_status()
    if not health.get("capabilities", {}).get("streaming_quotes"):
        return create_success_response(
            {
                "status": "stream_unavailable",
                "reason": "streaming capability disabled",
            }
        )

    # Check stream manager readiness
    manager = getattr(broker, "stream_manager", None)
    if manager is None:
        return create_success_response(
            {
                "status": "stream_unavailable",
                "reason": "stream manager unavailable",
            }
        )

    if not manager.is_running:
        return create_success_response(
            {
                "status": "stream_unavailable",
                "reason": "stream manager stopped",
            }
        )

    # Subscribe to account activity
    sub_success = await manager.subscribe_account_activity()
    if not sub_success:
        return create_success_response(
            {
                "status": "stream_unavailable",
                "reason": "account activity subscription failed",
            }
        )

    events = manager.get_latest_activity()
    return create_success_response(
        {
            "status": "success",
            "events": events,
            "count": len(events),
        }
    )
