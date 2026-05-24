import asyncio
import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

from open_stocks_mcp.logging_config import logger

T = TypeVar("T")


def install_robinhood_request_timeout(
    timeout_seconds: float, session: Any | None = None
) -> None:
    """Idempotently install a timeout policy on a requests-like session.

    This wraps the session's request method to ensure every call uses the
    centrally configured timeout, overriding any call-site defaults provided
    by the SDK.
    """
    if session is None:
        try:
            from robin_stocks.robinhood import helper

            session = helper.SESSION
        except ImportError:
            logger.warning(
                "robin_stocks not installed; skipping Robinhood timeout policy installation"
            )
            return

    # Check if already installed
    if getattr(session.request, "_is_timeout_wrapper", False) is True:
        session._robinhood_timeout = timeout_seconds
        return

    session._robinhood_timeout = timeout_seconds
    original_request = session.request

    @functools.wraps(original_request)
    def timeout_wrapper(*args: Any, **kwargs: Any) -> Any:
        kwargs["timeout"] = getattr(session, "_robinhood_timeout", 16.0)
        return original_request(*args, **kwargs)

    timeout_wrapper._is_timeout_wrapper = True  # type: ignore[attr-defined]
    session.request = timeout_wrapper
    logger.debug(f"Installed Robinhood request timeout policy: {timeout_seconds}s")


async def execute_broker_request(
    func: Callable[..., T],
    *args: Any,
    policy: Any | None = None,
    retry_safe: bool = True,
    **kwargs: Any,
) -> T:
    """Execute a synchronous broker SDK call with optional retries and deadline enforcement.

    Args:
        func: The synchronous broker SDK function to call.
        policy: Optional BrokerRequestConfig override.
        retry_safe: Whether it's safe to retry this operation (True for reads, False for mutations).
        *args, **kwargs: Arguments passed to the SDK function.
    """
    if policy is None:
        from open_stocks_mcp.config import get_config

        policy = get_config().broker_requests

    # max_retries: int
    # initial_delay: float
    # backoff_factor: float
    # deadline: float | None

    max_retries = int(policy.retry_max_retries) if retry_safe else 0
    initial_delay = float(policy.retry_initial_delay)
    backoff_factor = float(policy.retry_backoff_factor)
    deadline = policy.total_deadline_seconds
    if deadline is not None:
        deadline = float(deadline)

    start_time = time.time()
    last_exception = None

    for attempt in range(max_retries + 1):
        if deadline is not None:
            elapsed = time.time() - start_time
            if elapsed >= deadline:
                if last_exception:
                    raise last_exception
                raise TimeoutError(f"Broker request exceeded deadline of {deadline}s")

        try:
            # Run sync function in thread pool to avoid blocking the event loop
            return await asyncio.to_thread(func, *args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt == max_retries:
                raise e

            # Calculate delay for next retry
            delay = initial_delay * (backoff_factor**attempt)

            # Check if next attempt would likely exceed the deadline
            if deadline is not None:
                elapsed = time.time() - start_time
                if elapsed + delay >= deadline:
                    logger.warning(
                        f"Stopping retries for {getattr(func, '__name__', 'unknown')}: next delay ({delay:.2f}s) "
                        f"would exceed deadline budget ({deadline - elapsed:.2f}s remaining)"
                    )
                    raise e

            logger.info(
                f"Retrying {getattr(func, '__name__', 'unknown')} (attempt {attempt + 1}/{max_retries}) "
                f"after {delay:.2f}s delay due to: {e}"
            )
            await asyncio.sleep(delay)

    if last_exception:
        raise last_exception
    raise RuntimeError("Unreachable")
