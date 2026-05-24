"""Tests for YAML-backed server configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

from open_stocks_mcp.config import ConfigError, load_config


@pytest.mark.unit
@pytest.mark.journey_system
def test_loads_yaml_config_values(tmp_path: Path) -> None:
    path = tmp_path / "open-stocks-mcp.yaml"
    path.write_text(
        """
server:
  name: YAML Server
  log_level: DEBUG
rate_limits:
  calls_per_minute: 42
  calls_per_hour: 1200
  burst_size: 9
cache:
  ttl_market_seconds: 12
  ttl_account_seconds: 33
  max_size: 2048
feature_flags:
  enable_cache: false
  enable_circuit_breaker: true
""".strip()
    )

    cfg = load_config(config_path=path)

    assert cfg.name == "YAML Server"
    assert cfg.log_level == "DEBUG"
    assert cfg.rate_limits.calls_per_minute == 42
    assert cfg.rate_limits.calls_per_hour == 1200
    assert cfg.rate_limits.burst_size == 9
    assert cfg.cache.ttl_market_seconds == 12
    assert cfg.cache.ttl_account_seconds == 33
    assert cfg.cache.max_size == 2048
    assert cfg.feature_flags.enable_cache is False
    assert cfg.feature_flags.enable_circuit_breaker is True


@pytest.mark.unit
@pytest.mark.journey_system
def test_env_overrides_yaml_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        """
server:
  name: YAML Name
  log_level: WARNING
rate_limits:
  calls_per_minute: 10
  calls_per_hour: 200
  burst_size: 2
cache:
  ttl_market_seconds: 5
  ttl_account_seconds: 6
  max_size: 7
feature_flags:
  enable_cache: true
  enable_circuit_breaker: false
""".strip()
    )

    monkeypatch.setenv("MCP_SERVER_NAME", "Env Name")
    monkeypatch.setenv("LOG_LEVEL", "ERROR")
    monkeypatch.setenv("RATE_LIMIT_CALLS_PER_MINUTE", "55")
    monkeypatch.setenv("RATE_LIMIT_CALLS_PER_HOUR", "1550")
    monkeypatch.setenv("RATE_LIMIT_BURST_SIZE", "8")
    monkeypatch.setenv("CACHE_TTL_MARKET_SECONDS", "25")
    monkeypatch.setenv("CACHE_TTL_ACCOUNT_SECONDS", "35")
    monkeypatch.setenv("CACHE_MAX_SIZE", "300")
    monkeypatch.setenv("ENABLE_CACHE", "false")
    monkeypatch.setenv("ENABLE_CIRCUIT_BREAKER", "true")

    cfg = load_config(config_path=path)

    assert cfg.name == "Env Name"
    assert cfg.log_level == "ERROR"
    assert cfg.rate_limits.calls_per_minute == 55
    assert cfg.rate_limits.calls_per_hour == 1550
    assert cfg.rate_limits.burst_size == 8
    assert cfg.cache.ttl_market_seconds == 25
    assert cfg.cache.ttl_account_seconds == 35
    assert cfg.cache.max_size == 300
    assert cfg.feature_flags.enable_cache is False
    assert cfg.feature_flags.enable_circuit_breaker is True


@pytest.mark.unit
@pytest.mark.journey_system
@pytest.mark.parametrize("debug_value", ["1", "true", "TRUE", "yes", "on"])
def test_debug_env_enables_debug_log_level(
    monkeypatch: pytest.MonkeyPatch, debug_value: str
) -> None:
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.setenv("DEBUG", debug_value)

    cfg = load_config(config_path=Path("/tmp/definitely-missing-config.yaml"))

    assert cfg.log_level == "DEBUG"


@pytest.mark.unit
@pytest.mark.journey_system
def test_log_level_env_takes_precedence_over_debug_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")

    cfg = load_config(config_path=Path("/tmp/definitely-missing-config.yaml"))

    assert cfg.log_level == "WARNING"


@pytest.mark.unit
@pytest.mark.journey_system
@pytest.mark.parametrize("debug_value", ["", "0", "false", "no", "off"])
def test_false_debug_env_keeps_default_log_level(
    monkeypatch: pytest.MonkeyPatch, debug_value: str
) -> None:
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.setenv("DEBUG", debug_value)

    cfg = load_config(config_path=Path("/tmp/definitely-missing-config.yaml"))

    assert cfg.log_level == "INFO"


@pytest.mark.unit
@pytest.mark.journey_system
def test_missing_file_uses_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "MCP_SERVER_NAME",
        "LOG_LEVEL",
        "RATE_LIMIT_CALLS_PER_MINUTE",
        "RATE_LIMIT_CALLS_PER_HOUR",
        "RATE_LIMIT_BURST_SIZE",
        "CACHE_TTL_MARKET_SECONDS",
        "CACHE_TTL_ACCOUNT_SECONDS",
        "CACHE_MAX_SIZE",
        "ENABLE_CACHE",
        "ENABLE_CIRCUIT_BREAKER",
    ):
        monkeypatch.delenv(var, raising=False)

    cfg = load_config(config_path=Path("/tmp/definitely-missing-config.yaml"))

    assert cfg.name == "Open Stocks MCP"
    assert cfg.log_level == "INFO"
    assert cfg.rate_limits.calls_per_minute == 30
    assert cfg.rate_limits.calls_per_hour == 1000
    assert cfg.rate_limits.burst_size == 5
    assert cfg.cache.ttl_market_seconds > 0
    assert cfg.cache.ttl_account_seconds > 0
    assert cfg.cache.max_size > 0
    assert cfg.feature_flags.enable_cache is True
    assert cfg.feature_flags.enable_circuit_breaker is False


@pytest.mark.unit
@pytest.mark.journey_system
@pytest.mark.parametrize(
    "content,expected",
    [
        ("- item", "mapping"),
        ("[]", "mapping"),
        ("server: [", "YAML"),
        ("unknown: 1", "unknown"),
        ("server:\n  log_level: VERBOSE", "log_level"),
        ("rate_limits:\n  calls_per_minute: 0", "calls_per_minute"),
    ],
)
def test_invalid_yaml_and_values_raise_config_error(
    tmp_path: Path, content: str, expected: str
) -> None:
    path = tmp_path / "open-stocks-mcp.yaml"
    path.write_text(content)

    with pytest.raises(ConfigError, match=expected):
        load_config(config_path=path)


@pytest.mark.unit
@pytest.mark.journey_system
def test_invalid_boolean_env_value_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "open-stocks-mcp.yaml"
    path.write_text("feature_flags:\n  enable_cache: true")
    monkeypatch.setenv("ENABLE_CACHE", "definitely")

    with pytest.raises(ConfigError, match="ENABLE_CACHE"):
        load_config(config_path=path)


@pytest.mark.unit
@pytest.mark.journey_system
def test_load_config_from_open_stocks_config_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        """
server:
  name: Env Path Config
