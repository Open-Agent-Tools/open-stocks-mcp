"""Robinhood account feature tools."""
from typing import Any

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.error_handling import handle_robin_stocks_errors
from open_stocks_mcp.tools.robinhood_margin_tools import get_margin_interest
from open_stocks_mcp.tools.robinhood_notification_tools import get_notifications
from open_stocks_mcp.tools.robinhood_referral_tools import get_referrals
from open_stocks_mcp.tools.robinhood_subscription_tools import get_subscription_fees


@handle_robin_stocks_errors
async def get_account_features() -> dict[str, Any]:
    """
    Get comprehensive account features and settings.

    This function retrieves a summary of all account features,
    including Gold membership, margin status, and available features.

    Returns:
        Dict containing account features:
        {
            "result": {
                "features": {
                    "gold_membership": {
                        "is_member": true,
                        "monthly_fee": "5.00",
                        "features": ["level_ii_data", "extended_hours", "margin"]
                    },
                    "margin": {
                        "enabled": true,
                        "buying_power": "25000.00",
                        "current_rate": "2.5%"
                    },
                    "notifications": {
                        "enabled": true,
                        "unread_count": 3
                    },
                    "referrals": {
                        "total_referrals": 5,
                        "completed_referrals": 3
                    }
                },
                "status": "success"
            }
        }
    """
    logger.info("Getting comprehensive account features")

    # Gather data from multiple sources
    features_data = {}

    errors = []

    # Get subscription info
    try:
        subscription_result = await get_subscription_fees()
        if subscription_result["result"]["status"] == "success":
            features_data["gold_membership"] = {
                "is_member": subscription_result["result"]["is_gold_member"],
                "monthly_fee": subscription_result["result"]["monthly_fee"],
                "features": ["level_ii_data", "extended_hours", "margin"]
                if subscription_result["result"]["is_gold_member"]
                else [],
            }
    except Exception as e:
        logger.error(f"Error gathering subscription features: {e}")
        errors.append(f"subscription: {e}")

    # Get margin info
    try:
        margin_result = await get_margin_interest()
        if margin_result["result"]["status"] == "success":
            features_data["margin"] = {
                "enabled": True,
                "current_rate": margin_result["result"]["current_rate"],
                "total_charges": margin_result["result"]["total_charges"],
            }
    except Exception as e:
        logger.error(f"Error gathering margin features: {e}")
        errors.append(f"margin: {e}")

    # Get notifications info
    try:
        notifications_result = await get_notifications(count=5)
        if notifications_result["result"]["status"] == "success":
            features_data["notifications"] = {
                "enabled": True,
                "unread_count": notifications_result["result"]["unread_count"],
                "total_notifications": notifications_result["result"][
                    "total_notifications"
                ],
            }
    except Exception as e:
        logger.error(f"Error gathering notifications features: {e}")
        errors.append(f"notifications: {e}")

    # Get referrals info
    try:
        referrals_result = await get_referrals()
        if referrals_result["result"]["status"] == "success":
            features_data["referrals"] = {
                "total_referrals": referrals_result["result"]["total_referrals"],
                "completed_referrals": referrals_result["result"][
                    "completed_referrals"
                ],
                "total_rewards": referrals_result["result"]["total_rewards"],
            }
    except Exception as e:
        logger.error(f"Error gathering referrals features: {e}")
        errors.append(f"referrals: {e}")

    if errors:
        logger.warning(f"Partial success gathering account features: {errors}")
        return {
            "result": {
                "features": features_data,
                "error": f"Error gathering some account features: {'; '.join(errors)}",
                "status": "partial_success",
            }
        }
    else:
        logger.info("Successfully gathered account features")
        return {"result": {"features": features_data, "status": "success"}}
