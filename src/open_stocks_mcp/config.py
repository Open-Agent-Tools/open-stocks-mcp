"""Server configuration for Open Stocks MCP MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


class ConfigError(ValueError):
    """Raised when configuration cannot be parsed or validated."""


_ALLOWED_TOP_LEVEL_KEYS = {
    "environment",
    "server",
    "brokers",
    "rate_limits",
    "batch",
    "cache",
    "feature_flags",
    "retry",
    "timeout",
    "circuit_breaker",
    "broker_requests",
    "otel",
}


def _parse_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{field_name} must be an integer") from exc


def _parse_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{field_name} must be a number") from exc


def _parse_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "":
            return False
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off", ""}:
            return False
    raise ConfigError(f"{field_name} must be a boolean")


def _env_optional_int(name: str) -> int | None:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return None
    return _parse_int(raw_value, name)


def _validate_positive_int(value: int, field_name: str) -> int:
    if value <= 0:
        raise ConfigError(f"{field_name} must be > 0")
    return value


def _validate_log_level(value: str) -> str:
    valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    normalized = value.upper()
    if normalized not in valid:
        raise ConfigError(
            "server.log_level must be one of DEBUG/INFO/WARNING/ERROR/CRITICAL"
        )
    return normalized


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise ConfigError(f"YAML parse error in {path}: {exc}") from exc

    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError(f"Config in {path} must be a mapping")

    unknown = set(raw.keys()) - _ALLOWED_TOP_LEVEL_KEYS
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ConfigError(f"Config contains unknown top-level sections: {names}")

    return raw


def _discover_config_path(explicit_path: Path | None) -> Path | None:
    if explicit_path is not None:
        return explicit_path

    for env_var in ("OPEN_STOCKS_CONFIG", "OPEN_STOCKS_CONFIG_FILE", "OPEN_STOCKS_MCP_CONFIG"):
        env_path = os.getenv(env_var)
        if env_path:
            return Path(env_path)

    for candidate in (Path("open-stocks-mcp.yaml"), Path("config.yaml")):
        if candidate.exists():
            return candidate
    return None


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
        return self.quotes_ttl_seconds

    @property
    def ttl_account_seconds(self) -> float:
        return self.account_ttl_seconds


@dataclass
class BatchConfig:
    """Configuration for request batching."""

    batch_size: int = 10
    queue_max_wait: float = 0.5


@dataclass
class RateLimitConfig:
    """Configuration for runtime API call limits."""

    calls_per_minute: int = 30
    calls_per_hour: int = 1000
    burst_size: int = 5


@dataclass
class FeatureFlagConfig:
    """Feature flags for optional behavior."""

    enable_cache: bool = True
    enable_circuit_breaker: bool = False


@dataclass
class FeatureFlagDefinition:
    default: bool = False
    environments: dict[str, bool] = field(default_factory=dict)


@dataclass
class RetryConfig:
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
    request_timeout_seconds: float = 120.0


@dataclass
class CircuitBreakerConfig:
    enabled: bool = True
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 60.0

    @property
    def cooldown_seconds(self) -> float:
        """Backward-compatible alias for recovery timeout."""
        return self.recovery_timeout_seconds


@dataclass
class BrokerRequestConfig:
    robinhood_timeout_seconds: float = 16.0
    schwab_timeout_seconds: float = 30.0
    retry_max_retries: int = 3
    retry_initial_delay: float = 1.0
    retry_backoff_factor: float = 2.0
    total_deadline_seconds: float | None = None


@dataclass
class AlertConfig:
    """Configuration for the proactive alerting system."""

    enabled: bool = False
    webhook_url: str | None = None
    error_rate_degraded_threshold: float = 10.0
    error_rate_unhealthy_threshold: float = 25.0
    avg_response_time_degraded_ms: float = 5000.0
    avg_response_time_unhealthy_ms: float = 10000.0
    dedup_window_seconds: float = 300.0


@dataclass
class OtelConfig:
    enabled: bool = False
    service_name: str = "open-stocks-mcp"
    exporter_endpoint: str | None = None


@dataclass
class ServerConfig:
    name: str = "Open Stocks MCP"
    environment: str = "default"
    log_level: str = "INFO"
    monitoring_enabled: bool = True
    rate_limits: RateLimitConfig = field(default_factory=RateLimitConfig)
    batch: BatchConfig = field(default_factory=BatchConfig)
    feature_flags: FeatureFlagConfig = field(default_factory=FeatureFlagConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    retry: RetryConfig | None = None
    timeout: TimeoutConfig | None = None
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    broker_requests: BrokerRequestConfig = field(default_factory=BrokerRequestConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    otel: OtelConfig = field(default_factory=OtelConfig)
    feature_flag_definitions: dict[str, FeatureFlagDefinition] = field(
        default_factory=dict
    )
    schwab_api_key: str | None = None
    schwab_app_secret: str | None = None

    def __post_init__(self) -> None:
        if self.retry is None:
            self.retry = RetryConfig()
        if self.timeout is None:
            self.timeout = TimeoutConfig()

    def is_feature_enabled(self, flag_name: str) -> bool:
        if flag_name == "enable_cache":
            return self.feature_flags.enable_cache
        if flag_name == "enable_circuit_breaker":
            return self.feature_flags.enable_circuit_breaker

        definition = self.feature_flag_definitions.get(flag_name)
        if definition is None:
            return False

        if self.environment in definition.environments:
            return definition.environments[self.environment]
        return definition.default


def load_config(config_path: Path | str | None = None) -> ServerConfig:
    """Load server configuration from YAML + environment with env precedence."""
    explicit = Path(config_path) if config_path is not None else None
    selected = _discover_config_path(explicit)
    raw: dict[str, Any] = {}
    if selected is not None:
        if selected.exists():
            raw = _load_yaml_mapping(selected)
        elif explicit is not None:
            raw = {}
        else:
            raise ConfigError(f"Config file not found: {selected}")

    server = raw.get("server", {}) if isinstance(raw.get("server", {}), dict) else {}
    brokers = raw.get("brokers", {}) if isinstance(raw.get("brokers", {}), dict) else {}
    rate_limits = (
        raw.get("rate_limits", {})
        if isinstance(raw.get("rate_limits", {}), dict)
        else {}
    )
    batch_config = (
        raw.get("batch", {}) if isinstance(raw.get("batch", {}), dict) else {}
    )
    cache = raw.get("cache", {}) if isinstance(raw.get("cache", {}), dict) else {}
    feature_flags = (
        raw.get("feature_flags", {})
        if isinstance(raw.get("feature_flags", {}), dict)
        else {}
    )
    environment = str(raw.get("environment", "default"))

    for section_name, section_value in (
        ("server", raw.get("server", {})),
        ("brokers", raw.get("brokers", {})),
        ("rate_limits", raw.get("rate_limits", {})),
        ("batch", raw.get("batch", {})),
        ("cache", raw.get("cache", {})),
        ("feature_flags", raw.get("feature_flags", {})),
    ):
        if section_value is not None and not isinstance(section_value, dict):
            raise ConfigError(f"{section_name} must be a mapping")

    feature_flag_definitions: dict[str, FeatureFlagDefinition] = {}
    for flag_name, flag_value in feature_flags.items():
        if flag_name in {"enable_cache", "enable_circuit_breaker"}:
            continue
        if isinstance(flag_value, bool):
            feature_flag_definitions[flag_name] = FeatureFlagDefinition(
                default=flag_value
            )
            continue
        if not isinstance(flag_value, dict):
            raise ConfigError(f"feature_flags.{flag_name} must be a boolean or mapping")
        default_raw = flag_value.get("default", False)
        if not isinstance(default_raw, bool):
            raise ConfigError(f"feature_flags.{flag_name}.default must be a boolean")
        env_values_raw = flag_value.get("environments", {})
        if not isinstance(env_values_raw, dict):
            raise ConfigError(
                f"feature_flags.{flag_name}.environments must be a mapping"
            )
        env_values: dict[str, bool] = {}
        for env_name, env_enabled in env_values_raw.items():
            if not isinstance(env_enabled, bool):
                raise ConfigError(
                    f"feature_flags.{flag_name}.environments.{env_name} must be a boolean"
                )
            env_values[str(env_name)] = env_enabled
        feature_flag_definitions[flag_name] = FeatureFlagDefinition(
            default=default_raw,
            environments=env_values,
        )

    name = os.getenv("MCP_SERVER_NAME", str(server.get("name", "Open Stocks MCP")))
    log_level = _validate_log_level(
        os.getenv("LOG_LEVEL", str(server.get("log_level", "INFO")))
    )

    calls_per_minute = _validate_positive_int(
        _parse_int(
            os.getenv(
                "RATE_LIMIT_CALLS_PER_MINUTE",
                str(rate_limits.get("calls_per_minute", 30)),
            ),
            "rate_limits.calls_per_minute",
        ),
        "rate_limits.calls_per_minute",
    )
    calls_per_hour = _validate_positive_int(
        _parse_int(
            os.getenv(
                "RATE_LIMIT_CALLS_PER_HOUR",
                str(rate_limits.get("calls_per_hour", 1000)),
            ),
            "rate_limits.calls_per_hour",
        ),
        "rate_limits.calls_per_hour",
    )
    burst_size = _validate_positive_int(
        _parse_int(
            os.getenv("RATE_LIMIT_BURST_SIZE", str(rate_limits.get("burst_size", 5))),
            "rate_limits.burst_size",
        ),
        "rate_limits.burst_size",
    )

    ttl_market_seconds = _parse_float(
        os.getenv(
            "CACHE_TTL_MARKET_SECONDS",
            os.getenv("CACHE_QUOTES_TTL", str(cache.get("ttl_market_seconds", 15.0))),
        ),
        "cache.ttl_market_seconds",
    )
    ttl_account_seconds = _parse_float(
        os.getenv(
            "CACHE_TTL_ACCOUNT_SECONDS",
            os.getenv("CACHE_ACCOUNT_TTL", str(cache.get("ttl_account_seconds", 60.0))),
        ),
        "cache.ttl_account_seconds",
    )
    cache_max_size = _validate_positive_int(
        _parse_int(
            os.getenv("CACHE_MAX_SIZE", str(cache.get("max_size", 1024))),
            "cache.max_size",
        ),
        "cache.max_size",
    )

    cache_enabled = _parse_bool(
        os.getenv("CACHE_ENABLED", str(feature_flags.get("enable_cache", True))),
        "CACHE_ENABLED",
    )
    enable_cache = _parse_bool(
        os.getenv("ENABLE_CACHE", str(feature_flags.get("enable_cache", True))),
        "ENABLE_CACHE",
    )
    enable_circuit_breaker = _parse_bool(
        os.getenv(
            "ENABLE_CIRCUIT_BREAKER",
            str(feature_flags.get("enable_circuit_breaker", False)),
        ),
        "ENABLE_CIRCUIT_BREAKER",
    )

    monitoring_enabled = _parse_bool(
        os.getenv("MONITORING_ENABLED", "true"),
        "MONITORING_ENABLED",
    )

    otel_enabled = _parse_bool(os.getenv("OTEL_ENABLED", "false"), "OTEL_ENABLED")

    cfg = ServerConfig(
        name=name,
        environment=os.getenv("OPEN_STOCKS_ENVIRONMENT", environment),
        log_level=log_level,
        monitoring_enabled=monitoring_enabled,
        rate_limits=RateLimitConfig(
            calls_per_minute=calls_per_minute,
            calls_per_hour=calls_per_hour,
            burst_size=burst_size,
        ),
        batch=BatchConfig(
            batch_size=_parse_int(
                os.getenv(
                    "OPEN_STOCKS_MCP_BATCH_SIZE",
                    str(batch_config.get("batch_size", 10)),
                ),
                "batch.batch_size",
            ),
            queue_max_wait=_parse_float(
                os.getenv(
                    "OPEN_STOCKS_MCP_QUEUE_MAX_WAIT",
                    str(batch_config.get("queue_max_wait", 0.5)),
                ),
                "batch.queue_max_wait",
            ),
        ),
        feature_flags=FeatureFlagConfig(
            enable_cache=enable_cache,
            enable_circuit_breaker=enable_circuit_breaker,
        ),
        cache=CacheConfig(
            enabled=cache_enabled,
            quotes_ttl_seconds=ttl_market_seconds,
            account_ttl_seconds=ttl_account_seconds,
            max_size=cache_max_size,
            strategy=os.getenv("CACHE_STRATEGY", str(cache.get("strategy", "ttl"))),
        ),
        retry=RetryConfig(
            max_retries=_parse_int(
                os.getenv("OPEN_STOCKS_MCP_RETRY_MAX_RETRIES", "3"),
                "OPEN_STOCKS_MCP_RETRY_MAX_RETRIES",
            ),
            initial_delay=_parse_float(
                os.getenv("OPEN_STOCKS_MCP_RETRY_INITIAL_DELAY", "1.0"),
                "OPEN_STOCKS_MCP_RETRY_INITIAL_DELAY",
            ),
            backoff_factor=_parse_float(
                os.getenv("OPEN_STOCKS_MCP_RETRY_BACKOFF_FACTOR", "2.0"),
                "OPEN_STOCKS_MCP_RETRY_BACKOFF_FACTOR",
            ),
            auth_max_retries=_parse_int(
                os.getenv("OPEN_STOCKS_MCP_RETRY_AUTH_MAX_RETRIES", "1"),
                "OPEN_STOCKS_MCP_RETRY_AUTH_MAX_RETRIES",
            ),
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
            request_timeout_seconds=_parse_float(
                os.getenv("OPEN_STOCKS_MCP_HTTP_REQUEST_TIMEOUT_SECONDS", "120.0"),
                "OPEN_STOCKS_MCP_HTTP_REQUEST_TIMEOUT_SECONDS",
            )
        ),
        circuit_breaker=CircuitBreakerConfig(
            enabled=_parse_bool(
                os.getenv("OPEN_STOCKS_MCP_CIRCUIT_BREAKER_ENABLED", "true"),
                "OPEN_STOCKS_MCP_CIRCUIT_BREAKER_ENABLED",
            ),
            failure_threshold=_parse_int(
                os.getenv("OPEN_STOCKS_MCP_CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5"),
                "OPEN_STOCKS_MCP_CIRCUIT_BREAKER_FAILURE_THRESHOLD",
            ),
            recovery_timeout_seconds=_parse_float(
                os.getenv(
                    "OPEN_STOCKS_MCP_CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS",
                    os.getenv(
                        "OPEN_STOCKS_MCP_CIRCUIT_BREAKER_COOLDOWN_SECONDS", "60.0"
                    ),
                ),
                "OPEN_STOCKS_MCP_CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS",
            ),
        ),
        broker_requests=BrokerRequestConfig(
            robinhood_timeout_seconds=_parse_float(
                os.getenv("OPEN_STOCKS_MCP_ROBINHOOD_REQUEST_TIMEOUT_SECONDS", "16.0"),
                "OPEN_STOCKS_MCP_ROBINHOOD_REQUEST_TIMEOUT_SECONDS",
            ),
            schwab_timeout_seconds=_parse_float(
                os.getenv("OPEN_STOCKS_MCP_SCHWAB_REQUEST_TIMEOUT_SECONDS", "30.0"),
                "OPEN_STOCKS_MCP_SCHWAB_REQUEST_TIMEOUT_SECONDS",
            ),
            retry_max_retries=_parse_int(
                os.getenv("OPEN_STOCKS_MCP_RETRY_MAX_RETRIES", "3"),
                "OPEN_STOCKS_MCP_RETRY_MAX_RETRIES",
            ),
            retry_initial_delay=_parse_float(
                os.getenv("OPEN_STOCKS_MCP_RETRY_INITIAL_DELAY", "1.0"),
                "OPEN_STOCKS_MCP_RETRY_INITIAL_DELAY",
            ),
            retry_backoff_factor=_parse_float(
                os.getenv("OPEN_STOCKS_MCP_RETRY_BACKOFF_FACTOR", "2.0"),
                "OPEN_STOCKS_MCP_RETRY_BACKOFF_FACTOR",
            ),
            total_deadline_seconds=(
                _parse_float(
                    os.getenv(
                        "OPEN_STOCKS_MCP_BROKER_REQUEST_TOTAL_DEADLINE_SECONDS", "0"
                    ),
                    "OPEN_STOCKS_MCP_BROKER_REQUEST_TOTAL_DEADLINE_SECONDS",
                )
                if os.getenv("OPEN_STOCKS_MCP_BROKER_REQUEST_TOTAL_DEADLINE_SECONDS")
                else None
            ),
        ),
        alerts=AlertConfig(
            enabled=_parse_bool(os.getenv("ALERTS_ENABLED", "false"), "ALERTS_ENABLED"),
            webhook_url=os.getenv("ALERT_WEBHOOK_URL") or None,
            error_rate_degraded_threshold=_parse_float(
                os.getenv("ALERT_ERROR_RATE_DEGRADED_THRESHOLD", "10.0"),
                "ALERT_ERROR_RATE_DEGRADED_THRESHOLD",
            ),
            error_rate_unhealthy_threshold=_parse_float(
                os.getenv("ALERT_ERROR_RATE_UNHEALTHY_THRESHOLD", "25.0"),
                "ALERT_ERROR_RATE_UNHEALTHY_THRESHOLD",
            ),
            avg_response_time_degraded_ms=_parse_float(
                os.getenv("ALERT_AVG_RESPONSE_TIME_DEGRADED_MS", "5000.0"),
                "ALERT_AVG_RESPONSE_TIME_DEGRADED_MS",
            ),
            avg_response_time_unhealthy_ms=_parse_float(
                os.getenv("ALERT_AVG_RESPONSE_TIME_UNHEALTHY_MS", "10000.0"),
                "ALERT_AVG_RESPONSE_TIME_UNHEALTHY_MS",
            ),
            dedup_window_seconds=_parse_float(
                os.getenv("ALERT_DEDUP_WINDOW_SECONDS", "300.0"),
                "ALERT_DEDUP_WINDOW_SECONDS",
            ),
        ),
        otel=OtelConfig(
            enabled=otel_enabled,
            service_name=os.getenv("OTEL_SERVICE_NAME", "open-stocks-mcp"),
            exporter_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or None,
        ),
        feature_flag_definitions=feature_flag_definitions,
        schwab_api_key=(
            os.getenv("SCHWAB_API_KEY")
            or str(
                (brokers.get("schwab", {}) if isinstance(brokers.get("schwab"), dict) else {}).get("api_key", "")
            )
            or None
        ),
        schwab_app_secret=(
            os.getenv("SCHWAB_APP_SECRET")
            or str(
                (brokers.get("schwab", {}) if isinstance(brokers.get("schwab"), dict) else {}).get("app_secret", "")
            )
            or None
        ),
    )

    if not cfg.feature_flags.enable_cache:
        cfg.cache.enabled = False

    return cfg


_global_config: ServerConfig | None = None


def get_config() -> ServerConfig:
    global _global_config
    if _global_config is None:
        _global_config = load_config()
    return _global_config


def get_cache_config() -> CacheConfig:
    return get_config().cache


def reset_cache_config() -> None:
    global _global_config
    _global_config = None
