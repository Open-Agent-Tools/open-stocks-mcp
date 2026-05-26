from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.tools.schwab_streaming_tools import schwab_stream_option_quotes


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
