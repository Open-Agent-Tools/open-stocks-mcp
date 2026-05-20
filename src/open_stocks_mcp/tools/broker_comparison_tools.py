"""Cross-broker comparison tools for side-by-side broker insights."""

from typing import Any

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
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _has_error(payload: dict[str, Any]) -> bool:
    status = str(payload.get("status", "")).lower()
    return "error" in payload or status in {
        "error",
        "broker_unavailable",
        "authentication_required",
        "unauthorized",
    }


async def _build_robinhood(symbols: list[str], include_orders: bool, max_orders: int) -> dict[str, Any]:
    portfolio = (await get_portfolio()).get("result", {})
    positions = (await get_positions()).get("result", {})

    if _has_error(portfolio) or _has_error(positions):
        return {
            "broker": "robinhood",
            "source": "robinhood",
            "available": False,
            "confidence": "low",
            "notes": [portfolio.get("error") or positions.get("error") or "Unavailable"],
            "pricing": {},
            "holdings": [],
            "orders": [],
        }

    pricing: dict[str, Any] = {}
    for symbol in symbols:
        quote_result = (await get_stock_price(symbol)).get("result", {})
        if _has_error(quote_result):
            continue
        pricing[symbol] = {
            "symbol": symbol,
            "price": _safe_float(quote_result.get("price")),
            "change": _safe_float(quote_result.get("change")),
            "change_percent": _safe_float(quote_result.get("change_percent")),
        }

    holdings = []
    for position in positions.get("positions", []):
        holdings.append(
            {
                "symbol": position.get("symbol"),
                "quantity": _safe_float(position.get("quantity")),
                "average_price": _safe_float(position.get("average_buy_price")),
                "market_value": _safe_float(position.get("market_value")),
            }
        )

    orders: list[dict[str, Any]] = []
    if include_orders:
        order_result = (await get_stock_orders()).get("result", {})
        for order in order_result.get("orders", [])[:max_orders]:
            orders.append(
                {
                    "symbol": order.get("symbol"),
                    "side": order.get("side"),
                    "state": order.get("state"),
                    "quantity": _safe_float(order.get("quantity")),
                    "price": _safe_float(order.get("average_price")),
                }
            )

    return {
        "broker": "robinhood",
        "source": "robinhood",
        "available": True,
        "confidence": "high",
        "notes": [],
        "pricing": pricing,
        "holdings": holdings,
        "orders": orders,
        "summary": {
            "equity": _safe_float(portfolio.get("equity")),
            "buying_power": _safe_float(portfolio.get("buying_power")),
            "market_value": _safe_float(portfolio.get("market_value")),
        },
    }


async def _build_schwab(symbols: list[str], include_orders: bool, max_orders: int) -> dict[str, Any]:
    numbers = (await get_schwab_account_numbers()).get("result", {})
    if _has_error(numbers) or not numbers.get("accounts"):
        return {
            "broker": "schwab",
            "source": "schwab",
            "available": False,
            "confidence": "low",
            "notes": [numbers.get("error") or "Schwab unavailable"],
            "pricing": {},
            "holdings": [],
            "orders": [],
        }

    account_hash = numbers["accounts"][0].get("hash_value")
    balances = (await get_schwab_account_balances(account_hash)).get("result", {})
    portfolio = (await get_schwab_portfolio(account_hash)).get("result", {})

    pricing: dict[str, Any] = {}
    for symbol in symbols:
        quote_result = (await get_schwab_quote(symbol)).get("result", {})
        if _has_error(quote_result):
            continue
        pricing[symbol] = {
            "symbol": symbol,
            "price": _safe_float(quote_result.get("last_price")),
            "change": _safe_float(quote_result.get("change")),
            "change_percent": _safe_float(quote_result.get("change_percent")),
        }

    holdings = []
    for position in portfolio.get("positions", []):
        holdings.append(
            {
                "symbol": position.get("symbol"),
                "quantity": _safe_float(position.get("quantity")),
                "average_price": _safe_float(position.get("average_price")),
                "market_value": _safe_float(position.get("market_value")),
            }
        )

    orders: list[dict[str, Any]] = []
    if include_orders:
        order_result = (await get_schwab_orders(account_hash, max_results=max_orders)).get(
            "result", {}
        )
        for order in order_result.get("orders", [])[:max_orders]:
            leg = (order.get("orderLegCollection") or [{}])[0]
            instrument = leg.get("instrument", {})
            orders.append(
                {
                    "symbol": instrument.get("symbol"),
                    "side": leg.get("instruction"),
                    "state": order.get("status"),
                    "quantity": _safe_float(leg.get("quantity")),
                    "price": _safe_float(order.get("price")),
                }
            )

    return {
        "broker": "schwab",
        "source": "schwab",
        "available": True,
        "confidence": "medium",
        "notes": [],
        "pricing": pricing,
        "holdings": holdings,
        "orders": orders,
        "summary": {
            "equity": _safe_float(
                balances.get("current_balances", {}).get("market_value")
            ),
            "buying_power": _safe_float(
                balances.get("current_balances", {}).get("buying_power")
            ),
            "market_value": _safe_float(
                balances.get("current_balances", {}).get("market_value")
            ),
        },
    }


