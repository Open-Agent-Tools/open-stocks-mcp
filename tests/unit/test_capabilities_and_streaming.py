from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

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

    async def get_account_info(self) -> dict[str, Any]:
        return {}

    async def get_portfolio(self) -> dict[str, Any]:
        return {}

    async def get_positions(self) -> dict[str, Any]:
        return {}

    async def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        return {}

    async def get_stock_price(self, symbol: str) -> dict[str, Any]:
        return {}

    async def order_buy_market(self, symbol: str, quantity: float) -> dict[str, Any]:
        return {}

    async def order_sell_market(self, symbol: str, quantity: float) -> dict[str, Any]:
        return {}


def test_broker_capabilities_defaults() -> None:
    capabilities = BrokerCapabilities()
    assert not capabilities.streaming_quotes
    assert not capabilities.options
    assert not capabilities.crypto


def test_base_broker_health_status() -> None:
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
async def test_schwab_stream_manager_handling() -> None:
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
    assert quote is not None
    assert quote["1"] == 150.0
    assert quote["2"] == 151.0


@pytest.mark.asyncio
async def test_schwab_stream_manager_option_quote_handling() -> None:
    from open_stocks_mcp.brokers.schwab_stream import SchwabStreamManager

    mock_broker = MagicMock()
    manager = SchwabStreamManager(mock_broker)

    # Test option message handling
    message = {
        "service": "LEVELONE_OPTIONS",
        "content": [{"key": "AAPL  260619C00150000", "1": 12.34, "2": 12.55}],
    }

    manager._handle_message(message)
    quote = manager.get_latest_option_quote("AAPL  260619C00150000")
    assert quote is not None
    assert quote["1"] == 12.34
    assert quote["2"] == 12.55

    # Verify equity cache is separate
    assert manager.get_latest_quote("AAPL") is None


@pytest.mark.asyncio
async def test_schwab_stream_manager_subscribe_option_quotes() -> None:
    from open_stocks_mcp.brokers.schwab_stream import SchwabStreamManager

    mock_broker = MagicMock()
    manager = SchwabStreamManager(mock_broker)
    manager._is_running = True
    manager.stream_client = AsyncMock()

    success = await manager.subscribe_option_quotes(["AAPL  260619C00150000"])
    assert success is True
    manager.stream_client.level_one_option_subs.assert_awaited_once_with(
        ["AAPL  260619C00150000"]
    )


@pytest.mark.asyncio
async def test_schwab_stream_manager_handles_level2_by_venue() -> None:
    from open_stocks_mcp.brokers.schwab_stream import SchwabStreamManager

    mock_broker = MagicMock()
    manager = SchwabStreamManager(mock_broker)

    manager._handle_message(
        {
            "service": "NASDAQ_BOOK",
            "content": [
                {"SYMBOL": "AAPL", "BOOK_TIME": 111, "BIDS": [{"p": 1}], "ASKS": []}
            ],
        }
    )
    manager._handle_message(
        {
            "service": "NYSE_BOOK",
            "content": [
                {"SYMBOL": "AAPL", "BOOK_TIME": 222, "BIDS": [], "ASKS": [{"p": 2}]}
            ],
        }
    )

    nasdaq_book = manager.get_latest_level2("AAPL", "nasdaq")
    nyse_book = manager.get_latest_level2("AAPL", "nyse")
    assert nasdaq_book is not None
    assert nyse_book is not None
    assert nasdaq_book["service"] == "NASDAQ_BOOK"
    assert nyse_book["service"] == "NYSE_BOOK"
    assert nasdaq_book["book_time"] == 111
    assert nyse_book["book_time"] == 222


@pytest.mark.asyncio
async def test_schwab_stream_manager_subscribe_level2() -> None:
    from open_stocks_mcp.brokers.schwab_stream import SchwabStreamManager

    mock_broker = MagicMock()
    manager = SchwabStreamManager(mock_broker)
    manager._is_running = True
    manager.stream_client = AsyncMock()

    success_nasdaq = await manager.subscribe_level2("AAPL", "nasdaq")
    success_nyse = await manager.subscribe_level2("AAPL", "nyse")
    unsupported = await manager.subscribe_level2("AAPL", "arca")

    assert success_nasdaq is True
    assert success_nyse is True
    assert unsupported is False
    manager.stream_client.nasdaq_book_subs.assert_awaited_once_with(["AAPL"])
    manager.stream_client.nyse_book_subs.assert_awaited_once_with(["AAPL"])


@pytest.mark.asyncio
async def test_schwab_stream_manager_subscribe_quotes_splitting() -> None:
    from open_stocks_mcp.brokers.schwab_stream import SchwabStreamManager

    mock_broker = MagicMock()
    manager = SchwabStreamManager(mock_broker)
    manager._is_running = True
    manager.stream_client = AsyncMock()

    symbols = ["AAPL", "AAPL  260619C00150000"]
    success = await manager.subscribe_quotes(symbols)
    assert success is True

    manager.stream_client.level_one_equity_subs.assert_awaited_once_with(["AAPL"])
    manager.stream_client.level_one_option_subs.assert_awaited_once_with(
        ["AAPL  260619C00150000"]
    )


