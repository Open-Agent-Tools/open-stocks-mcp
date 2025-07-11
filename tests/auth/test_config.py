"""Tests for auth config module."""

from pydantic import SecretStr

from open_stocks_mcp.auth.config import RobinhoodConfig


class TestRobinhoodConfig:
    """Test RobinhoodConfig class."""

    def test_has_credentials_with_both_provided(self) -> None:
        """Test has_credentials returns True when both username and password are provided."""
        config = RobinhoodConfig(username="testuser", password=SecretStr("testpass"))
        assert config.has_credentials() is True

    def test_has_credentials_with_no_username(self) -> None:
        """Test has_credentials returns False when username is None."""
        config = RobinhoodConfig(username=None, password=SecretStr("testpass"))
        assert config.has_credentials() is False

    def test_has_credentials_with_no_password(self) -> None:
        """Test has_credentials returns False when password is None."""
        config = RobinhoodConfig(username="testuser", password=None)
        assert config.has_credentials() is False

    def test_has_credentials_with_neither_provided(self) -> None:
        """Test has_credentials returns False when both are None."""
        config = RobinhoodConfig(username=None, password=None)
        assert config.has_credentials() is False

    def test_get_password_with_password_provided(self) -> None:
        """Test get_password returns the password string when provided."""
        config = RobinhoodConfig(username="testuser", password=SecretStr("testpass"))
        assert config.get_password() == "testpass"

    def test_get_password_with_no_password(self) -> None:
        """Test get_password returns None when password is None."""
        config = RobinhoodConfig(username="testuser", password=None)
        assert config.get_password() is None

    def test_default_expires_in(self) -> None:
        """Test default expires_in value."""
        config = RobinhoodConfig()
        assert config.expires_in == 86400  # 24 hours

    def test_custom_expires_in(self) -> None:
        """Test custom expires_in value."""
        config = RobinhoodConfig(expires_in=3600)  # 1 hour
        assert config.expires_in == 3600

    def test_model_config_attributes(self) -> None:
        """Test model configuration attributes."""
        config = RobinhoodConfig()
        assert config.model_config["env_file"] == ".env"
        assert config.model_config["env_file_encoding"] == "utf-8"
        assert config.model_config["env_prefix"] == "ROBINHOOD_"
