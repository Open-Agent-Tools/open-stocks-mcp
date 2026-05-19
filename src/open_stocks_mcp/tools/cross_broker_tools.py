"""Cross-broker portfolio aggregation tools."""

from typing import Any

from open_stocks_mcp.brokers.registry import get_broker_registry
from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.responses import create_success_response
from open_stocks_mcp.tools.robinhood_account_tools import get_portfolio, get_positions
from open_stocks_mcp.tools.schwab_account_tools import get_schwab_accounts


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert value to float, returning default on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


async def _collect_robinhood_data(
    broker_name: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Collect portfolio summary and positions from Robinhood.

    Returns:
        Tuple of (summary dict, positions list)
    """
    summary: dict[str, Any] = {}
    positions: list[dict[str, Any]] = []

    portfolio_result = await get_portfolio()
    portfolio_data = portfolio_result.get("result", {})
    if "error" not in portfolio_data:
        summary["market_value"] = _safe_float(portfolio_data.get("market_value"))
        summary["equity"] = _safe_float(portfolio_data.get("equity"))
        summary["buying_power"] = _safe_float(portfolio_data.get("buying_power"))

    positions_result = await get_positions()
    positions_data = positions_result.get("result", {})
    if "error" not in positions_data:
        for pos in positions_data.get("positions", []):
            positions.append(
                {
                    "symbol": pos.get("symbol"),
                    "quantity": _safe_float(pos.get("quantity")),
                    "average_buy_price": _safe_float(pos.get("average_buy_price")),
                    "market_value": None,
                    "broker": broker_name,
                }
            )

    return summary, positions


async def _collect_schwab_data(
    broker_name: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Collect portfolio summary and positions from Schwab.

    Returns:
        Tuple of (summary dict, positions list)
    """
    summary: dict[str, Any] = {"market_value": 0.0, "equity": 0.0, "buying_power": 0.0}
    positions: list[dict[str, Any]] = []

    accounts_result = await get_schwab_accounts(include_positions=True)
    accounts_data = accounts_result.get("result", {})
    if "error" in accounts_data:
        return summary, positions

    total_market_value = 0.0
    total_buying_power = 0.0

    for account in accounts_data.get("accounts", []):
        sec_account = account.get("securitiesAccount", {})
        balances = sec_account.get("currentBalances", {})
        total_market_value += _safe_float(balances.get("liquidationValue"))
        total_buying_power += _safe_float(balances.get("buyingPower"))

        for pos in sec_account.get("positions", []):
            instrument = pos.get("instrument", {})
            quantity = _safe_float(pos.get("longQuantity")) + _safe_float(
                pos.get("shortQuantity")
            )
            positions.append(
                {
                    "symbol": instrument.get("symbol"),
                    "quantity": quantity,
                    "average_buy_price": _safe_float(pos.get("averagePrice")),
                    "market_value": _safe_float(pos.get("marketValue")),
                    "broker": broker_name,
                }
            )

    summary["market_value"] = total_market_value
    summary["equity"] = total_market_value
    summary["buying_power"] = total_buying_power

    return summary, positions


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
    unavailable: list[str] = []
    all_positions: list[dict[str, Any]] = []
    total_market_value = 0.0
    total_equity = 0.0
    total_buying_power = 0.0

    for name in broker_names:
        broker = registry.get_broker(name)
        if broker is None or not broker.is_available():
            error_msg = None
            if broker is not None:
                error_msg = (
                    broker.auth_info.error_message or broker.auth_info.status.value
                )
            brokers_out[name] = {
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

        try:
            if name == "robinhood":
                summary, positions = await _collect_robinhood_data(name)
            elif name == "schwab":
                summary, positions = await _collect_schwab_data(name)
            else:
                logger.warning(f"No aggregation collector for broker: {name}")
                summary, positions = {}, []

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

        except Exception as exc:
            logger.error(
                f"Error collecting data from broker {name}: {exc}", exc_info=True
            )
            brokers_out[name] = {
                "status": "error",
                "error": str(exc),
                "market_value": 0.0,
                "equity": 0.0,
                "buying_power": 0.0,
                "positions": [],
                "position_count": 0,
            }
            unavailable.append(name)

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
