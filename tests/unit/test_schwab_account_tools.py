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
    @patch("open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_account_tools.asyncio.to_thread")
    async def test_get_account_numbers_success(
        self, mock_to_thread: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test successful account numbers retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "accountNumber": "12345678",
                "hashValue": "abc123def456",
            },
            {
                "accountNumber": "87654321",
                "hashValue": "xyz789uvw012",
            },
        ]
        mock_broker.client.get_account_numbers.return_value = mock_response
        mock_get_broker.return_value = (mock_broker, None)

        # Mock asyncio.to_thread
        mock_to_thread.return_value = [
            {"accountNumber": "12345678", "hashValue": "abc123def456"},
            {"accountNumber": "87654321", "hashValue": "xyz789uvw012"},
        ]

        result = await get_schwab_account_numbers()

        assert "result" in result
        assert "accounts" in result["result"]
        assert len(result["result"]["accounts"]) == 2
        assert result["result"]["accounts"][0]["hash"] == "abc123def456"

    @pytest.mark.journey_account
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error")
    async def test_get_account_numbers_auth_error(
        self, mock_get_broker: AsyncMock
    ) -> None:
        """Test account numbers when authentication fails."""
        # Mock authentication error
        error_response = {"result": {"error": "Not authenticated", "status": "error"}}
        mock_get_broker.return_value = (None, error_response)

        result = await get_schwab_account_numbers()

        assert result == error_response

    @pytest.mark.journey_account
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_account_tools.asyncio.to_thread")
    @patch("open_stocks_mcp.tools.schwab_account_tools.Client")
    async def test_get_account_success(
        self,
        mock_client: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test successful account retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock Client.Account.Fields
        mock_client.Account.Fields.POSITIONS = "positions"

        # Mock response
        mock_to_thread.return_value = {
            "securitiesAccount": {
                "accountNumber": "12345678",
                "type": "MARGIN",
                "roundTrips": 0,
                "isDayTrader": False,
                "isClosingOnlyRestricted": False,
                "positions": [],
            }
        }

        result = await get_schwab_account("abc123")

        assert "result" in result
        assert "account" in result["result"]
        assert result["result"]["account"]["accountNumber"] == "12345678"

    @pytest.mark.journey_account
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_account_tools.asyncio.to_thread")
    async def test_get_accounts_success(
        self, mock_to_thread: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test successful accounts retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock response
        mock_to_thread.return_value = [
            {
                "securitiesAccount": {
                    "accountNumber": "12345678",
                    "type": "MARGIN",
                }
            },
            {
                "securitiesAccount": {
                    "accountNumber": "87654321",
                    "type": "CASH",
                }
            },
        ]

        result = await get_schwab_accounts()

        assert "result" in result
        assert "accounts" in result["result"]
        assert len(result["result"]["accounts"]) == 2
        assert result["result"]["count"] == 2

    @pytest.mark.journey_portfolio
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_account_tools.asyncio.to_thread")
    @patch("open_stocks_mcp.tools.schwab_account_tools.Client")
    async def test_get_portfolio_success(
        self,
        mock_client: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test successful portfolio retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock Client.Account.Fields
        mock_client.Account.Fields.POSITIONS = "positions"

        # Mock response with positions
        mock_to_thread.return_value = {
            "securitiesAccount": {
                "positions": [
                    {
                        "shortQuantity": 0.0,
                        "averagePrice": 150.0,
                        "currentDayProfitLoss": 50.0,
                        "currentDayProfitLossPercentage": 2.5,
                        "longQuantity": 10.0,
                        "settledLongQuantity": 10.0,
                        "settledShortQuantity": 0.0,
                        "instrument": {
                            "assetType": "EQUITY",
                            "cusip": "037833100",
                            "symbol": "AAPL",
                        },
                        "marketValue": 1500.0,
                    }
                ]
            }
        }

        result = await get_schwab_portfolio("abc123")

        assert "result" in result
        assert "positions" in result["result"]
        assert len(result["result"]["positions"]) == 1
        assert result["result"]["positions"][0]["symbol"] == "AAPL"
        assert result["result"]["positions"][0]["quantity"] == 10.0

    @pytest.mark.journey_account
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_account_tools.asyncio.to_thread")
    @patch("open_stocks_mcp.tools.schwab_account_tools.Client")
    async def test_get_account_balances_success(
        self,
        mock_client: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test successful account balances retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock response with balances
        mock_to_thread.return_value = {
            "securitiesAccount": {
                "currentBalances": {
                    "liquidationValue": 50000.0,
                    "cashBalance": 10000.0,
                    "longMarketValue": 40000.0,
                    "shortMarketValue": 0.0,
                },
                "initialBalances": {
                    "accountValue": 48000.0,
                },
            }
        }

        result = await get_schwab_account_balances("abc123")

        assert "result" in result
        assert "current_balances" in result["result"]
        assert result["result"]["current_balances"]["liquidation_value"] == 50000.0
        assert result["result"]["current_balances"]["cash_balance"] == 10000.0

    @pytest.mark.journey_account
    @pytest.mark.unit
    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_account_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_account_tools.asyncio.to_thread")
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
