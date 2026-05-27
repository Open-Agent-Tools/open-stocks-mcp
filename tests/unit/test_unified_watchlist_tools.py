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
    ), patch(
        "open_stocks_mcp.tools.unified_watchlist_tools.load_schwab_watchlists",
        return_value=({"Income": ["SCHD", "VYM"]}, None),
    ):
        result = await get_unified_watchlists()

    assert result["result"]["status"] in ["success", "partial_success"]
    assert result["result"]["brokers"]["schwab"]["status"] == "success"

    watchlists = result["result"]["watchlists"]
    assert len(watchlists) == 2
    tech = next(w for w in watchlists if w["name"] == "Tech")
    assert "robinhood" in tech["brokers"]
    assert tech["symbols"] == ["AAPL", "MSFT"]


@pytest.mark.asyncio
async def test_get_unified_watchlists_merges_same_name_across_brokers(
    mock_registry, mock_robinhood, mock_schwab
):
    mock_registry.list_brokers.return_value = ["robinhood", "schwab"]
    mock_registry.get_broker.side_effect = lambda name: (
        mock_robinhood if name == "robinhood" else mock_schwab
    )

    rh_watchlists = {
        "result": {
            "watchlists": [{"name": "Tech", "symbols": ["AAPL"], "symbol_count": 1}],
            "status": "success",
        }
    }

    with patch(
        "open_stocks_mcp.tools.unified_watchlist_tools.get_rh_watchlists",
        return_value=rh_watchlists,
    ), patch(
        "open_stocks_mcp.tools.unified_watchlist_tools.load_schwab_watchlists",
        return_value=({"Tech": ["MSFT", "AAPL"]}, None),
    ):
        result = await get_unified_watchlists()

    tech = next(w for w in result["result"]["watchlists"] if w["name"] == "Tech")
    assert sorted(tech["brokers"]) == ["robinhood", "schwab"]
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
    ), patch(
        "open_stocks_mcp.tools.unified_watchlist_tools.get_schwab_watchlist",
        return_value=(["SCHD"], None),
    ):
        result = await get_unified_watchlist_by_name("Tech")

    assert result["result"]["status"] in ["success", "partial_success"]
    assert result["result"]["watchlist_name"] == "Tech"
    assert result["result"]["symbols"] == ["AAPL", "MSFT", "SCHD"]
    assert result["result"]["per_broker"]["schwab"]["status"] == "success"


@pytest.mark.asyncio
async def test_get_unified_watchlist_by_name_broker_error_not_masked_as_not_found(
    mock_registry, mock_robinhood, mock_schwab
):
    """When a broker returns an error, status should be partial_failure, not not_found."""
    mock_registry.list_brokers.return_value = ["robinhood", "schwab"]
    mock_registry.get_broker.side_effect = lambda name: (
        mock_robinhood if name == "robinhood" else mock_schwab
    )

    rh_error = {
        "result": {
            "status": "error",
            "message": "Authentication failed",
        }
    }

    with patch(
        "open_stocks_mcp.tools.unified_watchlist_tools.get_rh_watchlist_by_name",
        return_value=rh_error,
    ):
        result = await get_unified_watchlist_by_name("Tech")

    assert result["result"]["status"] == "partial_failure"
    assert result["result"]["per_broker"]["robinhood"]["status"] == "error"


@pytest.mark.asyncio
async def test_get_unified_watchlist_by_name_broker_unavailable_not_masked(
    mock_registry, mock_robinhood, mock_schwab
):
    """When a broker is unavailable, status should be partial_failure, not not_found."""
    mock_registry.list_brokers.return_value = ["robinhood", "schwab"]
    mock_robinhood.is_available.return_value = False
    mock_registry.get_broker.side_effect = lambda name: (
        mock_robinhood if name == "robinhood" else mock_schwab
    )

    result = await get_unified_watchlist_by_name("Tech")

    assert result["result"]["status"] == "partial_failure"
    assert result["result"]["per_broker"]["robinhood"]["status"] == "unavailable"


