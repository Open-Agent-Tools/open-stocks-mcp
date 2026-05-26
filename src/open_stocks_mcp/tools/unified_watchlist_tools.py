"""Unified Watchlist Tools for multi-broker support."""

from typing import Any

from open_stocks_mcp.brokers.registry import get_broker_registry
from open_stocks_mcp.tools.responses import create_success_response
from open_stocks_mcp.tools.watchlists.read import (
    get_all_watchlists as get_rh_watchlists,
)
from open_stocks_mcp.tools.watchlists.read import (
    get_watchlist_by_name as get_rh_watchlist_by_name,
)
from open_stocks_mcp.tools.watchlists.write import (
    add_symbols_to_watchlist as add_rh_symbols,
)
from open_stocks_mcp.tools.watchlists.write import (
    remove_symbols_from_watchlist as remove_rh_symbols,
)


def _normalize_symbols(symbols: list[str]) -> list[str]:
    """Uppercase and de-duplicate symbols."""
    normalized = []
    seen = set()
    for s in symbols:
        if isinstance(s, str):
            clean = s.upper().strip()
            if clean and clean not in seen:
                normalized.append(clean)
                seen.add(clean)
    return normalized


async def get_unified_watchlists(brokers: list[str] | None = None) -> dict[str, Any]:
    """Get all watchlists across supported brokers."""
    registry = await get_broker_registry()
    all_broker_names = registry.list_brokers()
    broker_names = brokers if brokers is not None else all_broker_names

    brokers_out = {}
    unified_watchlists = []
    warnings = []
    partial_failure = False

    for name in broker_names:
        if name not in all_broker_names:
            brokers_out[name] = {"status": "error", "message": "Broker not registered"}
            partial_failure = True
            continue

        broker = registry.get_broker(name)
        if name == "robinhood":
            if broker and broker.is_available():
                rh_res = await get_rh_watchlists()
                rh_data = rh_res.get("result", {})
                if rh_data.get("status") == "success":
                    brokers_out[name] = {
                        "status": "success",
                        "watchlist_count": rh_data.get("total_watchlists", 0),
                    }
                    for wl in rh_data.get("watchlists", []):
                        unified_watchlists.append(
                            {
                                "name": wl.get("name"),
                                "symbols": wl.get("symbols", []),
                                "symbol_count": wl.get("symbol_count", 0),
                                "brokers": ["robinhood"],
                            }
                        )
                else:
                    brokers_out[name] = {
                        "status": "error",
                        "message": rh_data.get("message", "Error fetching watchlists"),
                    }
                    partial_failure = True
            else:
                brokers_out[name] = {"status": "unavailable"}
                partial_failure = True
        elif name == "schwab":
            brokers_out[name] = {
                "status": "unsupported",
                "message": "Schwab does not currently expose a watchlist API.",
            }
            warnings.append(
                {
                    "broker": "schwab",
                    "message": "Watchlists are not supported on Schwab.",
                }
            )
        else:
            brokers_out[name] = {"status": "unsupported"}

    status = "success"
    if partial_failure:
        status = "partial_success"

    return create_success_response(
        {
            "watchlists": unified_watchlists,
            "total_watchlists": len(unified_watchlists),
            "brokers": brokers_out,
            "warnings": warnings,
            "status": status,
        }
    )


