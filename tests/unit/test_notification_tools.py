"""Unit tests for account features and notification tools."""

from typing import Any
from unittest.mock import patch

import pytest

from open_stocks_mcp.tools.robinhood_account_features_tools import (
    get_account_features,
    get_latest_notification,
    get_margin_calls,
    get_margin_interest,
    get_notifications,
    get_referrals,
    get_subscription_fees,
)
from open_stocks_mcp.tools.robinhood_user_profile_tools import get_account_settings


class TestNotifications:
    """Test notifications functionality."""

    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_notifications_success(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test successful notifications retrieval."""
        mock_execute_with_retry.return_value = [
            {
                "id": "notif_1",
                "title": "Order Executed",
                "message": "Your order for AAPL has been executed",
                "time": "2024-07-09T10:30:00Z",
                "type": "order_confirmation",
                "read": False,
            },
            {
                "id": "notif_2",
                "title": "Market Update",
                "message": "Market opened for trading",
                "time": "2024-07-09T09:30:00Z",
                "type": "market_update",
                "read": True,
            },
            {
                "id": "notif_3",
                "title": "Account Alert",
                "message": "Low buying power",
                "time": "2024-07-08T16:00:00Z",
                "type": "account_alert",
                "read": False,
            },
        ]

        result = await get_notifications(count=3)

        assert "result" in result
        assert result["result"]["total_notifications"] == 3
        assert result["result"]["unread_count"] == 2
        assert len(result["result"]["notifications"]) == 3
        assert result["result"]["notifications"][0]["title"] == "Order Executed"
        assert result["result"]["notifications"][0]["read"] is False
        assert result["result"]["notifications"][1]["read"] is True
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_notifications_no_data(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test notifications when no data is available."""
        mock_execute_with_retry.return_value = None

        result = await get_notifications()

        assert "result" in result
        assert result["result"]["total_notifications"] == 0
        assert result["result"]["unread_count"] == 0
        assert result["result"]["notifications"] == []
        assert result["result"]["status"] == "no_data"
        assert "No notifications found" in result["result"]["message"]

    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_notifications_empty_list(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test notifications with empty list."""
        mock_execute_with_retry.return_value = []

        result = await get_notifications()

        assert "result" in result
        assert result["result"]["total_notifications"] == 0
        assert result["result"]["unread_count"] == 0
        assert result["result"]["notifications"] == []
        assert result["result"]["status"] == "no_data"

    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_notifications_count_limit(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test notifications with count limit."""
        mock_execute_with_retry.return_value = [
            {"id": f"notif_{i}", "title": f"Notification {i}", "read": False}
            for i in range(10)
        ]

        result = await get_notifications(count=5)

        assert "result" in result
        assert result["result"]["total_notifications"] == 5
        assert result["result"]["unread_count"] == 5
        assert len(result["result"]["notifications"]) == 5
        assert result["result"]["status"] == "success"

    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_notifications_mixed_read_status(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test notifications with mixed read status."""
        mock_execute_with_retry.return_value = [
            {"id": "notif_1", "title": "Read Notification", "read": True},
            {"id": "notif_2", "title": "Unread Notification", "read": False},
            {"id": "notif_3", "title": "Default Read", "read": True},
            {"id": "notif_4", "title": "Missing Read Field"},  # No read field
        ]

        result = await get_notifications()

        assert "result" in result
        assert result["result"]["total_notifications"] == 4
        assert (
            result["result"]["unread_count"] == 1
        )  # Only the False one (missing defaults to True)
        assert result["result"]["status"] == "success"


class TestLatestNotification:
    """Test latest notification functionality."""

    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_latest_notification_success(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test successful latest notification retrieval."""
        mock_execute_with_retry.return_value = {
            "id": "latest_notif",
            "title": "Trade Confirmation",
            "message": "Your TSLA order has been filled",
            "time": "2024-07-09T15:45:00Z",
            "type": "order_confirmation",
            "read": False,
        }

        result = await get_latest_notification()

        assert "result" in result
        assert result["result"]["has_notification"] is True
        assert result["result"]["notification"]["title"] == "Trade Confirmation"
        assert result["result"]["notification"]["type"] == "order_confirmation"
        assert result["result"]["notification"]["read"] is False
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_latest_notification_no_data(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test latest notification when no data is available."""
        mock_execute_with_retry.return_value = None

        result = await get_latest_notification()

        assert "result" in result
        assert result["result"]["has_notification"] is False
        assert result["result"]["notification"] is None
        assert result["result"]["status"] == "no_data"
        assert "No notifications found" in result["result"]["message"]


class TestMarginCalls:
    """Test margin calls functionality."""

    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_margin_calls_success(self, mock_execute_with_retry: Any) -> None:
        """Test successful margin calls retrieval."""
        mock_execute_with_retry.return_value = [
            {
                "id": "margin_call_1",
                "amount": "2500.00",
                "due_date": "2024-07-15",
                "type": "maintenance",
                "status": "active",
            },
            {
                "id": "margin_call_2",
                "amount": "1000.00",
                "due_date": "2024-07-12",
                "type": "house",
                "status": "resolved",
            },
        ]

        result = await get_margin_calls()

        assert "result" in result
        assert result["result"]["total_calls"] == 2
        assert result["result"]["total_amount_due"] == "3500.00"
        assert result["result"]["has_active_calls"] is True
        assert len(result["result"]["margin_calls"]) == 2
        assert result["result"]["margin_calls"][0]["status"] == "active"
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_margin_calls_no_data(self, mock_execute_with_retry: Any) -> None:
        """Test margin calls when no data is available."""
        mock_execute_with_retry.return_value = None

        result = await get_margin_calls()

        assert "result" in result
        assert result["result"]["total_calls"] == 0
        assert result["result"]["total_amount_due"] == "0.00"
        assert result["result"]["has_active_calls"] is False
        assert result["result"]["margin_calls"] == []
        assert result["result"]["status"] == "no_data"
        assert "No margin calls found" in result["result"]["message"]

    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_margin_calls_no_active_calls(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test margin calls with no active calls."""
        mock_execute_with_retry.return_value = [
            {
                "id": "margin_call_1",
                "amount": "1500.00",
                "due_date": "2024-06-15",
                "type": "maintenance",
                "status": "resolved",
            },
            {
                "id": "margin_call_2",
                "amount": "800.00",
                "due_date": "2024-05-20",
                "type": "house",
                "status": "resolved",
            },
        ]

        result = await get_margin_calls()

        assert "result" in result
        assert result["result"]["total_calls"] == 2
        assert result["result"]["total_amount_due"] == "2300.00"
        assert result["result"]["has_active_calls"] is False
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_margin_calls_invalid_amounts(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test margin calls with invalid amount values."""
        mock_execute_with_retry.return_value = [
            {
                "id": "margin_call_1",
                "amount": "invalid",
                "status": "active",
            },
            {
                "id": "margin_call_2",
                "amount": None,
                "status": "active",
            },
            {
                "id": "margin_call_3",
                "amount": "1000.00",
                "status": "active",
            },
        ]

        result = await get_margin_calls()

        assert "result" in result
        assert result["result"]["total_calls"] == 3
        assert result["result"]["total_amount_due"] == "1000.00"  # Only valid amount
        assert result["result"]["has_active_calls"] is True
        assert result["result"]["status"] == "success"


class TestMarginInterest:
    """Test margin interest functionality."""

    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_margin_interest_success(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test successful margin interest retrieval."""
        mock_execute_with_retry.return_value = [
            {
                "date": "2024-07-01",
                "amount": "12.50",
                "rate": "2.5%",
                "balance": "5000.00",
            },
            {
                "date": "2024-06-01",
                "amount": "15.75",
                "rate": "2.5%",
                "balance": "6300.00",
            },
            {
                "date": "2024-05-01",
                "amount": "18.25",
                "rate": "2.8%",
                "balance": "6500.00",
            },
        ]

        result = await get_margin_interest()

        assert "result" in result
        assert result["result"]["charges_count"] == 3
        assert result["result"]["total_charges"] == "46.50"  # 12.50 + 15.75 + 18.25
        assert result["result"]["current_rate"] == "2.5%"  # From first charge
        assert len(result["result"]["interest_charges"]) == 3
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_margin_interest_no_data(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test margin interest when no data is available."""
        mock_execute_with_retry.return_value = None

        result = await get_margin_interest()

        assert "result" in result
        assert result["result"]["charges_count"] == 0
        assert result["result"]["total_charges"] == "0.00"
        assert result["result"]["current_rate"] == "N/A"
        assert result["result"]["interest_charges"] == []
        assert result["result"]["status"] == "no_data"
        assert "No margin interest charges found" in result["result"]["message"]

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_margin_interest_invalid_amounts(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test margin interest with invalid amount values."""
        mock_execute_with_retry.return_value = [
            {
                "date": "2024-07-01",
                "amount": "invalid",
                "rate": "2.5%",
            },
            {
                "date": "2024-06-01",
                "amount": "10.00",
                "rate": "2.5%",
            },
        ]

        result = await get_margin_interest()

        assert "result" in result
        assert result["result"]["charges_count"] == 2
        assert result["result"]["total_charges"] == "10.00"  # Only valid amount
        assert result["result"]["current_rate"] == "2.5%"
        assert result["result"]["status"] == "success"


class TestSubscriptionFees:
    """Test subscription fees functionality."""

    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_subscription_fees_success(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test successful subscription fees retrieval."""
        mock_execute_with_retry.return_value = [
            {
                "date": "2024-07-01",
                "amount": "5.00",
                "type": "gold_subscription",
                "status": "paid",
            },
            {
                "date": "2024-06-01",
                "amount": "5.00",
                "type": "gold_subscription",
                "status": "paid",
            },
            {
                "date": "2024-05-01",
                "amount": "5.00",
                "type": "gold_subscription",
                "status": "paid",
            },
        ]

        result = await get_subscription_fees()

        assert "result" in result
        assert result["result"]["fees_count"] == 3
        assert result["result"]["total_fees"] == "15.00"
        assert result["result"]["monthly_fee"] == "5.00"
        assert result["result"]["is_gold_member"] is True
        assert len(result["result"]["subscription_fees"]) == 3
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_subscription_fees_no_data(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test subscription fees when no data is available."""
        mock_execute_with_retry.return_value = None

        result = await get_subscription_fees()

        assert "result" in result
        assert result["result"]["fees_count"] == 0
        assert result["result"]["total_fees"] == "0.00"
        assert result["result"]["monthly_fee"] == "0.00"
        assert result["result"]["is_gold_member"] is False
        assert result["result"]["subscription_fees"] == []
        assert result["result"]["status"] == "no_data"
        assert "No subscription fees found" in result["result"]["message"]

    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_subscription_fees_non_gold(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test subscription fees for non-Gold member."""
        mock_execute_with_retry.return_value = [
            {
                "date": "2024-07-01",
                "amount": "1.00",
                "type": "other_fee",
                "status": "paid",
            }
        ]

        result = await get_subscription_fees()

        assert "result" in result
        assert result["result"]["fees_count"] == 1
        assert result["result"]["total_fees"] == "1.00"
        assert result["result"]["monthly_fee"] == "0.00"  # No gold subscription
        assert result["result"]["is_gold_member"] is False
        assert result["result"]["status"] == "success"


class TestReferrals:
    """Test referrals functionality."""

    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_referrals_success_dict_format(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test successful referrals retrieval with dict format."""
        mock_execute_with_retry.return_value = {
            "referral_code": "ABC123",
            "referrals": [
                {
                    "id": "ref_1",
                    "referred_user": "user_1",
                    "date": "2024-07-01",
                    "status": "completed",
                    "reward": "10.00",
                    "reward_type": "stock",
                },
                {
                    "id": "ref_2",
                    "referred_user": "user_2",
                    "date": "2024-06-15",
                    "status": "pending",
                    "reward": "10.00",
                    "reward_type": "stock",
                },
                {
                    "id": "ref_3",
                    "referred_user": "user_3",
                    "date": "2024-06-01",
                    "status": "completed",
                    "reward": "15.00",
                    "reward_type": "cash",
                },
            ],
        }

        result = await get_referrals()

        assert "result" in result
        assert result["result"]["total_referrals"] == 3
        assert result["result"]["completed_referrals"] == 2
        assert result["result"]["total_rewards"] == "25.00"  # 10.00 + 15.00
        assert result["result"]["referral_code"] == "ABC123"
        assert len(result["result"]["referrals"]) == 3
        assert result["result"]["status"] == "success"

    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_referrals_success_list_format(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test successful referrals retrieval with list format."""
        mock_execute_with_retry.return_value = [
            {
                "id": "ref_1",
                "referred_user": "user_1",
                "date": "2024-07-01",
                "status": "completed",
                "reward": "12.50",
                "reward_type": "stock",
            },
            {
                "id": "ref_2",
                "referred_user": "user_2",
                "date": "2024-06-15",
                "status": "completed",
                "reward": "12.50",
                "reward_type": "stock",
            },
        ]

        result = await get_referrals()

        assert "result" in result
        assert result["result"]["total_referrals"] == 2
        assert result["result"]["completed_referrals"] == 2
        assert result["result"]["total_rewards"] == "25.00"
        assert result["result"]["referral_code"] is None  # No code in list format
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_referrals_no_data(self, mock_execute_with_retry: Any) -> None:
        """Test referrals when no data is available."""
        mock_execute_with_retry.return_value = None

        result = await get_referrals()

        assert "result" in result
        assert result["result"]["total_referrals"] == 0
        assert result["result"]["completed_referrals"] == 0
        assert result["result"]["total_rewards"] == "0.00"
        assert result["result"]["referral_code"] is None
        assert result["result"]["referrals"] == []
        assert result["result"]["status"] == "no_data"
        assert "No referrals found" in result["result"]["message"]

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_referrals_invalid_rewards(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test referrals with invalid reward values."""
        mock_execute_with_retry.return_value = [
            {
                "id": "ref_1",
                "status": "completed",
                "reward": "invalid",
            },
            {
                "id": "ref_2",
                "status": "completed",
                "reward": "10.00",
            },
            {
                "id": "ref_3",
                "status": "pending",
                "reward": "5.00",
            },
        ]

        result = await get_referrals()

        assert "result" in result
        assert result["result"]["total_referrals"] == 3
        assert result["result"]["completed_referrals"] == 2
        assert (
            result["result"]["total_rewards"] == "10.00"
        )  # Only valid completed reward
        assert result["result"]["status"] == "success"


class TestAccountFeatures:
    """Test account features functionality."""

    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.get_referrals")
    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.get_notifications")
    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.get_margin_interest")
    @patch(
        "open_stocks_mcp.tools.robinhood_account_features_tools.get_subscription_fees"
    )
    @pytest.mark.asyncio
    async def test_get_account_features_success(
        self,
        mock_subscription_fees: Any,
        mock_margin_interest: Any,
        mock_notifications: Any,
        mock_referrals: Any,
    ) -> None:
        """Test successful account features retrieval."""
        mock_subscription_fees.return_value = {
            "result": {
                "status": "success",
                "is_gold_member": True,
                "monthly_fee": "5.00",
            }
        }

        mock_margin_interest.return_value = {
            "result": {
                "status": "success",
                "current_rate": "2.5%",
                "total_charges": "125.50",
            }
        }

        mock_notifications.return_value = {
            "result": {
                "status": "success",
                "unread_count": 3,
                "total_notifications": 15,
            }
        }

        mock_referrals.return_value = {
            "result": {
                "status": "success",
                "total_referrals": 5,
                "completed_referrals": 3,
                "total_rewards": "45.00",
            }
        }

        result = await get_account_features()

        assert "result" in result
        assert result["result"]["status"] == "success"
        assert "features" in result["result"]

        features = result["result"]["features"]
        assert features["gold_membership"]["is_member"] is True
        assert features["gold_membership"]["monthly_fee"] == "5.00"
        assert len(features["gold_membership"]["features"]) > 0

        assert features["margin"]["enabled"] is True
        assert features["margin"]["current_rate"] == "2.5%"
        assert features["margin"]["total_charges"] == "125.50"

        assert features["notifications"]["enabled"] is True
        assert features["notifications"]["unread_count"] == 3
        assert features["notifications"]["total_notifications"] == 15

        assert features["referrals"]["total_referrals"] == 5
        assert features["referrals"]["completed_referrals"] == 3
        assert features["referrals"]["total_rewards"] == "45.00"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.get_referrals")
    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.get_notifications")
    @patch("open_stocks_mcp.tools.robinhood_account_features_tools.get_margin_interest")
    @patch(
        "open_stocks_mcp.tools.robinhood_account_features_tools.get_subscription_fees"
    )
    @pytest.mark.asyncio
    async def test_get_account_features_partial_errors(
        self,
        mock_subscription_fees: Any,
        mock_margin_interest: Any,
        mock_notifications: Any,
        mock_referrals: Any,
    ) -> None:
        """Test account features with some errors."""
        mock_subscription_fees.return_value = {
            "result": {
                "status": "success",
                "is_gold_member": False,
                "monthly_fee": "0.00",
            }
        }

        mock_margin_interest.side_effect = Exception("Margin API Error")
        mock_notifications.side_effect = Exception("Notifications API Error")

        mock_referrals.return_value = {
            "result": {
                "status": "success",
                "total_referrals": 2,
                "completed_referrals": 1,
                "total_rewards": "15.00",
            }
        }

        result = await get_account_features()

        assert "result" in result
        assert result["result"]["status"] == "partial_success"
        assert "error" in result["result"]
        assert "features" in result["result"]

        features = result["result"]["features"]
        assert features["gold_membership"]["is_member"] is False
        assert features["referrals"]["total_referrals"] == 2
        # margin and notifications should be missing due to errors


class TestAccountSettings:
    """Test account settings functionality."""

    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_account_profile")
    @pytest.mark.asyncio
    async def test_get_account_settings_success(
        self, mock_get_account_profile: Any
    ) -> None:
        """Test successful account settings retrieval."""
        mock_get_account_profile.return_value = {
            "result": {
                "status": "success",
                "account_profile": {
                    "instant_eligibility": True,
                    "margin_balances": {
                        "day_trade_buying_power": "25000.00",
                        "overnight_buying_power": "12500.00",
                    },
                    "option_level": "2",
                    "crypto_enabled": True,
                    "dividend_reinvestment": False,
                    "extended_hours_trading": True,
                    "day_trade_count": 1,
                    "cash_management_enabled": True,
                    "max_ach_early_access_amount": "1000.00",
                },
            }
        }

        result = await get_account_settings()

        assert "result" in result
        assert result["result"]["status"] == "success"
        assert "settings" in result["result"]

        settings = result["result"]["settings"]
        assert settings["instant_settlement"] is True
        assert settings["margin_enabled"] is True
        assert settings["options_enabled"] is True
        assert settings["crypto_enabled"] is True
        assert settings["dividend_reinvestment"] is False
        assert settings["extended_hours_trading"] is True
        assert settings["day_trade_count"] == 1
        assert settings["cash_management_enabled"] is True
        assert settings["max_ach_early_access"] == "1000.00"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_account_profile")
    @pytest.mark.asyncio
    async def test_get_account_settings_no_data(
        self, mock_get_account_profile: Any
    ) -> None:
        """Test account settings when no data is available."""
        mock_get_account_profile.return_value = {
            "result": {"status": "no_data", "error": "No account profile data found"}
        }

        result = await get_account_settings()

        assert "result" in result
        assert result["result"]["status"] == "error"
        assert result["result"]["settings"] == {}
        assert "Could not retrieve account settings" in result["result"]["error"]

    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_account_profile")
    @pytest.mark.asyncio
    async def test_get_account_settings_minimal_data(
        self, mock_get_account_profile: Any
    ) -> None:
        """Test account settings with minimal data."""
        mock_get_account_profile.return_value = {
            "result": {
                "status": "success",
                "account_profile": {
                    "instant_eligibility": False,
                    "option_level": "0",
                },
            }
        }

        result = await get_account_settings()

        assert "result" in result
        assert result["result"]["status"] == "success"

        settings = result["result"]["settings"]
        assert settings["instant_settlement"] is False
        assert settings["margin_enabled"] is False  # No margin_balances
        assert settings["options_enabled"] is False  # option_level is "0"
        assert settings["crypto_enabled"] is False  # Default value
        assert settings["dividend_reinvestment"] is False  # Default value

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_account_profile")
    @pytest.mark.asyncio
    async def test_get_account_settings_exception(
        self, mock_get_account_profile: Any
    ) -> None:
        """Test account settings with exception."""
        mock_get_account_profile.side_effect = Exception("API Error")

        result = await get_account_settings()

        assert "result" in result
        assert result["result"]["status"] == "error"
        assert result["result"]["settings"] == {}
        assert "Error retrieving account settings" in result["result"]["error"]