@pytest.mark.asyncio
async def test_get_unified_watchlist_by_name_genuine_not_found(
    mock_registry, mock_robinhood, mock_schwab
):
    """When the watchlist genuinely doesn't exist (no broker errors), status is not_found."""
    mock_registry.list_brokers.return_value = ["robinhood", "schwab"]
    mock_registry.get_broker.side_effect = lambda name: (
        mock_robinhood if name == "robinhood" else mock_schwab
    )

    rh_not_found = {
        "result": {
            "status": "not_found",
        }
    }

    with patch(
        "open_stocks_mcp.tools.unified_watchlist_tools.get_rh_watchlist_by_name",
        return_value=rh_not_found,
    ):
        result = await get_unified_watchlist_by_name("NonExistent")

    assert result["result"]["status"] == "not_found"


@pytest.mark.asyncio
async def test_get_unified_watchlist_by_name_unregistered_broker_partial_failure(
    mock_registry, mock_robinhood
):
    """When an unregistered broker is requested, status should be partial_failure."""
    mock_registry.list_brokers.return_value = ["robinhood"]
    mock_registry.get_broker.side_effect = lambda name: (
        mock_robinhood if name == "robinhood" else None
    )

    rh_not_found = {
        "result": {
            "status": "not_found",
        }
    }

    with patch(
        "open_stocks_mcp.tools.unified_watchlist_tools.get_rh_watchlist_by_name",
        return_value=rh_not_found,
    ):
        result = await get_unified_watchlist_by_name("Tech", brokers=["robinhood", "fakeBroker"])

    assert result["result"]["status"] == "partial_failure"
    assert result["result"]["per_broker"]["fakeBroker"]["status"] == "error"


@pytest.mark.asyncio
async def test_add_symbols_to_unified_watchlist_partial_success(
    mock_registry, mock_robinhood, mock_schwab
):
    """Test success when RH and Schwab local store both succeed."""
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
    ), patch(
        "open_stocks_mcp.tools.unified_watchlist_tools.add_schwab_symbols",
        return_value=(["AAPL"], None),
    ):
        result = await add_symbols_to_unified_watchlist("Tech", ["aapl", "AAPL "])

    assert result["result"]["status"] == "success"
    assert "AAPL" in result["result"]["symbols_added"]
    assert len(result["result"]["symbols_added"]) == 1
    assert result["result"]["per_broker"]["robinhood"]["status"] == "success"
    assert result["result"]["per_broker"]["schwab"]["status"] == "success"


@pytest.mark.asyncio
async def test_remove_symbols_from_unified_watchlist_success(
    mock_registry, mock_robinhood, mock_schwab
):
    """Test success when RH and Schwab local store both succeed."""
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
    ), patch(
        "open_stocks_mcp.tools.unified_watchlist_tools.remove_schwab_symbols",
        return_value=([], None),
    ):
        result = await remove_symbols_from_unified_watchlist("Tech", ["AAPL"])

    assert result["result"]["status"] == "success"
    assert result["result"]["symbols_removed"] == ["AAPL"]
    assert result["result"]["per_broker"]["robinhood"]["status"] == "success"
    assert result["result"]["per_broker"]["schwab"]["status"] == "success"


@pytest.mark.asyncio
async def test_get_unified_watchlists_handles_corrupt_schwab_store(
    mock_registry, mock_robinhood, mock_schwab
):
    mock_registry.list_brokers.return_value = ["robinhood", "schwab"]
    mock_registry.get_broker.side_effect = lambda name: (
        mock_robinhood if name == "robinhood" else mock_schwab
    )

    rh_watchlists = {"result": {"watchlists": [], "status": "success"}}

    with patch(
        "open_stocks_mcp.tools.unified_watchlist_tools.get_rh_watchlists",
        return_value=rh_watchlists,
    ), patch(
        "open_stocks_mcp.tools.unified_watchlist_tools.load_schwab_watchlists",
        return_value=({}, "Unable to read Schwab watchlist store"),
    ):
        result = await get_unified_watchlists()

    assert result["result"]["status"] == "partial_success"
    assert result["result"]["brokers"]["schwab"]["status"] == "error"
    assert result["result"]["warnings"][0]["broker"] == "schwab"
