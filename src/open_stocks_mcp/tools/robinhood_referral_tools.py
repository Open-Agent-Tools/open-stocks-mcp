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
async def get_referrals() -> dict[str, Any]:
    """
    Get referral program information.

    This function retrieves information about the referral program,
    including referred users and rewards earned.

    Returns:
        Dict containing referral information:
        {
            "result": {
                "referrals": [
                    {
                        "id": "referral_id",
                        "referred_user": "user_id",
                        "date": "2024-01-10",
                        "status": "completed",
                        "reward": "10.00",
                        "reward_type": "stock"
                    },
                    ...
                ],
                "total_referrals": 5,
                "completed_referrals": 3,
                "total_rewards": "30.00",
                "referral_code": "ABC123",
                "status": "success"
            }
        }
    """
    logger.info("Getting referral information")

    # Get referrals
    referrals_data = await execute_with_retry(
        func=rh.get_referrals, func_name="get_referrals", max_retries=3
    )

    if not referrals_data:
        logger.info("No referrals found")
        return {
            "result": {
                "referrals": [],
                "total_referrals": 0,
                "completed_referrals": 0,
                "total_rewards": "0.00",
                "referral_code": None,
                "message": "No referrals found",
                "status": "no_data",
            }
        }

    # Process referrals
    processed_referrals = []
    completed_referrals = 0
    total_rewards = 0.0
    referral_code = None

    if isinstance(referrals_data, dict):
        # Handle case where referrals_data is a dict with referral info
        referral_code = referrals_data.get("referral_code")
        referrals_list = referrals_data.get("referrals", [])

        if isinstance(referrals_list, list):
            for referral in referrals_list:
                if isinstance(referral, dict):
                    processed_referrals.append(referral)

                    # Count completed referrals
                    if referral.get("status") == "completed":
                        completed_referrals += 1

                        # Sum rewards
                        reward = referral.get("reward", "0")
                        if reward:
                            with contextlib.suppress(ValueError, TypeError):
                                total_rewards += float(reward)

    elif isinstance(referrals_data, list):
        # Handle case where referrals_data is directly a list
        for referral in referrals_data:
            if isinstance(referral, dict):
                processed_referrals.append(referral)

                # Count completed referrals
                if referral.get("status") == "completed":
                    completed_referrals += 1

                    # Sum rewards
                    reward = referral.get("reward", "0")
                    if reward:
                        with contextlib.suppress(ValueError, TypeError):
                            total_rewards += float(reward)

    total_referrals = len(processed_referrals)

    logger.info(
        f"Found {total_referrals} referrals ({completed_referrals} completed, ${total_rewards:.2f} rewards)"
    )

    return {
        "result": {
            "referrals": processed_referrals,
            "total_referrals": total_referrals,
            "completed_referrals": completed_referrals,
            "total_rewards": f"{total_rewards:.2f}",
            "referral_code": referral_code,
            "status": "success",
        }
    }
