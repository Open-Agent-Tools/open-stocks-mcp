"""Exception types and classification helpers for broker API errors."""


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


class CircuitBreakerError(RobinStocksError):
    """Raised when circuit breaker blocks broker calls."""

    def __init__(
        self,
        message: str = "Circuit breaker open",
        original_error: Exception | None = None,
    ):
        super().__init__(message, "circuit_breaker", original_error)


def classify_error(error: Exception) -> RobinStocksError:
    """Classify an exception into a specific Robin Stocks error type."""
    # Check Python built-in network exception types first (before string matching)
    if isinstance(error, TimeoutError):
        return NetworkError("Network connectivity issue", error)
    if isinstance(error, ConnectionError):
        return NetworkError("Network connectivity issue", error)

    error_str = str(error).lower()

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

    if any(
        keyword in error_str
        for keyword in ["json", "parse", "decode", "invalid data", "malformed"]
    ):
        return DataError("Data parsing or validation error", error)

    return APIError(f"API error: {error}", error)
