"""Broker comparison tools for side-by-side metric analysis."""

from typing import Any

from open_stocks_mcp.brokers.registry import get_broker_registry
from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.responses import create_success_response
from open_stocks_mcp.tools.robinhood_account_tools import get_portfolio, get_positions
from open_stocks_mcp.tools.robinhood_order_tools import get_stock_orders
from open_stocks_mcp.tools.schwab_account_tools import (
    get_schwab_account_balances,
    get_schwab_account_numbers,
    get_schwab_portfolio,
)
from open_stocks_mcp.tools.schwab_market_tools import get_schwab_quote
from open_stocks_mcp.tools.schwab_trading_tools import get_schwab_orders
from open_stocks_mcp.tools.stocks.quote import get_stock_price


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert value to float, returning default on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


_ERROR_STATUSES = {"error", "no_data"}


def _has_error(data: dict[str, Any]) -> bool:
    """Return True if the response dict indicates an error or missing data."""
    return "error" in data or data.get("status") in _ERROR_STATUSES


async def _collect_robinhood_comparison(
    symbols: list[str] | None = None,
    include_orders: bool = True,
    max_orders: int = 5,
) -> dict[str, Any]:
    """Collect and normalize Robinhood data for comparison."""
    data: dict[str, Any] = {
        "broker": "robinhood",
        "source": "Robinhood API",
        "available": True,
        "confidence": "high",
        "notes": None,
        "pricing": {},
        "holdings": {},
        "orders": [],
        "summary": {
            "equity": 0.0,
            "buying_power": 0.0,
        },
    }

    # 1. Pricing
    if symbols:
        for symbol in symbols:
            price_result = await get_stock_price(symbol)
            price_data = price_result.get("result", {})
            if not _has_error(price_data):
                data["pricing"][symbol] = {
                    "price": _safe_float(price_data.get("price")),
                    "change": _safe_float(price_data.get("change")),
                    "change_percent": _safe_float(price_data.get("change_percent")),
                }

    # 2. Summary & Holdings
    portfolio_result = await get_portfolio()
    portfolio_data = portfolio_result.get("result", {})
    if _has_error(portfolio_data):
        data["available"] = False
        data["notes"] = portfolio_data.get("message") or portfolio_data.get("error")
    else:
        data["summary"]["equity"] = _safe_float(portfolio_data.get("equity"))
        data["summary"]["buying_power"] = _safe_float(
            portfolio_data.get("buying_power")
        )

    positions_result = await get_positions()
    positions_data = positions_result.get("result", {})
    if not _has_error(positions_data):
        for pos in positions_data.get("positions", []):
            symbol = pos.get("symbol")
            if not symbols or symbol in symbols:
                data["holdings"][symbol] = {
                    "quantity": _safe_float(pos.get("quantity")),
                    "average_buy_price": _safe_float(pos.get("average_buy_price")),
                }

    # 3. Orders
    if include_orders:
        orders_result = await get_stock_orders()
        orders_data = orders_result.get("result", {})
        if not _has_error(orders_data):
            rh_orders = orders_data.get("orders", [])
            for o in rh_orders[:max_orders]:
                symbol = o.get("symbol")
                if not symbols or symbol in symbols:
                    data["orders"].append(
                        {
                            "symbol": symbol,
                            "side": o.get("side"),
                            "quantity": _safe_float(o.get("quantity")),
                            "price": _safe_float(o.get("average_price")),
                            "state": o.get("state"),
                            "created_at": o.get("created_at"),
                        }
                    )

    return data


