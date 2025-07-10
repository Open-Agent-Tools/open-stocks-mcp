"""Robin Stocks error handling utilities."""

import asyncio
import functools
from collections.abc import Callable
from typing import Any

from open_stocks_mcp.logging_config import logger


class RobinStocksError(Exception):
    """Base exception for Robin Stocks related errors."""

    def __init__(
        self,
        message: str,
        error_type: str = "general",
        original_error: Exception | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.original_error = original_error


class AuthenticationError(RobinStocksError):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        original_error: Exception | None = None,
    ):
        super().__init__(message, "authentication", original_error)


class RateLimitError(RobinStocksError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        original_error: Exception | None = None,
    ):
        super().__init__(message, "rate_limit", original_error)


class NetworkError(RobinStocksError):
    """Raised when network connectivity issues occur."""

    def __init__(
        self, message: str = "Network error", original_error: Exception | None = None
    ):
        super().__init__(message, "network", original_error)


class DataError(RobinStocksError):
    """Raised when data parsing or validation fails."""

    def __init__(
        self, message: str = "Data error", original_error: Exception | None = None
    ):
        super().__init__(message, "data", original_error)


class APIError(RobinStocksError):
    """Raised for general API errors."""

    def __init__(
        self, message: str = "API error", original_error: Exception | None = None
    ):
        super().__init__(message, "api", original_error)


def classify_error(error: Exception) -> RobinStocksError:
    """Classify an exception into a specific Robin Stocks error type."""
    error_str = str(error).lower()

    # Authentication errors
    if any(
        keyword in error_str
        for keyword in [
            "unauthorized",
            "login",
            "authentication",
            "token",
            "session",
            "invalid credentials",
        ]
    ):
        return AuthenticationError("Authentication failed", error)

    # Rate limiting errors
    if any(
        keyword in error_str
        for keyword in [
            "rate limit",
            "too many requests",
            "429",
            "quota exceeded",
            "throttled",
        ]
    ):
        return RateLimitError("Rate limit exceeded", error)

    # Network errors
    if any(
        keyword in error_str
        for keyword in [
            "connection",
            "network",
            "timeout",
            "dns",
            "resolve",
            "unreachable",
        ]
    ):
        return NetworkError("Network connectivity issue", error)

    # Data errors
    if any(
        keyword in error_str
        for keyword in ["json", "parse", "decode", "invalid data", "malformed"]
    ):
        return DataError("Data parsing or validation error", error)

    # Default to general API error
    return APIError(f"API error: {error}", error)


def create_error_response(error: Exception, context: str = "") -> dict[str, Any]:
    """Create a standardized error response."""
    classified_error = classify_error(error)

    response = {
        "result": {
            "error": classified_error.message,
            "error_type": classified_error.error_type,
            "status": "error",
        }
    }

    if context:
        response["result"]["context"] = context

    logger.error(
        f"Robin Stocks error {context}: {classified_error.message}", exc_info=True
    )
    return response


def handle_robin_stocks_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to handle Robin Stocks API errors consistently."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        context = f"in {func.__name__}"
        try:
            return await func(*args, **kwargs)  # type: ignore[no-any-return]
        except Exception as e:
            return create_error_response(e, context)

    return wrapper


