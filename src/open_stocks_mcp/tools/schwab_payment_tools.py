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
