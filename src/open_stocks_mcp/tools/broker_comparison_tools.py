"""Broker comparison tools for side-by-side metric analysis."""

from typing import Any

from open_stocks_mcp.brokers.registry import get_broker_registry
from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.responses import create_success_response
from open_stocks_mcp.tools.robinhood_account_tools import get_portfolio, get_positions
from open_stocks_mcp.tools.robinhood_order_tools import get_stock_orders
from open_stocks_mcp.tools.robinhood_stock_tools import get_stock_price
from open_stocks_mcp.tools.schwab_account_tools import (
    get_schwab_account_balances,
    get_schwab_account_numbers,
    get_schwab_portfolio,
)
from open_stocks_mcp.tools.schwab_market_tools import get_schwab_quote
from open_stocks_mcp.tools.schwab_trading_tools import get_schwab_orders


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert value to float, returning default on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


async def _collect_robinhood_comparison(
    symbols: list[str] | None, include_orders: bool, max_orders: int
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
        "account": {"equity": 0.0, "buying_power": 0.0},
    }

    # 1. Pricing
    if symbols:
        for symbol in symbols:
            price_resp = await get_stock_price(symbol)
            price_data = price_resp.get("result", {})
            if "error" not in price_data:
                data["pricing"][symbol] = {
                    "price": _safe_float(price_data.get("price")),
                    "change": _safe_float(price_data.get("change")),
                    "change_percent": _safe_float(price_data.get("change_percent")),
                }

    # 2. Holdings
    positions_resp = await get_positions()
    positions_data = positions_resp.get("result", {})
    if "error" not in positions_data:
        for pos in positions_data.get("positions", []):
            symbol = pos.get("symbol")
            if not symbols or symbol in symbols:
                data["holdings"][symbol] = {
                    "quantity": _safe_float(pos.get("quantity")),
                    "average_buy_price": _safe_float(pos.get("average_buy_price")),
                    "equity": _safe_float(pos.get("equity")),
                }

    # 3. Account
    portfolio_resp = await get_portfolio()
    portfolio_data = portfolio_resp.get("result", {})
    if "error" not in portfolio_data:
        data["account"]["equity"] = _safe_float(portfolio_data.get("equity"))
        data["account"]["buying_power"] = _safe_float(portfolio_data.get("buying_power"))

    # 4. Orders
    if include_orders:
        orders_resp = await get_stock_orders()
        orders_data = orders_resp.get("result", [])
        if isinstance(orders_data, list):
            for order in orders_data[:max_orders]:
                data["orders"].append({
                    "symbol": order.get("symbol"),
                    "side": order.get("side"),
                    "state": order.get("state"),
                    "quantity": _safe_float(order.get("quantity")),
                    "price": _safe_float(order.get("price")),
                    "timestamp": order.get("updated_at") or order.get("created_at"),
                })

    return data


