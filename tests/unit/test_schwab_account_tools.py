"""Unit tests for Schwab account tools."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.tools.schwab_account_tools import (
    build_schwab_user_profile,
    get_schwab_account,
    get_schwab_account_balances,
    get_schwab_account_numbers,
    get_schwab_accounts,
    get_schwab_all_account_data,
    get_schwab_portfolio,
    get_schwab_user_preferences,
    schwab_check_margin_status,
    schwab_get_margin_interest,
)


class TestSchwabAccountTools:
    """Test Schwab account tools with mocked responses."""

    @pytest.mark.journey_account
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_account_tools.execute_broker_request")
    async def test_get_account_numbers_success(
        self,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
        schwab_account_numbers_payload: list[dict[str, Any]],
    ) -> None:
        """Test successful account numbers retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = schwab_account_numbers_payload
        mock_broker.client.get_account_numbers.return_value = mock_response
        mock_get_broker.return_value = (mock_broker, None)

        mock_to_thread.return_value = schwab_account_numbers_payload

        result = await get_schwab_account_numbers()

        assert "result" in result
        assert "accounts" in result["result"]
        assert len(result["result"]["accounts"]) == 2
        assert result["result"]["accounts"][0]["account_id"] == "12345678"
        assert result["result"]["accounts"][0]["hash_value"] == "abc123def456"

    @pytest.mark.journey_account
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error"
    )
    async def test_get_account_numbers_auth_error(
        self,
        mock_get_broker: AsyncMock,
        mock_schwab_auth_error: dict[str, Any],
    ) -> None:
        """Test account numbers when authentication fails."""
        mock_get_broker.return_value = (None, mock_schwab_auth_error)

        result = await get_schwab_account_numbers()

        assert result == mock_schwab_auth_error

    @pytest.mark.journey_account
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_account_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_account_tools.Client")
    async def test_get_account_success(
        self,
        mock_client: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
        schwab_account_payload: dict[str, Any],
    ) -> None:
        """Test successful account retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock Client.Account.Fields
        mock_client.Account.Fields.POSITIONS = "positions"

        mock_to_thread.return_value = schwab_account_payload

        result = await get_schwab_account("abc123")

        assert "result" in result
        assert "securitiesAccount" in result["result"]
        assert result["result"]["securitiesAccount"]["accountNumber"] == "12345678"

    @pytest.mark.journey_account
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_account_tools.execute_broker_request")
    async def test_get_accounts_success(
        self,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
        schwab_accounts_payload: list[dict[str, Any]],
    ) -> None:
        """Test successful accounts retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_to_thread.return_value = schwab_accounts_payload

        result = await get_schwab_accounts()

        assert "result" in result
        assert "accounts" in result["result"]
        assert len(result["result"]["accounts"]) == 2
        assert result["result"]["count"] == 2

    @pytest.mark.journey_portfolio
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_account_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_account_tools.Client")
    async def test_get_portfolio_success(
        self,
        mock_client: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
        mock_schwab_portfolio: dict[str, Any],
    ) -> None:
        """Test successful portfolio retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock Client.Account.Fields
        mock_client.Account.Fields.POSITIONS = "positions"

        mock_to_thread.return_value = mock_schwab_portfolio

        result = await get_schwab_portfolio("abc123")

        assert "result" in result
        assert "positions" in result["result"]
        assert len(result["result"]["positions"]) == 1
        assert result["result"]["positions"][0]["symbol"] == "AAPL"
        assert result["result"]["positions"][0]["quantity"] == 10.0

    @pytest.mark.journey_account
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_account_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_account_tools.Client")
    async def test_get_account_balances_success(
        self,
        mock_client: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
        schwab_balances_payload: dict[str, Any],
    ) -> None:
        """Test successful account balances retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_to_thread.return_value = schwab_balances_payload

        result = await get_schwab_account_balances("abc123")

        assert "result" in result
        assert "current_balances" in result["result"]
        assert result["result"]["current_balances"]["market_value"] == 50000.0
        assert result["result"]["current_balances"]["cash_balance"] == 10000.0

    @pytest.mark.journey_account
    @pytest.mark.unit
    @pytest.mark.exception_test
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_account_tools.execute_broker_request")
    async def test_get_account_numbers_error(
        self, mock_to_thread: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test account numbers error handling."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock API error
        mock_to_thread.side_effect = Exception("API Error")

        result = await get_schwab_account_numbers()

        assert "result" in result
        assert "error" in result["result"]

    @pytest.mark.journey_account
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_account_tools.execute_broker_request")
    @pytest.mark.parametrize(
        "function,args",
        [
            (get_schwab_account, ("abc123",)),
            (get_schwab_accounts, ()),
            (get_schwab_portfolio, ("abc123",)),
            (get_schwab_account_balances, ("abc123",)),
        ],
    )
    async def test_account_api_failures_bulk(
        self,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
        function,
        args,
    ) -> None:
        """Test various account tools for API failure responses."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        mock_to_thread.side_effect = Exception("API Error")

        result = await function(*args)
        assert result["result"]["status"] == "error"
        assert "API Error" in result["result"]["error"]

    @pytest.mark.journey_account
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_account_tools.execute_broker_request")
    async def test_get_user_preferences_success(
        self,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
        schwab_user_preferences_payload: dict[str, Any],
    ) -> None:
        """Test successful user preferences retrieval."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_to_thread.return_value = schwab_user_preferences_payload

        result = await get_schwab_user_preferences()

        assert "result" in result
        assert "user_preferences" in result["result"]
        assert result["result"]["user_preferences"]["userProps"]["firstName"] == "John"

    @pytest.mark.journey_account
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_account_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_account_tools.Client")
    async def test_get_all_account_data_success(
        self,
        mock_client: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
        schwab_user_preferences_payload: dict[str, Any],
        schwab_account_numbers_payload: list[dict[str, Any]],
        schwab_accounts_payload: list[dict[str, Any]],
    ) -> None:
        """Test successful aggregation of all account data."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock Client.Account.Fields
        mock_client.Account.Fields.POSITIONS = "positions"

        # Mock sequential calls in execute_broker_request
        mock_to_thread.side_effect = [
            schwab_user_preferences_payload,
            schwab_account_numbers_payload,
            schwab_accounts_payload,
        ]

        result = await get_schwab_all_account_data()

        assert "result" in result
        assert "user_preferences" in result["result"]
        assert "account_numbers" in result["result"]
        assert "accounts" in result["result"]
        assert result["result"]["count"] == 2

    @pytest.mark.journey_account
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_account_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_account_tools.Client")
    async def test_build_user_profile_success(
        self,
        mock_client: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
        schwab_user_preferences_payload: dict[str, Any],
        schwab_accounts_payload: list[dict[str, Any]],
    ) -> None:
        """Test successful normalized user profile building."""
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock Client.Account.Fields
        mock_client.Account.Fields.POSITIONS = "positions"

        # Mock sequential calls
        mock_to_thread.side_effect = [
            schwab_user_preferences_payload,
            schwab_accounts_payload,
        ]

        result = await build_schwab_user_profile()

        assert "result" in result
        assert "user_profile" in result["result"]
        profile = result["result"]["user_profile"]
        assert profile["account_count"] == 2
        assert "accounts" in profile
        assert "user_preferences" in profile


class TestSchwabMarginTools:
    """Test Schwab margin-status and margin-interest tools."""

    @pytest.mark.journey_notifications
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_account_tools.execute_broker_request")
    async def test_check_margin_status_active_call(
        self,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
        schwab_margin_call_balances_payload: dict[str, Any],
    ) -> None:
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_to_thread.return_value = schwab_margin_call_balances_payload

        result = await schwab_check_margin_status("abc123")

        assert result["result"]["margin_call"] is True
        assert result["result"]["equity"] == 25000.0
        assert result["result"]["maintenance_requirement"] == 30000.0
        assert result["result"]["deficit"] == 5000.0
        assert result["result"]["status"] == "success"

    @pytest.mark.journey_notifications
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_account_tools.execute_broker_request")
    async def test_check_margin_status_no_call(
        self,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
        schwab_no_margin_call_balances_payload: dict[str, Any],
    ) -> None:
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_to_thread.return_value = schwab_no_margin_call_balances_payload

        result = await schwab_check_margin_status("abc123")

        assert result["result"]["margin_call"] is False
        assert result["result"]["deficit"] == 0.0

    @pytest.mark.journey_notifications
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error"
    )
    async def test_check_margin_status_auth_error(
        self,
        mock_get_broker: AsyncMock,
        mock_schwab_auth_error: dict[str, Any],
    ) -> None:
        mock_get_broker.return_value = (None, mock_schwab_auth_error)
        result = await schwab_check_margin_status("abc123")
        assert result == mock_schwab_auth_error

    @pytest.mark.journey_notifications
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_account_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_account_tools.Client")
    async def test_get_margin_interest_filters_and_sums(
        self,
        mock_client: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
        schwab_margin_interest_transactions_payload: list[dict[str, Any]],
    ) -> None:
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_client.Transactions.TransactionType.DIVIDEND_OR_INTEREST = (
            "DIVIDEND_OR_INTEREST"
        )
        mock_to_thread.return_value = schwab_margin_interest_transactions_payload

        result = await schwab_get_margin_interest("abc123")

        assert result["result"]["charges_count"] == 2
        assert result["result"]["total_charges"] == pytest.approx(20.75)
        descriptions = [
            txn["description"] for txn in result["result"]["interest_charges"]
        ]
        assert "QUALIFIED DIVIDEND" not in descriptions
        for txn in result["result"]["interest_charges"]:
            assert "transactionId" in txn
            assert "description" in txn
            assert "netAmount" in txn
            assert "tradeDate" in txn

    @pytest.mark.journey_notifications
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error"
    )
    @patch("open_stocks_mcp.tools.schwab_account_tools.execute_broker_request")
    @patch("open_stocks_mcp.tools.schwab_account_tools.Client")
    async def test_get_margin_interest_empty(
        self,
        mock_client: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)
        mock_client.Transactions.TransactionType.DIVIDEND_OR_INTEREST = (
            "DIVIDEND_OR_INTEREST"
        )
        mock_to_thread.return_value = []

        result = await schwab_get_margin_interest("abc123")
        assert result["result"]["charges_count"] == 0
        assert result["result"]["total_charges"] == 0.0
        assert result["result"]["interest_charges"] == []

    @pytest.mark.journey_notifications
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error"
    )
    async def test_get_margin_interest_auth_error(
        self,
        mock_get_broker: AsyncMock,
        mock_schwab_auth_error: dict[str, Any],
    ) -> None:
        mock_get_broker.return_value = (None, mock_schwab_auth_error)
        result = await schwab_get_margin_interest("abc123")
        assert result == mock_schwab_auth_error
