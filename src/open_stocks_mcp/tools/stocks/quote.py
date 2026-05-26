"""Stock price, quote, and pricebook tools."""

from typing import Any

import robin_stocks.robinhood as rh

from open_stocks_mcp.config import load_config
from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.cache import cached_async
from open_stocks_mcp.tools.error_handling import (
    create_error_response,
    create_no_data_response,
    create_success_response,
    execute_with_retry,
    handle_robin_stocks_errors,
    log_api_call,
    validate_symbol,
)

_cache_cfg = load_config().cache


@handle_robin_stocks_errors
@cached_async(
    name="quotes",
    ttl=_cache_cfg.quotes_ttl_seconds,
    max_size=_cache_cfg.max_size,
    strategy=_cache_cfg.strategy,
)
async def get_stock_price(symbol: str) -> dict[str, Any]:
    """
    Get current stock price and basic metrics.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        A JSON object containing stock price data in the result field.
    """
    # Input validation
    if not validate_symbol(symbol):
        return create_error_response(
            ValueError(f"Invalid symbol format: {symbol}"), "symbol validation"
        )

    symbol = symbol.strip().upper()
    log_api_call("get_stock_price", symbol=symbol)

    # Get latest price and quote data with retry logic; coalesce_key deduplicates
    # concurrent calls for the same symbol while cache is cold.
    price_data = await execute_with_retry(
        rh.get_latest_price,
        symbol,
        "ask_price",
        coalesce_key=f"get_latest_price:{symbol}",
    )
    quote_data = await execute_with_retry(
        rh.get_quotes,
        symbol,
        coalesce_key=f"get_quotes:{symbol}",
    )

    if not price_data or not quote_data:
        return create_no_data_response(
            f"No price data found for symbol: {symbol}", {"symbol": symbol}
        )

    quote = quote_data[0] if quote_data else {}
    current_price = float(price_data[0]) if price_data and price_data[0] else 0.0

    # Calculate change and change percent
    previous_close = float(quote.get("previous_close", 0))
    change = current_price - previous_close if previous_close else 0.0
    change_percent = (change / previous_close * 100) if previous_close else 0.0

    logger.info(f"Successfully retrieved stock price for {symbol}")
    return create_success_response(
        {
            "symbol": symbol,
            "price": current_price,
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "previous_close": previous_close,
            "volume": int(quote.get("volume", 0)),
            "ask_price": float(quote.get("ask_price", 0)),
            "bid_price": float(quote.get("bid_price", 0)),
            "last_trade_price": float(quote.get("last_trade_price", 0)),
        }
    )


@handle_robin_stocks_errors
async def get_stock_quote_by_id(instrument_id: str) -> dict[str, Any]:
    """
    Get stock quote using Robinhood's internal instrument ID.

    Args:
        instrument_id: Robinhood's internal instrument ID

    Returns:
        A JSON object containing the stock quote in the result field.
    """
    # Input validation
    if not instrument_id or not instrument_id.strip():
        return create_error_response(
            ValueError("Instrument ID cannot be empty"), "instrument_id validation"
        )

    instrument_id = instrument_id.strip()
    log_api_call("get_stock_quote_by_id", instrument_id=instrument_id)

    # Get quote by ID with retry logic
    quote_data = await execute_with_retry(rh.get_stock_quote_by_id, instrument_id)

    if not quote_data:
        return create_no_data_response(
            f"No quote data found for instrument ID: {instrument_id}",
            {"instrument_id": instrument_id},
        )

    # Process quote data
    try:
        last_trade_price = float(quote_data.get("last_trade_price", 0))
        previous_close = float(quote_data.get("previous_close", 0))

        # Calculate change and percentage change
        change = last_trade_price - previous_close if previous_close else 0
        change_percent = (change / previous_close * 100) if previous_close else 0

        processed_quote = {
            "instrument_id": instrument_id,
            "symbol": quote_data.get("symbol", "N/A"),
            "price": last_trade_price,
            "previous_close": previous_close,
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "ask_price": float(quote_data.get("ask_price", 0)),
            "bid_price": float(quote_data.get("bid_price", 0)),
            "ask_size": int(quote_data.get("ask_size", 0)),
            "bid_size": int(quote_data.get("bid_size", 0)),
            "last_extended_hours_trade_price": float(
                quote_data.get("last_extended_hours_trade_price", 0)
            ),
            "previous_close_date": quote_data.get("previous_close_date", "N/A"),
            "trading_halted": quote_data.get("trading_halted", False),
            "has_traded": quote_data.get("has_traded", False),
            "last_trade_price_source": quote_data.get("last_trade_price_source", "N/A"),
            "updated_at": quote_data.get("updated_at", "N/A"),
            "instrument_url": quote_data.get("instrument", "N/A"),
        }

        logger.info(f"Successfully retrieved quote for instrument ID: {instrument_id}")
        return create_success_response(processed_quote)

    except (ValueError, TypeError) as e:
        return create_error_response(
            ValueError(f"Error processing quote data: {e!s}"), "quote processing"
        )


