"""
Account Features & Notifications Tools for Robin Stocks MCP Server.

This module provides comprehensive account features and notifications including:
- Account notifications and alerts
- Margin account information and calls
- Subscription fees and Gold membership
- Referral program information
- Account-specific features and settings

All functions use Robin Stocks API with proper error handling and async support.
"""

import contextlib
from typing import Any

import robin_stocks.robinhood as rh

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.error_handling import (
    execute_with_retry,
    handle_robin_stocks_errors,
)


@handle_robin_stocks_errors
async def get_notifications(count: int | None = 20) -> dict[str, Any]:
    """
    Get account notifications and alerts.

    This function retrieves recent account notifications including
    order confirmations, account alerts, and system messages.

    Args:
        count: Number of notifications to retrieve (default: 20)

    Returns:
        Dict containing account notifications:
        {
            "result": {
                "notifications": [
                    {
                        "id": "notification_id",
                        "title": "Order Executed",
                        "message": "Your order for AAPL has been executed",
                        "time": "2024-01-15T10:30:00Z",
                        "type": "order_confirmation",
                        "read": false
                    },
                    ...
                ],
                "total_notifications": 15,
                "unread_count": 8,
                "status": "success"
            }
        }
    """
    logger.info(f"Getting {count} account notifications")

    # Get notifications
    notifications_data = await execute_with_retry(
        func=rh.get_notifications,
        func_name="get_notifications",
        max_retries=3,
        info=None,  # Get all fields
    )

    if not notifications_data:
        logger.warning("No notifications found")
        return {
            "result": {
                "notifications": [],
                "total_notifications": 0,
                "unread_count": 0,
                "message": "No notifications found",
                "status": "no_data",
            }
        }

    # Process notifications and count unread
    processed_notifications = []
    unread_count = 0

    if isinstance(notifications_data, list):
        # Limit to requested count
        limited_notifications = (
            notifications_data[:count] if count else notifications_data
        )

        for notification in limited_notifications:
            if isinstance(notification, dict):
                # Check if notification is unread
                if not notification.get("read", True):
                    unread_count += 1

                processed_notifications.append(notification)

    total_notifications = len(processed_notifications)

    logger.info(
        f"Retrieved {total_notifications} notifications ({unread_count} unread)"
    )

    return {
        "result": {
            "notifications": processed_notifications,
            "total_notifications": total_notifications,
            "unread_count": unread_count,
            "status": "success",
        }
    }


@handle_robin_stocks_errors
async def get_latest_notification() -> dict[str, Any]:
    """
    Get the most recent notification.

    This function retrieves the latest notification from the account.

    Returns:
        Dict containing the latest notification:
        {
            "result": {
                "notification": {
                    "id": "notification_id",
                    "title": "Order Executed",
                    "message": "Your order for AAPL has been executed",
                    "time": "2024-01-15T10:30:00Z",
                    "type": "order_confirmation",
                    "read": false
                },
                "has_notification": true,
                "status": "success"
            }
        }
    """
    logger.info("Getting latest notification")

    # Get latest notification
    notification_data = await execute_with_retry(
        func=rh.get_latest_notification,
        func_name="get_latest_notification",
        max_retries=3,
    )

    if not notification_data:
        logger.warning("No latest notification found")
        return {
            "result": {
                "notification": None,
                "has_notification": False,
                "message": "No notifications found",
                "status": "no_data",
            }
        }

    logger.info("Retrieved latest notification")

    return {
        "result": {
            "notification": notification_data,
            "has_notification": True,
            "status": "success",
        }
    }


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
