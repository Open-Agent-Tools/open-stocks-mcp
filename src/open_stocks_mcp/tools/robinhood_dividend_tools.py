"""Robin Stocks dividend and income tracking tools."""

import asyncio
import contextlib
from typing import Any

import robin_stocks.robinhood as rh

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.error_handling import (
    handle_robin_stocks_errors,
)
from open_stocks_mcp.tools.rate_limiter import get_rate_limiter
from open_stocks_mcp.tools.session_manager import get_session_manager


@handle_robin_stocks_errors
async def get_dividends() -> dict[str, Any]:
    """Get all dividend payment history for the account.

    Returns complete dividend payment history including:
    - Payment dates
    - Amounts
    - Stock symbols
    - Payment status

    Returns:
        JSON object with dividend history in "result" field:
        {
            "result": {
                "dividends": [
                    {
                        "symbol": "AAPL",
                        "amount": "0.22",
                        "state": "paid",
                        "paid_at": "2024-02-15T00:00:00Z",
                        "position": "10.0",
                        "rate": "0.22",
                        "withholding": "0.00"
                    }
                ],
                "total_dividends": "123.45",
                "count": 25
            }
        }
    """
    try:
        # Ensure authenticated
        session_mgr = get_session_manager()
        if not await session_mgr.ensure_authenticated():
            return {"result": {"error": "Authentication required", "status": "error"}}

        # Apply rate limiting
        rate_limiter = get_rate_limiter()
        await rate_limiter.acquire()

        # Get dividend data
        loop = asyncio.get_event_loop()
        dividends = await loop.run_in_executor(None, rh.account.get_dividends)

        # Validate response
        if not dividends or not isinstance(dividends, list):
            dividends = []

        # Process dividend data
        processed_dividends = []
        total_amount = 0.0

        for dividend in dividends:
            # Extract relevant fields
            processed = {
                "id": dividend.get("id"),
                "amount": dividend.get("amount"),
                "state": dividend.get("state"),
                "paid_at": dividend.get("paid_at"),
                "position": dividend.get("position"),
                "rate": dividend.get("rate"),
                "withholding": dividend.get("withholding"),
                "instrument_id": dividend.get("instrument"),
                "account_id": dividend.get("account"),
                "record_date": dividend.get("record_date"),
                "payable_date": dividend.get("payable_date"),
            }

            # Get symbol from instrument URL if available
            instrument_url = dividend.get("instrument")
            if instrument_url:
                try:
                    instrument_data = await loop.run_in_executor(
                        None, rh.stocks.get_instrument_by_url, instrument_url
                    )
                    if instrument_data and isinstance(instrument_data, dict):
                        processed["symbol"] = instrument_data.get("symbol")
                        processed["name"] = instrument_data.get("simple_name")
                except Exception as e:
                    logger.warning(f"Failed to get instrument data: {e}")

            # Calculate total for paid dividends
            if dividend.get("state") == "paid" and dividend.get("amount"):
                with contextlib.suppress(ValueError, TypeError):
                    total_amount += float(dividend["amount"])

            processed_dividends.append(processed)

        return {
            "result": {
                "dividends": processed_dividends,
                "total_dividends": f"{total_amount:.2f}",
                "count": len(processed_dividends),
                "status": "success",
            }
        }

    except Exception as e:
        logger.error(f"Failed to get dividends: {e}")
        return {"result": {"error": str(e), "status": "error"}}


