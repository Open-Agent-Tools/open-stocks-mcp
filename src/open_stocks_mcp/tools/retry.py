"""Retry execution helpers for broker API calls."""

import asyncio
import functools
import inspect
from collections.abc import Callable
from typing import Any

from open_stocks_mcp.brokers.registry import (
    RegistryNotInitializedError,
    get_broker_registry_sync,
)
from open_stocks_mcp.config import load_config
from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.exceptions import (
    AuthenticationError,
    CircuitBreakerError,
    DataError,
    classify_error,
)


async def _refresh_session_with_registry_guard(
    session_manager: Any,
    broker_name: str | None,
    account_id: str | None,
) -> bool:
    """Refresh auth through the broker registry single-flight guard when present."""
    async def refresh_call() -> Any:
        result = session_manager.refresh_session()
        if inspect.isawaitable(result):
            return await result
        return result

    try:
        registry = get_broker_registry_sync()
    except RegistryNotInitializedError:
        return bool(await refresh_call())

    return bool(
        await registry.coordinate_auth_refresh(
            broker_name or "robinhood", account_id or "default", refresh_call
        )
    )


async def execute_with_retry(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int | None = None,
    delay: float | None = None,
    backoff_factor: float | None = None,
    handle_auth_errors: bool = True,
    rate_limit: bool = True,
    endpoint: str | None = None,
    broker_name: str | None = "robinhood",
    account_id: str | None = None,
    **kwargs: Any,
) -> Any:
    """Execute a function with retry logic for transient errors."""
    from open_stocks_mcp.tools.circuit_breaker import get_broker_circuit_breaker
    from open_stocks_mcp.tools.rate_limiter import get_rate_limiter
    from open_stocks_mcp.tools.session_manager import get_session_manager

    last_exception = None
    retry_config = load_config().retry
    if retry_config is None:
        raise RuntimeError("Retry configuration unavailable")
    configured_max_retries = (
        retry_config.max_retries if max_retries is None else max_retries
    )
    retry_delay = retry_config.initial_delay if delay is None else delay
    retry_backoff_factor = (
        retry_config.backoff_factor if backoff_factor is None else backoff_factor
    )
    session_manager = get_session_manager()
    circuit_breaker = get_broker_circuit_breaker()
    rate_limiter = get_rate_limiter() if rate_limit else None
    auth_retry_count = 0
    max_auth_retries = retry_config.auth_max_retries

    attempt = 0
    while attempt <= configured_max_retries:
        try:
            await circuit_breaker.before_request()
            if rate_limiter:
                await rate_limiter.acquire(endpoint)

            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                loop = asyncio.get_event_loop()
                bound_func = functools.partial(func, *args, **kwargs)
                result = await loop.run_in_executor(None, bound_func)

            session_manager.update_last_successful_call()
            await circuit_breaker.record_success()
            return result

        except Exception as e:
            if isinstance(e, CircuitBreakerError):
                raise
            last_exception = e
            classified_error = classify_error(e)
            if max_retries is None:
                configured_max_retries = retry_config.max_retries_for(
                    classified_error.error_type
                )

            if isinstance(classified_error, AuthenticationError) and handle_auth_errors:
                if session_manager.should_block_auth_retries():
                    logger.critical(
                        "Blocking authentication retry due to persistent session cache clear failures"
                    )
                    raise AuthenticationError(
                        "Session cache clear failures prevent safe authentication retry"
                    ) from e
                if auth_retry_count < max_auth_retries:
                    logger.warning(
                        f"Authentication error detected, attempting re-authentication: {e}"
                    )
                    auth_retry_count += 1

                    try:
                        success = await _refresh_session_with_registry_guard(
                            session_manager,
                            broker_name,
                            account_id,
                        )
                        if success:
                            logger.info(
                                "Re-authentication successful, retrying request"
                            )
                            continue
                        logger.error("Re-authentication failed")
                        await circuit_breaker.record_failure(
                            classified_error.error_type
                        )
                        raise classified_error
                    except Exception as reauth_error:
                        logger.error(f"Re-authentication error: {reauth_error}")
                        await circuit_breaker.record_failure(
                            classified_error.error_type
                        )
                        raise classified_error from reauth_error
                else:
                    logger.error(f"Authentication error after re-auth attempts: {e}")
                    await circuit_breaker.record_failure(classified_error.error_type)
                    raise classified_error from e

            if isinstance(classified_error, DataError):
                logger.error(f"Data error, not retrying: {e}")
                raise classified_error from e

            if attempt < configured_max_retries:
                wait_time = retry_delay * (retry_backoff_factor**attempt)
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}"
                )
                await asyncio.sleep(wait_time)
                attempt += 1
            else:
                logger.error(f"All {configured_max_retries + 1} attempts failed: {e}")
                await circuit_breaker.record_failure(classified_error.error_type)
                raise classified_error from e

    if last_exception:
        raise classify_error(last_exception)
