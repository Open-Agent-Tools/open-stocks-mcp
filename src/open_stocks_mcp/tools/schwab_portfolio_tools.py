"""Computed Schwab portfolio MCP tools."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from schwab.client import Client

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.broker_utils import (
    execute_broker_request,
    get_authenticated_broker_or_error,
)
from open_stocks_mcp.tools.error_handling import (
    create_error_response,
    create_success_response,
    handle_schwab_errors,
)


def _to_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _extract_accounts(accounts_data: Any) -> list[dict[str, Any]]:
    if isinstance(accounts_data, list):
        return [item for item in accounts_data if isinstance(item, dict)]
    if isinstance(accounts_data, dict):
        return [accounts_data]
    return []


def _position_row(account_hash: str, position: dict[str, Any]) -> dict[str, Any]:
    instrument = position.get("instrument", {})
    long_qty = _to_float(position.get("longQuantity"))
    short_qty = _to_float(position.get("shortQuantity"))
    return {
        "account_hash": account_hash,
        "symbol": instrument.get("symbol"),
        "asset_type": instrument.get("assetType"),
        "long_quantity": long_qty,
        "short_quantity": short_qty,
        "net_quantity": long_qty + short_qty,
        "average_price": _to_float(position.get("averagePrice")),
        "market_value": _to_float(position.get("marketValue")),
        "current_day_pl": _to_float(position.get("currentDayProfitLoss")),
        "instrument": instrument,
        "raw_position": position,
    }


def _normalize_option_position(row: dict[str, Any]) -> dict[str, Any]:
    instrument = row.get("instrument", {})
    return {
        "account_hash": row.get("account_hash"),
        "symbol": instrument.get("symbol"),
        "underlying_symbol": instrument.get("underlyingSymbol"),
        "option_type": instrument.get("putCall"),
        "strike_price": instrument.get("strikePrice"),
        "expiration_date": instrument.get("expirationDate"),
        "long_quantity": row.get("long_quantity", 0.0),
        "short_quantity": row.get("short_quantity", 0.0),
        "net_quantity": row.get("net_quantity", 0.0),
        "average_price": row.get("average_price", 0.0),
        "market_value": row.get("market_value", 0.0),
        "current_day_pl": row.get("current_day_pl", 0.0),
    }


@handle_schwab_errors
async def get_schwab_build_holdings() -> dict[str, Any]:
    """Build holdings from all Schwab account positions and quote enrichment."""
    broker, error = await get_authenticated_broker_or_error(
        "schwab", "build holdings across accounts"
    )
    if error:
        return error

    try:

        def _get_accounts() -> Any:
            response = broker.client.get_accounts(
                fields=Client.Account.Fields.POSITIONS
            )
            return response.json()

        accounts_data = await execute_broker_request(_get_accounts, retry_safe=True)
        accounts = _extract_accounts(accounts_data)

        all_rows: list[dict[str, Any]] = []
        symbols: set[str] = set()
        for account_entry in accounts:
            account = account_entry.get("securitiesAccount", {})
            account_hash = account.get("hashValue", "")
            for position in account.get("positions", []):
                row = _position_row(account_hash, position)
                symbol = row.get("symbol")
                if symbol:
                    all_rows.append(row)
                    symbols.add(str(symbol))

        quotes: dict[str, Any] = {}
        if symbols:

            def _get_quotes() -> Any:
                response = broker.client.get_quotes(sorted(symbols))
                return response.json()

            quotes_data = await execute_broker_request(_get_quotes, retry_safe=True)
            if isinstance(quotes_data, dict):
                quotes = quotes_data

        holdings: dict[str, dict[str, Any]] = {}
        for row in all_rows:
            symbol = str(row.get("symbol"))
            quote = quotes.get(symbol, {})
            quote_price = _to_float(
                quote.get("quote", {}).get("lastPrice") or quote.get("lastPrice")
            )
            holdings[symbol] = {
                "symbol": symbol,
                "quantity": row["net_quantity"],
                "average_buy_price": row["average_price"],
                "equity": row["market_value"],
                "market_value": row["market_value"],
                "price": quote_price,
                "day_change": _to_float(
                    quote.get("quote", {}).get("netChange") or quote.get("netChange")
                ),
                "day_change_percent": _to_float(
                    quote.get("quote", {}).get("netPercentChangeInDouble")
                    or quote.get("netPercentChangeInDouble")
                ),
                "account_hash": row.get("account_hash"),
            }

        return create_success_response(
            {
                "holdings": holdings,
                "total_positions": len(all_rows),
                "status": "ok",
            }
        )
    except Exception as exc:
        logger.error(f"Error building Schwab holdings: {exc}")
        return create_error_response(exc)


@handle_schwab_errors
async def get_schwab_day_trades() -> dict[str, Any]:
    """Compute day trades from recent Schwab trade transactions."""
    broker, error = await get_authenticated_broker_or_error(
        "schwab", "compute day trades"
    )
    if error:
        return error

    try:

        def _get_account_numbers() -> Any:
            response = broker.client.get_account_numbers()
            return response.json()

        account_numbers = await execute_broker_request(
            _get_account_numbers, retry_safe=True
        )
        account_hashes: list[str] = []
        for item in account_numbers if isinstance(account_numbers, list) else []:
            if not isinstance(item, dict):
                continue
            hash_value = item.get("hashValue")
            if isinstance(hash_value, str) and hash_value:
                account_hashes.append(hash_value)

        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=6)
        day_trade_count = 0
        trades: list[dict[str, Any]] = []

        for account_hash in account_hashes:

            def _get_transactions(current_account_hash: str = account_hash) -> Any:
                response = broker.client.get_transactions(
                    current_account_hash,
                    start_date=start_date,
                    end_date=end_date,
                    transaction_types=Client.Transactions.TransactionType.TRADE,
                )
                return response.json()

            txns = await execute_broker_request(_get_transactions, retry_safe=True)
            bucket: dict[tuple[str, str], set[str]] = defaultdict(set)
            for txn in txns if isinstance(txns, list) else []:
                if not isinstance(txn, dict):
                    continue
                symbol = str(txn.get("symbol") or "").upper()
                if not symbol:
                    continue
                txn_date = str(txn.get("transactionDate") or "")[:10]
                if not txn_date:
                    continue
                instruction = str(txn.get("instruction") or "").upper()
                side = (
                    "BUY"
                    if "BUY" in instruction
                    else "SELL"
                    if "SELL" in instruction
                    else ""
                )
                if not side:
                    continue
                bucket[(txn_date, symbol)].add(side)
                trades.append(
                    {
                        "account_hash": account_hash,
                        "date": txn_date,
                        "symbol": symbol,
                        "instruction": instruction,
                    }
                )

            for sides in bucket.values():
                if "BUY" in sides and "SELL" in sides:
                    day_trade_count += 1

        remaining_day_trades = max(0, 3 - day_trade_count)
        return create_success_response(
            {
                "day_trade_count": day_trade_count,
                "remaining_day_trades": remaining_day_trades,
                "pattern_day_trader": day_trade_count >= 4,
                "trades": trades,
                "status": "ok",
            }
        )
    except Exception as exc:
        logger.error(f"Error computing Schwab day trades: {exc}")
        return create_error_response(exc)


@handle_schwab_errors
async def get_schwab_aggregate_positions() -> dict[str, Any]:
    """Aggregate position totals across all linked Schwab accounts."""
    broker, error = await get_authenticated_broker_or_error(
        "schwab", "aggregate positions"
    )
    if error:
        return error

    try:

        def _get_accounts() -> Any:
            response = broker.client.get_accounts(
                fields=Client.Account.Fields.POSITIONS
            )
            return response.json()

        accounts_data = await execute_broker_request(_get_accounts, retry_safe=True)
        accounts = _extract_accounts(accounts_data)

        grouped: dict[tuple[str, str], dict[str, Any]] = {}
        for account_entry in accounts:
            account = account_entry.get("securitiesAccount", {})
            account_hash = account.get("hashValue", "")
            for position in account.get("positions", []):
                row = _position_row(account_hash, position)
                symbol = str(row.get("symbol") or "")
                asset_type = str(row.get("asset_type") or "")
                if not symbol:
                    continue
                key = (symbol, asset_type)
                if key not in grouped:
                    grouped[key] = {
                        "symbol": symbol,
                        "asset_type": asset_type,
                        "long_quantity": 0.0,
                        "short_quantity": 0.0,
                        "net_quantity": 0.0,
                        "market_value": 0.0,
                        "current_day_pl": 0.0,
                        "accounts": [],
                    }
                item = grouped[key]
                item["long_quantity"] += row["long_quantity"]
                item["short_quantity"] += row["short_quantity"]
                item["net_quantity"] += row["net_quantity"]
                item["market_value"] += row["market_value"]
                item["current_day_pl"] += row["current_day_pl"]
                item["accounts"].append(
                    {
                        "account_hash": row["account_hash"],
                        "long_quantity": row["long_quantity"],
                        "short_quantity": row["short_quantity"],
                        "net_quantity": row["net_quantity"],
                        "market_value": row["market_value"],
                    }
                )

        aggregates = list(grouped.values())
        return create_success_response(
            {
                "positions": aggregates,
                "count": len(aggregates),
                "status": "ok",
            }
        )
    except Exception as exc:
        logger.error(f"Error aggregating Schwab positions: {exc}")
        return create_error_response(exc)


@handle_schwab_errors
async def get_schwab_all_option_positions() -> dict[str, Any]:
    """Return all option positions across all Schwab accounts."""
    aggregate = await get_schwab_aggregate_positions()
    if "result" not in aggregate or aggregate["result"].get("status") == "error":
        return aggregate

    try:
        broker, error = await get_authenticated_broker_or_error(
            "schwab", "all option positions"
        )
        if error:
            return error

        def _get_accounts() -> Any:
            response = broker.client.get_accounts(
                fields=Client.Account.Fields.POSITIONS
            )
            return response.json()

        accounts_data = await execute_broker_request(_get_accounts, retry_safe=True)
        accounts = _extract_accounts(accounts_data)

        rows: list[dict[str, Any]] = []
        for account_entry in accounts:
            account = account_entry.get("securitiesAccount", {})
            account_hash = account.get("hashValue", "")
            for position in account.get("positions", []):
                row = _position_row(account_hash, position)
                if str(row.get("asset_type") or "").upper() == "OPTION":
                    rows.append(_normalize_option_position(row))

        open_positions = [
            row for row in rows if abs(_to_float(row.get("net_quantity"))) > 0.0
        ]
        return create_success_response(
            {
                "positions": rows,
                "total_positions": len(rows),
                "open_positions": len(open_positions),
                "closed_positions": len(rows) - len(open_positions),
                "status": "ok",
            }
        )
    except Exception as exc:
        logger.error(f"Error getting all Schwab option positions: {exc}")
        return create_error_response(exc)


@handle_schwab_errors
async def get_schwab_open_option_positions() -> dict[str, Any]:
    """Return open option positions (non-zero net quantity) across accounts."""
    all_positions = await get_schwab_all_option_positions()
    if "result" not in all_positions:
        return all_positions

    result = all_positions["result"]
    if result.get("status") == "error":
        return all_positions

    positions = result.get("positions", [])
    open_positions = [
        row for row in positions if abs(_to_float(row.get("net_quantity"))) > 0.0
    ]
    return create_success_response(
        {
            "positions": open_positions,
            "total_positions": len(open_positions),
            "status": "ok",
        }
    )
