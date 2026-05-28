"""Rate limiting for Robin Stocks API calls."""

import asyncio
import os
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any, Generic, TypeVar, cast

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.exceptions import RateLimitError

SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
BURST_WINDOW_SECONDS = 1
DEFAULT_CALLS_PER_MINUTE = 30
DEFAULT_CALLS_PER_HOUR = 1000
DEFAULT_BURST_SIZE = 5
DEFAULT_SCHWAB_CALLS_PER_MINUTE = 120
DEFAULT_SCHWAB_CALLS_PER_HOUR = 3600
DEFAULT_SCHWAB_BURST_SIZE = 20

_T = TypeVar("_T")


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
        self._waiters: deque[asyncio.Future[None]] = deque()

        # Track per-endpoint limits
        self.endpoint_buckets: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=100)
        )
        self.broker_buckets: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=100)
        )

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
            broker: Optional broker identifier
            max_wait: Maximum time to wait for a slot in seconds
        """
        start_time = time.time()
        deadline = start_time + max_wait if max_wait is not None else None

        while True:
            async with self._lock:
                now = time.time()

                # Remove old timestamps (older than 1 hour)
                cutoff_hour = now - SECONDS_PER_HOUR
                while self.call_times and self.call_times[0] < cutoff_hour:
                    self.call_times.popleft()

                wait_time = 0.0

                # Check hourly limit
                if len(self.call_times) >= self.calls_per_hour:
                    oldest_call = self.call_times[0]
                    wait_time = max(wait_time, (oldest_call + SECONDS_PER_HOUR) - now)

                # Check minute limit
                cutoff_minute = now - SECONDS_PER_MINUTE
                minute_calls = [t for t in self.call_times if t > cutoff_minute]
                if len(minute_calls) >= self.calls_per_minute:
                    wait_time = max(
                        wait_time, (minute_calls[0] + SECONDS_PER_MINUTE) - now
                    )

                # Check burst limit
                cutoff_burst = now - BURST_WINDOW_SECONDS
                burst_calls = [t for t in self.call_times if t > cutoff_burst]
                if len(burst_calls) >= self.burst_size:
                    wait_time = max(
                        wait_time, (burst_calls[0] + BURST_WINDOW_SECONDS) - now
                    )

                if wait_time <= 0:
                    # Capacity available
                    for _ in range(int(weight)):
                        self.call_times.append(now)
                    if endpoint:
                        self.endpoint_buckets[endpoint].append(now)
                    if broker:
                        self.broker_buckets[broker].append(now)
                    return

                # Check if we've exceeded max_wait
                if deadline is not None and (now + wait_time) > deadline:
                    raise RateLimitError(
                        f"Rate limit wait time {wait_time:.1f}s exceeds max_wait {max_wait}s"
                    )

            # Need to wait.
            if wait_time > 0:
                logger.debug(f"Rate limit reached. Waiting {wait_time:.3f}s")
                await asyncio.sleep(wait_time)

            # Loop again to re-check capacity and potentially wait more or acquire

    def reset(self) -> None:
        """Reset rate limiter state."""
        self.call_times.clear()
        self.endpoint_buckets.clear()
        self.broker_buckets.clear()
        for waiter in self._waiters:
            if not waiter.done():
                waiter.cancel()
        self._waiters.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get current rate limiter statistics.

        Returns:
            Dictionary with current usage statistics
        """
        now = time.time()

        # Calculate current usage
        cutoff_minute = now - SECONDS_PER_MINUTE

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
                    "calls_last_hour": sum(
                        1 for t in bucket if t > now - SECONDS_PER_HOUR
                    ),
                }
                for endpoint, bucket in self.endpoint_buckets.items()
            },
            "broker_usage": {
                broker: {
                    "calls_last_minute": sum(1 for t in bucket if t > cutoff_minute),
                    "calls_last_hour": sum(
                        1 for t in bucket if t > now - SECONDS_PER_HOUR
                    ),
                }
                for broker, bucket in self.broker_buckets.items()
            },
        }