@handle_robin_stocks_errors
async def get_total_dividends() -> dict[str, Any]:
    """Get total dividends received across all time.

    Provides a summary of all dividend payments including:
    - Total amount received
    - Number of payments
    - Date range

    Returns:
        JSON object with dividend totals in "result" field:
        {
            "result": {
                "total_amount": "1234.56",
                "payment_count": 45,
                "first_payment_date": "2020-01-15T00:00:00Z",
                "last_payment_date": "2024-12-15T00:00:00Z",
                "by_year": {
                    "2024": "234.56",
                    "2023": "456.78"
                }
            }
        }
    """
    try:
        # Ensure authenticated
        session_mgr = get_session_manager()
        if not await session_mgr.ensure_authenticated():
            return {"result": {"error": "Authentication required", "status": "error"}}

        # Apply rate limiting
        rate_limiter = get_rate_limiter()
        await rate_limiter.acquire()

        # Use robin_stocks built-in function
        loop = asyncio.get_event_loop()
        total = await loop.run_in_executor(None, rh.account.get_total_dividends)

        # Also get detailed dividends for additional stats
        dividends = await loop.run_in_executor(None, rh.account.get_dividends)

        # Calculate additional statistics
        by_year: dict[str, float] = {}
        first_date = None
        last_date = None
        paid_count = 0

        if dividends and isinstance(dividends, list):
            for dividend in dividends:
                if dividend.get("state") == "paid" and dividend.get("paid_at"):
                    paid_count += 1
                    paid_date = dividend["paid_at"]
                    year = paid_date[:4] if paid_date else None

                    if year:
                        amount = float(dividend.get("amount", 0))
                        by_year[year] = by_year.get(year, 0) + amount

                    # Track date range
                    if not first_date or paid_date < first_date:
                        first_date = paid_date
                    if not last_date or paid_date > last_date:
                        last_date = paid_date

        # Format by_year totals
        by_year_formatted = {
            year: f"{amount:.2f}"
            for year, amount in sorted(by_year.items(), reverse=True)
        }

        return {
            "result": {
                "total_amount": total if total else "0.00",
                "payment_count": paid_count,
                "first_payment_date": first_date,
                "last_payment_date": last_date,
                "by_year": by_year_formatted,
                "status": "success",
            }
        }

    except Exception as e:
        logger.error(f"Failed to get total dividends: {e}")
        return {"result": {"error": str(e), "status": "error"}}


@handle_robin_stocks_errors
async def get_dividends_by_instrument(symbol: str) -> dict[str, Any]:
    """Get dividend history for a specific stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "MSFT")

    Returns:
        JSON object with dividend history for the symbol in "result" field:
        {
            "result": {
                "symbol": "AAPL",
                "dividends": [
                    {
                        "amount": "0.22",
                        "paid_at": "2024-02-15T00:00:00Z",
                        "rate": "0.22",
                        "position": "10.0"
                    }
                ],
                "total_amount": "8.80",
                "count": 4
            }
        }
    """
    try:
        # Validate input
        if not symbol or not isinstance(symbol, str):
            return {
                "result": {"error": "Symbol parameter is required", "status": "error"}
            }

        symbol = symbol.upper().strip()

        # Ensure authenticated
        session_mgr = get_session_manager()
        if not await session_mgr.ensure_authenticated():
            return {"result": {"error": "Authentication required", "status": "error"}}

        # Apply rate limiting
        rate_limiter = get_rate_limiter()
        await rate_limiter.acquire()

        # Get dividends by instrument
        loop = asyncio.get_event_loop()
        dividends = await loop.run_in_executor(
            None, rh.account.get_dividends_by_instrument, symbol
        )

        # Process dividend data
        processed_dividends = []
        total_amount = 0.0

        if dividends and isinstance(dividends, list):
            for dividend in dividends:
                processed = {
                    "id": dividend.get("id"),
                    "amount": dividend.get("amount"),
                    "state": dividend.get("state"),
                    "paid_at": dividend.get("paid_at"),
                    "position": dividend.get("position"),
                    "rate": dividend.get("rate"),
                    "withholding": dividend.get("withholding"),
                    "record_date": dividend.get("record_date"),
                    "payable_date": dividend.get("payable_date"),
                }

                # Calculate total for paid dividends
                if dividend.get("state") == "paid" and dividend.get("amount"):
                    with contextlib.suppress(ValueError, TypeError):
                        total_amount += float(dividend["amount"])

                processed_dividends.append(processed)

        return {
            "result": {
                "symbol": symbol,
                "dividends": processed_dividends,
                "total_amount": f"{total_amount:.2f}",
                "count": len(processed_dividends),
                "status": "success",
            }
        }

    except Exception as e:
        logger.error(f"Failed to get dividends for {symbol}: {e}")
        return {"result": {"error": str(e), "status": "error"}}