@handle_robin_stocks_errors
async def get_pricebook_by_symbol(symbol: str) -> dict[str, Any]:
    """
    Get Level II order book data for a symbol (requires Gold subscription).

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        A JSON object containing Level II order book data in the result field.
    """
    # Input validation
    if not validate_symbol(symbol):
        return create_error_response(
            ValueError(f"Invalid symbol format: {symbol}"), "symbol validation"
        )

    symbol = symbol.strip().upper()
    log_api_call("get_pricebook_by_symbol", symbol=symbol)

    # Get pricebook data with retry logic
    pricebook_data = await execute_with_retry(rh.get_pricebook_by_symbol, symbol)

    if not pricebook_data:
        return create_no_data_response(
            f"No pricebook data found for symbol: {symbol}. Note: This feature requires Robinhood Gold subscription.",
            {"symbol": symbol},
        )

    # Process pricebook data
    try:
        processed_asks = []
        processed_bids = []

        # Process asks (sell orders)
        if pricebook_data.get("asks"):
            for ask in pricebook_data["asks"]:
                if ask:
                    processed_asks.append(
                        {
                            "price": float(ask.get("price", 0)),
                            "quantity": int(ask.get("quantity", 0)),
                            "side": "ask",
                        }
                    )

        # Process bids (buy orders)
        if pricebook_data.get("bids"):
            for bid in pricebook_data["bids"]:
                if bid:
                    processed_bids.append(
                        {
                            "price": float(bid.get("price", 0)),
                            "quantity": int(bid.get("quantity", 0)),
                            "side": "bid",
                        }
                    )

        # Sort asks by price (ascending) and bids by price (descending)
        processed_asks.sort(key=lambda x: x["price"])  # type: ignore[arg-type,return-value]
        processed_bids.sort(key=lambda x: x["price"], reverse=True)  # type: ignore[arg-type,return-value]

        processed_pricebook = {
            "symbol": symbol,
            "asks": processed_asks,
            "bids": processed_bids,
            "ask_count": len(processed_asks),
            "bid_count": len(processed_bids),
            "spread": (processed_asks[0]["price"] - processed_bids[0]["price"])  # type: ignore[operator]
            if processed_asks and processed_bids
            else 0.0,
            "updated_at": pricebook_data.get("updated_at", "N/A"),
            "note": "Level II data requires Robinhood Gold subscription",
        }

        logger.info(
            f"Successfully retrieved pricebook for {symbol}: {len(processed_asks)} asks, {len(processed_bids)} bids"
        )
        return create_success_response(processed_pricebook)

    except (ValueError, TypeError, KeyError) as e:
        return create_error_response(
            ValueError(f"Error processing pricebook data: {e!s}"),
            "pricebook processing",
        )