def _derive_symbols(
    requested_symbols: list[str] | None,
    robinhood_entry: dict[str, Any],
    schwab_entry: dict[str, Any],
) -> list[str]:
    if requested_symbols:
        return [symbol.upper() for symbol in requested_symbols]

    derived: set[str] = set()
    for entry in (robinhood_entry, schwab_entry):
        for holding in entry.get("holdings", []):
            symbol = holding.get("symbol")
            if symbol:
                derived.add(str(symbol).upper())
    return sorted(derived)


async def get_broker_comparison(
    symbols: list[str] | None = None,
    include_orders: bool = True,
    max_orders: int = 5,
) -> dict[str, Any]:
    """Return side-by-side broker comparison with normalized output."""
    requested_symbols = [symbol.upper() for symbol in symbols] if symbols else []

    robinhood_entry = await _build_robinhood(requested_symbols, include_orders, max_orders)
    schwab_entry = await _build_schwab(requested_symbols, include_orders, max_orders)
    final_symbols = _derive_symbols(symbols, robinhood_entry, schwab_entry)

    if not symbols:
        robinhood_entry = await _build_robinhood(final_symbols, include_orders, max_orders)
        schwab_entry = await _build_schwab(final_symbols, include_orders, max_orders)

    comparison: dict[str, Any] = {}
    for symbol in final_symbols:
        comparison[symbol] = {
            "robinhood": {
                "price": robinhood_entry.get("pricing", {}).get(symbol, {}).get("price"),
                "holding_quantity": next(
                    (
                        item.get("quantity")
                        for item in robinhood_entry.get("holdings", [])
                        if item.get("symbol") == symbol
                    ),
                    0.0,
                ),
            },
            "schwab": {
                "price": schwab_entry.get("pricing", {}).get(symbol, {}).get("price"),
                "holding_quantity": next(
                    (
                        item.get("quantity")
                        for item in schwab_entry.get("holdings", [])
                        if item.get("symbol") == symbol
                    ),
                    0.0,
                ),
            },
        }

    notes: list[str] = []
    if not robinhood_entry.get("available"):
        notes.append(f"robinhood unavailable: {', '.join(robinhood_entry.get('notes', []))}")
    if not schwab_entry.get("available"):
        notes.append(f"schwab unavailable: {', '.join(schwab_entry.get('notes', []))}")

    available_count = sum(
        1 for entry in (robinhood_entry, schwab_entry) if entry.get("available")
    )
    status = "success" if available_count == 2 else "partial" if available_count == 1 else "error"

    return create_success_response(
        {
            "brokers": {
                "robinhood": robinhood_entry,
                "schwab": schwab_entry,
            },
            "comparison": comparison,
            "availability_notes": notes,
            "status": status,
        }
    )