async def _collect_schwab_comparison(
    symbols: list[str] | None, include_orders: bool, max_orders: int
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
        "account": {"equity": 0.0, "buying_power": 0.0},
    }

    # 0. Get account hash
    acct_resp = await get_schwab_account_numbers()
    acct_data = acct_resp.get("result", [])
    if not acct_data or "error" in (acct_data[0] if isinstance(acct_data, list) else acct_data):
        data["available"] = False
        data["notes"] = "Failed to retrieve Schwab account numbers"
        return data

    account_hash = acct_data[0].get("hash")

    # 1. Pricing
    if symbols:
        for symbol in symbols:
            quote_resp = await get_schwab_quote(symbol)
            quote_data = quote_resp.get("result", {})
            if "error" not in quote_data:
                data["pricing"][symbol] = {
                    "price": _safe_float(quote_data.get("last_price")),
                    "change": _safe_float(quote_data.get("net_change")),
                    "change_percent": _safe_float(quote_data.get("net_change_percent")),
                }

    # 2. Holdings
    portfolio_resp = await get_schwab_portfolio(account_hash)
    portfolio_data = portfolio_resp.get("result", {})
    if "error" not in portfolio_data:
        sec_account = portfolio_data.get("securitiesAccount", {})
        for pos in sec_account.get("positions", []):
            symbol = pos.get("instrument", {}).get("symbol")
            if not symbols or symbol in symbols:
                quantity = _safe_float(pos.get("longQuantity")) + _safe_float(pos.get("shortQuantity"))
                data["holdings"][symbol] = {
                    "quantity": quantity,
                    "average_buy_price": _safe_float(pos.get("averagePrice")),
                    "equity": _safe_float(pos.get("marketValue")),
                }

    # 3. Account
    balances_resp = await get_schwab_account_balances(account_hash)
    balances_data = balances_resp.get("result", {})
    if "error" not in balances_data:
        curr_balances = balances_data.get("currentBalances", {})
        data["account"]["equity"] = _safe_float(curr_balances.get("liquidationValue"))
        data["account"]["buying_power"] = _safe_float(curr_balances.get("buyingPower"))

    # 4. Orders
    if include_orders:
        orders_resp = await get_schwab_orders(account_hash, max_results=max_orders)
        orders_data = orders_resp.get("result", {}).get("orders", [])
        if isinstance(orders_data, list):
            for order in orders_data:
                # Schwab orders usually have a list of orderLegCollection
                leg = order.get("orderLegCollection", [{}])[0]
                data["orders"].append({
                    "symbol": leg.get("instrument", {}).get("symbol"),
                    "side": leg.get("instruction", "").lower(),
                    "state": order.get("status", "").lower(),
                    "quantity": _safe_float(order.get("quantity")),
                    "price": _safe_float(order.get("price")),
                    "timestamp": order.get("enteredTime"),
                })

    return data


async def get_broker_comparison(
    symbols: list[str] | None = None, include_orders: bool = True, max_orders: int = 5
) -> dict[str, Any]:
    """
    Returns broker-normalized pricing, holdings, and recent order context.

    Returns:
        Dict with result containing:
        - brokers: per-broker normalized data
        - comparison: symbol-indexed comparison of metrics
        - availability_notes: list of issues encountered
        - status: success, partial, or error
    """
    registry = await get_broker_registry()
    broker_names = registry.list_brokers()

    brokers_out: dict[str, Any] = {}
    availability_notes: dict[str, str] = {}
    
    # Track symbols for side-by-side comparison
    all_symbols = set(symbols) if symbols else set()

    for name in broker_names:
        broker = registry.get_broker(name)
        if broker is None or not broker.is_available():
            brokers_out[name] = {
                "broker": name,
                "available": False,
                "notes": "Broker not authenticated or unavailable",
            }
            availability_notes[name] = "Not authenticated"
            continue

        try:
            if name == "robinhood":
                data = await _collect_robinhood_comparison(symbols, include_orders, max_orders)
            elif name == "schwab":
                data = await _collect_schwab_comparison(symbols, include_orders, max_orders)
            else:
                continue

            brokers_out[name] = data
            if not data.get("available", True):
                availability_notes[name] = data.get("notes", "Unknown error")
            
            # Add any discovered symbols from holdings if symbols was None
            if symbols is None:
                all_symbols.update(data["holdings"].keys())

        except Exception as exc:
            logger.error(f"Error collecting comparison data for {name}: {exc}", exc_info=True)
            brokers_out[name] = {
                "broker": name,
                "available": False,
                "notes": str(exc),
            }
            availability_notes[name] = str(exc)

    # Generate side-by-side comparison
    comparison: dict[str, Any] = {}
    for symbol in sorted(all_symbols):
        symbol_comp: dict[str, Any] = {}
        for name, data in brokers_out.items():
            if not data.get("available"):
                continue
            
            symbol_comp[name] = {
                "price": data["pricing"].get(symbol, {}).get("price"),
                "quantity": data["holdings"].get(symbol, {}).get("quantity", 0.0),
                "equity": data["holdings"].get(symbol, {}).get("equity", 0.0),
            }
        comparison[symbol] = symbol_comp

    status = "success"
    if availability_notes:
        status = "partial" if any(b.get("available") for b in brokers_out.values()) else "error"

    return create_success_response({
        "brokers": brokers_out,
        "comparison": comparison,
        "availability_notes": availability_notes,
        "status": status,
    })
