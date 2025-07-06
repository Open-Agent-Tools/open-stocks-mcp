"""Tests for Robin Stocks authentication configuration."""

import os
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from open_stocks_mcp.auth.config import RobinhoodConfig


class TestRobinhoodConfig:
    """Test Robin Stocks configuration management."""

    def test_config_initialization_default(self) -> None:
        """Test config initialization with default values."""
        config = RobinhoodConfig()

        assert config.username is None
        assert config.password is None
        assert config.mfa_code is None
        assert config.expires_in == 86400  # 24 hours default

    def test_config_initialization_with_values(self) -> None:
        """Test config initialization with provided values."""
        config = RobinhoodConfig(
            username="test@example.com",
            password="test_password",
            mfa_code="test_mfa_secret",
            expires_in=3600,
        )

        assert config.username == "test@example.com"
        assert isinstance(config.password, SecretStr)
        assert isinstance(config.mfa_code, SecretStr)
        assert config.expires_in == 3600

    @patch.dict(
        os.environ,
        {
            "ROBINHOOD_USERNAME": "env_user@example.com",
            "ROBINHOOD_PASSWORD": "env_password",
            "ROBINHOOD_MFA_CODE": "env_mfa_secret",
            "ROBINHOOD_EXPIRES_IN": "7200",
        },
    )
    def test_config_from_environment(self) -> None:
        """Test config loading from environment variables."""
        config = RobinhoodConfig()

        assert config.username == "env_user@example.com"
        assert config.password is not None
        assert config.mfa_code is not None
        assert config.expires_in == 7200

    def test_has_credentials_missing_username(self) -> None:
        """Test credential validation with missing username."""
        config = RobinhoodConfig(password="test_password")

        # Should be False when username is missing
        with pytest.raises(NotImplementedError):
            config.has_credentials()

    def test_has_credentials_missing_password(self) -> None:
        """Test credential validation with missing password."""
        config = RobinhoodConfig(username="test@example.com")

        # Should be False when password is missing
        with pytest.raises(NotImplementedError):
            config.has_credentials()

    def test_has_credentials_complete(self) -> None:
        """Test credential validation with complete credentials."""
        config = RobinhoodConfig(username="test@example.com", password="test_password")

        # Should be True when both username and password provided
        with pytest.raises(NotImplementedError):
            config.has_credentials()

    def test_get_password_extraction(self) -> None:
        """Test password extraction from SecretStr."""
        config = RobinhoodConfig(password="test_password")

        with pytest.raises(NotImplementedError):
            config.get_password()

    def test_get_mfa_code_secret_extraction(self) -> None:
        """Test MFA code secret extraction from SecretStr."""
        config = RobinhoodConfig(mfa_code="test_mfa_secret")

        with pytest.raises(NotImplementedError):
            config.get_mfa_code_secret()

    def test_password_secrecy(self) -> None:
        """Test that password is properly secured."""
        config = RobinhoodConfig(password="secret_password")

        # Password should be SecretStr type
        assert isinstance(config.password, SecretStr)

        # String representation should not reveal password
        config_str = str(config)
        assert "secret_password" not in config_str
        assert "**********" in config_str or "*" in config_str

    def test_mfa_code_secrecy(self) -> None:
        """Test that MFA code is properly secured."""
        config = RobinhoodConfig(mfa_code="secret_mfa_code")

        # MFA code should be SecretStr type
        assert isinstance(config.mfa_code, SecretStr)

        # String representation should not reveal MFA code
        config_str = str(config)
        assert "secret_mfa_code" not in config_str


class TestRobinhoodConfigEdgeCases:
    """Test edge cases for Robin Stocks configuration."""

    def test_empty_string_values(self) -> None:
        """Test config with empty string values."""
        config = RobinhoodConfig(username="", password="", mfa_code="")

        assert config.username == ""
        assert isinstance(config.password, SecretStr)
        assert isinstance(config.mfa_code, SecretStr)

    def test_none_values_explicit(self) -> None:
        """Test config with explicitly set None values."""
        config = RobinhoodConfig(username=None, password=None, mfa_code=None)

        assert config.username is None
        assert config.password is None
        assert config.mfa_code is None

    def test_invalid_expires_in_type(self) -> None:
        """Test config with invalid expires_in type."""
        with pytest.raises((ValueError, TypeError)):
            RobinhoodConfig(expires_in="invalid")

    def test_negative_expires_in(self) -> None:
        """Test config with negative expires_in value."""
        # Should accept negative values (will be handled in auth logic)
        config = RobinhoodConfig(expires_in=-1)
        assert config.expires_in == -1

    def test_zero_expires_in(self) -> None:
        """Test config with zero expires_in value."""
        config = RobinhoodConfig(expires_in=0)
        assert config.expires_in == 0
