"""Basic integration tests for core API functionality."""

import os
from typing import Any

import pytest
from dotenv import load_dotenv

from open_stocks_mcp.tools.robinhood_account_tools import (
    get_account_info,
    get_portfolio,
    get_positions,
)

# Load environment variables
load_dotenv()


@pytest.fixture(scope="module")
def robinhood_session() -> Any:
    """Handle Robinhood login for integration tests."""
    username = os.getenv("ROBINHOOD_USERNAME")
    password = os.getenv("ROBINHOOD_PASSWORD")

    if not username or not password:
        pytest.skip("Robinhood credentials not provided")

    import robin_stocks.robinhood as rh

    try:
        login_result = rh.login(username, password)
        if login_result:
            yield
        else:
            pytest.skip("Failed to login to Robinhood")
    finally:
        rh.logout()


@pytest.mark.integration
class TestBasicIntegration:
    """Test basic API functionality that should work reliably."""

    @pytest.mark.asyncio
    async def test_get_account_info(self, robinhood_session: Any) -> None:
        """Test getting basic account information."""
        result = await get_account_info()
        assert "result" in result
        assert isinstance(result["result"], dict)

    @pytest.mark.asyncio
    async def test_get_portfolio(self, robinhood_session: Any) -> None:
        """Test getting portfolio information."""
        result = await get_portfolio()
        assert "result" in result
        assert isinstance(result["result"], dict)

    @pytest.mark.asyncio
    async def test_get_positions(self, robinhood_session: Any) -> None:
        """Test getting positions."""
        result = await get_positions()
        assert "result" in result
        assert isinstance(result["result"], dict)  # Changed from list to dict


@pytest.mark.integration
@pytest.mark.exception_test
@pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
@pytest.mark.asyncio
async def test_api_error_handling() -> None:
    """Test API error handling without authentication."""
    # This should handle the case where we're not authenticated
    result = await get_account_info()
    assert "result" in result
    # Should either succeed or have error info
    assert "error" in result["result"] or "username" in result["result"]
