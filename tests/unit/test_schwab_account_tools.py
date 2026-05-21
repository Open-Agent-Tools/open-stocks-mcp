"""Unit tests for Schwab account tools."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.tools.schwab_account_tools import (
    get_schwab_account,
    get_schwab_account_balances,
    get_schwab_account_numbers,
    get_schwab_accounts,
    get_schwab_portfolio,
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
        broker_auth_error_payload: dict[str, Any],
    ) -> None:
        """Test account numbers when authentication fails."""
        mock_get_broker.return_value = (None, broker_auth_error_payload)

        result = await get_schwab_account_numbers()

        assert result == broker_auth_error_payload

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
        schwab_account_payload: dict[str, Any],
    ) -> None:
        """Test successful portfolio retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock Client.Account.Fields
        mock_client.Account.Fields.POSITIONS = "positions"

        mock_to_thread.return_value = schwab_account_payload

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
