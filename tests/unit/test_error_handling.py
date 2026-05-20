"""Tests for configurable retry behavior and authentication error handling."""

import asyncio
from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from open_stocks_mcp.brokers.registry import BrokerRegistry
from open_stocks_mcp.tools import rate_limiter, retry
from open_stocks_mcp.tools import session_manager as session_manager_module
from open_stocks_mcp.tools.error_handling import (
    AuthenticationError,
    NetworkError,
    execute_with_retry,
)


def _patch_retry_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> list[float]:
    session_manager = Mock()
    session_manager.update_last_successful_call = Mock()
    session_manager.refresh_session = Mock()
    session_manager.should_block_auth_retries = Mock(return_value=False)
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


@pytest.mark.asyncio
async def test_execute_with_retry_blocks_auth_retry_when_pickle_clear_failures_persist() -> None:
    """Auth retries should short-circuit when session cache clear keeps failing."""

    def auth_fail() -> None:
        raise Exception("authentication token expired")

    mock_session_manager = MagicMock()
    mock_session_manager.should_block_auth_retries.return_value = True
    mock_session_manager.refresh_session = AsyncMock(return_value=False)

    with (
        patch(
            "open_stocks_mcp.tools.session_manager.get_session_manager",
            return_value=mock_session_manager,
        ),
        patch("open_stocks_mcp.tools.rate_limiter.get_rate_limiter", return_value=None),
        pytest.raises(AuthenticationError, match="Session cache clear failures"),
    ):
        await execute_with_retry(auth_fail, max_retries=0)

    mock_session_manager.refresh_session.assert_not_called()


@pytest.mark.asyncio
async def test_execute_with_retry_attempts_reauth_when_not_blocked() -> None:
    """Auth retries should still attempt reauth when not blocked."""

    def auth_fail() -> None:
        raise Exception("authentication token expired")

    mock_session_manager = MagicMock()
    mock_session_manager.should_block_auth_retries.return_value = False
    mock_session_manager.refresh_session = AsyncMock(return_value=False)

    with (
        patch(
            "open_stocks_mcp.tools.session_manager.get_session_manager",
            return_value=mock_session_manager,
        ),
        patch("open_stocks_mcp.tools.rate_limiter.get_rate_limiter", return_value=None),
        pytest.raises(AuthenticationError),
    ):
        await execute_with_retry(auth_fail, max_retries=0)

    mock_session_manager.refresh_session.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_with_retry_coalesces_concurrent_auth_refreshes() -> None:
    """A burst of auth failures should trigger one refresh for the account key."""
    attempts = 0

    async def auth_then_success() -> str:
        nonlocal attempts
        attempts += 1
        if attempts <= 20:
            raise Exception("authentication token expired")
        return "ok"

    registry = BrokerRegistry()
    mock_session_manager = MagicMock()
    mock_session_manager.should_block_auth_retries.return_value = False
    mock_session_manager.update_last_successful_call = Mock()

    async def refresh_session() -> bool:
        await asyncio.sleep(0.01)
        return True

    mock_session_manager.refresh_session = AsyncMock(side_effect=refresh_session)

    with (
        patch(
            "open_stocks_mcp.tools.session_manager.get_session_manager",
            return_value=mock_session_manager,
        ),
        patch("open_stocks_mcp.tools.rate_limiter.get_rate_limiter", return_value=None),
        patch(
            "open_stocks_mcp.tools.retry.get_broker_registry_sync",
            return_value=registry,
        ),
    ):
        results = await asyncio.gather(
            *[
                execute_with_retry(auth_then_success, max_retries=0)
                for _ in range(20)
            ]
        )

    assert results == ["ok"] * 20
    mock_session_manager.refresh_session.assert_awaited_once()
