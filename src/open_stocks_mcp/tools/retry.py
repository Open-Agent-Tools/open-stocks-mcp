"""Retry execution helpers for broker API calls."""

import asyncio
import functools
from collections.abc import Callable
from typing import Any

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.exceptions import (
    AuthenticationError,
    DataError,
    classify_error,
)


async def execute_with_retry(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    handle_auth_errors: bool = True,
    rate_limit: bool = True,
    endpoint: str | None = None,
    **kwargs: Any,
) -> Any:
    """Execute a function with retry logic for transient errors."""
    from open_stocks_mcp.tools.rate_limiter import get_rate_limiter
    from open_stocks_mcp.tools.session_manager import get_session_manager

    last_exception = None
    session_manager = get_session_manager()
    rate_limiter = get_rate_limiter() if rate_limit else None
    auth_retry_count = 0
    max_auth_retries = 1

    for attempt in range(max_retries + 1):
        try:
            if rate_limiter:
                await rate_limiter.acquire(endpoint)

            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                loop = asyncio.get_event_loop()
                bound_func = functools.partial(func, *args, **kwargs)
                result = await loop.run_in_executor(None, bound_func)

            session_manager.update_last_successful_call()
            return result

        except Exception as e:
            last_exception = e
            classified_error = classify_error(e)

            if isinstance(classified_error, AuthenticationError) and handle_auth_errors:
                if auth_retry_count < max_auth_retries:
                    logger.warning(
                        f"Authentication error detected, attempting re-authentication: {e}"
                    )
                    auth_retry_count += 1

                    try:
                        success = await session_manager.refresh_session()
                        if success:
                            logger.info("Re-authentication successful, retrying request")
                            attempt -= 1
                            continue
                        logger.error("Re-authentication failed")
                        raise classified_error
                    except Exception as reauth_error:
                        logger.error(f"Re-authentication error: {reauth_error}")
                        raise classified_error from reauth_error
                else:
                    logger.error(f"Authentication error after re-auth attempts: {e}")
                    raise classified_error from e

            if isinstance(classified_error, DataError):
                logger.error(f"Data error, not retrying: {e}")
                raise classified_error from e

            if attempt < max_retries:
                wait_time = delay * (backoff_factor**attempt)
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"All {max_retries + 1} attempts failed: {e}")
                raise classified_error from e

    if last_exception:
        raise classify_error(last_exception)
