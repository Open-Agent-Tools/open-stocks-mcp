"""Bounded concurrent fan-out helpers for broker enrichment lookups.

Per-row instrument and quote lookups are common N+1 traps in this codebase
(see issue #986). These helpers let call sites:

- Deduplicate identical lookup keys (instrument URLs, option IDs, symbols)
  so duplicates within a single request hit the broker only once.
- Issue the remaining unique lookups concurrently with a bounded semaphore
  instead of serially.
- Surface per-key failures via ``return_exceptions=True`` so a single bad
  lookup does not abort the whole batch.

The helpers intentionally do not call ``execute_with_retry`` themselves —
that keeps each call site in control of its retry/error contract and lets
existing module-level mocks (which patch ``execute_with_retry``) keep
working.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Iterable
from typing import TypeVar

DEFAULT_BATCH_CONCURRENCY = 8

T = TypeVar("T")


async def gather_bounded(
    coros: Iterable[Awaitable[T]],
    *,
    limit: int = DEFAULT_BATCH_CONCURRENCY,
) -> list[T | BaseException]:
    """Run ``coros`` concurrently, capping in-flight tasks at ``limit``.

    Mirrors ``asyncio.gather(..., return_exceptions=True)`` — results are
    returned in submission order, and per-coroutine exceptions appear in
    place of values rather than aborting the batch.
    """
    coros_list = list(coros)
    if not coros_list:
        return []

    effective_limit = max(1, limit)
    semaphore = asyncio.Semaphore(effective_limit)

    async def _bounded(coro: Awaitable[T]) -> T:
        async with semaphore:
            return await coro

    return await asyncio.gather(
        *(_bounded(c) for c in coros_list), return_exceptions=True
    )


def dedupe_preserving_order(keys: Iterable[str | None]) -> list[str]:
    """Return the unique non-empty keys from ``keys`` in first-seen order."""
    seen: set[str] = set()
    unique: list[str] = []
    for key in keys:
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(key)
    return unique
