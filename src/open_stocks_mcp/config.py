"""Server configuration for Open Stocks MCP MCP server"""

import os
from typing import Any

import yaml
from pydantic import BaseModel, Field, StrictBool, ValidationError


class CacheConfig(BaseModel):
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


class RetryConfig(BaseModel):
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


class TimeoutConfig(BaseModel):
    """Configuration for HTTP request timeout behavior."""

    request_timeout_seconds: float = 120.0


class CircuitBreakerConfig(BaseModel):
    """Configuration for broker-call circuit breaker behavior."""

    enabled: bool = True
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 60.0

    @property
    def cooldown_seconds(self) -> float:
        """Backward-compatible alias for ``recovery_timeout_seconds``."""
        return self.recovery_timeout_seconds


class BrokerRequestConfig(BaseModel):
    """Configuration for broker-specific request policies."""

    robinhood_timeout_seconds: float = 16.0
    schwab_timeout_seconds: float = 30.0
    retry_max_retries: int = 3
    retry_initial_delay: float = 1.0
    retry_backoff_factor: float = 2.0
    total_deadline_seconds: float | None = None


class OtelConfig(BaseModel):
    """OpenTelemetry tracing configuration"""

    enabled: bool = False
    service_name: str = "open-stocks-mcp"
    exporter_endpoint: str | None = None


class BrokerConfig(BaseModel):
    """Configuration for individual brokers."""

    username: str | None = None
    password: str | None = None
    api_key: str | None = None
    app_secret: str | None = None


class FeatureFlags(BaseModel):
    """Configuration for feature flags.

    Uses StrictBool to avoid YAML 1.1 boolean coercion (the "Norway Problem"
    where ``no`` and similar tokens silently parse as ``False``).
    """

    robinhood: StrictBool = True
    schwab: StrictBool = False
    environments: dict[str, dict[str, StrictBool]] = Field(default_factory=dict)


