"""Unit tests for unified watchlist tools."""

from unittest.mock import MagicMock, patch

import pytest

from open_stocks_mcp.tools.unified_watchlist_tools import (
    add_symbols_to_unified_watchlist,
    get_unified_watchlist_by_name,
    get_unified_watchlists,
    remove_symbols_from_unified_watchlist,
)


@pytest.fixture
def mock_registry():
    with patch(
        "open_stocks_mcp.tools.unified_watchlist_tools.get_broker_registry"
    ) as mock:
        registry = MagicMock()
        mock.return_value = registry
        yield registry


@pytest.fixture
def mock_robinhood():
    broker = MagicMock()
    broker.name = "robinhood"
    broker.is_available.return_value = True
    return broker


@pytest.fixture
def mock_schwab():
    broker = MagicMock()
    broker.name = "schwab"
    broker.is_available.return_value = True
    return broker


@pytest.mark.asyncio
async def test_get_unified_watchlists_success(
    mock_registry, mock_robinhood, mock_schwab
):
    """Test normalized response for all watchlists across brokers."""
    mock_registry.list_brokers.return_value = ["robinhood", "schwab"]
    mock_registry.get_broker.side_effect = lambda name: (
        mock_robinhood if name == "robinhood" else mock_schwab
    )

    rh_watchlists = {
        "result": {
            "watchlists": [
                {"name": "Tech", "symbols": ["AAPL", "MSFT"], "symbol_count": 2}
            ],
            "status": "success",
        }
    }

    with patch(
        "open_stocks_mcp.tools.unified_watchlist_tools.get_rh_watchlists",
        return_value=rh_watchlists,
    ):
        result = await get_unified_watchlists()

    assert result["result"]["status"] in ["success", "partial_success"]
    assert "robinhood" in result["result"]["brokers"]
    assert "schwab" in result["result"]["brokers"]
    assert result["result"]["brokers"]["schwab"]["status"] == "unsupported"

    # Check aggregation
    watchlists = result["result"]["watchlists"]
    assert len(watchlists) >= 1
    tech = next(w for w in watchlists if w["name"] == "Tech")
    assert "robinhood" in tech["brokers"]
    assert tech["symbols"] == ["AAPL", "MSFT"]


@pytest.mark.asyncio
async def test_get_unified_watchlist_by_name_success(
    mock_registry, mock_robinhood, mock_schwab
):
    """Test normalized response for a single watchlist by name."""
    mock_registry.list_brokers.return_value = ["robinhood", "schwab"]
    mock_registry.get_broker.side_effect = lambda name: (
        mock_robinhood if name == "robinhood" else mock_schwab
    )

    rh_watchlist = {
        "result": {
            "name": "Tech",
            "symbols": ["AAPL", "MSFT"],
            "symbol_count": 2,
            "status": "success",
        }
    }

    with patch(
        "open_stocks_mcp.tools.unified_watchlist_tools.get_rh_watchlist_by_name",
        return_value=rh_watchlist,
    ):
        result = await get_unified_watchlist_by_name("Tech")

    assert result["result"]["status"] in ["success", "partial_success"]
    assert result["result"]["watchlist_name"] == "Tech"
    assert result["result"]["symbols"] == ["AAPL", "MSFT"]
    assert "robinhood" in result["result"]["brokers"]
    assert "schwab" in result["result"]["brokers"]
    assert result["result"]["per_broker"]["schwab"]["status"] == "unsupported"


@pytest.mark.asyncio
async def test_add_symbols_to_unified_watchlist_success_with_unsupported_broker(
    mock_registry, mock_robinhood, mock_schwab
):
    """Test success when RH succeeds and unsupported brokers are neutral."""
    mock_registry.list_brokers.return_value = ["robinhood", "schwab"]
    mock_registry.get_broker.side_effect = lambda name: (
        mock_robinhood if name == "robinhood" else mock_schwab
    )

    rh_result = {
        "result": {"success": True, "symbols_added": ["AAPL"], "status": "success"}
    }

    with patch(
        "open_stocks_mcp.tools.unified_watchlist_tools.add_rh_symbols",
        return_value=rh_result,
    ):
        result = await add_symbols_to_unified_watchlist("Tech", ["aapl", "AAPL "])

    assert result["result"]["status"] == "success"
    assert "AAPL" in result["result"]["symbols_added"]
    assert len(result["result"]["symbols_added"]) == 1  # De-duplicated and uppercased
    assert result["result"]["per_broker"]["robinhood"]["status"] == "success"
    assert result["result"]["per_broker"]["schwab"]["status"] == "unsupported"


@pytest.mark.asyncio
async def test_remove_symbols_from_unified_watchlist_success_with_unsupported_broker(
    mock_registry, mock_robinhood, mock_schwab
):
    """Test success when RH succeeds and unsupported brokers are neutral."""
    mock_registry.list_brokers.return_value = ["robinhood", "schwab"]
    mock_registry.get_broker.side_effect = lambda name: (
        mock_robinhood if name == "robinhood" else mock_schwab
    )

    rh_result = {
        "result": {"success": True, "symbols_removed": ["AAPL"], "status": "success"}
    }

    with patch(
        "open_stocks_mcp.tools.unified_watchlist_tools.remove_rh_symbols",
        return_value=rh_result,
    ):
        result = await remove_symbols_from_unified_watchlist("Tech", ["AAPL"])

    assert result["result"]["status"] == "success"
    assert result["result"]["symbols_removed"] == ["AAPL"]
    assert result["result"]["per_broker"]["robinhood"]["status"] == "success"
