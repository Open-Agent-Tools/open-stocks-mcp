"""Unit tests for broker comparison tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.brokers.base import BaseBroker, BrokerAuthStatus


class MockBroker(BaseBroker):
    """Mock broker for testing."""

    def __init__(self, name: str, authenticated: bool = True):
        super().__init__(name)
        if authenticated:
            self._auth_info.status = BrokerAuthStatus.AUTHENTICATED
        else:
            self._auth_info.status = BrokerAuthStatus.AUTH_FAILED
            self._auth_info.error_message = "Mock auth failed"

    async def authenticate(self) -> bool:
        return self._auth_info.status == BrokerAuthStatus.AUTHENTICATED

    async def is_authenticated(self) -> bool:
        return self._auth_info.status == BrokerAuthStatus.AUTHENTICATED

    async def logout(self) -> None:
        self._auth_info.status = BrokerAuthStatus.NOT_AUTHENTICATED

    async def get_account_info(self):
        return {"result": {"mock": "account"}}

    async def get_portfolio(self):
        return {"result": {"mock": "portfolio"}}

    async def get_positions(self):
        return {"result": {"mock": "positions"}}

    async def get_stock_quote(self, symbol: str):
        return {"result": {"price": 100}}

    async def get_stock_price(self, symbol: str):
        return {"result": {"price": 100}}

    async def order_buy_market(self, symbol: str, quantity: float):
        return {"result": {"order": "buy"}}

    async def order_sell_market(self, symbol: str, quantity: float):
        return {"result": {"order": "sell"}}


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_broker_comparison_success():
    """Test successful broker comparison with both brokers available."""
    # We need to import it here because it doesn't exist yet
    from open_stocks_mcp.tools.broker_comparison_tools import get_broker_comparison

    mock_registry = MagicMock()
    mock_registry.list_brokers.return_value = ["robinhood", "schwab"]

    rh_broker = MockBroker("robinhood", authenticated=True)
    schwab_broker = MockBroker("schwab", authenticated=True)
    mock_registry.get_broker.side_effect = lambda name: (
        rh_broker if name == "robinhood" else schwab_broker
    )

    # Mock Robinhood responses
    mock_rh_price = AsyncMock(
        return_value={"result": {"symbol": "AAPL", "price": 150.0, "status": "success"}}
    )
    mock_rh_portfolio = AsyncMock(
        return_value={
            "result": {"equity": 10000.0, "buying_power": 2000.0, "status": "success"}
        }
    )
    mock_rh_positions = AsyncMock(
        return_value={
            "result": {
                "positions": [{"symbol": "AAPL", "quantity": 10}],
                "status": "success",
            }
        }
    )
    mock_rh_orders = AsyncMock(
        return_value={
            "result": {
                "orders": [
                    {"symbol": "AAPL", "side": "BUY", "quantity": 5, "state": "filled"}
                ],
                "status": "success",
            }
        }
    )

    # Mock Schwab responses
    mock_schwab_quote = AsyncMock(
        return_value={
            "result": {"symbol": "AAPL", "last_price": 150.5, "status": "success"}
        }
    )
    mock_schwab_account_numbers = AsyncMock(
        return_value={
            "result": {"accounts": [{"hash_value": "hash1"}], "status": "success"}
        }
    )
    mock_schwab_balances = AsyncMock(
        return_value={
            "result": {
                "current_balances": {"liquidationValue": 5000.0, "buyingPower": 1000.0},
                "status": "success",
            }
        }
    )
    mock_schwab_portfolio = AsyncMock(
        return_value={
            "result": {
                "positions": [{"symbol": "AAPL", "quantity": 5}],
                "status": "success",
            }
        }
    )
    mock_schwab_orders = AsyncMock(
        return_value={
            "result": {
                "orders": [
                    {
                        "orderLegCollection": [
                            {
                                "instruction": "BUY",
                                "quantity": 2,
                                "instrument": {"symbol": "AAPL"},
                            }
                        ],
                        "status": "FILLED",
                        "enteredTime": "2023-10-27T14:55:00Z",
                        "price": 150.5,
                    }
                ],
                "status": "success",
            }
        }
    )

    with (
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_broker_registry",
            return_value=mock_registry,
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_stock_price",
            mock_rh_price,
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_portfolio",
            mock_rh_portfolio,
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_positions",
            mock_rh_positions,
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_stock_orders",
            mock_rh_orders,
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_schwab_quote",
            mock_schwab_quote,
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_schwab_account_numbers",
            mock_schwab_account_numbers,
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_schwab_account_balances",
            mock_schwab_balances,
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_schwab_portfolio",
            mock_schwab_portfolio,
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_schwab_orders",
            mock_schwab_orders,
        ),
    ):
        result = await get_broker_comparison(symbols=["AAPL"])

    assert result["result"]["status"] == "success"
    data = result["result"]
    assert "brokers" in data
    assert "comparison" in data

    # Check Robinhood data normalization
    rh_data = data["brokers"]["robinhood"]
    assert rh_data["available"] is True
    assert rh_data["pricing"]["AAPL"]["price"] == 150.0
    assert rh_data["holdings"]["AAPL"]["quantity"] == 10
    assert rh_data["orders"][0]["symbol"] == "AAPL"

    # Check Schwab data normalization
    schwab_data = data["brokers"]["schwab"]
    assert schwab_data["available"] is True
    assert schwab_data["pricing"]["AAPL"]["price"] == 150.5
    assert schwab_data["holdings"]["AAPL"]["quantity"] == 5
    assert schwab_data["orders"][0]["symbol"] == "AAPL"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_broker_comparison_partial_failure():
    """Test broker comparison when one broker is unavailable."""
    from open_stocks_mcp.tools.broker_comparison_tools import get_broker_comparison

    mock_registry = MagicMock()
    mock_registry.list_brokers.return_value = ["robinhood", "schwab"]

    rh_broker = MockBroker("robinhood", authenticated=True)
    schwab_broker = MockBroker("schwab", authenticated=False)  # Schwab down
    mock_registry.get_broker.side_effect = lambda name: (
        rh_broker if name == "robinhood" else schwab_broker
    )

    # Mock Robinhood responses
    mock_rh_price = AsyncMock(
        return_value={"result": {"symbol": "AAPL", "price": 150.0, "status": "success"}}
    )
    mock_rh_portfolio = AsyncMock(
        return_value={
            "result": {"equity": 10000.0, "buying_power": 2000.0, "status": "success"}
        }
    )
    mock_rh_positions = AsyncMock(
        return_value={
            "result": {
                "positions": [{"symbol": "AAPL", "quantity": 10}],
                "status": "success",
            }
        }
    )
    mock_rh_orders = AsyncMock(
        return_value={"result": {"orders": [], "status": "success"}}
    )

    with (
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_broker_registry",
            return_value=mock_registry,
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_stock_price",
            mock_rh_price,
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_portfolio",
            mock_rh_portfolio,
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_positions",
            mock_rh_positions,
        ),
        patch(
            "open_stocks_mcp.tools.broker_comparison_tools.get_stock_orders",
            mock_rh_orders,
        ),
    ):
        result = await get_broker_comparison(symbols=["AAPL"])

    assert result["result"]["status"] == "partial"
    data = result["result"]
    assert data["brokers"]["robinhood"]["available"] is True
    assert data["brokers"]["schwab"]["available"] is False
    assert "schwab" in data["availability_notes"]
