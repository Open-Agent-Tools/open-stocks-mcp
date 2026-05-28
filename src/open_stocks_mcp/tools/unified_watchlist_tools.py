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
from open_stocks_mcp.tools.watchlists.schwab_local_store import (
    add_symbols as add_schwab_symbols,
)
from open_stocks_mcp.tools.watchlists.schwab_local_store import (
    get_watchlist as get_schwab_watchlist,
)
from open_stocks_mcp.tools.watchlists.schwab_local_store import (
    load_watchlists as load_schwab_watchlists,
)
from open_stocks_mcp.tools.watchlists.schwab_local_store import (
    remove_symbols as remove_schwab_symbols,
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


def _compute_mutation_status(per_broker: dict[str, dict[str, Any]]) -> str:
    """Compute mutation status while treating unsupported brokers as neutral."""
    actionable_statuses = [
        broker_result.get("status")
        for broker_result in per_broker.values()
        if broker_result.get("status") != "unsupported"
    ]

    if not actionable_statuses:
        return "error"
    if all(status == "success" for status in actionable_statuses):
        return "success"
    if any(status == "success" for status in actionable_statuses):
        return "partial_success"
    return "error"


def _append_or_merge_watchlist(
    unified_watchlists: list[dict[str, Any]], name: str, symbols: list[str], broker: str
) -> None:
    """Merge watchlist rows with the same name across brokers."""
    for row in unified_watchlists:
        if row.get("name") != name:
            continue

        merged_symbols = sorted(set(row.get("symbols", [])) | set(symbols))
        row["symbols"] = merged_symbols
        row["symbol_count"] = len(merged_symbols)
        if broker not in row["brokers"]:
            row["brokers"].append(broker)
        return

    unified_watchlists.append(
        {
            "name": name,
            "symbols": symbols,
            "symbol_count": len(symbols),
            "brokers": [broker],
        }
    )


async def get_unified_watchlists(brokers: list[str] | None = None) -> dict[str, Any]:
    """Get all watchlists across supported brokers."""
    registry = await get_broker_registry()
    all_broker_names = registry.list_brokers()
    broker_names = brokers if brokers is not None else all_broker_names

    brokers_out: dict[str, dict[str, Any]] = {}
    unified_watchlists: list[dict[str, Any]] = []
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
            schwab_watchlists, load_error = load_schwab_watchlists()
            if load_error:
                brokers_out[name] = {"status": "error", "message": load_error}
                warnings.append({"broker": "schwab", "message": load_error})
                partial_failure = True
            else:
                brokers_out[name] = {
                    "status": "success",
                    "watchlist_count": len(schwab_watchlists),
                    "storage_backend": "local_file",
                }
                for watchlist_name, watchlist_symbols in schwab_watchlists.items():
                    _append_or_merge_watchlist(
                        unified_watchlists,
                        name=watchlist_name,
                        symbols=watchlist_symbols,
                        broker="schwab",
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

    per_broker: dict[str, dict[str, Any]] = {}
    combined_symbols: set[str] = set()
    warnings = []
    found_any = False
    partial_failure = False

    for name in broker_names:
        if name not in all_broker_names:
            per_broker[name] = {"status": "error", "message": "Broker not registered"}
            partial_failure = True
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
                    partial_failure = True
            else:
                per_broker[name] = {"status": "unavailable"}
                partial_failure = True
        elif name == "schwab":
            schwab_symbols, load_error = get_schwab_watchlist(watchlist_name)
            if load_error:
                per_broker[name] = {"status": "error", "message": load_error}
                warnings.append({"broker": "schwab", "message": load_error})
            elif schwab_symbols is None:
                per_broker[name] = {"status": "not_found"}
            else:
                per_broker[name] = {"status": "success", "symbols": schwab_symbols}
                combined_symbols.update(schwab_symbols)
                found_any = True

    symbols = sorted(combined_symbols)

    if found_any:
        status = "success"
    elif partial_failure:
        status = "partial_failure"
    else:
        status = "not_found"

    return create_success_response(
        {
            "watchlist_name": watchlist_name,
            "symbols": symbols,
            "symbol_count": len(symbols),
            "brokers": list(per_broker.keys()),
            "per_broker": per_broker,
            "warnings": warnings,
            "status": status,
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
    per_broker: dict[str, dict[str, Any]] = {}
    warnings: list[dict[str, str]] = []

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
            combined_symbols, save_error = add_schwab_symbols(watchlist_name, normalized)
            if save_error:
                per_broker[name] = {
                    "status": "error",
                    "success": False,
                    "message": save_error,
                }
                warnings.append({"broker": "schwab", "message": save_error})
            else:
                per_broker[name] = {
                    "status": "success",
                    "success": True,
                    "symbols": combined_symbols,
                    "storage_backend": "local_file",
                }

    status = _compute_mutation_status(per_broker)

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
    per_broker: dict[str, dict[str, Any]] = {}
    warnings: list[dict[str, str]] = []

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
            remaining_symbols, save_error = remove_schwab_symbols(watchlist_name, normalized)
            if save_error:
                per_broker[name] = {
                    "status": "error",
                    "success": False,
                    "message": save_error,
                }
                warnings.append({"broker": "schwab", "message": save_error})
            else:
                per_broker[name] = {
                    "status": "success",
                    "success": True,
                    "symbols": remaining_symbols,
                    "storage_backend": "local_file",
                }

    status = _compute_mutation_status(per_broker)

    return create_success_response(
        {
            "watchlist_name": watchlist_name,
            "symbols_removed": normalized,
            "per_broker": per_broker,
            "warnings": warnings,
            "status": status,
        }
    )
