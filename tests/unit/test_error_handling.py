"""Tests for configurable retry behavior."""

from collections.abc import Callable
from unittest.mock import Mock

import pytest

from open_stocks_mcp.tools import rate_limiter, retry
from open_stocks_mcp.tools import session_manager as session_manager_module
from open_stocks_mcp.tools.error_handling import NetworkError, execute_with_retry


def _patch_retry_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> list[float]:
    session_manager = Mock()
    session_manager.update_last_successful_call = Mock()
    session_manager.refresh_session = Mock()
    monkeypatch.setattr(
        session_manager_module, "get_session_manager", lambda: session_manager
    )
    monkeypatch.setattr(rate_limiter, "get_rate_limiter", lambda: None)

    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(retry.asyncio, "sleep", fake_sleep)
    return sleep_calls


def _always_fails(counter: list[int]) -> Callable[[], None]:
    def fail() -> None:
        counter.append(1)
        raise RuntimeError("connection timeout")

    return fail


@pytest.mark.asyncio
async def test_execute_with_retry_uses_configured_retry_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPEN_STOCKS_MCP_RETRY_MAX_RETRIES", "2")
    monkeypatch.setenv("OPEN_STOCKS_MCP_RETRY_INITIAL_DELAY", "0.25")
    monkeypatch.setenv("OPEN_STOCKS_MCP_RETRY_BACKOFF_FACTOR", "3.0")
    sleep_calls = _patch_retry_dependencies(monkeypatch)
    attempts: list[int] = []

    with pytest.raises(NetworkError):
        await execute_with_retry(_always_fails(attempts))

    assert len(attempts) == 3
    assert sleep_calls == [0.25, 0.75]


@pytest.mark.asyncio
async def test_execute_with_retry_uses_per_error_class_retry_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPEN_STOCKS_MCP_RETRY_MAX_RETRIES", "0")
    monkeypatch.setenv("OPEN_STOCKS_MCP_RETRY_NETWORK_MAX_RETRIES", "2")
    sleep_calls = _patch_retry_dependencies(monkeypatch)
    attempts: list[int] = []

    with pytest.raises(NetworkError):
        await execute_with_retry(_always_fails(attempts))

    assert len(attempts) == 3
    assert sleep_calls == [1.0, 2.0]


@pytest.mark.asyncio
async def test_execute_with_retry_explicit_arguments_override_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPEN_STOCKS_MCP_RETRY_MAX_RETRIES", "3")
    monkeypatch.setenv("OPEN_STOCKS_MCP_RETRY_NETWORK_MAX_RETRIES", "3")
    sleep_calls = _patch_retry_dependencies(monkeypatch)
    attempts: list[int] = []

    with pytest.raises(NetworkError):
        await execute_with_retry(
            _always_fails(attempts),
            max_retries=0,
            delay=0.5,
            backoff_factor=10.0,
        )

    assert len(attempts) == 1
    assert sleep_calls == []
