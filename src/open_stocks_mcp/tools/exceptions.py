"""Exception types and classification helpers for broker API errors."""


class BrokerError(Exception):
    """Base exception for broker-related errors."""

    def __init__(
        self,
        message: str,
        broker: str,
        error_type: str,
        original_error: Exception | None = None,
    ):
        super().__init__(f"[{broker}] {message}")
        self.message = message
        self.broker = broker
        self.error_type = error_type
        self.original_error = original_error


class BrokerAuthenticationError(BrokerError):
    """Raised when broker authentication fails."""

    def __init__(
        self,
        broker: str,
        message: str = "Authentication failed",
        original_error: Exception | None = None,
    ):
        BrokerError.__init__(self, message, broker, "authentication", original_error)


class BrokerRateLimitError(BrokerError):
    """Raised when broker rate limits are exceeded."""

    def __init__(
        self,
        broker: str,
        message: str = "Rate limit exceeded",
        original_error: Exception | None = None,
    ):
        BrokerError.__init__(self, message, broker, "rate_limit", original_error)


class BrokerNetworkError(BrokerError):
    """Raised when broker network errors occur."""

    def __init__(
        self,
        broker: str,
        message: str = "Network error",
        original_error: Exception | None = None,
    ):
        BrokerError.__init__(self, message, broker, "network", original_error)


class BrokerDataError(BrokerError):
    """Raised when broker data parsing or validation fails."""

    def __init__(
        self,
        broker: str,
        message: str = "Data error",
        original_error: Exception | None = None,
    ):
        BrokerError.__init__(self, message, broker, "data", original_error)


class BrokerAPIError(BrokerError):
    """Raised for general broker API errors."""

    def __init__(
        self,
        broker: str,
        message: str = "API error",
        original_error: Exception | None = None,
    ):
        BrokerError.__init__(self, message, broker, "api", original_error)


class RobinStocksError(BrokerError):
    """Base exception for Robin Stocks related errors."""

    def __init__(
        self,
        message: str,
        error_type: str = "general",
        original_error: Exception | None = None,
    ):
        super().__init__(
            message=message,
            broker="robinhood",
            error_type=error_type,
            original_error=original_error,
        )


class AuthenticationError(BrokerAuthenticationError, RobinStocksError):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        original_error: Exception | None = None,
    ):
        super().__init__("robinhood", message, original_error)


class RateLimitError(BrokerRateLimitError, RobinStocksError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        original_error: Exception | None = None,
    ):
        super().__init__("robinhood", message, original_error)


class NetworkError(BrokerNetworkError, RobinStocksError):
    """Raised when network connectivity issues occur."""

    def __init__(
        self, message: str = "Network error", original_error: Exception | None = None
    ):
        super().__init__("robinhood", message, original_error)


class DataError(BrokerDataError, RobinStocksError):
    """Raised when data parsing or validation fails."""

    def __init__(
        self, message: str = "Data error", original_error: Exception | None = None
    ):
        super().__init__("robinhood", message, original_error)


class APIError(BrokerAPIError, RobinStocksError):
    """Raised for general API errors."""

    def __init__(
        self, message: str = "API error", original_error: Exception | None = None
    ):
        super().__init__("robinhood", message, original_error)


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


def classify_schwab_error(error: Exception) -> BrokerError:
    """Classify an exception into a Schwab-tagged broker error type."""
    if isinstance(error, TimeoutError):
        return BrokerNetworkError("schwab", "Network connectivity issue", error)
    if isinstance(error, ConnectionError):
        return BrokerNetworkError("schwab", "Network connectivity issue", error)

    response = getattr(error, "response", None)
    status_code = getattr(response, "status_code", None)
    if status_code == 401:
        return BrokerAuthenticationError("schwab", "Authentication failed", error)
    if status_code == 429:
        return BrokerRateLimitError("schwab", "Rate limit exceeded", error)
    if isinstance(status_code, int) and 400 <= status_code < 600:
        return BrokerAPIError("schwab", f"API error: {error}", error)

    error_str = str(error).lower()
    if any(k in error_str for k in ["401", "unauthorized", "token expired"]):
        return BrokerAuthenticationError("schwab", "Authentication failed", error)
    if any(k in error_str for k in ["429", "rate limit", "too many requests"]):
        return BrokerRateLimitError("schwab", "Rate limit exceeded", error)
    if any(k in error_str for k in ["connection", "network", "timeout", "dns"]):
        return BrokerNetworkError("schwab", "Network connectivity issue", error)
    if any(k in error_str for k in ["json", "decode", "parse", "malformed"]):
        return BrokerDataError("schwab", "Data parsing or validation error", error)
    return BrokerAPIError("schwab", f"API error: {error}", error)
