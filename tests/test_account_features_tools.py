"""
Tests for Account Features & Notifications Tools.

This module tests the account features and notifications functions including:
- Account notifications
- Margin calls and interest
- Subscription fees
- Referral information
- Comprehensive account features
"""

from unittest.mock import AsyncMock, Mock, patch

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


class TestAccountFeaturesTools:
    """Test suite for account features and notifications tools."""

    @pytest.fixture
    def mock_session_manager(self):
        """Mock session manager for testing."""
        mock_session = Mock()
        mock_session.is_authenticated.return_value = True
        mock_session.is_session_valid.return_value = True
        return mock_session

    @pytest.fixture
    def mock_rate_limiter(self):
        """Mock rate limiter for testing."""
        mock_limiter = Mock()
        mock_limiter.acquire = AsyncMock()
        return mock_limiter

    @pytest.fixture
    def sample_notifications(self):
        """Sample notifications data for testing."""
        return [
            {
                "id": "notification_1",
                "title": "Order Executed",
                "message": "Your order for AAPL has been executed",
                "time": "2024-01-15T10:30:00Z",
                "type": "order_confirmation",
                "read": False,
            },
            {
                "id": "notification_2",
                "title": "Dividend Received",
                "message": "You received a dividend payment",
                "time": "2024-01-14T09:00:00Z",
                "type": "dividend",
                "read": True,
            },
            {
                "id": "notification_3",
                "title": "Account Alert",
                "message": "Your account balance is low",
                "time": "2024-01-13T15:30:00Z",
                "type": "account_alert",
                "read": False,
            },
        ]

    @pytest.fixture
    def sample_margin_calls(self):
        """Sample margin calls data for testing."""
        return [
            {
                "id": "margin_call_1",
                "amount": "2500.00",
                "due_date": "2024-01-20",
                "type": "maintenance",
                "status": "active",
            },
            {
                "id": "margin_call_2",
                "amount": "1000.00",
                "due_date": "2024-01-18",
                "type": "initial",
                "status": "resolved",
            },
        ]

    @pytest.fixture
    def sample_margin_interest(self):
        """Sample margin interest data for testing."""
        return [
            {
                "date": "2024-01-15",
                "amount": "12.50",
                "rate": "2.5%",
                "balance": "5000.00",
            },
            {
                "date": "2024-01-14",
                "amount": "11.25",
                "rate": "2.5%",
                "balance": "4500.00",
            },
        ]

    @pytest.fixture
    def sample_subscription_fees(self):
        """Sample subscription fees data for testing."""
        return [
            {
                "date": "2024-01-01",
                "amount": "5.00",
                "type": "gold_subscription",
                "status": "paid",
            },
            {
                "date": "2023-12-01",
                "amount": "5.00",
                "type": "gold_subscription",
                "status": "paid",
            },
        ]

    @pytest.fixture
    def sample_referrals(self):
        """Sample referrals data for testing."""
        return {
            "referral_code": "ABC123",
            "referrals": [
                {
                    "id": "referral_1",
                    "referred_user": "user_1",
                    "date": "2024-01-10",
                    "status": "completed",
                    "reward": "10.00",
                    "reward_type": "stock",
                },
                {
                    "id": "referral_2",
                    "referred_user": "user_2",
                    "date": "2024-01-08",
                    "status": "pending",
                    "reward": "10.00",
                    "reward_type": "stock",
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_get_notifications_success(
        self, mock_session_manager, mock_rate_limiter, sample_notifications
    ):
        """Test successful notifications retrieval."""
        with patch(
            "open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_notifications

            result = await get_notifications(count=20)

            assert result["result"]["status"] == "success"
            assert result["result"]["total_notifications"] == 3
            assert result["result"]["unread_count"] == 2
            assert len(result["result"]["notifications"]) == 3
            assert result["result"]["notifications"][0]["title"] == "Order Executed"

    @pytest.mark.asyncio
    async def test_get_notifications_no_data(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test notifications when no data is returned."""
        with patch(
            "open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = None

            result = await get_notifications()

            assert result["result"]["status"] == "no_data"
            assert result["result"]["total_notifications"] == 0
            assert result["result"]["unread_count"] == 0
            assert result["result"]["notifications"] == []

    @pytest.mark.asyncio
    async def test_get_notifications_limited_count(
        self, mock_session_manager, mock_rate_limiter, sample_notifications
    ):
        """Test notifications with limited count."""
        with patch(
            "open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_notifications

            result = await get_notifications(count=2)

            assert result["result"]["status"] == "success"
            assert result["result"]["total_notifications"] == 2
            assert len(result["result"]["notifications"]) == 2

    @pytest.mark.asyncio
    async def test_get_latest_notification_success(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test successful latest notification retrieval."""
        latest_notification = {
            "id": "notification_1",
            "title": "Order Executed",
            "message": "Your order for AAPL has been executed",
            "time": "2024-01-15T10:30:00Z",
            "type": "order_confirmation",
            "read": False,
        }

        with patch(
            "open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = latest_notification

            result = await get_latest_notification()

            assert result["result"]["status"] == "success"
            assert result["result"]["has_notification"] is True
            assert result["result"]["notification"]["title"] == "Order Executed"

    @pytest.mark.asyncio
    async def test_get_latest_notification_no_data(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test latest notification when no data is returned."""
        with patch(
            "open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = None

            result = await get_latest_notification()

            assert result["result"]["status"] == "no_data"
            assert result["result"]["has_notification"] is False
            assert result["result"]["notification"] is None

    @pytest.mark.asyncio
    async def test_get_margin_calls_success(
        self, mock_session_manager, mock_rate_limiter, sample_margin_calls
    ):
        """Test successful margin calls retrieval."""
        with patch(
            "open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_margin_calls

            result = await get_margin_calls()

            assert result["result"]["status"] == "success"
            assert result["result"]["total_calls"] == 2
            assert result["result"]["total_amount_due"] == "3500.00"
            assert result["result"]["has_active_calls"] is True

    @pytest.mark.asyncio
    async def test_get_margin_calls_no_data(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test margin calls when no data is returned."""
        with patch(
            "open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = None

            result = await get_margin_calls()

            assert result["result"]["status"] == "no_data"
            assert result["result"]["total_calls"] == 0
            assert result["result"]["total_amount_due"] == "0.00"
            assert result["result"]["has_active_calls"] is False

    @pytest.mark.asyncio
    async def test_get_margin_interest_success(
        self, mock_session_manager, mock_rate_limiter, sample_margin_interest
    ):
        """Test successful margin interest retrieval."""
        with patch(
            "open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_margin_interest

            result = await get_margin_interest()

            assert result["result"]["status"] == "success"
            assert result["result"]["charges_count"] == 2
            assert result["result"]["total_charges"] == "23.75"
            assert result["result"]["current_rate"] == "2.5%"

    @pytest.mark.asyncio
    async def test_get_margin_interest_no_data(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test margin interest when no data is returned."""
        with patch(
            "open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = None

            result = await get_margin_interest()

            assert result["result"]["status"] == "no_data"
            assert result["result"]["charges_count"] == 0
            assert result["result"]["total_charges"] == "0.00"
            assert result["result"]["current_rate"] == "N/A"

    @pytest.mark.asyncio
    async def test_get_subscription_fees_success(
        self, mock_session_manager, mock_rate_limiter, sample_subscription_fees
    ):
        """Test successful subscription fees retrieval."""
        with patch(
            "open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_subscription_fees

            result = await get_subscription_fees()

            assert result["result"]["status"] == "success"
            assert result["result"]["fees_count"] == 2
            assert result["result"]["total_fees"] == "10.00"
            assert result["result"]["monthly_fee"] == "5.00"
            assert result["result"]["is_gold_member"] is True

    @pytest.mark.asyncio
    async def test_get_subscription_fees_no_data(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test subscription fees when no data is returned."""
        with patch(
            "open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = None

            result = await get_subscription_fees()

            assert result["result"]["status"] == "no_data"
            assert result["result"]["fees_count"] == 0
            assert result["result"]["total_fees"] == "0.00"
            assert result["result"]["monthly_fee"] == "0.00"
            assert result["result"]["is_gold_member"] is False

    @pytest.mark.asyncio
    async def test_get_referrals_success(
        self, mock_session_manager, mock_rate_limiter, sample_referrals
    ):
        """Test successful referrals retrieval."""
        with patch(
            "open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_referrals

            result = await get_referrals()

            assert result["result"]["status"] == "success"
            assert result["result"]["total_referrals"] == 2
            assert result["result"]["completed_referrals"] == 1
            assert result["result"]["total_rewards"] == "10.00"
            assert result["result"]["referral_code"] == "ABC123"

    @pytest.mark.asyncio
    async def test_get_referrals_list_format(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test referrals retrieval when data is in list format."""
        referrals_list = [
            {"id": "referral_1", "status": "completed", "reward": "10.00"}
        ]

        with patch(
            "open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = referrals_list

            result = await get_referrals()

            assert result["result"]["status"] == "success"
            assert result["result"]["total_referrals"] == 1
            assert result["result"]["completed_referrals"] == 1
            assert result["result"]["total_rewards"] == "10.00"

    @pytest.mark.asyncio
    async def test_get_referrals_no_data(self, mock_session_manager, mock_rate_limiter):
        """Test referrals when no data is returned."""
        with patch(
            "open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = None

            result = await get_referrals()

            assert result["result"]["status"] == "no_data"
            assert result["result"]["total_referrals"] == 0
            assert result["result"]["completed_referrals"] == 0
            assert result["result"]["total_rewards"] == "0.00"

    @pytest.mark.asyncio
    async def test_get_account_features_success(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test successful account features compilation."""
        # Mock all the individual function calls
        with (
            patch(
                "open_stocks_mcp.tools.robinhood_account_features_tools.get_subscription_fees"
            ) as mock_sub,
            patch(
                "open_stocks_mcp.tools.robinhood_account_features_tools.get_margin_interest"
            ) as mock_margin,
            patch(
                "open_stocks_mcp.tools.robinhood_account_features_tools.get_notifications"
            ) as mock_notif,
            patch(
                "open_stocks_mcp.tools.robinhood_account_features_tools.get_referrals"
            ) as mock_ref,
        ):
            mock_sub.return_value = {
                "result": {
                    "status": "success",
                    "is_gold_member": True,
                    "monthly_fee": "5.00",
                }
            }

            mock_margin.return_value = {
                "result": {
                    "status": "success",
                    "current_rate": "2.5%",
                    "total_charges": "25.00",
                }
            }

            mock_notif.return_value = {
                "result": {
                    "status": "success",
                    "unread_count": 3,
                    "total_notifications": 15,
                }
            }

            mock_ref.return_value = {
                "result": {
                    "status": "success",
                    "total_referrals": 5,
                    "completed_referrals": 3,
                    "total_rewards": "30.00",
                }
            }

            result = await get_account_features()

            assert result["result"]["status"] == "success"
            assert "gold_membership" in result["result"]["features"]
            assert "margin" in result["result"]["features"]
            assert "notifications" in result["result"]["features"]
            assert "referrals" in result["result"]["features"]
            assert result["result"]["features"]["gold_membership"]["is_member"] is True

    @pytest.mark.asyncio
    async def test_get_account_features_partial_success(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test account features with partial success."""
        with (
            patch(
                "open_stocks_mcp.tools.robinhood_account_features_tools.get_subscription_fees"
            ) as mock_sub,
            patch(
                "open_stocks_mcp.tools.robinhood_account_features_tools.get_margin_interest"
            ) as mock_margin,
            patch(
                "open_stocks_mcp.tools.robinhood_account_features_tools.get_notifications"
            ) as mock_notif,
            patch(
                "open_stocks_mcp.tools.robinhood_account_features_tools.get_referrals"
            ) as mock_ref,
        ):
            mock_sub.return_value = {
                "result": {
                    "status": "success",
                    "is_gold_member": True,
                    "monthly_fee": "5.00",
                }
            }
            mock_margin.side_effect = Exception("Margin API error")
            mock_notif.return_value = {
                "result": {
                    "status": "success",
                    "unread_count": 3,
                    "total_notifications": 15,
                }
            }
            mock_ref.return_value = {
                "result": {
                    "status": "success",
                    "total_referrals": 5,
                    "completed_referrals": 3,
                    "total_rewards": "30.00",
                }
            }

            result = await get_account_features()

            assert result["result"]["status"] == "partial_success"
            assert "gold_membership" in result["result"]["features"]
            assert "notifications" in result["result"]["features"]
            assert "referrals" in result["result"]["features"]
            assert "error" in result["result"]

    @pytest.mark.asyncio
    async def test_notifications_error_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test error handling for notifications."""
        with patch(
            "open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("API Error")

            result = await get_notifications()

            assert result["result"]["status"] == "error"
            assert "error" in result["result"]

    @pytest.mark.asyncio
    async def test_margin_calls_error_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test error handling for margin calls."""
        with patch(
            "open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("API Error")

            result = await get_margin_calls()

            assert result["result"]["status"] == "error"
            assert "error" in result["result"]

    @pytest.mark.asyncio
    async def test_margin_interest_error_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test error handling for margin interest."""
        with patch(
            "open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("API Error")

            result = await get_margin_interest()

            assert result["result"]["status"] == "error"
            assert "error" in result["result"]

    @pytest.mark.asyncio
    async def test_subscription_fees_error_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test error handling for subscription fees."""
        with patch(
            "open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("API Error")

            result = await get_subscription_fees()

            assert result["result"]["status"] == "error"
            assert "error" in result["result"]

    @pytest.mark.asyncio
    async def test_referrals_error_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test error handling for referrals."""
        with patch(
            "open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("API Error")

            result = await get_referrals()

            assert result["result"]["status"] == "error"
            assert "error" in result["result"]

    @pytest.mark.asyncio
    async def test_margin_calls_calculation_edge_cases(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test margin calls calculation with edge cases."""
        edge_case_calls = [
            {"id": "call_1", "amount": "invalid_amount", "status": "active"},
            {"id": "call_2", "amount": "1000.00", "status": "inactive"},
        ]

        with patch(
            "open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = edge_case_calls

            result = await get_margin_calls()

            assert result["result"]["status"] == "success"
            assert result["result"]["total_calls"] == 2
            assert result["result"]["total_amount_due"] == "1000.00"
            assert result["result"]["has_active_calls"] is True

    @pytest.mark.asyncio
    async def test_referrals_reward_calculation(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test referrals reward calculation with edge cases."""
        edge_case_referrals = [
            {"id": "ref_1", "status": "completed", "reward": "10.00"},
            {"id": "ref_2", "status": "completed", "reward": "invalid_reward"},
            {"id": "ref_3", "status": "pending", "reward": "5.00"},
        ]

        with patch(
            "open_stocks_mcp.tools.robinhood_account_features_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = edge_case_referrals

            result = await get_referrals()

            assert result["result"]["status"] == "success"
            assert result["result"]["total_referrals"] == 3
            assert result["result"]["completed_referrals"] == 2
            assert (
                result["result"]["total_rewards"] == "10.00"
            )  # Only valid completed rewards
