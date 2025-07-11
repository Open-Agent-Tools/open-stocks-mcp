"""Unit tests for user profile management tools."""

from typing import Any
from unittest.mock import patch

import pytest

from open_stocks_mcp.tools.robinhood_user_profile_tools import (
    get_account_profile,
    get_basic_profile,
    get_complete_profile,
    get_investment_profile,
    get_security_profile,
    get_user_profile,
)


class TestAccountProfile:
    """Test account profile functionality."""

    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_account_profile_success(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test successful account profile retrieval."""
        mock_execute_with_retry.return_value = {
            "account_number": "12345678",
            "day_trade_count": "2",
            "max_ach_early_access_amount": "1000.00",
            "cash_management_enabled": True,
            "option_level": "2",
            "instant_eligibility": True,
            "margin_balances": {
                "day_trade_buying_power": "25000.00",
                "overnight_buying_power": "12500.00",
                "margin_limit": "10000.00",
                "marked_pattern_day_trader_date": None,
                "unallocated_margin_cash": "2500.00",
            },
            "is_pattern_day_trader": False,
            "updated_at": "2024-07-09T16:00:00Z",
            "created_at": "2020-01-01T10:00:00Z",
            "sma_debit": "0.00",
            "sma_held_for_orders": "0.00",
        }

        result = await get_account_profile()

        assert "result" in result
        assert result["result"]["account_profile"]["account_number"] == "12345678"
        assert result["result"]["account_profile"]["day_trade_count"] == "2"
        assert result["result"]["account_profile"]["option_level"] == "2"
        assert result["result"]["account_profile"]["instant_eligibility"] is True
        assert (
            result["result"]["account_profile"]["margin_balances"][
                "day_trade_buying_power"
            ]
            == "25000.00"
        )
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_account_profile_no_data(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test account profile when no data is available."""
        mock_execute_with_retry.return_value = None

        result = await get_account_profile()

        assert "result" in result
        assert result["result"]["account_profile"] == {}
        assert result["result"]["status"] == "no_data"
        assert "No account profile data found" in result["result"]["error"]

    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_account_profile_minimal_data(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test account profile with minimal data."""
        mock_execute_with_retry.return_value = {
            "account_number": "87654321",
            "option_level": "0",
            "instant_eligibility": False,
        }

        result = await get_account_profile()

        assert "result" in result
        assert result["result"]["account_profile"]["account_number"] == "87654321"
        assert result["result"]["account_profile"]["option_level"] == "0"
        assert result["result"]["account_profile"]["instant_eligibility"] is False
        assert result["result"]["status"] == "success"


class TestBasicProfile:
    """Test basic profile functionality."""

    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_basic_profile_success(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test successful basic profile retrieval."""
        mock_execute_with_retry.return_value = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone_number": "+1234567890",
            "date_of_birth": "1990-01-01",
            "address": {
                "city": "New York",
                "state": "NY",
                "zipcode": "10001",
                "address_line_1": "123 Main St",
                "address_line_2": "Apt 4B",
            },
            "employment": {
                "employment_status": "employed",
                "employer": "Tech Corp",
                "position": "Software Engineer",
                "years_employed": "5",
            },
            "citizenship": "US",
            "marital_status": "single",
            "number_dependents": "0",
            "updated_at": "2024-07-09T12:00:00Z",
        }

        result = await get_basic_profile()

        assert "result" in result
        assert result["result"]["basic_profile"]["first_name"] == "John"
        assert result["result"]["basic_profile"]["last_name"] == "Doe"
        assert result["result"]["basic_profile"]["email"] == "john.doe@example.com"
        assert result["result"]["basic_profile"]["phone_number"] == "+1234567890"
        assert result["result"]["basic_profile"]["address"]["city"] == "New York"
        assert (
            result["result"]["basic_profile"]["employment"]["employer"] == "Tech Corp"
        )
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_basic_profile_no_data(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test basic profile when no data is available."""
        mock_execute_with_retry.return_value = None

        result = await get_basic_profile()

        assert "result" in result
        assert result["result"]["basic_profile"] == {}
        assert result["result"]["status"] == "no_data"
        assert "No basic profile data found" in result["result"]["error"]

    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_basic_profile_partial_data(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test basic profile with partial data."""
        mock_execute_with_retry.return_value = {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane.smith@example.com",
            # Missing phone, address, employment
        }

        result = await get_basic_profile()

        assert "result" in result
        assert result["result"]["basic_profile"]["first_name"] == "Jane"
        assert result["result"]["basic_profile"]["last_name"] == "Smith"
        assert result["result"]["basic_profile"]["email"] == "jane.smith@example.com"
        assert result["result"]["status"] == "success"


class TestInvestmentProfile:
    """Test investment profile functionality."""

    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_investment_profile_success(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test successful investment profile retrieval."""
        mock_execute_with_retry.return_value = {
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
            "understand_option_risks": True,
            "agree_fully_paid_lending": False,
            "updated_at": "2024-07-09T12:00:00Z",
        }

        result = await get_investment_profile()

        assert "result" in result
        assert result["result"]["investment_profile"]["risk_tolerance"] == "moderate"
        assert (
            result["result"]["investment_profile"]["investment_experience"]
            == "some_experience"
        )
        assert (
            result["result"]["investment_profile"]["investment_objective"] == "growth"
        )
        assert result["result"]["investment_profile"]["time_horizon"] == "long_term"
        assert result["result"]["investment_profile"]["annual_income"] == "50000-100000"
        assert result["result"]["investment_profile"]["professional_trader"] is False
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_investment_profile_no_data(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test investment profile when no data is available."""
        mock_execute_with_retry.return_value = None

        result = await get_investment_profile()

        assert "result" in result
        assert result["result"]["investment_profile"] == {}
        assert result["result"]["status"] == "no_data"
        assert "No investment profile data found" in result["result"]["error"]

    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_investment_profile_conservative(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test investment profile for conservative investor."""
        mock_execute_with_retry.return_value = {
            "risk_tolerance": "conservative",
            "investment_experience": "no_experience",
            "investment_objective": "income",
            "time_horizon": "short_term",
            "liquidity_needs": "high",
            "annual_income": "25000-50000",
            "net_worth": "25000-50000",
            "professional_trader": False,
            "option_trading_experience": "none",
        }

        result = await get_investment_profile()

        assert "result" in result
        assert (
            result["result"]["investment_profile"]["risk_tolerance"] == "conservative"
        )
        assert (
            result["result"]["investment_profile"]["investment_objective"] == "income"
        )
        assert result["result"]["investment_profile"]["time_horizon"] == "short_term"
        assert result["result"]["investment_profile"]["liquidity_needs"] == "high"
        assert result["result"]["status"] == "success"


class TestSecurityProfile:
    """Test security profile functionality."""

    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_security_profile_success(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test successful security profile retrieval."""
        mock_execute_with_retry.return_value = {
            "sms_enabled": True,
            "email_enabled": True,
            "push_notifications": True,
            "two_factor_enabled": True,
            "backup_codes_generated": True,
            "last_login": "2024-07-09T10:30:00Z",
            "login_attempts": 0,
            "account_locked": False,
            "password_reset_required": False,
            "security_questions_set": True,
            "verified_email": True,
            "verified_phone": True,
            "challenge_questions_enabled": True,
            "updated_at": "2024-07-09T12:00:00Z",
        }

        result = await get_security_profile()

        assert "result" in result
        assert result["result"]["security_profile"]["sms_enabled"] is True
        assert result["result"]["security_profile"]["email_enabled"] is True
        assert result["result"]["security_profile"]["two_factor_enabled"] is True
        assert result["result"]["security_profile"]["backup_codes_generated"] is True
        assert result["result"]["security_profile"]["account_locked"] is False
        assert result["result"]["security_profile"]["password_reset_required"] is False
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_security_profile_no_data(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test security profile when no data is available."""
        mock_execute_with_retry.return_value = None

        result = await get_security_profile()

        assert "result" in result
        assert result["result"]["security_profile"] == {}
        assert result["result"]["status"] == "no_data"
        assert "No security profile data found" in result["result"]["error"]

    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_security_profile_minimal_security(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test security profile with minimal security features."""
        mock_execute_with_retry.return_value = {
            "sms_enabled": False,
            "email_enabled": True,
            "push_notifications": False,
            "two_factor_enabled": False,
            "backup_codes_generated": False,
            "account_locked": False,
            "password_reset_required": False,
        }

        result = await get_security_profile()

        assert "result" in result
        assert result["result"]["security_profile"]["sms_enabled"] is False
        assert result["result"]["security_profile"]["two_factor_enabled"] is False
        assert result["result"]["security_profile"]["backup_codes_generated"] is False
        assert result["result"]["status"] == "success"


class TestUserProfile:
    """Test user profile functionality."""

    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_user_profile_success(self, mock_execute_with_retry: Any) -> None:
        """Test successful user profile retrieval."""
        mock_execute_with_retry.return_value = {
            "username": "john_doe",
            "email": "john.doe@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "id": "user_id_12345",
            "created_at": "2020-01-01T00:00:00Z",
            "email_verified": True,
            "phone_number": "+1234567890",
            "profile_name": "John Doe",
            "url": "https://robinhood.com/user/user_id_12345/",
            "id_info": "verified",
            "international_info": {
                "supports_international": False,
                "currency_code": "USD",
            },
            "updated_at": "2024-07-09T12:00:00Z",
        }

        result = await get_user_profile()

        assert "result" in result
        assert result["result"]["user_profile"]["username"] == "john_doe"
        assert result["result"]["user_profile"]["email"] == "john.doe@example.com"
        assert result["result"]["user_profile"]["first_name"] == "John"
        assert result["result"]["user_profile"]["last_name"] == "Doe"
        assert result["result"]["user_profile"]["id"] == "user_id_12345"
        assert result["result"]["user_profile"]["email_verified"] is True
        assert result["result"]["user_profile"]["profile_name"] == "John Doe"
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_user_profile_no_data(self, mock_execute_with_retry: Any) -> None:
        """Test user profile when no data is available."""
        mock_execute_with_retry.return_value = None

        result = await get_user_profile()

        assert "result" in result
        assert result["result"]["user_profile"] == {}
        assert result["result"]["status"] == "no_data"
        assert "No user profile data found" in result["result"]["error"]

    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.execute_with_retry")
    @pytest.mark.asyncio
    async def test_get_user_profile_unverified_email(
        self, mock_execute_with_retry: Any
    ) -> None:
        """Test user profile with unverified email."""
        mock_execute_with_retry.return_value = {
            "username": "jane_smith",
            "email": "jane.smith@example.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "id": "user_id_67890",
            "email_verified": False,
            "profile_name": "Jane Smith",
        }

        result = await get_user_profile()

        assert "result" in result
        assert result["result"]["user_profile"]["username"] == "jane_smith"
        assert result["result"]["user_profile"]["email_verified"] is False
        assert result["result"]["status"] == "success"


class TestCompleteProfile:
    """Test complete profile functionality."""

    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_security_profile")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_investment_profile")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_account_profile")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_basic_profile")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_user_profile")
    @pytest.mark.asyncio
    async def test_get_complete_profile_success(
        self,
        mock_user_profile: Any,
        mock_basic_profile: Any,
        mock_account_profile: Any,
        mock_investment_profile: Any,
        mock_security_profile: Any,
    ) -> None:
        """Test successful complete profile retrieval."""
        mock_user_profile.return_value = {
            "result": {
                "status": "success",
                "user_profile": {
                    "username": "john_doe",
                    "email": "john.doe@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                },
            }
        }

        mock_basic_profile.return_value = {
            "result": {
                "status": "success",
                "basic_profile": {
                    "phone_number": "+1234567890",
                    "date_of_birth": "1990-01-01",
                    "address": {"city": "New York", "state": "NY"},
                },
            }
        }

        mock_account_profile.return_value = {
            "result": {
                "status": "success",
                "account_profile": {
                    "account_number": "12345678",
                    "option_level": "2",
                    "instant_eligibility": True,
                },
            }
        }

        mock_investment_profile.return_value = {
            "result": {
                "status": "success",
                "investment_profile": {
                    "risk_tolerance": "moderate",
                    "investment_experience": "some_experience",
                    "investment_objective": "growth",
                },
            }
        }

        mock_security_profile.return_value = {
            "result": {
                "status": "success",
                "security_profile": {
                    "two_factor_enabled": True,
                    "email_enabled": True,
                    "sms_enabled": True,
                },
            }
        }

        result = await get_complete_profile()

        assert "result" in result
        assert result["result"]["profiles_loaded"] == 5
        assert result["result"]["status"] == "success"

        complete = result["result"]["complete_profile"]
        assert complete["user_info"]["username"] == "john_doe"
        assert complete["basic_profile"]["phone_number"] == "+1234567890"
        assert complete["account_profile"]["option_level"] == "2"
        assert complete["investment_profile"]["risk_tolerance"] == "moderate"
        assert complete["security_profile"]["two_factor_enabled"] is True

    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_security_profile")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_investment_profile")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_account_profile")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_basic_profile")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_user_profile")
    @pytest.mark.asyncio
    async def test_get_complete_profile_partial_success(
        self,
        mock_user_profile: Any,
        mock_basic_profile: Any,
        mock_account_profile: Any,
        mock_investment_profile: Any,
        mock_security_profile: Any,
    ) -> None:
        """Test complete profile with some failures."""
        mock_user_profile.return_value = {
            "result": {
                "status": "success",
                "user_profile": {
                    "username": "john_doe",
                    "email": "john.doe@example.com",
                },
            }
        }

        mock_basic_profile.return_value = {
            "result": {"status": "no_data", "error": "No basic profile data found"}
        }

        mock_account_profile.return_value = {
            "result": {
                "status": "success",
                "account_profile": {"account_number": "12345678", "option_level": "2"},
            }
        }

        mock_investment_profile.return_value = {
            "result": {"status": "no_data", "error": "No investment profile data found"}
        }

        mock_security_profile.return_value = {
            "result": {
                "status": "success",
                "security_profile": {"two_factor_enabled": True, "email_enabled": True},
            }
        }

        result = await get_complete_profile()

        assert "result" in result
        assert result["result"]["profiles_loaded"] == 3  # Only 3 successful
        assert result["result"]["status"] == "success"

        complete = result["result"]["complete_profile"]
        assert "user_info" in complete
        assert "account_profile" in complete
        assert "security_profile" in complete
        assert "basic_profile" not in complete  # Failed to load
        assert "investment_profile" not in complete  # Failed to load

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_security_profile")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_investment_profile")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_account_profile")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_basic_profile")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_user_profile")
    @pytest.mark.asyncio
    async def test_get_complete_profile_exception(
        self,
        mock_user_profile: Any,
        mock_basic_profile: Any,
        mock_account_profile: Any,
        mock_investment_profile: Any,
        mock_security_profile: Any,
    ) -> None:
        """Test complete profile with exception."""
        mock_user_profile.return_value = {
            "result": {
                "status": "success",
                "user_profile": {"username": "john_doe"},
            }
        }

        mock_basic_profile.side_effect = Exception("API Error")

        result = await get_complete_profile()

        assert "result" in result
        assert result["result"]["profiles_loaded"] == 1  # Only user profile succeeded
        assert result["result"]["status"] == "partial_success"
        assert "Error loading complete profile" in result["result"]["error"]

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_security_profile")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_investment_profile")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_account_profile")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_basic_profile")
    @patch("open_stocks_mcp.tools.robinhood_user_profile_tools.get_user_profile")
    @pytest.mark.asyncio
    async def test_get_complete_profile_all_failures(
        self,
        mock_user_profile: Any,
        mock_basic_profile: Any,
        mock_account_profile: Any,
        mock_investment_profile: Any,
        mock_security_profile: Any,
    ) -> None:
        """Test complete profile when all profiles fail."""
        mock_user_profile.return_value = {
            "result": {"status": "no_data", "error": "No user profile data found"}
        }

        mock_basic_profile.return_value = {
            "result": {"status": "no_data", "error": "No basic profile data found"}
        }

        mock_account_profile.return_value = {
            "result": {"status": "no_data", "error": "No account profile data found"}
        }

        mock_investment_profile.return_value = {
            "result": {"status": "no_data", "error": "No investment profile data found"}
        }

        mock_security_profile.return_value = {
            "result": {"status": "no_data", "error": "No security profile data found"}
        }

        result = await get_complete_profile()

        assert "result" in result
        assert result["result"]["profiles_loaded"] == 0
        assert result["result"]["status"] == "success"  # Still success with 0 profiles
        assert result["result"]["complete_profile"] == {}