@patch("schwab.streaming.StreamClient")
@pytest.mark.asyncio
async def test_schwab_stream_manager_start(mock_stream_client_class: MagicMock) -> None:
    from open_stocks_mcp.brokers.schwab_stream import SchwabStreamManager

    mock_broker = MagicMock()
    mock_broker.is_available.return_value = True
    mock_broker.client = MagicMock()

    manager = SchwabStreamManager(mock_broker)

    # Mock login to avoid actual connection
    mock_stream_client = mock_stream_client_class.return_value

    async def async_none() -> None:
        return None

    mock_stream_client.login = MagicMock(return_value=async_none())

    # We don't want to actually start the background loop in tests usually,
    # but we can mock it
    with patch("asyncio.create_task"):
        success = await manager.start()
        assert success is True
        assert manager.is_running is True


@pytest.mark.asyncio
async def test_schwab_stream_manager_handles_account_activity() -> None:
    from open_stocks_mcp.brokers.schwab_stream import SchwabStreamManager

    mock_broker = MagicMock()
    manager = SchwabStreamManager(mock_broker)

    message = {
        "service": "ACCT_ACTIVITY",
        "content": [{"key": "ACT001", "1": "OrderEntryRequest", "2": "<xml/>"}],
    }

    manager._handle_message(message)
    activity = manager.get_latest_activity()
    assert len(activity) == 1
    assert activity[0]["key"] == "ACT001"
    assert activity[0]["1"] == "OrderEntryRequest"
    assert activity[0]["2"] == "<xml/>"

    # Verify equity/option caches are unaffected
    assert manager.get_latest_quote("ACT001") is None
    assert manager.get_latest_option_quote("ACT001") is None


@pytest.mark.asyncio
async def test_schwab_stream_manager_subscribe_account_activity() -> None:
    from open_stocks_mcp.brokers.schwab_stream import SchwabStreamManager

    mock_broker = MagicMock()
    manager = SchwabStreamManager(mock_broker)
    manager._is_running = True
    manager.stream_client = AsyncMock()

    result = await manager.subscribe_account_activity()
    assert result is True
    manager.stream_client.account_activity_sub.assert_awaited_once()


@pytest.mark.asyncio
async def test_schwab_stream_manager_level2_handling() -> None:
    from open_stocks_mcp.brokers.schwab_stream import SchwabStreamManager

    mock_broker = MagicMock()
    manager = SchwabStreamManager(mock_broker)

    # Test NASDAQ_BOOK message handling
    nasdaq_message = {
        "service": "NASDAQ_BOOK",
        "content": [
            {
                "key": "AAPL",
                "SYMBOL": "AAPL",
                "BIDS": [{"PRICE": 150.0, "SIZE": 100}],
                "ASKS": [{"PRICE": 151.0, "SIZE": 200}],
            }
        ],
    }

    manager._handle_message(nasdaq_message)
    book = manager.get_latest_level2("AAPL")
    assert book is not None
    assert book["SYMBOL"] == "AAPL"
    assert book["BIDS"][0]["PRICE"] == 150.0

    # Test NYSE_BOOK message handling
    nyse_message = {
        "service": "NYSE_BOOK",
        "content": [
            {
                "key": "IBM",
                "SYMBOL": "IBM",
                "BIDS": [{"PRICE": 130.0, "SIZE": 50}],
                "ASKS": [{"PRICE": 131.0, "SIZE": 60}],
            }
        ],
    }

    manager._handle_message(nyse_message)
    book = manager.get_latest_level2("IBM")
    assert book is not None
    assert book["SYMBOL"] == "IBM"
    assert book["BIDS"][0]["PRICE"] == 130.0


@pytest.mark.asyncio
async def test_schwab_stream_manager_subscribe_level2() -> None:
    from open_stocks_mcp.brokers.schwab_stream import SchwabStreamManager

    mock_broker = MagicMock()
    manager = SchwabStreamManager(mock_broker)
    manager._is_running = True
    manager.stream_client = AsyncMock()

    # Test NASDAQ subscription
    success = await manager.subscribe_level2("AAPL", "nasdaq")
    assert success is True
    manager.stream_client.nasdaq_book_subs.assert_awaited_once_with(["AAPL"])

    # Test NYSE subscription
    success = await manager.subscribe_level2("IBM", "nyse")
    assert success is True
    manager.stream_client.nyse_book_subs.assert_awaited_once_with(["IBM"])

    # Test unsupported venue
    success = await manager.subscribe_level2("AAPL", "unknown")
    assert success is False


@patch("schwab.streaming.StreamClient")
@pytest.mark.asyncio
async def test_schwab_stream_manager_start_registers_book_handlers(
    mock_stream_client_class: MagicMock,
) -> None:
    from open_stocks_mcp.brokers.schwab_stream import SchwabStreamManager

    mock_broker = MagicMock()
    mock_broker.is_available.return_value = True
    mock_broker.client = MagicMock()

    manager = SchwabStreamManager(mock_broker)
    mock_stream_client = mock_stream_client_class.return_value
    mock_stream_client.login = AsyncMock()

    with patch("asyncio.create_task"):
        await manager.start()
        mock_stream_client.add_nasdaq_book_handler.assert_called_once()
        mock_stream_client.add_nyse_book_handler.assert_called_once()
