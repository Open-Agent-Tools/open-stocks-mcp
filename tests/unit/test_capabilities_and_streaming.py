from unittest.mock import MagicMock, patch

import pytest

from open_stocks_mcp.brokers.base import (
    BaseBroker,
    BrokerAuthStatus,
    BrokerCapabilities,
)


class MockBroker(BaseBroker):
    async def authenticate(self) -> bool:
        return True

    async def is_authenticated(self) -> bool:
        return True

    async def logout(self) -> None:
        pass

    async def get_account_info(self):
        return {}

    async def get_portfolio(self):
        return {}

    async def get_positions(self):
        return {}

    async def get_stock_quote(self, symbol):
        return {}

    async def get_stock_price(self, symbol):
        return {}

    async def order_buy_market(self, symbol, quantity):
        return {}

    async def order_sell_market(self, symbol, quantity):
        return {}


def test_broker_capabilities_defaults():
    capabilities = BrokerCapabilities()
    assert not capabilities.streaming_quotes
    assert not capabilities.options
    assert not capabilities.crypto


def test_base_broker_health_status():
    broker = MockBroker("test_broker")
    broker._auth_info.status = BrokerAuthStatus.AUTHENTICATED
    broker._capabilities.streaming_quotes = True

    status = broker.get_health_status()
    assert status["broker"] == "test_broker"
    assert status["is_available"] is True
    assert status["auth_status"] == "authenticated"
    assert status["capabilities"]["streaming_quotes"] is True
    assert status["streaming_ready"] is True


@pytest.mark.asyncio
async def test_schwab_stream_manager_handling():
    from open_stocks_mcp.brokers.schwab_stream import SchwabStreamManager

    mock_broker = MagicMock()
    manager = SchwabStreamManager(mock_broker)

    # Test message handling
    message = {
        "service": "LEVELONE_EQUITIES",
        "content": [{"key": "AAPL", "1": 150.0, "2": 151.0}],
    }

    manager._handle_message(message)
    quote = manager.get_latest_quote("AAPL")
    assert quote["1"] == 150.0
    assert quote["2"] == 151.0


@patch("schwab.streaming.StreamClient")
@pytest.mark.asyncio
async def test_schwab_stream_manager_start(mock_stream_client_class):
    from open_stocks_mcp.brokers.schwab_stream import SchwabStreamManager

    mock_broker = MagicMock()
    mock_broker.is_available.return_value = True
    mock_broker.client = MagicMock()

    manager = SchwabStreamManager(mock_broker)

    # Mock login to avoid actual connection
    mock_stream_client = mock_stream_client_class.return_value

    async def async_none():
        return None

    mock_stream_client.login = MagicMock(return_value=async_none())

    # We don't want to actually start the background loop in tests usually,
    # but we can mock it
    with patch("asyncio.create_task"):
        success = await manager.start()
        assert success is True
        assert manager.is_running is True
