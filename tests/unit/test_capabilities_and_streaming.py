import pytest
import asyncio
from unittest.mock import MagicMock, patch
from open_stocks_mcp.brokers.schwab_stream import SchwabStreamManager

@pytest.mark.asyncio
async def test_schwab_stream_manager_handling():
    """Test that SchwabStreamManager correctly handles and caches quote messages."""
    mock_broker = MagicMock()
    manager = SchwabStreamManager(mock_broker)
    
    # Test message handling
    message = {
        "service": "LEVELONE_EQUITIES",
        "content": [
            {"key": "AAPL", "1": 150.0, "2": 151.0}
        ]
    }
    
    manager._handle_message(message)
    quote = manager.get_latest_quote("AAPL")
    assert quote["key"] == "AAPL"
    assert quote["1"] == 150.0
    assert quote["2"] == 151.0

@patch("schwab.streaming.StreamClient")
@pytest.mark.asyncio
async def test_schwab_stream_manager_start(mock_stream_client_class):
    """Test starting the SchwabStreamManager."""
    from open_stocks_mcp.brokers.schwab_stream import SchwabStreamManager
    
    mock_broker = MagicMock()
    mock_broker.is_available.return_value = True
    mock_broker.client = MagicMock()
    
    manager = SchwabStreamManager(mock_broker)
    
    # Mock StreamClient
    mock_stream_client = mock_stream_client_class.return_value
    
    async def async_none():
        return None
    
    mock_stream_client.login = MagicMock(side_effect=async_none)
    
    with patch("asyncio.create_task"):
        success = await manager.start()
        assert success is True
        assert manager.is_running is True

@patch("schwab.streaming.StreamClient")
@pytest.mark.asyncio
async def test_schwab_stream_manager_subscribe(mock_stream_client_class):
    """Test subscribing to quotes via SchwabStreamManager."""
    mock_broker = MagicMock()
    mock_broker.is_available.return_value = True
    mock_broker.client = MagicMock()
    
    manager = SchwabStreamManager(mock_broker)
    
    # Start manager
    mock_stream_client = mock_stream_client_class.return_value
    async def async_none(*args, **kwargs): return None
    mock_stream_client.login = MagicMock(side_effect=async_none)
    mock_stream_client.level_one_equity_subs = MagicMock(side_effect=async_none)
    
    with patch("asyncio.create_task"):
        await manager.start()
        success = await manager.subscribe_quotes(["AAPL", "GOOGL"])
        
        assert success is True
        mock_stream_client.level_one_equity_subs.assert_called_with(["AAPL", "GOOGL"])
