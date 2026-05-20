"""Server configuration for Open Stocks MCP MCP server"""

import os
from dataclasses import dataclass, field


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.lower() in {"1", "true", "yes", "on"}


def _env_float_from(names: tuple[str, ...], default: float) -> float:
    for name in names:
        raw_value = os.getenv(name)
        if raw_value is None:
            continue
        try:
            return float(raw_value)
        except ValueError as exc:
            raise ValueError(f"{name} must be a number") from exc
    return default


def _env_int_from(names: tuple[str, ...], default: int) -> int:
    for name in names:
        raw_value = os.getenv(name)
        if raw_value is None:
            continue
        try:
            return int(raw_value)
        except ValueError as exc:
            raise ValueError(f"{name} must be an integer") from exc
    return default


def _env_optional_int(name: str) -> int | None:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return None
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc


@dataclass
class CacheConfig:
    """Configuration for the in-memory caching layer."""

    enabled: bool = True
    quotes_ttl_seconds: float = 15.0
    account_ttl_seconds: float = 60.0
    max_size: int = 1024
    strategy: str = "ttl"

    @property
    def ttl_market_seconds(self) -> float:
        """Compatibility alias for the market-data cache TTL."""
        return self.quotes_ttl_seconds

    @property
    def ttl_account_seconds(self) -> float:
        """Compatibility alias for the account-data cache TTL."""
        return self.account_ttl_seconds


@dataclass
class RetryConfig:
    """Configuration for transient API retry behavior."""

    max_retries: int = 3
    initial_delay: float = 1.0
    backoff_factor: float = 2.0
    auth_max_retries: int = 1
    authentication_max_retries: int | None = None
    network_max_retries: int | None = None
    rate_limit_max_retries: int | None = None
    api_max_retries: int | None = None
    data_max_retries: int | None = None

    def max_retries_for(self, error_type: str) -> int:
        """Return retry attempts for a classified error type."""
        overrides = {
            "authentication": self.authentication_max_retries,
            "network": self.network_max_retries,
            "rate_limit": self.rate_limit_max_retries,
            "api": self.api_max_retries,
            "data": self.data_max_retries,
        }
        override = overrides.get(error_type)
        if override is not None:
            return override
        return self.max_retries


@dataclass
class TimeoutConfig:
    """Configuration for HTTP request timeout behavior."""

    request_timeout_seconds: float = 120.0


@dataclass
class OtelConfig:
    """OpenTelemetry tracing configuration"""

    enabled: bool = False
    service_name: str = "open-stocks-mcp"
    exporter_endpoint: str | None = None


@dataclass
class ServerConfig:
    """Configuration for the MCP server"""

    name: str = "Open Stocks MCP"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    monitoring_enabled: bool = True
    cache: CacheConfig = field(default_factory=CacheConfig)
    retry: RetryConfig | None = None
    timeout: TimeoutConfig | None = None
    otel: OtelConfig = field(default_factory=OtelConfig)

    def __post_init__(self) -> None:
        if self.retry is None:
            self.retry = RetryConfig()
        if self.timeout is None:
            self.timeout = TimeoutConfig()


def load_config() -> ServerConfig:
    """Load server configuration from environment or defaults"""
    cache = CacheConfig(
        enabled=_env_bool("CACHE_ENABLED", True),
        quotes_ttl_seconds=_env_float_from(
            ("CACHE_TTL_MARKET_SECONDS", "CACHE_QUOTES_TTL"), 15.0
        ),
        account_ttl_seconds=_env_float_from(
            ("CACHE_TTL_ACCOUNT_SECONDS", "CACHE_ACCOUNT_TTL"), 60.0
        ),
        max_size=_env_int_from(("CACHE_MAX_SIZE",), 1024),
        strategy=os.getenv("CACHE_STRATEGY", "ttl"),
    )
    enabled_str = os.getenv("OTEL_ENABLED", "false").strip().lower()
    otel_enabled = enabled_str in ("1", "true", "yes")
    return ServerConfig(
        name=os.getenv("MCP_SERVER_NAME", "Open Stocks MCP"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        monitoring_enabled=os.getenv("MONITORING_ENABLED", "true").lower() == "true",
        cache=cache,
        retry=RetryConfig(
            max_retries=_env_int("OPEN_STOCKS_MCP_RETRY_MAX_RETRIES", 3),
            initial_delay=_env_float("OPEN_STOCKS_MCP_RETRY_INITIAL_DELAY", 1.0),
            backoff_factor=_env_float("OPEN_STOCKS_MCP_RETRY_BACKOFF_FACTOR", 2.0),
            auth_max_retries=_env_int("OPEN_STOCKS_MCP_RETRY_AUTH_MAX_RETRIES", 1),
            authentication_max_retries=_env_optional_int(
                "OPEN_STOCKS_MCP_RETRY_AUTHENTICATION_MAX_RETRIES"
            ),
            network_max_retries=_env_optional_int(
                "OPEN_STOCKS_MCP_RETRY_NETWORK_MAX_RETRIES"
            ),
            rate_limit_max_retries=_env_optional_int(
                "OPEN_STOCKS_MCP_RETRY_RATE_LIMIT_MAX_RETRIES"
            ),
            api_max_retries=_env_optional_int("OPEN_STOCKS_MCP_RETRY_API_MAX_RETRIES"),
            data_max_retries=_env_optional_int(
                "OPEN_STOCKS_MCP_RETRY_DATA_MAX_RETRIES"
            ),
        ),
        timeout=TimeoutConfig(
            request_timeout_seconds=_env_float(
                "OPEN_STOCKS_MCP_HTTP_REQUEST_TIMEOUT_SECONDS", 120.0
            )
        ),
        otel=OtelConfig(
            enabled=otel_enabled,
            service_name=os.getenv("OTEL_SERVICE_NAME", "open-stocks-mcp"),
            exporter_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or None,
        ),
    )


# Global config instance for process-level access.
_global_config: ServerConfig | None = None


def get_config() -> ServerConfig:
    """Get the global server configuration instance."""
    global _global_config
    if _global_config is None:
        _global_config = load_config()
    return _global_config


def get_cache_config() -> CacheConfig:
    """Get the global cache configuration."""
    return get_config().cache


def reset_cache_config() -> None:
    """Reset the global configuration instance, primarily for tests."""
    global _global_config
    _global_config = None