async def get_unified_watchlist_by_name(
    watchlist_name: str, brokers: list[str] | None = None
) -> dict[str, Any]:
    """Get a specific watchlist by name across supported brokers."""
    registry = await get_broker_registry()
    all_broker_names = registry.list_brokers()
    broker_names = brokers if brokers is not None else all_broker_names

    per_broker = {}
    combined_symbols = set()
    warnings = []
    found_any = False

    for name in broker_names:
        if name not in all_broker_names:
            per_broker[name] = {"status": "error", "message": "Broker not registered"}
            continue

        broker = registry.get_broker(name)
        if name == "robinhood":
            if broker and broker.is_available():
                rh_res = await get_rh_watchlist_by_name(watchlist_name)
                rh_data = rh_res.get("result", {})
                if rh_data.get("status") == "success":
                    per_broker[name] = {
                        "status": "success",
                        "symbols": rh_data.get("symbols", []),
                    }
                    combined_symbols.update(rh_data.get("symbols", []))
                    found_any = True
                elif rh_data.get("status") == "not_found":
                    per_broker[name] = {"status": "not_found"}
                else:
                    per_broker[name] = {
                        "status": "error",
                        "message": rh_data.get("message", "Error"),
                    }
            else:
                per_broker[name] = {"status": "unavailable"}
        elif name == "schwab":
            per_broker[name] = {"status": "unsupported"}
            warnings.append(
                {
                    "broker": "schwab",
                    "message": "Watchlists are not supported on Schwab.",
                }
            )

    symbols = sorted(combined_symbols)
    return create_success_response(
        {
            "watchlist_name": watchlist_name,
            "symbols": symbols,
            "symbol_count": len(symbols),
            "brokers": list(per_broker.keys()),
            "per_broker": per_broker,
            "warnings": warnings,
            "status": "success" if found_any else "not_found",
        }
    )


async def add_symbols_to_unified_watchlist(
    watchlist_name: str, symbols: list[str], brokers: list[str] | None = None
) -> dict[str, Any]:
    """Add symbols to a watchlist across supported brokers."""
    registry = await get_broker_registry()
    all_broker_names = registry.list_brokers()
    broker_names = brokers if brokers is not None else all_broker_names

    normalized = _normalize_symbols(symbols)
    per_broker = {}
    warnings = []

    for name in broker_names:
        if name not in all_broker_names:
            per_broker[name] = {
                "status": "error",
                "success": False,
                "message": "Broker not registered",
            }
            continue

        broker = registry.get_broker(name)
        if name == "robinhood":
            if broker and broker.is_available():
                res = await add_rh_symbols(watchlist_name, normalized)
                data = res.get("result", {})
                per_broker[name] = data
            else:
                per_broker[name] = {"status": "unavailable", "success": False}
        elif name == "schwab":
            per_broker[name] = {
                "status": "unsupported",
                "success": False,
                "message": "Schwab does not support watchlist mutations via API.",
            }
            warnings.append(
                {"broker": "schwab", "message": "Add operation ignored for Schwab."}
            )

    # Determine overall status
    success_count = sum(1 for b in per_broker.values() if b.get("status") == "success")
    if success_count == len(per_broker) and len(per_broker) > 0:
        status = "success"
    elif success_count > 0:
        status = "partial_success"
    else:
        status = "error"

    return create_success_response(
        {
            "watchlist_name": watchlist_name,
            "symbols_added": normalized,
            "per_broker": per_broker,
            "warnings": warnings,
            "status": status,
        }
    )


async def remove_symbols_from_unified_watchlist(
    watchlist_name: str, symbols: list[str], brokers: list[str] | None = None
) -> dict[str, Any]:
    """Remove symbols from a watchlist across supported brokers."""
    registry = await get_broker_registry()
    all_broker_names = registry.list_brokers()
    broker_names = brokers if brokers is not None else all_broker_names

    normalized = _normalize_symbols(symbols)
    per_broker = {}
    warnings = []

    for name in broker_names:
        if name not in all_broker_names:
            per_broker[name] = {
                "status": "error",
                "success": False,
                "message": "Broker not registered",
            }
            continue

        broker = registry.get_broker(name)
        if name == "robinhood":
            if broker and broker.is_available():
                res = await remove_rh_symbols(watchlist_name, normalized)
                data = res.get("result", {})
                per_broker[name] = data
            else:
                per_broker[name] = {"status": "unavailable", "success": False}
        elif name == "schwab":
            per_broker[name] = {
                "status": "unsupported",
                "success": False,
                "message": "Schwab does not support watchlist mutations via API.",
            }
            warnings.append(
                {"broker": "schwab", "message": "Remove operation ignored for Schwab."}
            )

    success_count = sum(1 for b in per_broker.values() if b.get("status") == "success")
    if success_count == len(per_broker) and len(per_broker) > 0:
        status = "success"
    elif success_count > 0:
        status = "partial_success"
    else:
        status = "error"

    return create_success_response(
        {
            "watchlist_name": watchlist_name,
            "symbols_removed": normalized,
            "per_broker": per_broker,
            "warnings": warnings,
            "status": status,
        }
    )
