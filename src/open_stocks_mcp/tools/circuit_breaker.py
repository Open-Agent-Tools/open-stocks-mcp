"""Circuit breaker protections around broker-call execution paths."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from open_stocks_mcp.config import get_config
from open_stocks_mcp.tools.exceptions import CircuitBreakerError


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker runtime configuration."""

    enabled: bool = True
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 60.0

    @property
    def cooldown_seconds(self) -> float:
        """Backward-compatible alias for recovery timeout."""
        return self.recovery_timeout_seconds


class BrokerCircuitBreaker:
    """Asyncio-safe state machine for broker-call protections."""

    def __init__(
        self,
        config: CircuitBreakerConfig,
        *,
        monotonic_fn: Any = None,
        time_fn: Any = None,
    ) -> None:
        self._config = config
        self._state = "closed"
        self._failure_count = 0
        self._opened_at: float | None = None
        self._next_retry_at: float | None = None
        self._half_open_probe_in_flight = False
        self._lock = asyncio.Lock()
        self._monotonic = monotonic_fn or time.monotonic
        self._time = time_fn or time.time
        self._next_retry_monotonic: float | None = None

    async def before_request(self) -> None:
        """Raise when breaker is open and cooldown has not elapsed."""
        if not self._config.enabled:
            return
        async with self._lock:
            now_m = float(self._monotonic())
            if self._state == "open":
                if (
                    self._next_retry_monotonic is not None
                    and now_m >= self._next_retry_monotonic
                ):
                    self._state = "half_open"
                    self._half_open_probe_in_flight = False
                else:
                    raise CircuitBreakerError("Broker circuit breaker is open")

            if self._state == "half_open":
                if self._half_open_probe_in_flight:
                    raise CircuitBreakerError("Broker circuit breaker is open")
                self._half_open_probe_in_flight = True

    async def record_success(self) -> None:
        """Record successful execution and reset from open/half-open paths."""
        if not self._config.enabled:
            return
        async with self._lock:
            self._state = "closed"
            self._failure_count = 0
            self._opened_at = None
            self._next_retry_at = None
            self._next_retry_monotonic = None
            self._half_open_probe_in_flight = False

    async def record_failure(self, error_type: str) -> None:
        """Record broker failure and trip the breaker when threshold is reached."""
        if not self._config.enabled:
            return
        if error_type not in {"authentication", "network", "rate_limit", "api"}:
            return
        async with self._lock:
            if self._state == "half_open":
                self._open_locked()
                return
            if self._state == "open":
                self._open_locked()
                return

            self._failure_count += 1
            if self._failure_count >= self._config.failure_threshold:
                self._open_locked()

    def snapshot(self) -> dict[str, Any]:
        """Return breaker state for status and health surfaces."""
        return {
            "enabled": self._config.enabled,
            "state": self._state,
            "failure_count": self._failure_count,
            "failure_threshold": self._config.failure_threshold,
            "recovery_timeout_seconds": self._config.recovery_timeout_seconds,
            "cooldown_seconds": self._config.cooldown_seconds,
            "opened_at": self._opened_at,
            "next_retry_at": self._next_retry_at,
        }

    def _open_locked(self) -> None:
        now_wall = float(self._time())
        now_m = float(self._monotonic())
        self._state = "open"
        self._failure_count = self._config.failure_threshold
        self._opened_at = now_wall
        self._next_retry_at = now_wall + self._config.cooldown_seconds
        self._next_retry_monotonic = now_m + self._config.cooldown_seconds
        self._half_open_probe_in_flight = False


_breaker: BrokerCircuitBreaker | None = None


def get_broker_circuit_breaker() -> BrokerCircuitBreaker:
    """Get process-global broker circuit breaker."""
    global _breaker
    if _breaker is None:
        cfg = get_config().circuit_breaker
        _breaker = BrokerCircuitBreaker(
            CircuitBreakerConfig(
                enabled=cfg.enabled,
                failure_threshold=cfg.failure_threshold,
                recovery_timeout_seconds=cfg.recovery_timeout_seconds,
            )
        )
    return _breaker


def reset_broker_circuit_breaker() -> None:
    """Reset process-global circuit breaker instance."""
    global _breaker
    _breaker = None