feature_flags:
  brokers.robinhood:
    default: false
""".strip()
    )
    monkeypatch.setenv("OPEN_STOCKS_CONFIG", str(path))
    monkeypatch.delenv("OPEN_STOCKS_CONFIG_FILE", raising=False)

    cfg = load_config()
    assert cfg.name == "Env Path Config"
    assert cfg.is_feature_enabled("brokers.robinhood") is False


@pytest.mark.unit
@pytest.mark.journey_system
def test_load_config_from_open_stocks_config_file_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "config-file.yaml"
    path.write_text(
        """
server:
  name: Env Path Config File
feature_flags:
  brokers.schwab:
    default: true
""".strip()
    )
    monkeypatch.delenv("OPEN_STOCKS_CONFIG", raising=False)
    monkeypatch.setenv("OPEN_STOCKS_CONFIG_FILE", str(path))

    cfg = load_config()
    assert cfg.name == "Env Path Config File"
    assert cfg.is_feature_enabled("brokers.schwab") is True


@pytest.mark.unit
@pytest.mark.journey_system
def test_feature_flags_resolve_per_environment(tmp_path: Path) -> None:
    path = tmp_path / "feature-flags.yaml"
    path.write_text(
        """
environment: prod
feature_flags:
  brokers.robinhood:
    default: false
    environments:
      prod: true
  brokers.schwab:
    default: false
""".strip()
    )

    cfg = load_config(config_path=path)
    assert cfg.is_feature_enabled("brokers.robinhood") is True
    assert cfg.is_feature_enabled("brokers.schwab") is False
    assert cfg.is_feature_enabled("brokers.unknown") is False


@pytest.mark.unit
@pytest.mark.journey_system
def test_invalid_feature_flag_schema_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad-feature-flags.yaml"
    path.write_text(
        """
feature_flags:
  brokers.robinhood:
    default: maybe
""".strip()
    )

    with pytest.raises(ConfigError, match=r"brokers\.robinhood"):
        load_config(config_path=path)
