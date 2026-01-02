"""Unit tests for Schwab options tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.tools.schwab_options_tools import (
    get_schwab_option_chain,
    get_schwab_option_chain_by_expiration,
    get_schwab_option_expirations,
    get_schwab_options_positions,
    schwab_option_buy_to_open,
    schwab_option_sell_to_close,
)


class TestSchwabOptionsTools:
    """Test Schwab options tools with mocked responses."""

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_options_tools.asyncio.to_thread")
    @patch("open_stocks_mcp.tools.schwab_options_tools.Client")
    async def test_get_option_chain_success(
        self,
        mock_client: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test successful option chain retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock Client enums
        mock_client.Options.ContractType.CALL = "CALL"
        mock_client.Options.ContractType.PUT = "PUT"
        mock_client.Options.ContractType.ALL = "ALL"

        # Mock response
        mock_to_thread.return_value = {
            "symbol": "AAPL",
            "status": "SUCCESS",
            "underlying": {"symbol": "AAPL", "last": 175.50},
            "callExpDateMap": {
                "2024-01-19": {
                    "170.0": [
                        {
                            "putCall": "CALL",
                            "symbol": "AAPL_011924C170",
                            "description": "AAPL Jan 19 2024 170 Call",
                            "bid": 6.50,
                            "ask": 6.55,
                        }
                    ]
                }
            },
        }

        result = await get_schwab_option_chain(
            "AAPL", contract_type="call", strike_count=5
        )

        assert "result" in result
        assert result["result"]["symbol"] == "AAPL"

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error")
    async def test_get_option_chain_auth_error(
        self, mock_get_broker: AsyncMock
    ) -> None:
        """Test option chain when authentication fails."""
        # Mock authentication error
        error_response = {"result": {"error": "Not authenticated", "status": "error"}}
        mock_get_broker.return_value = (None, error_response)

        result = await get_schwab_option_chain("AAPL")

        assert result == error_response

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error")
    async def test_get_option_chain_invalid_contract_type(
        self, mock_get_broker: AsyncMock
    ) -> None:
        """Test option chain with invalid contract type."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        result = await get_schwab_option_chain("AAPL", contract_type="invalid")

        assert "result" in result
        assert "error" in result["result"]
        assert "Invalid contract_type" in result["result"]["error"]

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_options_tools.asyncio.to_thread")
    @patch("open_stocks_mcp.tools.schwab_options_tools.Client")
    async def test_get_option_chain_by_expiration_success(
        self,
        mock_client: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test successful option chain by expiration retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock Client enums
        mock_client.Options.ContractType.CALL = "CALL"

        # Mock response
        mock_to_thread.return_value = {
            "symbol": "AAPL",
            "status": "SUCCESS",
            "callExpDateMap": {},
        }

        result = await get_schwab_option_chain_by_expiration(
            "AAPL", from_date="2024-01-01", to_date="2024-12-31", contract_type="call"
        )

        assert "result" in result
        assert result["result"]["symbol"] == "AAPL"

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_options_tools.asyncio.to_thread")
    async def test_get_option_expirations_success(
        self, mock_to_thread: AsyncMock, mock_get_broker: AsyncMock
    ) -> None:
        """Test successful option expirations retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock response
        mock_to_thread.return_value = {
            "expirationList": [
                {"expirationDate": "2024-01-19"},
                {"expirationDate": "2024-02-16"},
                {"expirationDate": "2024-03-15"},
            ]
        }

        result = await get_schwab_option_expirations("AAPL")

        assert "result" in result
        assert result["result"]["symbol"] == "AAPL"
        assert len(result["result"]["expirations"]) == 3
        assert result["result"]["count"] == 3

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_options_tools.asyncio.to_thread")
    @patch("open_stocks_mcp.tools.schwab_options_tools.Client")
    async def test_get_options_positions_success(
        self,
        mock_client: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test successful options positions retrieval."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock Client.Account.Fields
        mock_client.Account.Fields.POSITIONS = "positions"

        # Mock response
        mock_to_thread.return_value = {
            "securitiesAccount": {
                "positions": [
                    {
                        "shortQuantity": 0.0,
                        "averagePrice": 6.50,
                        "currentDayProfitLoss": 50.0,
                        "longQuantity": 1.0,
                        "instrument": {
                            "assetType": "OPTION",
                            "symbol": "AAPL_011924C170",
                            "underlyingSymbol": "AAPL",
                            "putCall": "CALL",
                            "strikePrice": 170.0,
                            "expirationDate": "2024-01-19",
                        },
                        "marketValue": 700.0,
                    },
                    {
                        "shortQuantity": 0.0,
                        "averagePrice": 150.0,
                        "currentDayProfitLoss": -25.0,
                        "longQuantity": 10.0,
                        "instrument": {
                            "assetType": "EQUITY",
                            "symbol": "AAPL",
                        },
                        "marketValue": 1750.0,
                    },
                ]
            }
        }

        result = await get_schwab_options_positions("abc123")

        assert "result" in result
        assert "positions" in result["result"]
        assert len(result["result"]["positions"]) == 1  # Only options
        assert result["result"]["positions"][0]["symbol"] == "AAPL_011924C170"
        assert result["result"]["positions"][0]["option_type"] == "CALL"

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_options_tools.asyncio.to_thread")
    @patch("open_stocks_mcp.tools.schwab_options_tools.option_buy_to_open_market")
    async def test_option_buy_to_open_success(
        self,
        mock_order_template: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test successful option buy to open order."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock order template
        mock_order_template.return_value = {"orderType": "MARKET"}

        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"Location": "/orders/12345"}
        mock_to_thread.return_value = mock_response

        result = await schwab_option_buy_to_open(
            "abc123", "AAPL", 1, "CALL", 170.0, "2024-01-19"
        )

        assert "result" in result
        assert result["result"]["status"] == "order_placed"
        assert result["result"]["action"] == "buy_to_open"
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["option_type"] == "CALL"

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_options_tools.asyncio.to_thread")
    @patch("open_stocks_mcp.tools.schwab_options_tools.option_sell_to_close_market")
    async def test_option_sell_to_close_success(
        self,
        mock_order_template: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test successful option sell to close order."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock order template
        mock_order_template.return_value = {"orderType": "MARKET"}

        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Location": "/orders/67890"}
        mock_to_thread.return_value = mock_response

        result = await schwab_option_sell_to_close(
            "abc123", "AAPL", 1, "PUT", 165.0, "2024-02-16"
        )

        assert "result" in result
        assert result["result"]["status"] == "order_placed"
        assert result["result"]["action"] == "sell_to_close"
        assert result["result"]["symbol"] == "AAPL"
        assert result["result"]["option_type"] == "PUT"

    @pytest.mark.journey_options
    @pytest.mark.unit
    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @pytest.mark.asyncio
    @patch("open_stocks_mcp.tools.schwab_options_tools.get_authenticated_broker_or_error")
    @patch("open_stocks_mcp.tools.schwab_options_tools.asyncio.to_thread")
    @patch("open_stocks_mcp.tools.schwab_options_tools.Client")
    async def test_get_option_chain_error(
        self,
        mock_client: MagicMock,
        mock_to_thread: AsyncMock,
        mock_get_broker: AsyncMock,
    ) -> None:
        """Test option chain error handling."""
        # Mock broker
        mock_broker = MagicMock()
        mock_get_broker.return_value = (mock_broker, None)

        # Mock Client enums
        mock_client.Options.ContractType.CALL = "CALL"

        # Mock API error
        mock_to_thread.side_effect = Exception("API Error")

        result = await get_schwab_option_chain("AAPL", contract_type="call")

        assert "result" in result
        assert "error" in result["result"]
