"""Schwab payment and dividend extraction MCP tools."""

import asyncio
import datetime
from decimal import Decimal
from typing import Any

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.broker_utils import (
    get_authenticated_broker_or_error,
)
from open_stocks_mcp.tools.error_handling import (
    create_error_response,
    create_success_response,
    handle_schwab_errors,
)


def _classify_transaction(tx: dict[str, Any]) -> str:
    """Classify a Schwab transaction into payment categories.

    Args:
        tx: Transaction dictionary from Schwab API

    Returns:
        One of: "dividend", "interest", "stock_loan", "other"
    """
    tx_type = tx.get("type", "")
    description = tx.get("description", "").upper()

    if tx_type == "DIVIDEND_OR_INTEREST":
        if "INTEREST" in description:
            return "interest"
        return "dividend"

    if tx_type == "JOURNAL" and (
        "SECURITIES LENDING REVENUE" in description or "STOCK LOAN" in description
    ):
        return "stock_loan"

    return "other"


@handle_schwab_errors
async def schwab_get_dividends(
    account_hash: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Get dividend payments for a Schwab account.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end_date (YYYY-MM-DD)

    Returns:
        Dict with list of dividends and total amount
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get dividends for {account_hash}"
    )
    if error:
        return error

    try:
        parsed_start_date = (
            datetime.date.fromisoformat(start_date) if start_date is not None else None
        )
        parsed_end_date = (
            datetime.date.fromisoformat(end_date) if end_date is not None else None
        )

        # We hard-code transaction_types to DIVIDEND_OR_INTEREST for this tool
        # but _classify_transaction will filter out interest.
        response = await asyncio.to_thread(
            broker.client.get_transactions,
            account_hash,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            transaction_types=["DIVIDEND_OR_INTEREST"],
            symbol=None,
        )

        transactions = response.json() if hasattr(response, "json") else response

        if not isinstance(transactions, list):
            transactions = []

        # Filter for dividends and calculate total
        dividends = []
        total_amount = Decimal("0.00")

        for tx in transactions:
            if _classify_transaction(tx) == "dividend":
                dividends.append(tx)
                net_amount = tx.get("netAmount", 0)
                total_amount += Decimal(str(net_amount))

        return create_success_response(
            {
                "dividends": dividends,
                "total_amount": str(total_amount.quantize(Decimal("0.01"))),
                "count": len(dividends),
            }
        )

    except Exception as e:
        logger.error(f"Error getting Schwab dividends for {account_hash}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_get_stock_loan_payments(
    account_hash: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Get stock loan (securities lending) payments for a Schwab account.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)

    Returns:
        Dict with list of loan payments, total amount, and enrollment status
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get stock loan payments for {account_hash}"
    )
    if error:
        return error

    try:
        parsed_start_date = (
            datetime.date.fromisoformat(start_date) if start_date is not None else None
        )
        parsed_end_date = (
            datetime.date.fromisoformat(end_date) if end_date is not None else None
        )

        response = await asyncio.to_thread(
            broker.client.get_transactions,
            account_hash,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            transaction_types=["JOURNAL"],
            symbol=None,
        )

        transactions = response.json() if hasattr(response, "json") else response

        if not isinstance(transactions, list):
            transactions = []

        loan_payments = []
        total_amount = Decimal("0.00")

        for tx in transactions:
            if _classify_transaction(tx) == "stock_loan":
                loan_payments.append(tx)
                net_amount = tx.get("netAmount", 0)
                total_amount += Decimal(str(net_amount))

        return create_success_response(
            {
                "loan_payments": loan_payments,
                "total_amount": str(total_amount.quantize(Decimal("0.01"))),
                "count": len(loan_payments),
                "enrolled": len(loan_payments) > 0,
            }
        )

    except Exception as e:
        logger.error(
            f"Error getting Schwab stock loan payments for {account_hash}: {e}"
        )
        return create_error_response(e)


