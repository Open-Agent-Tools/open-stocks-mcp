"""Retry execution helpers for broker API calls."""

import asyncio
import functools
from collections.abc import Callable
from typing import Any

from open_stocks_mcp.config import load_config
from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.exceptions import (
    AuthenticationError,
    CircuitBreakerError,
    DataError,
    classify_error,
)

DEFAULT_MAX_RETRIES = 3


async def execute_with_retry(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int | None = None,
    delay: float | None = None,
    backoff_factor: float | None = None,
    handle_auth_errors: bool = True,
    rate_limit: bool = True,
    endpoint: str | None = None,
    broker_name: str = "robinhood",
    account_id: str | None = None,
    coalesce_key: str | None = None,
    **kwargs: Any,
) -> Any:
    """Execute a function with retry logic for transient errors.

    When *coalesce_key* is supplied the call is wrapped in a singleflight
    coordinator: if an identical key is already in-flight the caller shares
    that result instead of triggering a new broker call. Only supply a key for
    read-only operations; never use it for mutating/trading calls.
    """
    if coalesce_key is not None:
        from open_stocks_mcp.tools.rate_limiter import get_request_coordinator

        coordinator = get_request_coordinator()

        async def _call() -> Any:
            return await execute_with_retry(
                func,
                *args,
                max_retries=max_retries,
                delay=delay,
                backoff_factor=backoff_factor,
                handle_auth_errors=handle_auth_errors,
                rate_limit=rate_limit,
                endpoint=endpoint,
                broker_name=broker_name,
                account_id=account_id,
                coalesce_key=None,
                **kwargs,
            )

        return await coordinator.execute(coalesce_key, _call)

    from open_stocks_mcp.brokers.registry import get_broker_registry
    from open_stocks_mcp.brokers.session_state import get_session_manager
    from open_stocks_mcp.tools.circuit_breaker import get_broker_circuit_breaker
    from open_stocks_mcp.tools.rate_limiter import get_rate_limiter

    last_exception = None
    retry_config = load_config().retry
    if retry_config is None:
        raise RuntimeError("Retry configuration unavailable")
    configured_max_retries = (
        retry_config.max_retries if max_retries is None else max_retries
    )
    if configured_max_retries is None:
        configured_max_retries = DEFAULT_MAX_RETRIES
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
                bound_func = functools.partial(func, *args, **kwargs)
                result = await asyncio.to_thread(bound_func)

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
                        success = await (
                            await get_broker_registry()
                        ).coordinated_refresh(
                            broker_name=broker_name,
                            account_id=account_id,
                            refresh_coro=session_manager.refresh_session,
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
