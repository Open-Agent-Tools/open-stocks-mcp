"""Configuration management for Robin Stocks authentication."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class RobinhoodConfig(BaseSettings):
    """Configuration settings for Robinhood authentication."""

    username: str | None = Field(default=None)
    password: SecretStr | None = Field(default=None)
    expires_in: int = Field(default=86400)  # 24 hours

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_prefix": "ROBINHOOD_",
    }

    def has_credentials(self) -> bool:
        """Check if required credentials are provided."""
        # TODO: Implement credential validation
        raise NotImplementedError("Credential validation not implemented")

    def get_password(self) -> str | None:
        """Get password as string (safely extracting from SecretStr)."""
        # TODO: Implement safe password extraction
        raise NotImplementedError("Password extraction not implemented")
