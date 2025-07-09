"""
Tests for User Profile Tools.

This module tests the user profile management functions including:
- Account profile retrieval
- Basic user profile information
- Investment profile and risk assessment
- Security profile settings
- Complete profile compilation
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from open_stocks_mcp.tools.robinhood_user_profile_tools import (
    get_account_profile,
    get_account_settings,
    get_basic_profile,
    get_complete_profile,
    get_investment_profile,
    get_security_profile,
    get_user_profile,
)


class TestUserProfileTools:
    """Test suite for user profile management tools."""

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
    def sample_account_profile(self):
        """Sample account profile data for testing."""
        return {
            "account_number": "12345678",
            "day_trade_count": 2,
            "max_ach_early_access_amount": "1000.00",
            "cash_management_enabled": True,
            "option_level": "2",
            "instant_eligibility": True,
            "margin_balances": {
                "day_trade_buying_power": "25000.00",
                "overnight_buying_power": "12500.00",
            },
        }

    @pytest.fixture
    def sample_basic_profile(self):
        """Sample basic profile data for testing."""
        return {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone_number": "+1234567890",
            "date_of_birth": "1990-01-01",
            "address": {"city": "New York", "state": "NY", "zipcode": "10001"},
            "employment": {
                "employment_status": "employed",
                "employer": "Tech Corp",
                "position": "Software Engineer",
            },
        }

    @pytest.fixture
    def sample_investment_profile(self):
        """Sample investment profile data for testing."""
        return {
            "risk_tolerance": "moderate",
            "investment_experience": "some_experience",
            "investment_objective": "growth",
            "time_horizon": "long_term",
            "liquidity_needs": "low",
            "annual_income": "50000-100000",
            "net_worth": "100000-250000",
            "investment_experience_stocks": "some_experience",
            "investment_experience_options": "no_experience",
            "option_trading_experience": "none",
            "professional_trader": False,
        }

    @pytest.fixture
    def sample_security_profile(self):
        """Sample security profile data for testing."""
        return {
            "sms_enabled": True,
            "email_enabled": True,
            "push_notifications": True,
            "two_factor_enabled": True,
            "backup_codes_generated": True,
            "last_login": "2024-01-15T10:30:00Z",
            "login_attempts": 0,
            "account_locked": False,
            "password_reset_required": False,
        }

    @pytest.fixture
    def sample_user_profile(self):
        """Sample user profile data for testing."""
        return {
            "username": "john_doe",
            "email": "john.doe@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "id": "user_id_123",
            "created_at": "2020-01-01T00:00:00Z",
            "email_verified": True,
            "phone_number": "+1234567890",
            "profile_name": "John Doe",
        }

    @pytest.mark.asyncio
    async def test_get_account_profile_success(
        self, mock_session_manager, mock_rate_limiter, sample_account_profile
    ):
        """Test successful account profile retrieval."""
        with patch(
            "open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_account_profile

            result = await get_account_profile()

            assert result["result"]["status"] == "success"
            assert result["result"]["account_profile"]["account_number"] == "12345678"
            assert result["result"]["account_profile"]["day_trade_count"] == 2
            assert result["result"]["account_profile"]["option_level"] == "2"

    @pytest.mark.asyncio
    async def test_get_account_profile_no_data(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test account profile when no data is returned."""
        with patch(
            "open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = None

            result = await get_account_profile()

            assert result["result"]["status"] == "no_data"
            assert result["result"]["account_profile"] == {}
            assert "No account profile data found" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_get_basic_profile_success(
        self, mock_session_manager, mock_rate_limiter, sample_basic_profile
    ):
        """Test successful basic profile retrieval."""
        with patch(
            "open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_basic_profile

            result = await get_basic_profile()

            assert result["result"]["status"] == "success"
            assert result["result"]["basic_profile"]["first_name"] == "John"
            assert result["result"]["basic_profile"]["last_name"] == "Doe"
            assert result["result"]["basic_profile"]["email"] == "john.doe@example.com"

    @pytest.mark.asyncio
    async def test_get_basic_profile_no_data(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test basic profile when no data is returned."""
        with patch(
            "open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = None

            result = await get_basic_profile()

            assert result["result"]["status"] == "no_data"
            assert result["result"]["basic_profile"] == {}
            assert "No basic profile data found" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_get_investment_profile_success(
        self, mock_session_manager, mock_rate_limiter, sample_investment_profile
    ):
        """Test successful investment profile retrieval."""
        with patch(
            "open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_investment_profile

            result = await get_investment_profile()

            assert result["result"]["status"] == "success"
            assert (
                result["result"]["investment_profile"]["risk_tolerance"] == "moderate"
            )
            assert (
                result["result"]["investment_profile"]["investment_experience"]
                == "some_experience"
            )
            assert (
                result["result"]["investment_profile"]["investment_objective"]
                == "growth"
            )

    @pytest.mark.asyncio
    async def test_get_investment_profile_no_data(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test investment profile when no data is returned."""
        with patch(
            "open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = None

            result = await get_investment_profile()

            assert result["result"]["status"] == "no_data"
            assert result["result"]["investment_profile"] == {}
            assert "No investment profile data found" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_get_security_profile_success(
        self, mock_session_manager, mock_rate_limiter, sample_security_profile
    ):
        """Test successful security profile retrieval."""
        with patch(
            "open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_security_profile

            result = await get_security_profile()

            assert result["result"]["status"] == "success"
            assert result["result"]["security_profile"]["sms_enabled"] is True
            assert result["result"]["security_profile"]["two_factor_enabled"] is True
            assert result["result"]["security_profile"]["account_locked"] is False

    @pytest.mark.asyncio
    async def test_get_security_profile_no_data(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test security profile when no data is returned."""
        with patch(
            "open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = None

            result = await get_security_profile()

            assert result["result"]["status"] == "no_data"
            assert result["result"]["security_profile"] == {}
            assert "No security profile data found" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_get_user_profile_success(
        self, mock_session_manager, mock_rate_limiter, sample_user_profile
    ):
        """Test successful user profile retrieval."""
        with patch(
            "open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = sample_user_profile

            result = await get_user_profile()

            assert result["result"]["status"] == "success"
            assert result["result"]["user_profile"]["username"] == "john_doe"
            assert result["result"]["user_profile"]["email"] == "john.doe@example.com"
            assert result["result"]["user_profile"]["id"] == "user_id_123"

    @pytest.mark.asyncio
    async def test_get_user_profile_no_data(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test user profile when no data is returned."""
        with patch(
            "open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.return_value = None

            result = await get_user_profile()

            assert result["result"]["status"] == "no_data"
            assert result["result"]["user_profile"] == {}
            assert "No user profile data found" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_get_complete_profile_success(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test successful complete profile compilation."""
        with (
            patch(
                "open_stocks_mcp.tools.robinhood_user_profile_tools.get_user_profile"
            ) as mock_user,
            patch(
                "open_stocks_mcp.tools.robinhood_user_profile_tools.get_basic_profile"
            ) as mock_basic,
            patch(
                "open_stocks_mcp.tools.robinhood_user_profile_tools.get_account_profile"
            ) as mock_account,
            patch(
                "open_stocks_mcp.tools.robinhood_user_profile_tools.get_investment_profile"
            ) as mock_investment,
            patch(
                "open_stocks_mcp.tools.robinhood_user_profile_tools.get_security_profile"
            ) as mock_security,
        ):
            mock_user.return_value = {
                "result": {
                    "status": "success",
                    "user_profile": {"username": "john_doe"},
                }
            }
            mock_basic.return_value = {
                "result": {"status": "success", "basic_profile": {"first_name": "John"}}
            }
            mock_account.return_value = {
                "result": {
                    "status": "success",
                    "account_profile": {"account_number": "123"},
                }
            }
            mock_investment.return_value = {
                "result": {
                    "status": "success",
                    "investment_profile": {"risk_tolerance": "moderate"},
                }
            }
            mock_security.return_value = {
                "result": {
                    "status": "success",
                    "security_profile": {"sms_enabled": True},
                }
            }

            result = await get_complete_profile()

            assert result["result"]["status"] == "success"
            assert result["result"]["profiles_loaded"] == 5
            assert "user_info" in result["result"]["complete_profile"]
            assert "basic_profile" in result["result"]["complete_profile"]
            assert "account_profile" in result["result"]["complete_profile"]
            assert "investment_profile" in result["result"]["complete_profile"]
            assert "security_profile" in result["result"]["complete_profile"]

    @pytest.mark.asyncio
    async def test_get_complete_profile_partial_success(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test complete profile with partial success."""
        with (
            patch(
                "open_stocks_mcp.tools.robinhood_user_profile_tools.get_user_profile"
            ) as mock_user,
            patch(
                "open_stocks_mcp.tools.robinhood_user_profile_tools.get_basic_profile"
            ) as mock_basic,
            patch(
                "open_stocks_mcp.tools.robinhood_user_profile_tools.get_account_profile"
            ) as mock_account,
            patch(
                "open_stocks_mcp.tools.robinhood_user_profile_tools.get_investment_profile"
            ) as mock_investment,
            patch(
                "open_stocks_mcp.tools.robinhood_user_profile_tools.get_security_profile"
            ) as mock_security,
        ):
            mock_user.return_value = {
                "result": {
                    "status": "success",
                    "user_profile": {"username": "john_doe"},
                }
            }
            mock_basic.return_value = {
                "result": {"status": "success", "basic_profile": {"first_name": "John"}}
            }
            mock_account.return_value = {"result": {"status": "no_data"}}
            mock_investment.return_value = {
                "result": {
                    "status": "success",
                    "investment_profile": {"risk_tolerance": "moderate"},
                }
            }
            mock_security.return_value = {"result": {"status": "no_data"}}

            result = await get_complete_profile()

            assert result["result"]["status"] == "success"
            assert result["result"]["profiles_loaded"] == 3
            assert "user_info" in result["result"]["complete_profile"]
            assert "basic_profile" in result["result"]["complete_profile"]
            assert "investment_profile" in result["result"]["complete_profile"]
            assert "account_profile" not in result["result"]["complete_profile"]
            assert "security_profile" not in result["result"]["complete_profile"]

    @pytest.mark.asyncio
    async def test_get_complete_profile_with_exception(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test complete profile with exception handling."""
        with (
            patch(
                "open_stocks_mcp.tools.robinhood_user_profile_tools.get_user_profile"
            ) as mock_user,
            patch(
                "open_stocks_mcp.tools.robinhood_user_profile_tools.get_basic_profile"
            ) as mock_basic,
            patch(
                "open_stocks_mcp.tools.robinhood_user_profile_tools.get_account_profile"
            ) as mock_account,
            patch(
                "open_stocks_mcp.tools.robinhood_user_profile_tools.get_investment_profile"
            ) as mock_investment,
            patch(
                "open_stocks_mcp.tools.robinhood_user_profile_tools.get_security_profile"
            ) as mock_security,
        ):
            mock_user.return_value = {
                "result": {
                    "status": "success",
                    "user_profile": {"username": "john_doe"},
                }
            }
            mock_basic.side_effect = Exception("API Error")
            mock_account.return_value = {
                "result": {
                    "status": "success",
                    "account_profile": {"account_number": "123"},
                }
            }
            mock_investment.return_value = {
                "result": {
                    "status": "success",
                    "investment_profile": {"risk_tolerance": "moderate"},
                }
            }
            mock_security.return_value = {
                "result": {
                    "status": "success",
                    "security_profile": {"sms_enabled": True},
                }
            }

            result = await get_complete_profile()

            assert result["result"]["status"] == "partial_success"
            assert result["result"]["profiles_loaded"] == 4
            assert "error" in result["result"]
            assert "API Error" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_get_account_settings_success(
        self, mock_session_manager, mock_rate_limiter, sample_account_profile
    ):
        """Test successful account settings retrieval."""
        with patch(
            "open_stocks_mcp.tools.robinhood_user_profile_tools.get_account_profile"
        ) as mock_account:
            mock_account.return_value = {
                "result": {
                    "status": "success",
                    "account_profile": sample_account_profile,
                }
            }

            result = await get_account_settings()

            assert result["result"]["status"] == "success"
            assert result["result"]["settings"]["instant_settlement"] is True
            assert result["result"]["settings"]["margin_enabled"] is True
            assert result["result"]["settings"]["options_enabled"] is True
            assert result["result"]["settings"]["day_trade_count"] == 2

    @pytest.mark.asyncio
    async def test_get_account_settings_no_account_data(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test account settings when account data is not available."""
        with patch(
            "open_stocks_mcp.tools.robinhood_user_profile_tools.get_account_profile"
        ) as mock_account:
            mock_account.return_value = {"result": {"status": "no_data"}}

            result = await get_account_settings()

            assert result["result"]["status"] == "error"
            assert "Could not retrieve account settings" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_get_account_settings_with_exception(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test account settings with exception handling."""
        with patch(
            "open_stocks_mcp.tools.robinhood_user_profile_tools.get_account_profile"
        ) as mock_account:
            mock_account.side_effect = Exception("Network Error")

            result = await get_account_settings()

            assert result["result"]["status"] == "error"
            assert "Network Error" in result["result"]["error"]

    @pytest.mark.asyncio
    async def test_profile_tools_error_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test error handling for profile tools."""
        with patch(
            "open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("API Error")

            result = await get_account_profile()

            assert result["result"]["status"] == "error"
            assert "error" in result["result"]

    @pytest.mark.asyncio
    async def test_basic_profile_error_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test error handling for basic profile."""
        with patch(
            "open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("Network Error")

            result = await get_basic_profile()

            assert result["result"]["status"] == "error"
            assert "error" in result["result"]

    @pytest.mark.asyncio
    async def test_investment_profile_error_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test error handling for investment profile."""
        with patch(
            "open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("Database Error")

            result = await get_investment_profile()

            assert result["result"]["status"] == "error"
            assert "error" in result["result"]

    @pytest.mark.asyncio
    async def test_security_profile_error_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test error handling for security profile."""
        with patch(
            "open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("Auth Error")

            result = await get_security_profile()

            assert result["result"]["status"] == "error"
            assert "error" in result["result"]

    @pytest.mark.asyncio
    async def test_user_profile_error_handling(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test error handling for user profile."""
        with patch(
            "open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry"
        ) as mock_execute:
            mock_execute.side_effect = Exception("Service Error")

            result = await get_user_profile()

            assert result["result"]["status"] == "error"
            assert "error" in result["result"]

    @pytest.mark.asyncio
    async def test_account_settings_feature_detection(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test account settings feature detection logic."""
        minimal_account_profile = {
            "account_number": "12345678",
            "instant_eligibility": False,
            "option_level": "0",
            "day_trade_count": 0,
            "cash_management_enabled": False,
            "max_ach_early_access_amount": "0.00",
        }

        with patch(
            "open_stocks_mcp.tools.robinhood_user_profile_tools.get_account_profile"
        ) as mock_account:
            mock_account.return_value = {
                "result": {
                    "status": "success",
                    "account_profile": minimal_account_profile,
                }
            }

            result = await get_account_settings()

            assert result["result"]["status"] == "success"
            assert result["result"]["settings"]["instant_settlement"] is False
            assert result["result"]["settings"]["margin_enabled"] is False
            assert result["result"]["settings"]["options_enabled"] is False
            assert result["result"]["settings"]["day_trade_count"] == 0

    @pytest.mark.asyncio
    async def test_complete_profile_empty_results(
        self, mock_session_manager, mock_rate_limiter
    ):
        """Test complete profile with all empty results."""
        with (
            patch(
                "open_stocks_mcp.tools.robinhood_user_profile_tools.get_user_profile"
            ) as mock_user,
            patch(
                "open_stocks_mcp.tools.robinhood_user_profile_tools.get_basic_profile"
            ) as mock_basic,
            patch(
                "open_stocks_mcp.tools.robinhood_user_profile_tools.get_account_profile"
            ) as mock_account,
            patch(
                "open_stocks_mcp.tools.robinhood_user_profile_tools.get_investment_profile"
            ) as mock_investment,
            patch(
                "open_stocks_mcp.tools.robinhood_user_profile_tools.get_security_profile"
            ) as mock_security,
        ):
            mock_user.return_value = {"result": {"status": "no_data"}}
            mock_basic.return_value = {"result": {"status": "no_data"}}
            mock_account.return_value = {"result": {"status": "no_data"}}
            mock_investment.return_value = {"result": {"status": "no_data"}}
            mock_security.return_value = {"result": {"status": "no_data"}}

            result = await get_complete_profile()

            assert result["result"]["status"] == "success"
            assert result["result"]["profiles_loaded"] == 0
            assert result["result"]["complete_profile"] == {}
