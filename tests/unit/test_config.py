import os
from unittest.mock import patch

import pytest
import yaml

from open_stocks_mcp.config import ServerConfig, load_config


def test_load_config_default():
    """Test that load_config returns a ServerConfig with defaults when no env/YAML is present."""
    with patch.dict(os.environ, {}, clear=True):
        config = load_config()
        assert isinstance(config, ServerConfig)
        assert config.name == "Open Stocks MCP"
        assert config.log_level == "INFO"
        assert config.monitoring_enabled is True

def test_load_config_env_override():
    """Test that environment variables still override defaults."""
    with patch.dict(os.environ, {"MCP_SERVER_NAME": "Custom Server", "LOG_LEVEL": "DEBUG"}, clear=True):
        config = load_config()
        assert config.name == "Custom Server"
        assert config.log_level == "DEBUG"

def test_load_config_yaml_file(tmp_path):
    """Test loading configuration from a YAML file via OPEN_STOCKS_CONFIG."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    
    config_data = {
        "name": "YAML Server",
        "log_level": "WARNING",
        "monitoring_enabled": False,
        "cache": {
            "enabled": False,
            "max_size": 500
        }
    }
    
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)
        
    with patch.dict(os.environ, {"OPEN_STOCKS_CONFIG": str(config_file)}, clear=True):
        config = load_config()
        assert config.name == "YAML Server"
        assert config.log_level == "WARNING"
        assert config.monitoring_enabled is False
        assert config.cache.enabled is False
        assert config.cache.max_size == 500

def test_load_config_yaml_file_alternate_env(tmp_path):
    """Test loading configuration from a YAML file via OPEN_STOCKS_CONFIG_FILE."""
    config_file = tmp_path / "alternate.yaml"
    
    config_data = {"name": "Alternate YAML"}
    
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)
        
    with patch.dict(os.environ, {"OPEN_STOCKS_CONFIG_FILE": str(config_file)}, clear=True):
        config = load_config()
        assert config.name == "Alternate YAML"

def test_load_config_yaml_with_env_fallback(tmp_path):
    """Test that environment variables override YAML values (Standard precedence)."""
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump({"name": "YAML Name", "log_level": "INFO"}, f)
        
    with patch.dict(os.environ, {
        "OPEN_STOCKS_CONFIG": str(config_file),
        "MCP_SERVER_NAME": "Env Name"
    }, clear=True):
        config = load_config()
        assert config.name == "Env Name"  # Env overrides YAML
        assert config.log_level == "INFO" # YAML value preserved

def test_load_config_invalid_yaml(tmp_path):
    """Test that invalid YAML raises ValueError."""
    config_file = tmp_path / "invalid.yaml"
    with open(config_file, "w") as f:
        f.write("invalid: yaml: : :")
        
    with patch.dict(os.environ, {"OPEN_STOCKS_CONFIG": str(config_file)}, clear=True):
        with pytest.raises(ValueError) as excinfo:
            load_config()
        assert "invalid" in str(excinfo.value).lower()
        assert str(config_file) in str(excinfo.value)

def test_load_config_schema_validation(tmp_path):
    """Test that invalid field types in YAML raise ValueError."""
    config_file = tmp_path / "bad_schema.yaml"
    with open(config_file, "w") as f:
        yaml.dump({"cache": {"max_size": "not-an-int"}}, f)
        
    with patch.dict(os.environ, {"OPEN_STOCKS_CONFIG": str(config_file)}, clear=True):
        with pytest.raises(ValueError) as excinfo:
            load_config()
        assert "cache" in str(excinfo.value).lower()

def test_norway_problem(tmp_path):
    """Exercise StrictBool against YAML 1.1's ``no``/``off`` boolean coercion.

    PyYAML parses bareword ``no`` and ``off`` as ``False``; this asserts the
    parsed False reaches the flag (rather than being silently dropped).
    Uses ``robinhood`` because its default is True, so a False resolution is
    a real signal that the YAML value won.
    """
    config_file = tmp_path / "norway.yaml"
    with open(config_file, "w") as f:
        f.write("feature_flags:\n  robinhood: no\n")

    with patch.dict(os.environ, {"OPEN_STOCKS_CONFIG": str(config_file)}, clear=True):
        config = load_config()
        assert config.is_feature_enabled("robinhood") is False

def test_feature_flags_defaults(tmp_path):
    """Test that unknown flags resolve to False."""
    with patch.dict(os.environ, {}, clear=True):
        config = load_config()
        assert config.is_feature_enabled("non_existent_flag") is False

def test_feature_flags_environment_override(tmp_path):
    """Test environment-specific feature flag overrides."""
    config_file = tmp_path / "flags.yaml"
    config_data = {
        "environment": "production",
        "feature_flags": {
            "robinhood": True,
            "schwab": False,
            "environments": {
                "development": {
                    "schwab": True
                }
            }
        }
    }
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)
        
    # Test production (default)
    with patch.dict(os.environ, {"OPEN_STOCKS_CONFIG": str(config_file)}, clear=True):
        config = load_config()
        assert config.is_feature_enabled("robinhood") is True
        assert config.is_feature_enabled("schwab") is False
        
    # Test development override
    with patch.dict(os.environ, {
        "OPEN_STOCKS_CONFIG": str(config_file),
        "OPEN_STOCKS_ENV": "development"
    }, clear=True):
        config = load_config()
        assert config.is_feature_enabled("robinhood") is True
        assert config.is_feature_enabled("schwab") is True