@handle_robin_stocks_errors
async def get_interest_payments() -> dict[str, Any]:
    """Get interest payment history from cash management.

    Returns history of interest payments from:
    - Cash management accounts
    - Money market funds
    - Other interest-bearing accounts

    Returns:
        JSON object with interest payment history in "result" field:
        {
            "result": {
                "interest_payments": [
                    {
                        "amount": "1.23",
                        "paid_at": "2024-12-01T00:00:00Z",
                        "type": "cash_management",
                        "rate": "0.50"
                    }
                ],
                "total_interest": "45.67",
                "count": 12
            }
        }
    """
    try:
        # Ensure authenticated
        session_mgr = get_session_manager()
        if not await session_mgr.ensure_authenticated():
            return {"result": {"error": "Authentication required", "status": "error"}}

        # Apply rate limiting
        rate_limiter = get_rate_limiter()
        await rate_limiter.acquire()

        # Get interest payments
        loop = asyncio.get_event_loop()
        interest_payments = await loop.run_in_executor(
            None, rh.account.get_interest_payments
        )

        # Process interest payment data
        processed_payments = []
        total_amount = 0.0

        if interest_payments and isinstance(interest_payments, list):
            for payment in interest_payments:
                processed = {
                    "id": payment.get("id"),
                    "amount": payment.get("amount"),
                    "paid_at": payment.get("paid_at"),
                    "type": payment.get("type", "cash_management"),
                    "rate": payment.get("rate"),
                    "state": payment.get("state"),
                    "created_at": payment.get("created_at"),
                }

                # Calculate total for paid interest
                if payment.get("state") == "paid" and payment.get("amount"):
                    with contextlib.suppress(ValueError, TypeError):
                        total_amount += float(payment["amount"])

                processed_payments.append(processed)

        return {
            "result": {
                "interest_payments": processed_payments,
                "total_interest": f"{total_amount:.2f}",
                "count": len(processed_payments),
                "status": "success",
            }
        }

    except Exception as e:
        logger.error(f"Failed to get interest payments: {e}")
        return {"result": {"error": str(e), "status": "error"}}


@handle_robin_stocks_errors
async def get_stock_loan_payments() -> dict[str, Any]:
    """Get stock loan payment history.

    Returns history of payments received from lending shares through
    the stock lending program (if enrolled).

    Returns:
        JSON object with stock loan payment history in "result" field:
        {
            "result": {
                "loan_payments": [
                    {
                        "amount": "0.45",
                        "paid_at": "2024-12-01T00:00:00Z",
                        "symbol": "AMC",
                        "shares_loaned": "100"
                    }
                ],
                "total_loan_income": "12.34",
                "count": 8
            }
        }
    """
    try:
        # Ensure authenticated
        session_mgr = get_session_manager()
        if not await session_mgr.ensure_authenticated():
            return {"result": {"error": "Authentication required", "status": "error"}}

        # Apply rate limiting
        rate_limiter = get_rate_limiter()
        await rate_limiter.acquire()

        # Get stock loan payments
        loop = asyncio.get_event_loop()
        loan_payments = await loop.run_in_executor(
            None, rh.account.get_stock_loan_payments
        )

        # Process loan payment data
        processed_payments = []
        total_amount = 0.0

        if loan_payments and isinstance(loan_payments, list):
            for payment in loan_payments:
                processed = {
                    "id": payment.get("id"),
                    "amount": payment.get("amount"),
                    "paid_at": payment.get("paid_at"),
                    "state": payment.get("state"),
                    "shares_loaned": payment.get("shares_loaned"),
                    "rate": payment.get("rate"),
                    "instrument_id": payment.get("instrument"),
                    "created_at": payment.get("created_at"),
                }

                # Get symbol from instrument URL if available
                instrument_url = payment.get("instrument")
                if instrument_url:
                    try:
                        instrument_data = await loop.run_in_executor(
                            None, rh.stocks.get_instrument_by_url, instrument_url
                        )
                        if instrument_data and isinstance(instrument_data, dict):
                            processed["symbol"] = instrument_data.get("symbol")
                            processed["name"] = instrument_data.get("simple_name")
                    except Exception as e:
                        logger.warning(f"Failed to get instrument data: {e}")

                # Calculate total for paid loans
                if payment.get("state") == "paid" and payment.get("amount"):
                    with contextlib.suppress(ValueError, TypeError):
                        total_amount += float(payment["amount"])

                processed_payments.append(processed)

        return {
            "result": {
                "loan_payments": processed_payments,
                "total_loan_income": f"{total_amount:.2f}",
                "count": len(processed_payments),
                "enrolled": len(processed_payments) > 0,
                "status": "success",
            }
        }

    except Exception as e:
        logger.error(f"Failed to get stock loan payments: {e}")
        return {"result": {"error": str(e), "status": "error"}}
