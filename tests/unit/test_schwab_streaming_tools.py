from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.tools.schwab_streaming_tools import (
    schwab_stream_account_activity,
    schwab_stream_level2,
    schwab_stream_option_quotes,
    schwab_stream_quotes,
)


@pytest.mark.asyncio
async def test_schwab_stream_option_quotes_success() -> None:
    mock_broker = MagicMock()
    mock_broker.get_health_status.return_value = {
        "capabilities": {"streaming_quotes": True}
    }
    mock_broker.stream_manager.is_running = True
    mock_broker.stream_manager.subscribe_option_quotes = AsyncMock(return_value=True)
    mock_broker.stream_manager.get_latest_option_quote.return_value = {
        "key": "AAPL  260619C00150000",
        "1": 12.34,
        "2": 12.55,
    }

    with patch(
        "open_stocks_mcp.tools.schwab_streaming_tools.get_authenticated_broker_or_error",
        AsyncMock(return_value=(mock_broker, None)),
    ):
        result = await schwab_stream_option_quotes(["AAPL  260619C00150000"])

    assert result["result"]["status"] == "success"
    assert "AAPL  260619C00150000" in result["result"]["quotes"]
    assert result["result"]["count"] == 1
    assert result["result"]["quotes"]["AAPL  260619C00150000"]["1"] == 12.34


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "capability, manager_exists, is_running, sub_success, cached_quote, expected_reason",
    [
        (False, True, True, True, {"1": 1.0}, "streaming capability disabled"),
        (True, False, True, True, {"1": 1.0}, "stream manager unavailable"),
        (True, True, False, True, {"1": 1.0}, "stream manager stopped"),
        (True, True, True, False, {"1": 1.0}, "option quote subscription failed"),
        (True, True, True, True, None, "no cached option quote snapshot"),
    ],
)
async def test_schwab_stream_option_quotes_unavailable(
    capability: bool,
    manager_exists: bool,
    is_running: bool,
    sub_success: bool,
    cached_quote: dict[str, Any] | None,
    expected_reason: str,
) -> None:
    mock_broker = MagicMock()
    mock_broker.get_health_status.return_value = {
        "capabilities": {"streaming_quotes": capability}
    }
    if not manager_exists:
        mock_broker.stream_manager = None
    else:
        mock_broker.stream_manager.is_running = is_running
        mock_broker.stream_manager.subscribe_option_quotes = AsyncMock(
            return_value=sub_success
        )
        mock_broker.stream_manager.get_latest_option_quote.return_value = cached_quote

    with patch(
        "open_stocks_mcp.tools.schwab_streaming_tools.get_authenticated_broker_or_error",
        AsyncMock(return_value=(mock_broker, None)),
    ):
        result = await schwab_stream_option_quotes(["AAPL  260619C00150000"])

    assert result["result"]["status"] == "stream_unavailable"
    assert result["result"]["reason"] == expected_reason
    assert result["result"]["symbols"] == ["AAPL  260619C00150000"]


@pytest.mark.asyncio
async def test_schwab_stream_quotes_success() -> None:
    mock_broker = MagicMock()
    mock_broker.get_health_status.return_value = {
        "capabilities": {"streaming_quotes": True}
    }
    mock_broker.stream_manager.is_running = True
    mock_broker.stream_manager.subscribe_quotes = AsyncMock(return_value=True)
    mock_broker.stream_manager.get_latest_quote.return_value = {
        "key": "AAPL",
        "1": 150.25,
        "2": 150.30,
        "8": 1000,
    }

    with patch(
        "open_stocks_mcp.tools.schwab_streaming_tools.get_authenticated_broker_or_error",
        AsyncMock(return_value=(mock_broker, None)),
    ):
        result = await schwab_stream_quotes(["AAPL"])

    assert result["result"]["status"] == "success"
    assert result["result"]["count"] == 1
    assert result["result"]["quotes"]["AAPL"]["1"] == 150.25


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "capability, manager_exists, is_running, sub_success, cached_quote, expected_reason",
    [
        (False, True, True, True, {"1": 1.0}, "streaming capability disabled"),
        (True, False, True, True, {"1": 1.0}, "stream manager unavailable"),
        (True, True, False, True, {"1": 1.0}, "stream manager stopped"),
        (True, True, True, False, {"1": 1.0}, "equity quote subscription failed"),
        (True, True, True, True, None, "no cached equity quote snapshot"),
    ],
)
async def test_schwab_stream_quotes_unavailable(
    capability: bool,
    manager_exists: bool,
    is_running: bool,
    sub_success: bool,
    cached_quote: dict[str, Any] | None,
    expected_reason: str,
) -> None:
    mock_broker = MagicMock()
    mock_broker.get_health_status.return_value = {
        "capabilities": {"streaming_quotes": capability}
    }
    if not manager_exists:
        mock_broker.stream_manager = None
    else:
        mock_broker.stream_manager.is_running = is_running
        mock_broker.stream_manager.subscribe_quotes = AsyncMock(
            return_value=sub_success
        )
        mock_broker.stream_manager.get_latest_quote.return_value = cached_quote

    with patch(
        "open_stocks_mcp.tools.schwab_streaming_tools.get_authenticated_broker_or_error",
        AsyncMock(return_value=(mock_broker, None)),
    ):
        result = await schwab_stream_quotes(["AAPL"])

    assert result["result"]["status"] == "stream_unavailable"
    assert result["result"]["reason"] == expected_reason
    assert result["result"]["symbols"] == ["AAPL"]