def handle_robin_stocks_sync_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to handle Robin Stocks API errors for sync functions."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        context = f"in {func.__name__}"
        try:
            return func(*args, **kwargs)  # type: ignore[no-any-return]
        except Exception as e:
            return create_error_response(e, context)

    return wrapper


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
    """Execute a function with retry logic for transient errors.

    Args:
        func: Function to execute
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay on each retry
        handle_auth_errors: Whether to attempt re-authentication on auth errors
        rate_limit: Whether to apply rate limiting
        endpoint: Optional endpoint identifier for rate limiting
    """
    from open_stocks_mcp.tools.rate_limiter import get_rate_limiter
    from open_stocks_mcp.tools.session_manager import get_session_manager

    last_exception = None
    session_manager = get_session_manager()
    rate_limiter = get_rate_limiter() if rate_limit else None
    auth_retry_count = 0
    max_auth_retries = 1

    for attempt in range(max_retries + 1):
        try:
            # Apply rate limiting if enabled
            if rate_limiter:
                await rate_limiter.acquire(endpoint)

            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, func, *args, **kwargs)

            # Update last successful call on success
            session_manager.update_last_successful_call()
            return result

        except Exception as e:
            last_exception = e
            classified_error = classify_error(e)

            # Handle authentication errors with re-authentication
            if isinstance(classified_error, AuthenticationError) and handle_auth_errors:
                if auth_retry_count < max_auth_retries:
                    logger.warning(
                        f"Authentication error detected, attempting re-authentication: {e}"
                    )
                    auth_retry_count += 1

                    # Try to refresh the session
                    try:
                        success = await session_manager.refresh_session()
                        if success:
                            logger.info(
                                "Re-authentication successful, retrying request"
                            )
                            # Don't count this as a regular retry attempt
                            attempt -= 1
                            continue
                        else:
                            logger.error("Re-authentication failed")
                            raise classified_error
                    except Exception as reauth_error:
                        logger.error(f"Re-authentication error: {reauth_error}")
                        raise classified_error from reauth_error
                else:
                    logger.error(f"Authentication error after re-auth attempts: {e}")
                    raise classified_error from e

            # Don't retry data errors
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

    # This should never be reached, but just in case
    if last_exception:
        raise classify_error(last_exception)


def validate_symbol(symbol: str) -> bool:
    """Validate a stock symbol format."""
    if not symbol or not isinstance(symbol, str):
        return False

    # Basic validation: 1-5 characters, alphanumeric, uppercase
    symbol = symbol.strip().upper()
    if len(symbol) < 1 or len(symbol) > 5:
        return False

    return symbol.isalnum()


def validate_period(period: str) -> bool:
    """Validate a time period parameter."""
    valid_periods = ["day", "week", "month", "3month", "year", "5year", "all"]
    return period in valid_periods


def validate_span(span: str) -> bool:
    """Validate a time span parameter."""
    valid_spans = ["day", "week", "month", "3month", "year", "5year", "all"]
    return span in valid_spans


def sanitize_api_response(data: Any) -> Any:
    """Sanitize API response data to remove sensitive information."""
    if isinstance(data, dict):
        # Remove sensitive fields
        sensitive_fields = [
            "password",
            "token",
            "secret",
            "key",
            "authorization",
            "account_number",
            "routing_number",
            "ssn",
            "tax_id",
        ]

        sanitized = {}
        for key, value in data.items():
            if key.lower() in sensitive_fields:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict | list):
                sanitized[key] = sanitize_api_response(value)
            else:
                sanitized[key] = value
        return sanitized

    elif isinstance(data, list):
        return [sanitize_api_response(item) for item in data]

    return data


def log_api_call(func_name: str, symbol: str | None = None, **kwargs: Any) -> None:
    """Log API call for monitoring and debugging."""
    log_data = {"function": func_name}

    if symbol:
        log_data["symbol"] = symbol

    # Add non-sensitive kwargs
    for key, value in kwargs.items():
        if key.lower() not in ["password", "token", "secret", "key"]:
            log_data[key] = value

    logger.info(f"Robin Stocks API call: {log_data}")


def create_no_data_response(
    message: str, context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Create a standardized no-data response."""
    response = {"result": {"message": message, "status": "no_data"}}

    if context:
        response["result"].update(context)

    return response


def create_success_response(data: dict[str, Any]) -> dict[str, Any]:
    """Create a standardized success response."""
    # Allow overriding the status if it's already in the data
    default_status = "success"
    if "status" not in data:
        data["status"] = default_status

    response = {"result": data}

    return response
