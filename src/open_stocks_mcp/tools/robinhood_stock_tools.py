"""Backward-compat shim - real implementations live in tools.stocks subpackage."""

from open_stocks_mcp.tools.stocks import (  # noqa: F401
    _fetch_instruments_batch,
    find_instrument_data,
    get_instruments_by_symbols,
    get_market_hours,
    get_price_history,
    get_pricebook_by_symbol,
    get_stock_info,
    get_stock_price,
    get_stock_quote_by_id,
    search_stocks,
)