class RequestCoordinator:
    """Asyncio-safe singleflight coordinator for deduplicating concurrent reads.

    Callers that supply the same key while a request is already in-flight receive
    the same result without triggering a second broker call. Mutating/trading paths
    must NOT use a coalesce key so they are never deduplicated.
    """

    def __init__(self) -> None:
        self._in_flight: dict[str, asyncio.Future[object]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()
        self.coalesced_count: int = 0

    async def execute(
        self,
        key: str,
        coro_factory: Callable[[], Awaitable[_T]],
    ) -> _T:
        """Execute *coro_factory* unless a call with *key* is already in-flight.

        When a duplicate key is detected the caller awaits the existing future
        instead of launching a new coroutine, so the underlying broker call runs
        only once regardless of how many concurrent callers arrive.
        """
        waiter: asyncio.Future[_T]
        async with self._lock:
            existing_waiter = self._in_flight.get(key)
            if existing_waiter is not None:
                self.coalesced_count += 1
                waiter = cast("asyncio.Future[_T]", existing_waiter)
                is_new = False
            else:
                waiter = asyncio.get_running_loop().create_future()
                self._in_flight[key] = cast("asyncio.Future[object]", waiter)
                is_new = True

        if not is_new:
            return await asyncio.shield(waiter)

        try:
            result = await coro_factory()
            waiter.set_result(result)
            return result
        except BaseException as exc:
            if isinstance(exc, asyncio.CancelledError):
                waiter.cancel()
            else:
                waiter.set_exception(exc)
                waiter.exception()
            raise
        finally:
            async with self._lock:
                self._in_flight.pop(key, None)


class Batcher(Generic[_T]):
    """Async batching helper for coalescing multiple requests into one API call."""

    def __init__(
        self,
        name: str,
        batch_size: int = 10,
        queue_max_wait: float = 0.5,
    ) -> None:
        self.name = name
        self.batch_size = batch_size
        self.queue_max_wait = queue_max_wait
        self._queue: list[tuple[str, asyncio.Future[_T | None]]] = []
        self._lock = asyncio.Lock()
        self._flush_task: asyncio.Task[None] | None = None

    async def fetch(
        self,
        symbol: str,
        fetch_many_callable: Callable[
            [list[str]], dict[str, _T] | Coroutine[Any, Any, dict[str, _T]]
        ],
    ) -> _T | None:
        """Add a symbol to the batch and wait for the result.

        Args:
            symbol: The stock symbol to fetch
            fetch_many_callable: A callable that takes a list of symbols and returns a dict mapping symbols to data

        Returns:
            The data for the requested symbol
        """
        symbol = symbol.upper()
        waiter: asyncio.Future[_T | None] = asyncio.get_running_loop().create_future()

        async with self._lock:
            self._queue.append((symbol, waiter))

            if len(self._queue) >= self.batch_size:
                # Trigger immediate flush if batch size reached
                if self._flush_task:
                    self._flush_task.cancel()
                await self._flush(fetch_many_callable)
            elif not self._flush_task:
                # Start a timer to flush after queue_max_wait
                self._flush_task = asyncio.create_task(
                    self._delayed_flush(fetch_many_callable)
                )

        return await waiter

    async def _delayed_flush(
        self,
        fetch_many_callable: Callable[
            [list[str]], dict[str, _T] | Coroutine[Any, Any, dict[str, _T]]
        ],
    ) -> None:
        try:
            await asyncio.sleep(self.queue_max_wait)
            async with self._lock:
                await self._flush(fetch_many_callable)
        except asyncio.CancelledError:
            pass
        finally:
            self._flush_task = None

    async def _flush(
        self,
        fetch_many_callable: Callable[
            [list[str]], dict[str, _T] | Coroutine[Any, Any, dict[str, _T]]
        ],
    ) -> None:
        if not self._queue:
            return

        current_batch = self._queue[:]
        self._queue.clear()

        symbols = [s for s, _ in current_batch]

        try:
            if asyncio.iscoroutinefunction(fetch_many_callable):
                async_fn = cast(
                    Callable[[list[str]], Coroutine[Any, Any, dict[str, _T]]],
                    fetch_many_callable,
                )
                results = await async_fn(symbols)
            else:
                sync_fn = cast(
                    Callable[[list[str]], dict[str, _T]],
                    fetch_many_callable,
                )
                results = await asyncio.get_running_loop().run_in_executor(
                    None, sync_fn, symbols
                )

            for symbol, waiter in current_batch:
                if not waiter.done():
                    waiter.set_result(results.get(symbol))
        except Exception as exc:
            for _, waiter in current_batch:
                if not waiter.done():
                    waiter.set_exception(exc)


# Global rate limiter instance
_rate_limiter: RateLimiter | None = None

# Global request coordinator instance
_request_coordinator: RequestCoordinator | None = None

# Global batchers
_batchers: dict[str, Batcher[Any]] = {}


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid %s=%r; using default %s", name, raw, default)
        return default


def get_broker_rate_limit_defaults(broker_name: str) -> tuple[int, int, int]:
    """Return broker-specific (per-minute, per-hour, burst) rate-limit defaults."""
    normalized = broker_name.strip().lower()
    if normalized == "schwab":
        # Schwab integration docs call out ~120 req/min as the intended baseline.
        return (
            _int_env(
                "OPEN_STOCKS_SCHWAB_CALLS_PER_MINUTE", DEFAULT_SCHWAB_CALLS_PER_MINUTE
            ),
            _int_env(
                "OPEN_STOCKS_SCHWAB_CALLS_PER_HOUR", DEFAULT_SCHWAB_CALLS_PER_HOUR
            ),
            _int_env("OPEN_STOCKS_SCHWAB_BURST_SIZE", DEFAULT_SCHWAB_BURST_SIZE),
        )
    return (
        _int_env("OPEN_STOCKS_ROBINHOOD_CALLS_PER_MINUTE", DEFAULT_CALLS_PER_MINUTE),
        _int_env("OPEN_STOCKS_ROBINHOOD_CALLS_PER_HOUR", DEFAULT_CALLS_PER_HOUR),
        _int_env("OPEN_STOCKS_ROBINHOOD_BURST_SIZE", DEFAULT_BURST_SIZE),
    )


def get_batcher(
    name: str,
    batch_size: int = 10,
    queue_max_wait: float = 0.5,
) -> Batcher[Any]:
    """Get or create a named batcher instance."""
    if name not in _batchers:
        _batchers[name] = Batcher(name, batch_size, queue_max_wait)
    return _batchers[name]


def reset_batchers() -> None:
    """Reset all batcher state for test isolation."""
    global _batchers
    _batchers = {}


def configure_global_rate_limiter(
    calls_per_minute: int,
    calls_per_hour: int,
    burst_size: int,
) -> RateLimiter:
    """Configure the process-global rate limiter from startup config."""
    global _rate_limiter
    _rate_limiter = RateLimiter(
        calls_per_minute=calls_per_minute,
        calls_per_hour=calls_per_hour,
        burst_size=burst_size,
    )
    return _rate_limiter


def reset_global_rate_limiter() -> None:
    """Reset global rate limiter state for test isolation."""
    global _rate_limiter
    _rate_limiter = None


def reset_request_coordinator() -> None:
    """Reset global request coordinator for test isolation."""
    global _request_coordinator
    _request_coordinator = None


def get_rate_limiter(broker_name: str | None = None) -> RateLimiter:
    """Get the global rate limiter instance.

    Returns:
        The global RateLimiter instance
    """
    global _rate_limiter
    if broker_name:
        from open_stocks_mcp.brokers.registry import get_broker_registry_sync

        return get_broker_registry_sync().get_rate_limiter(broker_name)
    if _rate_limiter is None:
        # Initialize with conservative defaults
        _rate_limiter = RateLimiter(
            calls_per_minute=DEFAULT_CALLS_PER_MINUTE,
            calls_per_hour=DEFAULT_CALLS_PER_HOUR,
            burst_size=DEFAULT_BURST_SIZE,
        )
    return _rate_limiter


def get_request_coordinator() -> RequestCoordinator:
    """Get the global request coordinator instance."""
    global _request_coordinator
    if _request_coordinator is None:
        _request_coordinator = RequestCoordinator()
    return _request_coordinator


async def rate_limited_call(
    func: Any,
    *args: Any,
    endpoint: str | None = None,
    broker_name: str | None = None,
    **kwargs: Any,
) -> Any:
    """Execute a function with rate limiting.

    Args:
        func: Function to execute
        endpoint: Optional endpoint identifier
        *args, **kwargs: Arguments to pass to the function

    Returns:
        Result of the function call
    """
    limiter = get_rate_limiter(broker_name=broker_name)
    await limiter.acquire(endpoint)

    if asyncio.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return await asyncio.to_thread(func, *args, **kwargs)
