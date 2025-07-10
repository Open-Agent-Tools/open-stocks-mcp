"""Rate limiting for Robin Stocks API calls."""

import asyncio
import time
from collections import defaultdict, deque
from typing import Any

from open_stocks_mcp.logging_config import logger


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

    async def acquire(self, endpoint: str | None = None, weight: float = 1.0) -> None:
        """Acquire permission to make an API call.

        Args:
            endpoint: Optional endpoint identifier for per-endpoint limiting
            weight: Weight of this call (some calls may count more)
        """
        async with self._lock:
            now = time.time()

            # Remove old timestamps (older than 1 hour)
            cutoff_hour = now - 3600
            while self.call_times and self.call_times[0] < cutoff_hour:
                self.call_times.popleft()

            # Check hourly limit
            if len(self.call_times) >= self.calls_per_hour:
                # Calculate wait time
                oldest_call = self.call_times[0]
                wait_time = (oldest_call + 3600) - now
                if wait_time > 0:
                    logger.warning(
                        f"Rate limit reached (hourly). Waiting {wait_time:.1f}s"
                    )
                    await asyncio.sleep(wait_time)
                    # Recursive call after wait
                    await self.acquire(endpoint, weight)
                    return

            # Check minute limit
            cutoff_minute = now - 60
            recent_calls = sum(1 for t in self.call_times if t > cutoff_minute)

            if recent_calls >= self.calls_per_minute:
                # Find the oldest call in the last minute
                minute_calls = [t for t in self.call_times if t > cutoff_minute]
                if minute_calls:
                    wait_time = (minute_calls[0] + 60) - now
                    if wait_time > 0:
                        logger.warning(
                            f"Rate limit reached (minute). Waiting {wait_time:.1f}s"
                        )
                        await asyncio.sleep(wait_time)
                        # Recursive call after wait
                        await self.acquire(endpoint, weight)
                        return

            # Check burst limit
            cutoff_burst = now - 1  # 1 second window for burst
            burst_calls = sum(1 for t in self.call_times if t > cutoff_burst)

            if burst_calls >= self.burst_size:
                wait_time = 1.0 - (
                    now - max(t for t in self.call_times if t > cutoff_burst)
                )
                if wait_time > 0:
                    logger.debug(f"Burst limit reached. Waiting {wait_time:.3f}s")
                    await asyncio.sleep(wait_time)

            # Record the call
            for _ in range(int(weight)):
                self.call_times.append(now)

            # Track per-endpoint if specified
            if endpoint:
                self.endpoint_buckets[endpoint].append(now)

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
