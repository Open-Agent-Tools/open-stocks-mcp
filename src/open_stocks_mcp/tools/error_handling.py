"""Compatibility facade for error handling helpers.

This module remains as a stable import surface while implementation is split
across focused modules.
"""

from open_stocks_mcp.tools.exceptions import (
    APIError,
    AuthenticationError,
    CircuitBreakerError,
    DataError,
    NetworkError,
    RateLimitError,
    RobinStocksError,
    classify_error,
)
from open_stocks_mcp.tools.responses import (
    create_error_response,
    create_no_data_response,
    create_success_response,
    handle_robin_stocks_errors,
    handle_robin_stocks_sync_errors,
    handle_schwab_errors,
    log_api_call,
    sanitize_api_response,
)
from open_stocks_mcp.tools.retry import DEFAULT_MAX_RETRIES, execute_with_retry
from open_stocks_mcp.tools.validation import (
    validate_period,
    validate_symbol,
)

__all__ = [
    "DEFAULT_MAX_RETRIES",
    "APIError",
    "AuthenticationError",
    "CircuitBreakerError",
    "DataError",
    "NetworkError",
    "RateLimitError",
    "RobinStocksError",
    "classify_error",
    "create_error_response",
    "create_no_data_response",
    "create_success_response",
    "execute_with_retry",
    "handle_robin_stocks_errors",
    "handle_robin_stocks_sync_errors",
    "handle_schwab_errors",
    "log_api_call",
    "sanitize_api_response",
    "validate_period",
    "validate_symbol",
]