class ServerConfig(BaseModel):
    """Configuration for the MCP server"""

    name: str = "Open Stocks MCP"
    log_level: str = "INFO"
    monitoring_enabled: bool = True
    environment: str = "production"
    cache: CacheConfig = Field(default_factory=CacheConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    timeout: TimeoutConfig = Field(default_factory=TimeoutConfig)
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    broker_requests: BrokerRequestConfig = Field(default_factory=BrokerRequestConfig)
    otel: OtelConfig = Field(default_factory=OtelConfig)
    brokers: dict[str, BrokerConfig] = Field(default_factory=dict)
    feature_flags: FeatureFlags = Field(default_factory=FeatureFlags)

    def is_feature_enabled(self, flag_name: str) -> bool:
        """Resolve feature flag with environment-specific overrides.

        Example precedence::

            feature_flags:
              robinhood: false        # global default for the flag
              environments:
                production:
                  robinhood: true     # overrides the global default in prod

        Lookup order:
        1. Environment-specific override (``feature_flags.environments[env]``).
        2. Global flag value on :class:`FeatureFlags`.
        3. ``False`` for unknown flags.
        """
        env_overrides = self.feature_flags.environments.get(self.environment, {})
        if flag_name in env_overrides:
            return bool(env_overrides[flag_name])

        if hasattr(self.feature_flags, flag_name):
            return bool(getattr(self.feature_flags, flag_name))

        return False


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
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


def _env_optional_int(name: str) -> int | None:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return None
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


    """Load server configuration from YAML, environment, or defaults.

    Precedence is Environment > YAML > Defaults.
    """
    config_dict: dict[str, Any] = {}

    # 1. Load from YAML file if specified
    config_path = os.getenv("OPEN_STOCKS_CONFIG") or os.getenv("OPEN_STOCKS_CONFIG_FILE")
    if config_path:
        if not os.path.exists(config_path):
            raise ValueError(f"Config file not found: {config_path}")
        try:
            with open(config_path) as f:
                yaml_data = yaml.safe_load(f)
                if yaml_data:
                    config_dict.update(yaml_data)
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML in {config_path}: {exc}") from exc
        except Exception as exc:
            raise ValueError(f"Error reading config file {config_path}: {exc}") from exc

    # 2. Layer environment variable overrides
    # Basic Server Config
    if name := os.getenv("MCP_SERVER_NAME"):
        config_dict["name"] = name
    if log_level := os.getenv("LOG_LEVEL"):
        config_dict["log_level"] = log_level
    if monitoring := os.getenv("MONITORING_ENABLED"):
        config_dict["monitoring_enabled"] = monitoring.lower() == "true"
    if env := os.getenv("OPEN_STOCKS_ENV"):
        config_dict["environment"] = env

    # Cache Config
    cache_dict = config_dict.setdefault("cache", {})
    if cache_enabled := os.getenv("CACHE_ENABLED"):
        cache_dict["enabled"] = cache_enabled.lower() == "true"
    if cache_ttl_quotes := os.getenv("CACHE_QUOTES_TTL") or os.getenv("CACHE_TTL_MARKET_SECONDS"):
        cache_dict["quotes_ttl_seconds"] = _env_float_value(cache_ttl_quotes, "CACHE_QUOTES_TTL")
    if cache_ttl_account := os.getenv("CACHE_ACCOUNT_TTL") or os.getenv("CACHE_TTL_ACCOUNT_SECONDS"):
        cache_dict["account_ttl_seconds"] = _env_float_value(cache_ttl_account, "CACHE_ACCOUNT_TTL")
    if cache_max_size := os.getenv("CACHE_MAX_SIZE"):
        cache_dict["max_size"] = _env_int_value(cache_max_size, "CACHE_MAX_SIZE")
    if cache_strategy := os.getenv("CACHE_STRATEGY"):
        cache_dict["strategy"] = cache_strategy

    # Otel Config
    otel_dict = config_dict.setdefault("otel", {})
    if otel_enabled := os.getenv("OTEL_ENABLED"):
        otel_dict["enabled"] = otel_enabled.lower() == "true"
    if otel_service := os.getenv("OTEL_SERVICE_NAME"):
        otel_dict["service_name"] = otel_service
    if otel_endpoint := os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        otel_dict["exporter_endpoint"] = otel_endpoint

    # Brokers Config (Compatibility with existing env vars)
    brokers_dict = config_dict.setdefault("brokers", {})
    rh_dict = brokers_dict.setdefault("robinhood", {})
    if rh_user := os.getenv("ROBINHOOD_USERNAME"):
        rh_dict["username"] = rh_user
    if rh_pass := os.getenv("ROBINHOOD_PASSWORD"):
        rh_dict["password"] = rh_pass

    schwab_dict = brokers_dict.setdefault("schwab", {})
    if schwab_key := os.getenv("SCHWAB_API_KEY"):
        schwab_dict["api_key"] = schwab_key
    if schwab_secret := os.getenv("SCHWAB_APP_SECRET"):
        schwab_dict["app_secret"] = schwab_secret

    # Retry Config
    retry_dict = config_dict.setdefault("retry", {})
    if r_max := os.getenv("OPEN_STOCKS_MCP_RETRY_MAX_RETRIES"):
        retry_dict["max_retries"] = _env_int_value(r_max, "OPEN_STOCKS_MCP_RETRY_MAX_RETRIES")
    if r_delay := os.getenv("OPEN_STOCKS_MCP_RETRY_INITIAL_DELAY"):
        retry_dict["initial_delay"] = _env_float_value(r_delay, "OPEN_STOCKS_MCP_RETRY_INITIAL_DELAY")
    if r_backoff := os.getenv("OPEN_STOCKS_MCP_RETRY_BACKOFF_FACTOR"):
        retry_dict["backoff_factor"] = _env_float_value(r_backoff, "OPEN_STOCKS_MCP_RETRY_BACKOFF_FACTOR")
    if r_auth := os.getenv("OPEN_STOCKS_MCP_RETRY_AUTH_MAX_RETRIES"):
        retry_dict["auth_max_retries"] = _env_int_value(r_auth, "OPEN_STOCKS_MCP_RETRY_AUTH_MAX_RETRIES")
    for env_name, field_name in (
        ("OPEN_STOCKS_MCP_RETRY_AUTHENTICATION_MAX_RETRIES", "authentication_max_retries"),
        ("OPEN_STOCKS_MCP_RETRY_NETWORK_MAX_RETRIES", "network_max_retries"),
        ("OPEN_STOCKS_MCP_RETRY_RATE_LIMIT_MAX_RETRIES", "rate_limit_max_retries"),
        ("OPEN_STOCKS_MCP_RETRY_API_MAX_RETRIES", "api_max_retries"),
        ("OPEN_STOCKS_MCP_RETRY_DATA_MAX_RETRIES", "data_max_retries"),
    ):
        opt_value = _env_optional_int(env_name)
        if opt_value is not None:
            retry_dict[field_name] = opt_value

    # Timeout Config
    timeout_dict = config_dict.setdefault("timeout", {})
    if t_request := os.getenv("OPEN_STOCKS_MCP_HTTP_REQUEST_TIMEOUT_SECONDS"):
        timeout_dict["request_timeout_seconds"] = _env_float_value(
            t_request, "OPEN_STOCKS_MCP_HTTP_REQUEST_TIMEOUT_SECONDS"
        )

    # Circuit Breaker Config
    cb_dict = config_dict.setdefault("circuit_breaker", {})
    if cb_enabled := os.getenv("OPEN_STOCKS_MCP_CIRCUIT_BREAKER_ENABLED"):
        cb_dict["enabled"] = cb_enabled.lower() in {"1", "true", "yes", "on"}
    if cb_threshold := os.getenv("OPEN_STOCKS_MCP_CIRCUIT_BREAKER_FAILURE_THRESHOLD"):
        cb_dict["failure_threshold"] = _env_int_value(
            cb_threshold, "OPEN_STOCKS_MCP_CIRCUIT_BREAKER_FAILURE_THRESHOLD"
        )
    # New canonical env var; fall back to the legacy ``COOLDOWN_SECONDS`` name.
    if cb_recovery := os.getenv(
        "OPEN_STOCKS_MCP_CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS"
    ) or os.getenv("OPEN_STOCKS_MCP_CIRCUIT_BREAKER_COOLDOWN_SECONDS"):
        cb_dict["recovery_timeout_seconds"] = _env_float_value(
            cb_recovery,
            "OPEN_STOCKS_MCP_CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS",
        )

    # Broker Requests Config
    br_dict = config_dict.setdefault("broker_requests", {})
    if br_rh_to := os.getenv("OPEN_STOCKS_MCP_ROBINHOOD_REQUEST_TIMEOUT_SECONDS"):
        br_dict["robinhood_timeout_seconds"] = _env_float_value(
            br_rh_to, "OPEN_STOCKS_MCP_ROBINHOOD_REQUEST_TIMEOUT_SECONDS"
        )
    if br_sch_to := os.getenv("OPEN_STOCKS_MCP_SCHWAB_REQUEST_TIMEOUT_SECONDS"):
        br_dict["schwab_timeout_seconds"] = _env_float_value(
            br_sch_to, "OPEN_STOCKS_MCP_SCHWAB_REQUEST_TIMEOUT_SECONDS"
        )
    # Retry tuning shared with broker-level requests
    if r_max := os.getenv("OPEN_STOCKS_MCP_RETRY_MAX_RETRIES"):
        br_dict["retry_max_retries"] = _env_int_value(r_max, "OPEN_STOCKS_MCP_RETRY_MAX_RETRIES")
    if r_delay := os.getenv("OPEN_STOCKS_MCP_RETRY_INITIAL_DELAY"):
        br_dict["retry_initial_delay"] = _env_float_value(
            r_delay, "OPEN_STOCKS_MCP_RETRY_INITIAL_DELAY"
        )
    if r_backoff := os.getenv("OPEN_STOCKS_MCP_RETRY_BACKOFF_FACTOR"):
        br_dict["retry_backoff_factor"] = _env_float_value(
            r_backoff, "OPEN_STOCKS_MCP_RETRY_BACKOFF_FACTOR"
        )
    if br_deadline := os.getenv("OPEN_STOCKS_MCP_BROKER_REQUEST_TOTAL_DEADLINE_SECONDS"):
        br_dict["total_deadline_seconds"] = _env_float_value(
            br_deadline, "OPEN_STOCKS_MCP_BROKER_REQUEST_TOTAL_DEADLINE_SECONDS"
        )

    try:
        return ServerConfig(**config_dict)
    except ValidationError as exc:
        raise ValueError(f"Configuration validation failed: {exc}") from exc


def _env_int_value(raw_value: str, name: str) -> int:
    """Coerce an already-resolved env string to int, raising on bad input."""
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _env_float_value(raw_value: str, name: str) -> float:
    """Coerce an already-resolved env string to float, raising on bad input."""
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc


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
