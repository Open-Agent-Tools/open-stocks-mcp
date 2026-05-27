"""Cross-broker portfolio aggregation tools."""

import asyncio
from typing import Any

from open_stocks_mcp.brokers.registry import get_broker_registry
from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.responses import create_success_response


async def get_aggregated_portfolio() -> dict[str, Any]:
    """Aggregate portfolio data across all registered brokers.

    Returns a normalized portfolio view combining positions and summary values
    from all available brokers. Brokers that are not authenticated contribute
    a degraded (status=unavailable) entry rather than failing the whole call.

    Returns:
        Dict with result containing:
        - aggregated: combined totals and merged positions list
        - brokers: per-broker rollup with status, summary, and positions
        - partial_failure: True if any broker was unavailable
        - unavailable_brokers: list of broker names that could not contribute
    """
    registry = await get_broker_registry()
    broker_names = registry.list_brokers()

    brokers_out: dict[str, Any] = {}
    unavailable_records: dict[str, dict[str, Any]] = {}
    unavailable: list[str] = []
    all_positions: list[dict[str, Any]] = []
    total_market_value = 0.0
    total_equity = 0.0
    total_buying_power = 0.0
    available_names: list[str] = []
    coros = []

    for name in broker_names:
        broker = registry.get_broker(name)
        if broker is None or not broker.is_available():
            error_msg = None
            if broker is not None:
                error_msg = (
                    broker.auth_info.error_message or broker.auth_info.status.value
                )
            unavailable_records[name] = {
                "status": "unavailable",
                "error": error_msg,
                "market_value": 0.0,
                "equity": 0.0,
                "buying_power": 0.0,
                "positions": [],
                "position_count": 0,
            }
            unavailable.append(name)
            logger.warning(f"Broker {name} unavailable for aggregation: {error_msg}")
            continue

        available_names.append(name)
        coros.append(broker.get_portfolio_snapshot())

    if coros:
        results = await asyncio.gather(*coros, return_exceptions=True)
        for name, result in zip(available_names, results, strict=True):
            if isinstance(result, BaseException):
                logger.error(
                    f"Error collecting data from broker {name}: {result}",
                    exc_info=result,
                )
                brokers_out[name] = {
                    "status": "error",
                    "error": str(result),
                    "market_value": 0.0,
                    "equity": 0.0,
                    "buying_power": 0.0,
                    "positions": [],
                    "position_count": 0,
                }
                unavailable.append(name)
                continue

            summary, positions = result
            market_value = summary.get("market_value", 0.0)
            equity = summary.get("equity", 0.0)
            buying_power = summary.get("buying_power", 0.0)

            brokers_out[name] = {
                "status": "available",
                "error": None,
                "market_value": market_value,
                "equity": equity,
                "buying_power": buying_power,
                "positions": positions,
                "position_count": len(positions),
            }
            all_positions.extend(positions)
            total_market_value += market_value
            total_equity += equity
            total_buying_power += buying_power

    for name in broker_names:
        if name in brokers_out:
            continue
        if name in unavailable_records:
            brokers_out[name] = unavailable_records[name]

    return create_success_response(
        {
            "aggregated": {
                "total_market_value": total_market_value,
                "total_equity": total_equity,
                "total_buying_power": total_buying_power,
                "positions": all_positions,
                "position_count": len(all_positions),
            },
            "brokers": brokers_out,
            "partial_failure": len(unavailable) > 0,
            "unavailable_brokers": unavailable,
            "registered_brokers": broker_names,
        }
    )
