"""Robinhood account feature tools."""
import contextlib
from typing import Any

import robin_stocks.robinhood as rh

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.error_handling import (
    execute_with_retry,
    handle_robin_stocks_errors,
)


@handle_robin_stocks_errors
async def get_margin_calls() -> dict[str, Any]:
    """
    Get margin call information.

    This function retrieves information about any active margin calls,
    including amounts due and deadlines.

    Returns:
        Dict containing margin call information:
        {
            "result": {
                "margin_calls": [
                    {
                        "id": "margin_call_id",
                        "amount": "2500.00",
                        "due_date": "2024-01-20",
                        "type": "maintenance",
                        "status": "active"
                    },
                    ...
                ],
                "total_calls": 1,
                "total_amount_due": "2500.00",
                "has_active_calls": true,
                "status": "success"
            }
        }
    """
    logger.info("Getting margin call information")

    # Get margin calls
    margin_calls_data = await execute_with_retry(
        func=rh.get_margin_calls, func_name="get_margin_calls", max_retries=3
    )

    if not margin_calls_data:
        logger.info("No margin calls found")
        return {
            "result": {
                "margin_calls": [],
                "total_calls": 0,
                "total_amount_due": "0.00",
                "has_active_calls": False,
                "message": "No margin calls found",
                "status": "no_data",
            }
        }

    # Process margin calls
    processed_calls = []
    total_amount_due = 0.0
    has_active_calls = False

    if isinstance(margin_calls_data, list):
        for call in margin_calls_data:
            if isinstance(call, dict):
                processed_calls.append(call)

                # Calculate total amount due
                amount = call.get("amount", "0")
                if amount:
                    with contextlib.suppress(ValueError, TypeError):
                        total_amount_due += float(amount)

                # Check if call is active
                if call.get("status") == "active":
                    has_active_calls = True

    total_calls = len(processed_calls)

    logger.info(
        f"Found {total_calls} margin calls (total due: ${total_amount_due:.2f})"
    )

    return {
        "result": {
            "margin_calls": processed_calls,
            "total_calls": total_calls,
            "total_amount_due": f"{total_amount_due:.2f}",
            "has_active_calls": has_active_calls,
            "status": "success",
        }
    }

@handle_robin_stocks_errors
async def get_margin_interest() -> dict[str, Any]:
    """
    Get margin interest charges and rates.

    This function retrieves information about margin interest charges,
    including rates and historical charges.

    Returns:
        Dict containing margin interest information:
        {
            "result": {
                "interest_charges": [
                    {
                        "date": "2024-01-15",
                        "amount": "12.50",
                        "rate": "2.5%",
                        "balance": "5000.00"
                    },
                    ...
                ],
                "current_rate": "2.5%",
                "total_charges": "125.00",
                "charges_count": 10,
                "status": "success"
            }
        }
    """
    logger.info("Getting margin interest information")

    # Get margin interest
    interest_data = await execute_with_retry(
        func=rh.get_margin_interest, func_name="get_margin_interest", max_retries=3
    )

    if not interest_data:
        logger.info("No margin interest charges found")
        return {
            "result": {
                "interest_charges": [],
                "current_rate": "N/A",
                "total_charges": "0.00",
                "charges_count": 0,
                "message": "No margin interest charges found",
                "status": "no_data",
            }
        }

    # Process interest charges
    processed_charges = []
    total_charges = 0.0
    current_rate = "N/A"

    if isinstance(interest_data, list):
        for charge in interest_data:
            if isinstance(charge, dict):
                processed_charges.append(charge)

                # Sum total charges
                amount = charge.get("amount", "0")
                if amount:
                    with contextlib.suppress(ValueError, TypeError):
                        total_charges += float(amount)

                # Get current rate from latest charge
                if not current_rate or current_rate == "N/A":
                    rate = charge.get("rate")
                    if rate:
                        current_rate = rate

    charges_count = len(processed_charges)

    logger.info(
        f"Found {charges_count} margin interest charges (total: ${total_charges:.2f})"
    )

    return {
        "result": {
            "interest_charges": processed_charges,
            "current_rate": current_rate,
            "total_charges": f"{total_charges:.2f}",
            "charges_count": charges_count,
            "status": "success",
        }
    }
