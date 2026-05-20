"""Unit tests for broker comparison tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.tools.broker_comparison_tools import get_broker_comparison


class TestGetBrokerComparison:
    """Tests for broker-normalized comparison data and partial failure handling."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_successful_comparison(self):
        """Assert comparison returns normalized data from both brokers."""
        # Mocking Robinhood responses
        rh_price = {"result": {"price": 150.0, "symbol": "AAPL"}}
        rh_portfolio = {"result": {"equity": 10000.0, "buying_power": 5000.0}}
        rh_positions = {"result": {"positions": [{"symbol": "AAPL", "quantity": 10}]}}
        rh_orders = {"result": [{"symbol": "AAPL", "side": "buy", "state": "filled", "quantity": 5, "price": 145.0}]}

        # Mocking Schwab responses
        schwab_quote = {"result": {"last_price": 151.0, "symbol": "AAPL"}}
        schwab_account_numbers = {"result": [{"hash": "account_1"}]}
        schwab_balances = {"result": {"currentBalances": {"liquidationValue": 8000.0, "buyingPower": 2000.0}}}
        schwab_portfolio = {"result": {"securitiesAccount": {"positions": [{"instrument": {"symbol": "AAPL"}, "longQuantity": 5, "marketValue": 755.0}]}}}
        schwab_orders = {"result": {"orders": [{"symbol": "AAPL", "orderLegCollection": [{"instruction": "BUY", "instrument": {"symbol": "AAPL"}}], "status": "FILLED", "quantity": 2, "price": 148.0}]}}

        # Setup registry mock
        mock_registry_instance = MagicMock()
        mock_registry_instance.list_brokers.return_value = ["robinhood", "schwab"]
        rh_broker = MagicMock()
        rh_broker.is_available.return_value = True
        schwab_broker = MagicMock()
        schwab_broker.is_available.return_value = True
        mock_registry_instance.get_broker.side_effect = lambda name: rh_broker if name == "robinhood" else schwab_broker

        with (
            patch("open_stocks_mcp.tools.broker_comparison_tools.get_stock_price", AsyncMock(return_value=rh_price)),
            patch("open_stocks_mcp.tools.broker_comparison_tools.get_portfolio", AsyncMock(return_value=rh_portfolio)),
            patch("open_stocks_mcp.tools.broker_comparison_tools.get_positions", AsyncMock(return_value=rh_positions)),
            patch("open_stocks_mcp.tools.broker_comparison_tools.get_stock_orders", AsyncMock(return_value=rh_orders)),
            patch("open_stocks_mcp.tools.broker_comparison_tools.get_schwab_quote", AsyncMock(return_value=schwab_quote)),
            patch("open_stocks_mcp.tools.broker_comparison_tools.get_schwab_account_numbers", AsyncMock(return_value=schwab_account_numbers)),
            patch("open_stocks_mcp.tools.broker_comparison_tools.get_schwab_account_balances", AsyncMock(return_value=schwab_balances)),
            patch("open_stocks_mcp.tools.broker_comparison_tools.get_schwab_portfolio", AsyncMock(return_value=schwab_portfolio)),
            patch("open_stocks_mcp.tools.broker_comparison_tools.get_schwab_orders", AsyncMock(return_value=schwab_orders)),
            patch("open_stocks_mcp.tools.broker_comparison_tools.get_broker_registry", AsyncMock(return_value=mock_registry_instance)),
        ):
            result = await get_broker_comparison(symbols=["AAPL"])

        assert result["result"]["status"] == "success"
        comparison = result["result"]["comparison"]
        assert "AAPL" in comparison
        
        # Verify Robinhood normalization
        rh_data = result["result"]["brokers"]["robinhood"]
        assert rh_data["available"] is True
        assert rh_data["pricing"]["AAPL"]["price"] == 150.0
        assert rh_data["holdings"]["AAPL"]["quantity"] == 10
        assert len(rh_data["orders"]) == 1
        assert rh_data["orders"][0]["side"] == "buy"

        # Verify Schwab normalization
        schwab_data = result["result"]["brokers"]["schwab"]
        assert schwab_data["available"] is True
        assert schwab_data["pricing"]["AAPL"]["price"] == 151.0
        assert schwab_data["holdings"]["AAPL"]["quantity"] == 5
        assert len(schwab_data["orders"]) == 1
        assert schwab_data["orders"][0]["side"] == "buy"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_partial_failure(self):
        """Assert comparison remains present for Robinhood when Schwab fails."""
        # Robinhood success mocks
        rh_price = {"result": {"price": 150.0, "symbol": "AAPL"}}
        rh_portfolio = {"result": {"equity": 10000.0, "buying_power": 5000.0}}
        rh_positions = {"result": {"positions": [{"symbol": "AAPL", "quantity": 10}]}}
        rh_orders = {"result": []}

        # Schwab failure mock
        schwab_failure = {"result": {"status": "broker_unavailable", "error": "API Error"}}

        # Setup registry mock
        mock_registry_instance = MagicMock()
        mock_registry_instance.list_brokers.return_value = ["robinhood", "schwab"]
        rh_broker = MagicMock()
        rh_broker.is_available.return_value = True
        schwab_broker = MagicMock()
        schwab_broker.is_available.return_value = True
        mock_registry_instance.get_broker.side_effect = lambda name: rh_broker if name == "robinhood" else schwab_broker

        with (
            patch("open_stocks_mcp.tools.broker_comparison_tools.get_stock_price", AsyncMock(return_value=rh_price)),
            patch("open_stocks_mcp.tools.broker_comparison_tools.get_portfolio", AsyncMock(return_value=rh_portfolio)),
            patch("open_stocks_mcp.tools.broker_comparison_tools.get_positions", AsyncMock(return_value=rh_positions)),
            patch("open_stocks_mcp.tools.broker_comparison_tools.get_stock_orders", AsyncMock(return_value=rh_orders)),
            patch("open_stocks_mcp.tools.broker_comparison_tools.get_schwab_account_numbers", AsyncMock(return_value=schwab_failure)),
            patch("open_stocks_mcp.tools.broker_comparison_tools.get_broker_registry", AsyncMock(return_value=mock_registry_instance)),
        ):
            result = await get_broker_comparison(symbols=["AAPL"])

        assert result["result"]["status"] == "partial"
        assert "robinhood" in result["result"]["brokers"]
        assert result["result"]["brokers"]["robinhood"]["available"] is True
        assert result["result"]["brokers"]["schwab"]["available"] is False
        assert "schwab" in result["result"]["availability_notes"]
