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
async def get_subscription_fees() -> dict[str, Any]:
    """
    Get Robinhood Gold subscription fees.

    This function retrieves information about Robinhood Gold subscription
    fees and billing history.

    Returns:
        Dict containing subscription fee information:
        {
            "result": {
                "subscription_fees": [
                    {
                        "date": "2024-01-01",
                        "amount": "5.00",
                        "type": "gold_subscription",
                        "status": "paid"
                    },
                    ...
                ],
                "monthly_fee": "5.00",
                "total_fees": "60.00",
                "fees_count": 12,
                "is_gold_member": true,
                "status": "success"
            }
        }
    """
    logger.info("Getting subscription fees")

    # Get subscription fees
    fees_data = await execute_with_retry(
        func=rh.get_subscription_fees, func_name="get_subscription_fees", max_retries=3
    )

    if not fees_data:
        logger.info("No subscription fees found")
        return {
            "result": {
                "subscription_fees": [],
                "monthly_fee": "0.00",
                "total_fees": "0.00",
                "fees_count": 0,
                "is_gold_member": False,
                "message": "No subscription fees found",
                "status": "no_data",
            }
        }

    # Process subscription fees
    processed_fees = []
    total_fees = 0.0
    monthly_fee = "0.00"
    is_gold_member = False

    if isinstance(fees_data, list):
        for fee in fees_data:
            if isinstance(fee, dict):
                processed_fees.append(fee)

                # Sum total fees
                amount = fee.get("amount", "0")
                if amount:
                    with contextlib.suppress(ValueError, TypeError):
                        total_fees += float(amount)

                # Check if user is Gold member
                if fee.get("type") == "gold_subscription":
                    is_gold_member = True
                    if not monthly_fee or monthly_fee == "0.00":
                        monthly_fee = amount

    fees_count = len(processed_fees)

    logger.info(f"Found {fees_count} subscription fees (total: ${total_fees:.2f})")

    return {
        "result": {
            "subscription_fees": processed_fees,
            "monthly_fee": monthly_fee,
            "total_fees": f"{total_fees:.2f}",
            "fees_count": fees_count,
            "is_gold_member": is_gold_member,
            "status": "success",
        }
    }