async def _collect_schwab_comparison(
    symbols: list[str] | None = None,
    include_orders: bool = True,
    max_orders: int = 5,
) -> dict[str, Any]:
    """Collect and normalize Schwab data for comparison."""
    data: dict[str, Any] = {
        "broker": "schwab",
        "source": "Schwab API",
        "available": True,
        "confidence": "high",
        "notes": None,
        "pricing": {},
        "holdings": {},
        "orders": [],
        "summary": {
            "equity": 0.0,
            "buying_power": 0.0,
        },
    }

    # Schwab needs an account hash for many calls
    accounts_result = await get_schwab_account_numbers()
    accounts_data = accounts_result.get("result", {})
    if _has_error(accounts_data) or not accounts_data.get("accounts"):
        data["available"] = False
        data["notes"] = accounts_data.get("error", "No accounts found")
        return data

    account_hash = accounts_data["accounts"][0]["hash_value"]

    # 1. Pricing
    if symbols:
        for symbol in symbols:
            quote_result = await get_schwab_quote(symbol)
            quote_data = quote_result.get("result", {})
            if not _has_error(quote_data):
                data["pricing"][symbol] = {
                    "price": _safe_float(quote_data.get("last_price")),
                    "change": _safe_float(quote_data.get("change")),
                    "change_percent": _safe_float(quote_data.get("change_percent")),
                }

    # 2. Summary & Holdings
    balances_result = await get_schwab_account_balances(account_hash)
    balances_data = balances_result.get("result", {})
    if not _has_error(balances_data):
        curr = balances_data.get("current_balances", {})
        data["summary"]["equity"] = _safe_float(curr.get("market_value"))
        data["summary"]["buying_power"] = _safe_float(curr.get("buying_power"))

    portfolio_result = await get_schwab_portfolio(account_hash)
    portfolio_data = portfolio_result.get("result", {})
    if not _has_error(portfolio_data):
        for pos in portfolio_data.get("positions", []):
            symbol = pos.get("symbol")
            if not symbols or symbol in symbols:
                data["holdings"][symbol] = {
                    "quantity": _safe_float(pos.get("quantity")),
                    "average_buy_price": _safe_float(pos.get("average_price")),
                }

    # 3. Orders
    if include_orders:
        orders_result = await get_schwab_orders(
            account_hash, max_results=max_orders * 2
        )
        orders_data = orders_result.get("result", {})
        if not _has_error(orders_data):
            schwab_orders = orders_data.get("orders", [])
            for o in schwab_orders:
                if len(data["orders"]) >= max_orders:
                    break

                # Schwab order structure is complex, extracting basic fields
                # This depends on how get_schwab_orders formats them
                # Based on schwab_trading_tools.py, it returns raw response.json()

                legs = o.get("orderLegCollection", [])
                if not legs:
                    continue

                leg = legs[0]
                instr = leg.get("instrument", {})
                symbol = instr.get("symbol")

                if not symbol:
                    continue

                if not symbols or symbol in symbols:
                    data["orders"].append(
                        {
                            "symbol": symbol,
                            "side": leg.get("instruction"),
                            "quantity": _safe_float(o.get("quantity")),
                            "price": _safe_float(o.get("price")),
                            "state": o.get("status"),
                            "created_at": o.get("enteredTime"),
                        }
                    )

    return data


async def get_broker_comparison(
    symbols: list[str] | None = None,
    include_orders: bool = True,
    max_orders: int = 5,
) -> dict[str, Any]:
    """Get side-by-side broker comparison for pricing, holdings, and orders.

    Args:
        symbols: Optional list of symbols to filter by.
        include_orders: Whether to include recent orders.
        max_orders: Maximum number of orders to return per broker.

    Returns:
        Dict with comparison result.
    """
    registry = await get_broker_registry()
    broker_names = registry.list_brokers()

    brokers_out: dict[str, Any] = {}
    availability_notes: dict[str, str] = {}
    partial_failure = False

    for name in broker_names:
        broker = registry.get_broker(name)
        if broker is None or not broker.is_available():
            brokers_out[name] = {
                "broker": name,
                "available": False,
                "notes": "Broker not authenticated or unavailable",
            }
            availability_notes[name] = "Not authenticated"
            partial_failure = True
            continue

        try:
            if name == "robinhood":
                broker_data = await _collect_robinhood_comparison(
                    symbols, include_orders, max_orders
                )
            elif name == "schwab":
                broker_data = await _collect_schwab_comparison(
                    symbols, include_orders, max_orders
                )
            else:
                logger.warning(f"No comparison collector for broker: {name}")
                continue

            if not broker_data.get("available", True):
                partial_failure = True
                availability_notes[name] = broker_data.get("notes", "Unknown error")

            brokers_out[name] = broker_data

        except Exception as exc:
            logger.error(
                f"Error collecting comparison data from {name}: {exc}", exc_info=True
            )
            brokers_out[name] = {
                "broker": name,
                "available": False,
                "notes": str(exc),
            }
            availability_notes[name] = str(exc)
            partial_failure = True

    # Build comparison summary
    comparison: dict[str, Any] = {
        "symbols": symbols if symbols else [],
        "metrics": ["pricing", "holdings", "orders"],
    }

    status = "success"
    if partial_failure:
        status = "partial"
    if not any(b.get("available") for b in brokers_out.values()):
        status = "error"

    return create_success_response(
        {
            "brokers": brokers_out,
            "comparison": comparison,
            "availability_notes": availability_notes,
            "status": status,
        }
    )
