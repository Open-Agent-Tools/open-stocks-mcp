"""Rate limiting for Robin Stocks API calls."""

import asyncio
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from typing import Any

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.exceptions import RateLimitError


class RateLimiter:
    """Rate limiter for API calls using token bucket algorithm."""

    def __init__(
        self,
        calls_per_minute: int = 60,
        calls_per_hour: int = 1800,
        burst_size: int = 10,
    ):
        """Initialize rate limiter.

        Args:
            calls_per_minute: Maximum calls allowed per minute
            calls_per_hour: Maximum calls allowed per hour
            burst_size: Maximum burst size for rapid calls
        """
        self.calls_per_minute = calls_per_minute
        self.calls_per_hour = calls_per_hour
        self.burst_size = burst_size

        # Track call timestamps
        self.call_times: deque[float] = deque(maxlen=calls_per_hour)
        self._lock = asyncio.Lock()

        # Track per-endpoint limits
        self.endpoint_buckets: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=100)
        )
        self.broker_buckets: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=100)
        )
        self._wait_queue: deque[object] = deque()

    async def acquire(
        self,
        endpoint: str | None = None,
        weight: float = 1.0,
        broker: str | None = None,
        max_wait: float | None = None,
    ) -> None:
        """Acquire permission to make an API call.

        Args:
            endpoint: Optional endpoint identifier for per-endpoint limiting
            weight: Weight of this call (some calls may count more)
        """
        request_weight = max(1, int(weight))
        deadline = None if max_wait is None else time.time() + max_wait
        token = object()

        async with self._lock:
            self._wait_queue.append(token)

        while True:
            wait_time = 0.0
            async with self._lock:
                now = time.time()
                self._prune_old_calls(now)

                if self._wait_queue and self._wait_queue[0] is token:
                    if self._has_capacity(now, request_weight):
                        self._wait_queue.popleft()
                        self._record_call(now, request_weight, endpoint, broker)
                        return
                    wait_time = self._time_until_capacity(now)

                if deadline is not None:
                    remaining = deadline - now
                    if remaining <= 0:
                        self._remove_waiter(token)
                        raise RateLimitError(
                            "Rate limit exceeded while waiting for queued capacity"
                        )
                    if wait_time <= 0:
                        wait_time = min(0.01, remaining)
                    else:
                        wait_time = min(wait_time, remaining)
                elif wait_time <= 0:
                    wait_time = 0.01

            if wait_time >= 1.0:
                logger.warning(
                    "Rate limit reached. Waiting %.1fs for available capacity",
                    wait_time,
                )
            await asyncio.sleep(wait_time)

    def _prune_old_calls(self, now: float) -> None:
        cutoff_hour = now - 3600
        while self.call_times and self.call_times[0] < cutoff_hour:
            self.call_times.popleft()

    def _has_capacity(self, now: float, weight: int) -> bool:
        cutoff_minute = now - 60
        cutoff_burst = now - 1
        calls_last_minute = sum(1 for t in self.call_times if t > cutoff_minute)
        calls_last_burst = sum(1 for t in self.call_times if t > cutoff_burst)
        return (
            len(self.call_times) + weight <= self.calls_per_hour
            and calls_last_minute + weight <= self.calls_per_minute
            and calls_last_burst + weight <= self.burst_size
        )

    def _time_until_capacity(self, now: float) -> float:
        waits: list[float] = []
        if len(self.call_times) >= self.calls_per_hour:
            waits.append((self.call_times[0] + 3600) - now)

        cutoff_minute = now - 60
        minute_calls = [t for t in self.call_times if t > cutoff_minute]
        if len(minute_calls) >= self.calls_per_minute:
            waits.append((minute_calls[0] + 60) - now)

        cutoff_burst = now - 1
        burst_calls = [t for t in self.call_times if t > cutoff_burst]
        if len(burst_calls) >= self.burst_size:
            waits.append((burst_calls[0] + 1.0) - now)

        positive_waits = [wait for wait in waits if wait > 0]
        return max(positive_waits) if positive_waits else 0.01

    def _record_call(
        self, now: float, weight: int, endpoint: str | None, broker: str | None
    ) -> None:
        for _ in range(weight):
            self.call_times.append(now)
        if endpoint:
            self.endpoint_buckets[endpoint].append(now)
        if broker:
            self.broker_buckets[broker].append(now)

    def _remove_waiter(self, token: object) -> None:
        try:
            self._wait_queue.remove(token)
        except ValueError:
            return

    def reset(self) -> None:
        """Reset call tracking and queue state (primarily for tests)."""
        self.call_times.clear()
        self.endpoint_buckets.clear()
        self.broker_buckets.clear()
        self._wait_queue.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get current rate limiter statistics.

        Returns:
            Dictionary with current usage statistics
        """
        now = time.time()

        # Calculate current usage
        cutoff_minute = now - 60

        calls_last_minute = sum(1 for t in self.call_times if t > cutoff_minute)
        calls_last_hour = len(self.call_times)

        return {
            "calls_last_minute": calls_last_minute,
            "calls_last_hour": calls_last_hour,
            "limit_per_minute": self.calls_per_minute,
            "limit_per_hour": self.calls_per_hour,
            "burst_size": self.burst_size,
            "minute_usage_percent": (calls_last_minute / self.calls_per_minute) * 100,
            "hour_usage_percent": (calls_last_hour / self.calls_per_hour) * 100,
            "endpoint_usage": {
                endpoint: {
                    "calls_last_minute": sum(1 for t in bucket if t > cutoff_minute),
                    "calls_last_hour": sum(1 for t in bucket if t > now - 3600),
                }
                for endpoint, bucket in self.endpoint_buckets.items()
            },
            "broker_usage": {
                broker: {
                    "calls_last_minute": sum(1 for t in bucket if t > cutoff_minute),
                    "calls_last_hour": sum(1 for t in bucket if t > now - 3600),
                }
                for broker, bucket in self.broker_buckets.items()
            },
        }


# Global rate limiter instance
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance.

    Returns:
        The global RateLimiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        # Initialize with conservative defaults
        _rate_limiter = RateLimiter(
            calls_per_minute=30,  # Conservative: ~0.5 calls/second
            calls_per_hour=1000,  # Conservative hourly limit
            burst_size=5,  # Allow small bursts
        )
    return _rate_limiter


class _BatchState:
    """Per-loop batch state for coalescing symbol fetches."""

    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.pending: dict[str, list[asyncio.Future[Any]]] = defaultdict(list)
        self.drain_task: asyncio.Task[None] | None = None


_batch_states: dict[tuple[int, str], _BatchState] = {}


def reset_batch_state() -> None:
    """Clear global batching state for tests."""
    _batch_states.clear()


async def batch_fetch_symbols(
    batch_name: str,
    symbols: list[str],
    fetch_many: Callable[[list[str]], Awaitable[list[dict[str, Any]] | None]],
    *,
    batch_size: int,
    queue_max_wait: float,
) -> list[dict[str, Any] | None]:
    """Coalesce symbol requests into batched fetch_many invocations."""
    normalized = [symbol.strip().upper() for symbol in symbols]
    if not normalized:
        return []

    loop = asyncio.get_running_loop()
    state_key = (id(loop), batch_name)
    state = _batch_states.get(state_key)
    if state is None:
        state = _BatchState()
        _batch_states[state_key] = state

    futures_by_symbol: dict[str, asyncio.Future[Any]] = {}
    async with state.lock:
        for symbol in normalized:
            fut = loop.create_future()
            state.pending[symbol].append(fut)
            futures_by_symbol[symbol] = fut
        if state.drain_task is None or state.drain_task.done():
            state.drain_task = loop.create_task(
                _drain_batches(state, fetch_many, max(1, batch_size), queue_max_wait)
            )

    results_by_symbol = {
        symbol: await fut
        for symbol, fut in futures_by_symbol.items()
        if fut is not None
    }
    return [results_by_symbol.get(symbol) for symbol in normalized]


async def _drain_batches(
    state: _BatchState,
    fetch_many: Callable[[list[str]], Awaitable[list[dict[str, Any]] | None]],
    batch_size: int,
    queue_max_wait: float,
) -> None:
    try:
        await asyncio.sleep(max(0.0, queue_max_wait))
        while True:
            async with state.lock:
                if not state.pending:
                    return
                chunk_symbols = list(state.pending.keys())[:batch_size]
                chunk = {symbol: state.pending.pop(symbol) for symbol in chunk_symbols}

            rows = await fetch_many(chunk_symbols)
            rows = rows or []
            row_map: dict[str, dict[str, Any]] = {}
            for row in rows:
                symbol = str(row.get("symbol", "")).strip().upper()
                if symbol:
                    row_map[symbol] = row
            if len(row_map) != len(chunk_symbols) and len(rows) == len(chunk_symbols):
                for index, symbol in enumerate(chunk_symbols):
                    if symbol not in row_map:
                        row_map[symbol] = rows[index]

            for symbol, waiters in chunk.items():
                value = row_map.get(symbol)
                for fut in waiters:
                    if not fut.done():
                        fut.set_result(value)
    finally:
        async with state.lock:
            state.drain_task = None


async def rate_limited_call(
    func: Any, *args: Any, endpoint: str | None = None, **kwargs: Any
) -> Any:
    """Execute a function with rate limiting.

    Args:
        func: Function to execute
        endpoint: Optional endpoint identifier
        *args, **kwargs: Arguments to pass to the function

    Returns:
        Result of the function call
    """
    limiter = get_rate_limiter()
    await limiter.acquire(endpoint)

    if asyncio.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)
