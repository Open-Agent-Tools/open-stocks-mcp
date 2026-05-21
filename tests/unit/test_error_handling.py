"""Tests for configurable retry behavior and authentication error handling."""

import asyncio
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

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
async def test_execute_with_retry_uses_registry_single_flight_for_auth_refresh() -> None:
    calls = 0

    def auth_fail_then_success_factory() -> Callable[[], str]:
        state = {"attempts": 0}

        def runner() -> str:
            state["attempts"] += 1
            if state["attempts"] == 1:
                raise Exception("authentication token expired")
            return "ok"

        return runner

    async def coordinated_refresh(
        *, broker_name: str, account_id: str | None, refresh_coro: Callable[[], Any]
    ) -> bool:
        nonlocal calls
        calls += 1
        return await refresh_coro()

    registry = Mock()
    registry.coordinated_refresh = AsyncMock(side_effect=coordinated_refresh)
    breaker = Mock()
    breaker.before_request = AsyncMock(return_value=None)
    breaker.record_success = AsyncMock(return_value=None)
    breaker.record_failure = AsyncMock(return_value=None)

    session = Mock()
    session.should_block_auth_retries = Mock(return_value=False)
    session.refresh_session = AsyncMock(return_value=True)
    session.update_last_successful_call = Mock()

    with (
        patch(
            "open_stocks_mcp.tools.session_manager.get_session_manager",
            return_value=session,
        ),
        patch("open_stocks_mcp.tools.rate_limiter.get_rate_limiter", return_value=None),
        patch(
            "open_stocks_mcp.tools.circuit_breaker.get_broker_circuit_breaker",
            return_value=breaker,
        ),
        patch(
            "open_stocks_mcp.brokers.registry.get_broker_registry",
            AsyncMock(return_value=registry),
        ),
    ):
        results = await asyncio.gather(
            *[
                execute_with_retry(
                    auth_fail_then_success_factory(),
                    max_retries=1,
                    broker_name="robinhood",
                    account_id="acct-1",
                )
                for _ in range(20)
            ]
        )

    assert results == ["ok"] * 20
    assert calls == 20
    assert registry.coordinated_refresh.await_count == 20
