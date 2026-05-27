"""Tests for YAML-backed server configuration."""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import pytest

<<<<<<< HEAD
from open_stocks_mcp.config import ConfigError, RetryConfig, load_config
=======
from open_stocks_mcp.config import ConfigError, RetryConfig, load_config
>>>>>>> 9af2b56 (feat: implement typed broker configuration models from Schwab integration plan (#265))


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


@pytest.mark.unit
@pytest.mark.journey_system
def test_authentication_retry_count_uses_generic_max_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    retry_fields = {field.name for field in fields(RetryConfig)}
    retry = RetryConfig(max_retries=3)

    assert "authentication_max_retries" not in retry_fields
    assert retry.max_retries_for("authentication") == 3

    monkeypatch.setenv("OPEN_STOCKS_MCP_RETRY_MAX_RETRIES", "3")
    monkeypatch.setenv("OPEN_STOCKS_MCP_RETRY_AUTHENTICATION_MAX_RETRIES", "9")

    cfg = load_config(config_path=Path("/tmp/definitely-missing-config.yaml"))

    assert cfg.retry.max_retries_for("authentication") == 3


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


@pytest.mark.unit
@pytest.mark.journey_system
def test_timeout_tool_execution_timeout_seconds_parsed_from_yaml(
    tmp_path: Path,
) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("timeout:\n  tool_execution_timeout_seconds: 45.0")

    cfg = load_config(config_path=path)

    assert cfg.timeout is not None
    assert cfg.timeout.tool_execution_timeout_seconds == 45.0


@pytest.mark.unit
@pytest.mark.journey_system
def test_tool_execution_timeout_env_overrides_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("timeout:\n  tool_execution_timeout_seconds: 45.0")
    monkeypatch.setenv("OPEN_STOCKS_MCP_TOOL_EXECUTION_TIMEOUT_SECONDS", "99.0")

    cfg = load_config(config_path=path)

    assert cfg.timeout is not None
    assert cfg.timeout.tool_execution_timeout_seconds == 99.0


@pytest.mark.unit
@pytest.mark.journey_system
def test_tool_execution_timeout_defaults_to_30(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPEN_STOCKS_MCP_TOOL_EXECUTION_TIMEOUT_SECONDS", raising=False)

    cfg = load_config(config_path=Path("/tmp/definitely-missing-config.yaml"))

    assert cfg.timeout is not None
    assert cfg.timeout.tool_execution_timeout_seconds == 30.0


# ---------------------------------------------------------------------------
# Broker config tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.journey_system
def test_broker_config_defaults_missing_file(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "ROBINHOOD_USERNAME",
        "ROBINHOOD_PASSWORD",
        "SCHWAB_API_KEY",
        "SCHWAB_APP_SECRET",
        "SCHWAB_CALLBACK_URL",
        "SCHWAB_TOKEN_PATH",
        "ENABLED_BROKERS",
        "DEFAULT_BROKER",
    ):
        monkeypatch.delenv(var, raising=False)

    cfg = load_config(config_path=Path("/tmp/definitely-missing-config.yaml"))

    assert cfg.brokers.enabled_brokers == ["robinhood"]
    assert cfg.brokers.default_broker is None
    assert cfg.brokers.robinhood.username is None
    assert cfg.brokers.robinhood.password is None
    assert cfg.brokers.schwab.api_key is None
    assert cfg.brokers.schwab.app_secret is None


@pytest.mark.unit
@pytest.mark.journey_system
def test_broker_config_robinhood_credentials_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ROBINHOOD_USERNAME", "testuser")
    monkeypatch.setenv("ROBINHOOD_PASSWORD", "testpass")
    monkeypatch.delenv("ENABLED_BROKERS", raising=False)

    cfg = load_config(config_path=Path("/tmp/definitely-missing-config.yaml"))

    assert cfg.brokers.robinhood.username == "testuser"
    assert cfg.brokers.robinhood.password == "testpass"


@pytest.mark.unit
@pytest.mark.journey_system
def test_broker_config_schwab_credentials_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCHWAB_API_KEY", "mykey")
    monkeypatch.setenv("SCHWAB_APP_SECRET", "mysecret")
    monkeypatch.setenv("SCHWAB_CALLBACK_URL", "https://cb.example.com/")
    monkeypatch.setenv("SCHWAB_TOKEN_PATH", "/tmp/token.json")
    monkeypatch.delenv("ENABLED_BROKERS", raising=False)

    cfg = load_config(config_path=Path("/tmp/definitely-missing-config.yaml"))

    assert cfg.brokers.schwab.api_key == "mykey"
    assert cfg.brokers.schwab.app_secret == "mysecret"
    assert cfg.brokers.schwab.callback_url == "https://cb.example.com/"
    assert cfg.brokers.schwab.token_path == "/tmp/token.json"


@pytest.mark.unit
@pytest.mark.journey_system
def test_broker_config_yaml_overridden_by_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        """
brokers:
  robinhood:
    username: yaml_user
    password: yaml_pass
  schwab:
    api_key: yaml_key
""".strip()
    )
    monkeypatch.setenv("ROBINHOOD_USERNAME", "env_user")
    monkeypatch.setenv("ROBINHOOD_PASSWORD", "env_pass")
    monkeypatch.setenv("SCHWAB_API_KEY", "env_key")
    monkeypatch.delenv("ENABLED_BROKERS", raising=False)

    cfg = load_config(config_path=path)

    assert cfg.brokers.robinhood.username == "env_user"
    assert cfg.brokers.robinhood.password == "env_pass"
    assert cfg.brokers.schwab.api_key == "env_key"


@pytest.mark.unit
@pytest.mark.journey_system
def test_enabled_brokers_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLED_BROKERS", " Robinhood, schwab ")

    cfg = load_config(config_path=Path("/tmp/definitely-missing-config.yaml"))

    assert cfg.brokers.enabled_brokers == ["robinhood", "schwab"]


@pytest.mark.unit
@pytest.mark.journey_system
def test_enabled_brokers_empty_string(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLED_BROKERS", "")

    cfg = load_config(config_path=Path("/tmp/definitely-missing-config.yaml"))

    assert cfg.brokers.enabled_brokers == []


@pytest.mark.unit
@pytest.mark.journey_system
def test_enabled_brokers_unknown_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLED_BROKERS", "bogus,robinhood")

    cfg = load_config(config_path=Path("/tmp/definitely-missing-config.yaml"))

    assert cfg.brokers.enabled_brokers == ["robinhood"]
    assert "bogus" not in cfg.brokers.enabled_brokers


@pytest.mark.unit
@pytest.mark.journey_system
def test_default_broker_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLED_BROKERS", "robinhood,schwab")
    monkeypatch.setenv("DEFAULT_BROKER", "schwab")
    monkeypatch.setenv("SCHWAB_API_KEY", "k")
    monkeypatch.setenv("SCHWAB_APP_SECRET", "s")

    cfg = load_config(config_path=Path("/tmp/definitely-missing-config.yaml"))

    assert cfg.brokers.default_broker == "schwab"


@pytest.mark.unit
@pytest.mark.journey_system
def test_broker_config_yaml_values_used_when_no_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        """
brokers:
  robinhood:
    username: yaml_user
    password: yaml_pass
    pickle_name: mydb
    session_timeout_hours: 12
  schwab:
    api_key: yaml_key
    app_secret: yaml_secret
    callback_url: https://my.callback/
    token_path: /tmp/tok.json
  enabled_brokers:
    - robinhood
    - schwab
  default_broker: robinhood
""".strip()
    )
    for var in (
        "ROBINHOOD_USERNAME",
        "ROBINHOOD_PASSWORD",
        "SCHWAB_API_KEY",
        "SCHWAB_APP_SECRET",
        "SCHWAB_CALLBACK_URL",
        "SCHWAB_TOKEN_PATH",
        "ENABLED_BROKERS",
        "DEFAULT_BROKER",
    ):
        monkeypatch.delenv(var, raising=False)

    cfg = load_config(config_path=path)

    assert cfg.brokers.robinhood.username == "yaml_user"
    assert cfg.brokers.robinhood.password == "yaml_pass"
    assert cfg.brokers.robinhood.pickle_name == "mydb"
    assert cfg.brokers.robinhood.session_timeout_hours == 12
    assert cfg.brokers.schwab.api_key == "yaml_key"
    assert cfg.brokers.schwab.app_secret == "yaml_secret"
    assert cfg.brokers.schwab.callback_url == "https://my.callback/"
    assert cfg.brokers.schwab.token_path == "/tmp/tok.json"
    assert cfg.brokers.enabled_brokers == ["robinhood", "schwab"]
    assert cfg.brokers.default_broker == "robinhood"


@pytest.mark.unit
@pytest.mark.journey_system
def test_schwab_compat_fields_backed_by_broker_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCHWAB_API_KEY", "compat_key")
    monkeypatch.setenv("SCHWAB_APP_SECRET", "compat_secret")
    monkeypatch.setenv("SCHWAB_CALLBACK_URL", "https://compat.cb/")
    monkeypatch.setenv("SCHWAB_TOKEN_PATH", "/compat/tok")
    monkeypatch.delenv("ENABLED_BROKERS", raising=False)

    cfg = load_config(config_path=Path("/tmp/definitely-missing-config.yaml"))

    assert cfg.schwab_api_key == "compat_key"
    assert cfg.schwab_app_secret == "compat_secret"
    assert cfg.schwab_callback_url == "https://compat.cb/"
    assert cfg.schwab_token_path == "/compat/tok"
