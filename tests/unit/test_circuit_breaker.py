"""Unit tests for broker-call circuit breaker behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from open_stocks_mcp.config import (
    CircuitBreakerConfig as CanonicalCircuitBreakerConfig,
)
from open_stocks_mcp.config import (
    load_config,
    reset_cache_config,
)
from open_stocks_mcp.tools.circuit_breaker import (
    BrokerCircuitBreaker,
    CircuitBreakerConfig,
)
from open_stocks_mcp.tools.error_handling import CircuitBreakerError, execute_with_retry
from open_stocks_mcp.tools.exceptions import NetworkError


@pytest.mark.asyncio
async def test_breaker_trips_after_threshold_and_blocks() -> None:
    state = {"mono": 100.0, "wall": 1_000.0}
    breaker = BrokerCircuitBreaker(
        CircuitBreakerConfig(
            enabled=True, failure_threshold=2, recovery_timeout_seconds=5.0
        ),
        monotonic_fn=lambda: state["mono"],
        time_fn=lambda: state["wall"],
    )

    await breaker.before_request()
    await breaker.record_failure("network")
    assert breaker.snapshot()["state"] == "closed"

    await breaker.before_request()
    await breaker.record_failure("network")
    snap = breaker.snapshot()
    assert snap["state"] == "open"
    assert snap["failure_count"] == 2

    with pytest.raises(CircuitBreakerError):
        await breaker.before_request()


@pytest.mark.asyncio
async def test_half_open_probe_success_resets() -> None:
    state = {"mono": 100.0, "wall": 1_000.0}
    breaker = BrokerCircuitBreaker(
        CircuitBreakerConfig(
            enabled=True, failure_threshold=1, recovery_timeout_seconds=5.0
        ),
        monotonic_fn=lambda: state["mono"],
        time_fn=lambda: state["wall"],
    )
    await breaker.before_request()
    await breaker.record_failure("network")
    state["mono"] += 6.0
    state["wall"] += 6.0
    await breaker.before_request()
    await breaker.record_success()
    assert breaker.snapshot()["state"] == "closed"
    assert breaker.snapshot()["failure_count"] == 0


@pytest.mark.asyncio
async def test_half_open_probe_failure_reopens() -> None:
    state = {"mono": 100.0, "wall": 1_000.0}
    breaker = BrokerCircuitBreaker(
        CircuitBreakerConfig(
            enabled=True, failure_threshold=1, recovery_timeout_seconds=5.0
        ),
        monotonic_fn=lambda: state["mono"],
        time_fn=lambda: state["wall"],
    )
    await breaker.before_request()
    await breaker.record_failure("network")
    state["mono"] += 6.0
    state["wall"] += 6.0
    await breaker.before_request()
    await breaker.record_failure("network")
    assert breaker.snapshot()["state"] == "open"


@pytest.mark.asyncio
async def test_disabled_breaker_never_blocks() -> None:
    breaker = BrokerCircuitBreaker(
        CircuitBreakerConfig(
            enabled=False, failure_threshold=1, recovery_timeout_seconds=1.0
        )
    )
    await breaker.before_request()
    await breaker.record_failure("network")
    await breaker.before_request()
    assert breaker.snapshot()["state"] == "closed"


@pytest.mark.asyncio
async def test_execute_with_retry_records_failures_and_blocks_fast() -> None:
    mock_session_manager = Mock()
    mock_session_manager.update_last_successful_call = Mock()
    mock_session_manager.should_block_auth_retries = Mock(return_value=False)
    mock_session_manager.refresh_session = AsyncMock(return_value=False)

    def always_fail() -> None:
        raise RuntimeError("connection timeout")

    shared_breaker = BrokerCircuitBreaker(
        CircuitBreakerConfig(
            enabled=True, failure_threshold=1, recovery_timeout_seconds=60.0
        ),
        monotonic_fn=lambda: 10.0,
        time_fn=lambda: 100.0,
    )

    with (
        patch(
            "open_stocks_mcp.brokers.session_state.get_session_manager",
            return_value=mock_session_manager,
        ),
        patch("open_stocks_mcp.tools.rate_limiter.get_rate_limiter", return_value=None),
        patch(
            "open_stocks_mcp.tools.circuit_breaker.get_broker_circuit_breaker",
            return_value=shared_breaker,
        ),
        pytest.raises(NetworkError),
    ):
        await execute_with_retry(always_fail, max_retries=0)

    with (
        patch(
            "open_stocks_mcp.brokers.session_state.get_session_manager",
            return_value=mock_session_manager,
        ),
        patch("open_stocks_mcp.tools.rate_limiter.get_rate_limiter", return_value=None),
        patch(
            "open_stocks_mcp.tools.circuit_breaker.get_broker_circuit_breaker",
            return_value=shared_breaker,
        ),
        pytest.raises(CircuitBreakerError),
    ):
        await execute_with_retry(always_fail, max_retries=0)


@pytest.mark.asyncio
async def test_snapshot_includes_recovery_timeout_seconds() -> None:
    breaker = BrokerCircuitBreaker(
        CircuitBreakerConfig(
            enabled=True, failure_threshold=1, recovery_timeout_seconds=12.5
        )
    )
    snap = breaker.snapshot()
    assert snap["recovery_timeout_seconds"] == 12.5
    assert snap["cooldown_seconds"] == 12.5


def test_load_config_reads_recovery_timeout_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPEN_STOCKS_MCP_CIRCUIT_BREAKER_FAILURE_THRESHOLD", "2")
    monkeypatch.setenv(
        "OPEN_STOCKS_MCP_CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS", "0.25"
    )
    reset_cache_config()
    cfg = load_config()
    assert cfg.circuit_breaker.failure_threshold == 2
    assert cfg.circuit_breaker.recovery_timeout_seconds == 0.25
    assert cfg.circuit_breaker.cooldown_seconds == 0.25


def test_circuit_breaker_uses_canonical_config_dataclass() -> None:
    assert CircuitBreakerConfig is CanonicalCircuitBreakerConfig
