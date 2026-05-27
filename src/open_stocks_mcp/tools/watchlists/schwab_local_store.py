"""Local file-backed watchlist storage for Schwab parity."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

STORE_PATH_ENV = "OPEN_STOCKS_SCHWAB_WATCHLIST_STORE"
DEFAULT_STORE_PATH = Path("~/.open-stocks-mcp/schwab_watchlists.json").expanduser()


def get_store_path() -> Path:
    """Resolve the Schwab local watchlist store path."""
    configured = os.getenv(STORE_PATH_ENV, "").strip()
    if configured:
        return Path(configured).expanduser()
    return DEFAULT_STORE_PATH


def _normalize_payload(raw: Any) -> dict[str, list[str]]:
    if not isinstance(raw, dict):
        return {}

    watchlists = raw.get("watchlists", raw)
    if not isinstance(watchlists, dict):
        return {}

    normalized: dict[str, list[str]] = {}
    for name, symbols in watchlists.items():
        if not isinstance(name, str):
            continue
        if not isinstance(symbols, list):
            continue
        cleaned: list[str] = []
        seen: set[str] = set()
        for symbol in symbols:
            if not isinstance(symbol, str):
                continue
            value = symbol.strip().upper()
            if value and value not in seen:
                seen.add(value)
                cleaned.append(value)
        normalized[name] = cleaned
    return normalized


def load_watchlists() -> tuple[dict[str, list[str]], str | None]:
    """Load all Schwab watchlists from local storage."""
    path = get_store_path()
    if not path.exists():
        return {}, None

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, f"Unable to read Schwab watchlist store at {path}: {exc}"

    return _normalize_payload(raw), None


def save_watchlists(watchlists: dict[str, list[str]]) -> str | None:
    """Persist all Schwab watchlists to local storage."""
    path = get_store_path()
    payload = {"watchlists": watchlists}

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    except OSError as exc:
        return f"Unable to write Schwab watchlist store at {path}: {exc}"

    return None


def get_watchlist(name: str) -> tuple[list[str] | None, str | None]:
    """Load a single watchlist by name."""
    watchlists, error = load_watchlists()
    if error:
        return None, error
    return watchlists.get(name), None


def add_symbols(name: str, symbols: list[str]) -> tuple[list[str], str | None]:
    """Add symbols to a named watchlist and persist."""
    watchlists, error = load_watchlists()
    if error:
        return [], error

    existing = watchlists.get(name, [])
    merged = list(existing)
    seen = set(existing)
    for symbol in symbols:
        if symbol not in seen:
            seen.add(symbol)
            merged.append(symbol)

    watchlists[name] = merged
    error = save_watchlists(watchlists)
    return merged, error


def remove_symbols(name: str, symbols: list[str]) -> tuple[list[str], str | None]:
    """Remove symbols from a named watchlist and persist."""
    watchlists, error = load_watchlists()
    if error:
        return [], error

    existing = watchlists.get(name, [])
    remaining = [symbol for symbol in existing if symbol not in set(symbols)]

    if remaining:
        watchlists[name] = remaining
    elif name in watchlists:
        del watchlists[name]

    error = save_watchlists(watchlists)
    return remaining, error
