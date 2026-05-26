"""Compatibility re-exports for Robinhood watchlist tools."""

from open_stocks_mcp.tools.watchlists.read import (
    get_all_watchlists,
    get_watchlist_by_name,
    get_watchlist_performance,
)
from open_stocks_mcp.tools.watchlists.write import (
    add_symbols_to_watchlist,
    remove_symbols_from_watchlist,
)

__all__ = [
    "add_symbols_to_watchlist",
    "get_all_watchlists",
    "get_watchlist_by_name",
    "get_watchlist_performance",
    "remove_symbols_from_watchlist",
]
