"""Robinhood account feature tools."""
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
