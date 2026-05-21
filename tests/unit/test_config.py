"""Tests for server configuration loading."""

import os
from unittest.mock import patch

import pytest

from open_stocks_mcp.config import ServerConfig, load_config


def test_load_config_default() -> None:
    """load_config returns a ServerConfig with sensible defaults."""
    with patch.dict(os.environ, {}, clear=True):
        config = load_config()
        assert isinstance(config, ServerConfig)
        assert config.name == "Open Stocks MCP"
        assert config.log_level == "INFO"
        assert config.monitoring_enabled is True


def test_load_config_env_override() -> None:
    """Environment variables override defaults."""
    with patch.dict(os.environ, {"MCP_SERVER_NAME": "Custom Server", "LOG_LEVEL": "DEBUG"}, clear=True):
        config = load_config()
        assert config.name == "Custom Server"
        assert config.log_level == "DEBUG"


def test_log_level_default_is_info() -> None:
    """Without LOG_LEVEL or DEBUG, log_level defaults to INFO."""
    with patch.dict(os.environ, {}, clear=True):
        config = load_config()
        assert config.log_level == "INFO"


# --- DEBUG env var tests ---

@pytest.mark.parametrize("debug_value", ["1", "true", "True", "TRUE", "yes", "on"])
def test_debug_env_truthy_values_set_debug_log_level(debug_value: str) -> None:
    """DEBUG=<truthy> maps to log_level DEBUG when LOG_LEVEL is not set."""
    with patch.dict(os.environ, {"DEBUG": debug_value}, clear=True):
        config = load_config()
        assert config.log_level == "DEBUG", (
            f"DEBUG={debug_value!r} did not set log_level to DEBUG"
        )


@pytest.mark.parametrize("debug_value", ["0", "false", "False", "no", "off", ""])
def test_debug_env_falsy_values_keep_info_log_level(debug_value: str) -> None:
    """DEBUG=<falsy> keeps the default INFO log level."""
    env = {"DEBUG": debug_value} if debug_value else {}
    with patch.dict(os.environ, env, clear=True):
        config = load_config()
        assert config.log_level == "INFO", (
            f"DEBUG={debug_value!r} unexpectedly changed log_level"
        )


def test_explicit_log_level_wins_over_debug_env() -> None:
    """Explicit LOG_LEVEL env var overrides DEBUG=true."""
    with patch.dict(os.environ, {"DEBUG": "true", "LOG_LEVEL": "WARNING"}, clear=True):
        config = load_config()
        assert config.log_level == "WARNING"


def test_debug_env_does_not_affect_config_when_log_level_set() -> None:
    """LOG_LEVEL takes precedence over DEBUG for all truthy debug values."""
    with patch.dict(os.environ, {"DEBUG": "1", "LOG_LEVEL": "ERROR"}, clear=True):
        config = load_config()
        assert config.log_level == "ERROR"
