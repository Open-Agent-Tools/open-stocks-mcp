"""Tools for Schwab real-time streaming data."""

from typing import Any

from open_stocks_mcp.tools.broker_utils import (
    get_authenticated_broker_or_error,
)
from open_stocks_mcp.tools.error_handling import (
    create_success_response,
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