@handle_schwab_errors
async def schwab_get_dividends_by_symbol(
    account_hash: str,
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Get dividend payments for a specific symbol in a Schwab account.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        symbol: Stock symbol to filter dividends by (case-insensitive)
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)

    Returns:
        Dict with list of dividends, total amount, and symbol
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get dividends for {symbol} in {account_hash}"
    )
    if error:
        return error

    try:
        normalized_symbol = symbol.upper()
        parsed_start_date = (
            datetime.date.fromisoformat(start_date) if start_date is not None else None
        )
        parsed_end_date = (
            datetime.date.fromisoformat(end_date) if end_date is not None else None
        )

        response = await asyncio.to_thread(
            broker.client.get_transactions,
            account_hash,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            transaction_types=["DIVIDEND_OR_INTEREST"],
            symbol=normalized_symbol,
        )

        transactions = response.json() if hasattr(response, "json") else response

        if not isinstance(transactions, list):
            transactions = []

        dividends = []
        total_amount = Decimal("0.00")

        for tx in transactions:
            if _classify_transaction(tx) == "dividend":
                dividends.append(tx)
                net_amount = tx.get("netAmount", 0)
                total_amount += Decimal(str(net_amount))

        return create_success_response(
            {
                "symbol": normalized_symbol,
                "dividends": dividends,
                "total_amount": str(total_amount.quantize(Decimal("0.01"))),
                "count": len(dividends),
            }
        )
    except Exception as e:
        logger.error(
            f"Error getting Schwab dividends for {symbol} in {account_hash}: {e}"
        )
        return create_error_response(e)


@handle_schwab_errors
async def schwab_get_interest_payments(
    account_hash: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Get interest payments for a Schwab account."""
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get interest payments for {account_hash}"
    )
    if error:
        return error

    try:
        parsed_start_date = (
            datetime.date.fromisoformat(start_date) if start_date is not None else None
        )
        parsed_end_date = (
            datetime.date.fromisoformat(end_date) if end_date is not None else None
        )

        response = await asyncio.to_thread(
            broker.client.get_transactions,
            account_hash,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            transaction_types=["DIVIDEND_OR_INTEREST"],
            symbol=None,
        )

        transactions = response.json() if hasattr(response, "json") else response
        if not isinstance(transactions, list):
            transactions = []

        interest_payments = []
        total_amount = Decimal("0.00")

        for tx in transactions:
            if _classify_transaction(tx) == "interest":
                interest_payments.append(tx)
                net_amount = tx.get("netAmount", 0)
                total_amount += Decimal(str(net_amount))

        return create_success_response(
            {
                "interest_payments": interest_payments,
                "total_amount": str(total_amount.quantize(Decimal("0.01"))),
                "count": len(interest_payments),
            }
        )
    except Exception as e:
        logger.error(f"Error getting Schwab interest payments for {account_hash}: {e}")
        return create_error_response(e)


@handle_schwab_errors
async def schwab_get_total_dividends(
    account_hash: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Get aggregate dividend totals with year grouping for a Schwab account.

    Args:
        account_hash: Account hash from get_schwab_account_numbers()
        start_date: Optional start date (YYYY-MM-DD). Schwab enforces a 60-day
            default lookback; pass an explicit start_date for older history.
        end_date: Optional end date (YYYY-MM-DD)

    Returns:
        Dict with total_amount, count, by_year, first_payment_date, last_payment_date
    """
    broker, error = await get_authenticated_broker_or_error(
        "schwab", f"get total dividends for {account_hash}"
    )
    if error:
        return error

    try:
        parsed_start_date = (
            datetime.date.fromisoformat(start_date) if start_date is not None else None
        )
        parsed_end_date = (
            datetime.date.fromisoformat(end_date) if end_date is not None else None
        )

        response = await asyncio.to_thread(
            broker.client.get_transactions,
            account_hash,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            transaction_types=["DIVIDEND_OR_INTEREST"],
            symbol=None,
        )

        transactions = response.json() if hasattr(response, "json") else response
        if not isinstance(transactions, list):
            transactions = []

        total_amount = Decimal("0.00")
        by_year: dict[str, Decimal] = {}
        trade_dates: list[str] = []

        for tx in transactions:
            if _classify_transaction(tx) != "dividend":
                continue
            net_amount = Decimal(str(float(tx.get("netAmount") or 0)))
            total_amount += net_amount
            trade_date = tx.get("tradeDate", "")
            if trade_date:
                year = trade_date[:4]
                by_year[year] = by_year.get(year, Decimal("0.00")) + net_amount
                trade_dates.append(trade_date)

        sorted_by_year = {
            k: f"{v:.2f}"
            for k, v in sorted(by_year.items(), key=lambda x: x[0], reverse=True)
        }
        trade_dates.sort()

        return create_success_response(
            {
                "total_amount": f"{total_amount:.2f}",
                "count": len(trade_dates),
                "by_year": sorted_by_year,
                "first_payment_date": trade_dates[0] if trade_dates else None,
                "last_payment_date": trade_dates[-1] if trade_dates else None,
            }
        )

    except Exception as e:
        logger.error(f"Error getting Schwab total dividends for {account_hash}: {e}")
        return create_error_response(e)
