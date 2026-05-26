"""Response formatting, sanitization, and error decorators."""

import functools
from collections.abc import Callable
from typing import Any, TypeVar, cast

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.exceptions import classify_error

F = TypeVar("F", bound=Callable[..., Any])


def create_error_response(error: Exception, context: str = "") -> dict[str, Any]:
    """Create a standardized error response."""
    classified_error = classify_error(error)

    response: dict[str, Any] = {
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


def handle_robin_stocks_errors(func: F) -> F:
    """Decorator to handle Robin Stocks API errors consistently."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        context = f"in {func.__name__}"
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return create_error_response(e, context)

    return cast(F, wrapper)


def handle_schwab_errors(func: F) -> F:
    """Decorator to handle Schwab API errors consistently."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        context = f"in {func.__name__}"
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return create_error_response(e, context)

    return cast(F, wrapper)


def sanitize_api_response(data: Any) -> Any:
    """Sanitize API response data to remove sensitive information."""
    if isinstance(data, dict):
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

    if isinstance(data, list):
        return [sanitize_api_response(item) for item in data]

    return data


def log_api_call(func_name: str, symbol: str | None = None, **kwargs: Any) -> None:
    """Log API call for monitoring and debugging."""
    log_data = {"function": func_name}

    if symbol:
        log_data["symbol"] = symbol

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
    if "status" not in data:
        data["status"] = "success"
    return {"result": data}
