"""In-memory async caching layer for tool functions.

Wraps async callables with a TTL or LRU cache (powered by ``cachetools``) and
records hit/miss counters into the global :class:`MetricsCollector`. Used to
suppress redundant Robin Stocks API calls for hot read-only paths such as
quotes and portfolio overviews.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, TypeVar

from cachetools import LRUCache, TTLCache

from open_stocks_mcp.config import get_cache_config
from open_stocks_mcp.monitoring import get_metrics_collector

T = TypeVar("T")

# Module-level registry so clear_caches() can reset every wrapped function's
# state — tests in particular rely on this to avoid leaking across cases.
_CACHE_REGISTRY: list[tuple[str, Any, asyncio.Lock | None]] = []


def _make_key(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[Any, ...]:
    return args + tuple(sorted(kwargs.items()))


def _should_store(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, dict) and isinstance(value.get("result"), dict):
        return value["result"].get("status") not in {"error", "no_data"}
    return True


def cached_async(
    name: str,
    *,
    ttl: float | None = None,
    max_size: int = 1024,
    strategy: str = "ttl",
    clock: Callable[[], float] | None = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Return a decorator that memoizes an async callable.

    Args:
        name: Logical cache name used for metrics counters.
        ttl: Time-to-live in seconds (TTL strategy). Defaults to 60 when unset.
        max_size: Maximum number of cached entries.
        strategy: ``"ttl"`` (default) or ``"lru"``.
        clock: Optional monotonic clock for tests; only honored by the TTL
            strategy. Defaults to :func:`time.monotonic`.
    """
    if strategy not in {"ttl", "lru"}:
        raise ValueError(f"Unsupported cache strategy: {strategy!r}")

    if strategy == "ttl":
        timer = clock or time.monotonic
        cache: Any = TTLCache(
            maxsize=max_size, ttl=ttl if ttl is not None else 60, timer=timer
        )
    else:
        cache = LRUCache(maxsize=max_size)

    # We use a dictionary to store locks per event loop to ensure they are
    # always bound to the currently running loop. This prevents hangs and
    # "attached to a different loop" errors during testing.
    locks: dict[asyncio.AbstractEventLoop, asyncio.Lock] = {}

    _CACHE_REGISTRY.append((name, cache, None))

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            if not get_cache_config().enabled:
                return await func(*args, **kwargs)

            # Get or create lock for the current event loop
            loop = asyncio.get_running_loop()
            if loop not in locks:
                locks[loop] = asyncio.Lock()
            lock = locks[loop]

            key = _make_key(args, kwargs)
            metrics = get_metrics_collector()
            async with lock:
                if key in cache:
                    value: T = cache[key]
                    await metrics.record_cache_hit(name)
                    return value
                await metrics.record_cache_miss(name)
                value = await func(*args, **kwargs)
                if _should_store(value):
                    cache[key] = value
                return value

        return wrapper

    return decorator


def cached_tool(
    namespace: str,
    ttl_seconds: float,
    max_size: int = 1024,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Compatibility wrapper for the issue-plan cache decorator API."""
    return cached_async(name=namespace, ttl=ttl_seconds, max_size=max_size)


def clear_caches() -> None:
    """Clear every registered cache. Intended for tests."""
    for _name, cache, _lock in _CACHE_REGISTRY:
        cache.clear()


def clear_all_caches() -> None:
    """Compatibility alias for clearing registered caches."""
    clear_caches()
