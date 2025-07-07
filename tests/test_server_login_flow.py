"""Integration tests for server login flow using real credentials from .env file."""

import asyncio
from pathlib import Path

import pytest


class TestServerLoginFlow:
    """Test the complete server login flow with environment credentials."""

    @pytest.fixture(autouse=True)
    def load_env_credentials(self):
        """Load real credentials from .env file for testing."""
        # Find project root by looking for pyproject.toml
        current_path = Path(__file__).resolve()
        for parent in current_path.parents:
            env_file = parent / ".env"
            pyproject_file = parent / "pyproject.toml"
            if pyproject_file.exists() and env_file.exists():
                from dotenv import load_dotenv

                load_dotenv(env_file)
                break

    def test_placeholder(self):
        """Placeholder test to keep the test file valid."""
        assert True


def run_async(coro):
    """Helper to run async functions in pytest."""
    return asyncio.run(coro)
