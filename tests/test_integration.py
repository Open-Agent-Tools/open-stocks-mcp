"""Integration tests for Phase 1 functionality."""

import os
from unittest.mock import patch

import pytest
import robin_stocks.robinhood as rh
from dotenv import load_dotenv

from open_stocks_mcp.tools.robinhood_account_tools import (
    get_account_details,
    get_account_info,
    get_portfolio,
    get_portfolio_history,
    get_positions,
)
from open_stocks_mcp.tools.robinhood_order_tools import (
    get_stock_orders,
)

# Load environment variables from .env file
load_dotenv()


@pytest.fixture(scope="module")
def robinhood_session():
    """
    Pytest fixture to handle Robinhood login and logout for integration tests.
    Requires ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD to be set.
    """
    username = os.getenv("ROBINHOOD_USERNAME")
    password = os.getenv("ROBINHOOD_PASSWORD")

    # Skip test if username or password are not available
    if not all([username, password]):
        pytest.skip(
            "Skipping integration test: ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD "
            "environment variables must be set."
        )

    # Perform login with stored session if available
    login_response = rh.login(
        username=username,
        password=password,
        store_session=True,  # Store session for reuse
    )

    # Check for successful login before yielding to tests
    assert login_response is not None, (
        "Login failed: rh.login() returned None. Check credentials."
    )
    assert "access_token" in login_response, (
        f"Login failed: {login_response.get('detail', 'Unknown error')}"
    )

    yield

    # Teardown: logout and remove the pickle file to ensure clean state
    rh.logout()
    if os.path.exists("robinhood.pickle"):
        os.remove("robinhood.pickle")


@pytest.mark.integration
class TestIntegrationPhase1:
    """Integration tests for Phase 1 tools with real API calls."""

    @pytest.mark.asyncio
    async def test_get_account_info_integration(self, robinhood_session):
        """Test get_account_info with real API call."""
        result = await get_account_info()

        assert "result" in result
        assert result["result"]["status"] == "success"
        assert "username" in result["result"]
        assert "created_at" in result["result"]

    @pytest.mark.asyncio
    async def test_get_portfolio_integration(self, robinhood_session):
        """Test get_portfolio with real API call."""
        result = await get_portfolio()

        assert "result" in result
        assert result["result"]["status"] == "success"
        assert "market_value" in result["result"]
        assert "equity" in result["result"]

    @pytest.mark.asyncio
    async def test_get_account_details_integration(self, robinhood_session):
        """Test get_account_details with real API call."""
        result = await get_account_details()

        assert "result" in result
        if result["result"]["status"] == "success":
            assert "portfolio_equity" in result["result"]
            assert "total_equity" in result["result"]
            assert "account_buying_power" in result["result"]
        else:
            # Should be no_data status if no account data
            assert result["result"]["status"] in ["success", "no_data"]

    @pytest.mark.asyncio
    async def test_get_positions_integration(self, robinhood_session):
        """Test get_positions with real API call."""
        result = await get_positions()

        assert "result" in result
        assert result["result"]["status"] == "success"
        assert "positions" in result["result"]
        assert "count" in result["result"]
        assert isinstance(result["result"]["positions"], list)

    @pytest.mark.asyncio
    async def test_get_portfolio_history_integration(self, robinhood_session):
        """Test get_portfolio_history with real API call."""
        result = await get_portfolio_history("week")

        assert "result" in result
        if result["result"]["status"] == "success":
            assert "span" in result["result"]
            assert result["result"]["span"] == "week"
            assert "data_points_count" in result["result"]
            assert "recent_performance" in result["result"]
        else:
            # Should be no_data status if no history
            assert result["result"]["status"] in ["success", "no_data"]

    @pytest.mark.asyncio
    async def test_get_stock_orders_integration(self, robinhood_session):
        """Test get_stock_orders with real API call."""
        result = await get_stock_orders()

        assert "result" in result
        assert result["result"]["status"] == "success"
        assert "orders" in result["result"]
        assert "count" in result["result"]
        assert isinstance(result["result"]["orders"], list)

    @pytest.mark.asyncio
    async def test_portfolio_history_different_spans(self, robinhood_session):
        """Test portfolio_history with different time spans."""
        spans = ["day", "week", "month"]

        for span in spans:
            result = await get_portfolio_history(span)

            assert "result" in result
            if result["result"]["status"] == "success":
                assert result["result"]["span"] == span
            else:
                assert result["result"]["status"] in ["success", "no_data"]


class TestMockIntegration:
    """Integration tests using mocks to test error conditions and edge cases."""

    @pytest.mark.asyncio
    async def test_all_tools_return_proper_json_structure(self):
        """Test that all tools return proper JSON structure with result field."""
        tools = [
            get_account_info,
            get_portfolio,
            get_stock_orders,
            get_account_details,
            get_positions,
            get_portfolio_history,
        ]

        # Mock all robin_stocks calls to return empty/None data
        with (
            patch(
                "open_stocks_mcp.tools.robinhood_account_tools.rh.load_user_profile",
                return_value={},
            ),
            patch(
                "open_stocks_mcp.tools.robinhood_account_tools.rh.load_portfolio_profile",
                return_value={},
            ),
            patch(
                "open_stocks_mcp.tools.robinhood_order_tools.rh.get_all_stock_orders",
                return_value=[],
            ),
            patch(
                "open_stocks_mcp.tools.robinhood_account_tools.rh.load_phoenix_account",
                return_value=None,
            ),
            patch(
                "open_stocks_mcp.tools.robinhood_account_tools.rh.get_open_stock_positions",
                return_value=[],
            ),
            patch(
                "open_stocks_mcp.tools.robinhood_account_tools.rh.get_historical_portfolio",
                return_value=None,
            ),
        ):
            for tool in tools:
                if tool == get_portfolio_history:
                    result = await tool()
                else:
                    result = await tool()

                # Check JSON structure
                assert isinstance(result, dict)
                assert "result" in result
                assert isinstance(result["result"], dict)
                assert "status" in result["result"]

    @pytest.mark.asyncio
    async def test_error_handling_consistency(self):
        """Test that all tools handle errors consistently."""
        tools = [
            get_account_info,
            get_portfolio,
            get_stock_orders,
            get_account_details,
            get_positions,
            get_portfolio_history,
        ]

        for tool in tools:
            # Mock to raise exception
            with (
                patch(
                    "open_stocks_mcp.tools.robinhood_account_tools.rh.load_user_profile",
                    side_effect=Exception("Test Error"),
                ),
                patch(
                    "open_stocks_mcp.tools.robinhood_account_tools.rh.load_portfolio_profile",
                    side_effect=Exception("Test Error"),
                ),
                patch(
                    "open_stocks_mcp.tools.robinhood_order_tools.rh.get_all_stock_orders",
                    side_effect=Exception("Test Error"),
                ),
                patch(
                    "open_stocks_mcp.tools.robinhood_account_tools.rh.load_phoenix_account",
                    side_effect=Exception("Test Error"),
                ),
                patch(
                    "open_stocks_mcp.tools.robinhood_account_tools.rh.get_open_stock_positions",
                    side_effect=Exception("Test Error"),
                ),
                patch(
                    "open_stocks_mcp.tools.robinhood_account_tools.rh.get_historical_portfolio",
                    side_effect=Exception("Test Error"),
                ),
            ):
                if tool == get_portfolio_history:
                    result = await tool()
                else:
                    result = await tool()

                # Check error structure
                assert isinstance(result, dict)
                assert "result" in result
                assert result["result"]["status"] == "error"
                assert "error" in result["result"]