@pytest.mark.asyncio
async def test_schwab_stream_account_activity_returns_cached_events() -> None:
    mock_broker = MagicMock()
    mock_broker.get_health_status.return_value = {
        "capabilities": {"streaming_quotes": True}
    }
    mock_broker.stream_manager.is_running = True
    mock_broker.stream_manager.subscribe_account_activity = AsyncMock(return_value=True)
    mock_broker.stream_manager.get_latest_activity.return_value = [
        {"key": "ACT001", "1": "OrderEntryRequest"}
    ]

    with patch(
        "open_stocks_mcp.tools.schwab_streaming_tools.get_authenticated_broker_or_error",
        AsyncMock(return_value=(mock_broker, None)),
    ):
        result = await schwab_stream_account_activity()

    assert result["result"]["status"] == "success"
    assert result["result"]["events"] == [{"key": "ACT001", "1": "OrderEntryRequest"}]
    assert result["result"]["count"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "capability, manager_exists, is_running, sub_success, expected_reason",
    [
        (False, True, True, True, "streaming capability disabled"),
        (True, False, True, True, "stream manager unavailable"),
        (True, True, False, True, "stream manager stopped"),
        (True, True, True, False, "account activity subscription failed"),
    ],
)
async def test_schwab_stream_account_activity_unavailable(
    capability: bool,
    manager_exists: bool,
    is_running: bool,
    sub_success: bool,
    expected_reason: str,
) -> None:
    mock_broker = MagicMock()
    mock_broker.get_health_status.return_value = {
        "capabilities": {"streaming_quotes": capability}
    }
    if not manager_exists:
        mock_broker.stream_manager = None
    else:
        mock_broker.stream_manager.is_running = is_running
        mock_broker.stream_manager.subscribe_account_activity = AsyncMock(
            return_value=sub_success
        )

    with patch(
        "open_stocks_mcp.tools.schwab_streaming_tools.get_authenticated_broker_or_error",
        AsyncMock(return_value=(mock_broker, None)),
    ):
        result = await schwab_stream_account_activity()

    assert result["result"]["status"] == "stream_unavailable"
    assert result["result"]["reason"] == expected_reason


@pytest.mark.journey_market_data
@pytest.mark.asyncio
async def test_schwab_stream_level2_success() -> None:
    mock_broker = MagicMock()
    mock_broker.get_health_status.return_value = {
        "capabilities": {"streaming_quotes": True}
    }
    mock_broker.stream_manager.is_running = True
    mock_broker.stream_manager.subscribe_level2 = AsyncMock(return_value=True)
    mock_broker.stream_manager.get_latest_level2.return_value = {
        "symbol": "AAPL",
        "service": "NASDAQ_BOOK",
        "book_time": 1710000000,
        "bids": [],
        "asks": [],
    }

    with patch(
        "open_stocks_mcp.tools.schwab_streaming_tools.get_authenticated_broker_or_error",
        AsyncMock(return_value=(mock_broker, None)),
    ):
        result = await schwab_stream_level2("aapl", "nasdaq")

    assert result["result"]["status"] == "success"
    assert result["result"]["symbol"] == "AAPL"
    assert result["result"]["venue"] == "nasdaq"
    mock_broker.stream_manager.subscribe_level2.assert_awaited_once_with(
        "AAPL", "nasdaq"
    )
    mock_broker.stream_manager.get_latest_level2.assert_called_once_with(
        "AAPL", "nasdaq"
    )


@pytest.mark.journey_market_data
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "symbol,venue,capability,manager_exists,is_running,sub_success,snapshot,expected_reason",
    [
        ("AAPL", "arca", True, True, True, True, {"x": 1}, "unsupported venue"),
        (
            "AAPL",
            "nasdaq",
            False,
            True,
            True,
            True,
            {"x": 1},
            "streaming capability disabled",
        ),
        (
            "AAPL",
            "nasdaq",
            True,
            False,
            True,
            True,
            {"x": 1},
            "stream manager unavailable",
        ),
        ("AAPL", "nasdaq", True, True, False, True, {"x": 1}, "stream manager stopped"),
        ("AAPL", "nasdaq", True, True, True, False, {"x": 1}, "subscription failed"),
        ("AAPL", "nasdaq", True, True, True, True, None, "no snapshot available"),
    ],
)
async def test_schwab_stream_level2_unavailable(
    symbol: str,
    venue: str,
    capability: bool,
    manager_exists: bool,
    is_running: bool,
    sub_success: bool,
    snapshot: dict[str, Any] | None,
    expected_reason: str,
) -> None:
    mock_broker = MagicMock()
    mock_broker.get_health_status.return_value = {
        "capabilities": {"streaming_quotes": capability}
    }
    if manager_exists:
        mock_broker.stream_manager.is_running = is_running
        mock_broker.stream_manager.subscribe_level2 = AsyncMock(
            return_value=sub_success
        )
        mock_broker.stream_manager.get_latest_level2.return_value = snapshot
    else:
        mock_broker.stream_manager = None

    with patch(
        "open_stocks_mcp.tools.schwab_streaming_tools.get_authenticated_broker_or_error",
        AsyncMock(return_value=(mock_broker, None)),
    ):
        result = await schwab_stream_level2(symbol, venue)

    assert result["result"]["status"] == "stream_unavailable"
    assert result["result"]["reason"] == expected_reason
