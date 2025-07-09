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
from open_stocks_mcp.tools.robinhood_advanced_portfolio_tools import (
    get_build_holdings,
    get_build_user_profile,
    get_day_trades,
)
from open_stocks_mcp.tools.robinhood_dividend_tools import (
    get_dividends,
    get_dividends_by_instrument,
    get_interest_payments,
    get_stock_loan_payments,
    get_total_dividends,
)
from open_stocks_mcp.tools.robinhood_market_data_tools import (
    get_stock_earnings,
    get_stock_news,
    get_stock_ratings,
    get_stock_splits,
    get_stocks_by_tag,
    get_top_100,
    get_top_movers,
    get_top_movers_sp500,
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

    @pytest.mark.asyncio
    async def test_get_dividends_integration(self, robinhood_session):
        """Test get_dividends with real API call."""
        result = await get_dividends()

        assert "result" in result
        assert result["result"]["status"] == "success"
        assert "dividends" in result["result"]
        assert "total_dividends" in result["result"]
        assert "count" in result["result"]
        assert isinstance(result["result"]["dividends"], list)

    @pytest.mark.asyncio
    async def test_get_total_dividends_integration(self, robinhood_session):
        """Test get_total_dividends with real API call."""
        result = await get_total_dividends()

        assert "result" in result
        assert result["result"]["status"] == "success"
        assert "total_amount" in result["result"]
        assert "payment_count" in result["result"]
        assert "by_year" in result["result"]

    @pytest.mark.asyncio
    async def test_get_dividends_by_instrument_integration(self, robinhood_session):
        """Test get_dividends_by_instrument with real API call."""
        # Test with a common dividend stock
        result = await get_dividends_by_instrument("AAPL")

        assert "result" in result
        assert result["result"]["status"] == "success"
        assert "symbol" in result["result"]
        assert result["result"]["symbol"] == "AAPL"
        assert "dividends" in result["result"]
        assert "total_amount" in result["result"]
        assert "count" in result["result"]

    @pytest.mark.asyncio
    async def test_get_interest_payments_integration(self, robinhood_session):
        """Test get_interest_payments with real API call."""
        result = await get_interest_payments()

        assert "result" in result
        assert result["result"]["status"] == "success"
        assert "interest_payments" in result["result"]
        assert "total_interest" in result["result"]
        assert "count" in result["result"]
        assert isinstance(result["result"]["interest_payments"], list)

    @pytest.mark.asyncio
    async def test_get_stock_loan_payments_integration(self, robinhood_session):
        """Test get_stock_loan_payments with real API call."""
        result = await get_stock_loan_payments()

        assert "result" in result
        assert result["result"]["status"] == "success"
        assert "loan_payments" in result["result"]
        assert "total_loan_income" in result["result"]
        assert "count" in result["result"]
        assert "enrolled" in result["result"]
        assert isinstance(result["result"]["loan_payments"], list)

    @pytest.mark.asyncio
    async def test_get_top_movers_sp500_integration(self, robinhood_session):
        """Test get_top_movers_sp500 with real API call."""
        result = await get_top_movers_sp500("up")

        assert "result" in result
        assert result["result"]["status"] == "success"
        assert "direction" in result["result"]
        assert result["result"]["direction"] == "up"
        assert "movers" in result["result"]
        assert "count" in result["result"]
        assert isinstance(result["result"]["movers"], list)

    @pytest.mark.asyncio
    async def test_get_top_100_integration(self, robinhood_session):
        """Test get_top_100 with real API call."""
        result = await get_top_100()

        assert "result" in result
        assert result["result"]["status"] == "success"
        assert "stocks" in result["result"]
        assert "count" in result["result"]
        assert isinstance(result["result"]["stocks"], list)

    @pytest.mark.asyncio
    async def test_get_top_movers_integration(self, robinhood_session):
        """Test get_top_movers with real API call."""
        result = await get_top_movers()

        assert "result" in result
        assert result["result"]["status"] == "success"
        assert "movers" in result["result"]
        assert "count" in result["result"]
        assert isinstance(result["result"]["movers"], list)

    @pytest.mark.asyncio
    async def test_get_stocks_by_tag_integration(self, robinhood_session):
        """Test get_stocks_by_tag with real API call."""
        result = await get_stocks_by_tag("technology")

        assert "result" in result
        # May return success or no_data depending on tag availability
        assert result["result"]["status"] in ["success", "no_data"]
        if result["result"]["status"] == "success":
            assert "tag" in result["result"]
            assert result["result"]["tag"] == "technology"
            assert "stocks" in result["result"]
            assert "count" in result["result"]

    @pytest.mark.asyncio
    async def test_get_stock_ratings_integration(self, robinhood_session):
        """Test get_stock_ratings with real API call."""
        result = await get_stock_ratings("AAPL")

        assert "result" in result
        # May return success or no_data depending on rating availability
        assert result["result"]["status"] in ["success", "no_data"]
        if result["result"]["status"] == "success":
            assert "symbol" in result["result"]
            assert result["result"]["symbol"] == "AAPL"

    @pytest.mark.asyncio
    async def test_get_stock_earnings_integration(self, robinhood_session):
        """Test get_stock_earnings with real API call."""
        result = await get_stock_earnings("AAPL")

        assert "result" in result
        # May return success or no_data depending on earnings availability
        assert result["result"]["status"] in ["success", "no_data"]
        if result["result"]["status"] == "success":
            assert "symbol" in result["result"]
            assert result["result"]["symbol"] == "AAPL"
            assert "earnings" in result["result"]
            assert "count" in result["result"]

    @pytest.mark.asyncio
    async def test_get_stock_news_integration(self, robinhood_session):
        """Test get_stock_news with real API call."""
        result = await get_stock_news("AAPL")

        assert "result" in result
        # May return success or no_data depending on news availability
        assert result["result"]["status"] in ["success", "no_data"]
        if result["result"]["status"] == "success":
            assert "symbol" in result["result"]
            assert result["result"]["symbol"] == "AAPL"
            assert "news" in result["result"]
            assert "count" in result["result"]

    @pytest.mark.asyncio
    async def test_get_stock_splits_integration(self, robinhood_session):
        """Test get_stock_splits with real API call."""
        result = await get_stock_splits("AAPL")

        assert "result" in result
        # May return success or no_data depending on splits availability
        assert result["result"]["status"] in ["success", "no_data"]
        if result["result"]["status"] == "success":
            assert "symbol" in result["result"]
            assert result["result"]["symbol"] == "AAPL"
            assert "splits" in result["result"]
            assert "count" in result["result"]


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
            get_dividends,
            get_total_dividends,
            get_interest_payments,
            get_stock_loan_payments,
            get_top_100,
            get_top_movers,
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
            patch(
                "open_stocks_mcp.tools.robinhood_dividend_tools.rh.account.get_dividends",
                return_value=[],
            ),
            patch(
                "open_stocks_mcp.tools.robinhood_dividend_tools.rh.account.get_total_dividends",
                return_value="0.00",
            ),
            patch(
                "open_stocks_mcp.tools.robinhood_dividend_tools.rh.account.get_dividends_by_instrument",
                return_value=[],
            ),
            patch(
                "open_stocks_mcp.tools.robinhood_dividend_tools.rh.account.get_interest_payments",
                return_value=[],
            ),
            patch(
                "open_stocks_mcp.tools.robinhood_dividend_tools.rh.account.get_stock_loan_payments",
                return_value=[],
            ),
            patch(
                "open_stocks_mcp.tools.robinhood_market_data_tools.rh.get_top_100",
                return_value=[],
            ),
            patch(
                "open_stocks_mcp.tools.robinhood_market_data_tools.rh.get_top_movers",
                return_value=[],
            ),
        ):
            for tool in tools:
                if tool == get_portfolio_history:
                    result = await tool()
                elif tool == get_dividends_by_instrument:
                    result = await tool("AAPL")
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
            get_dividends,
            get_total_dividends,
            get_interest_payments,
            get_stock_loan_payments,
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
                patch(
                    "open_stocks_mcp.tools.robinhood_dividend_tools.rh.account.get_dividends",
                    side_effect=Exception("Test Error"),
                ),
                patch(
                    "open_stocks_mcp.tools.robinhood_dividend_tools.rh.account.get_total_dividends",
                    side_effect=Exception("Test Error"),
                ),
                patch(
                    "open_stocks_mcp.tools.robinhood_dividend_tools.rh.account.get_dividends_by_instrument",
                    side_effect=Exception("Test Error"),
                ),
                patch(
                    "open_stocks_mcp.tools.robinhood_dividend_tools.rh.account.get_interest_payments",
                    side_effect=Exception("Test Error"),
                ),
                patch(
                    "open_stocks_mcp.tools.robinhood_dividend_tools.rh.account.get_stock_loan_payments",
                    side_effect=Exception("Test Error"),
                ),
            ):
                if tool == get_portfolio_history:
                    result = await tool()
                elif tool == get_dividends_by_instrument:
                    result = await tool("AAPL")
                else:
                    result = await tool()

                # Check error structure
                assert isinstance(result, dict)
                assert "result" in result
                assert result["result"]["status"] == "error"
                assert "error" in result["result"]

    # Advanced Portfolio Analytics Integration Tests
    @pytest.mark.asyncio
    async def test_get_build_holdings_integration(self, robinhood_session):
        """Test get_build_holdings with real API call."""
        result = await get_build_holdings()

        assert "result" in result
        # May return success or no_data depending on holdings
        assert result["result"]["status"] in ["success", "no_data"]
        if result["result"]["status"] == "success":
            assert "holdings" in result["result"]
            assert "total_positions" in result["result"]
            assert isinstance(result["result"]["holdings"], dict)
            assert isinstance(result["result"]["total_positions"], int)

    @pytest.mark.asyncio
    async def test_get_build_user_profile_integration(self, robinhood_session):
        """Test get_build_user_profile with real API call."""
        result = await get_build_user_profile()

        assert "result" in result
        # May return success or no_data depending on profile availability
        assert result["result"]["status"] in ["success", "no_data"]
        if result["result"]["status"] == "success":
            # Check for expected financial fields
            profile = result["result"]
            expected_fields = ["equity", "cash", "status"]
            for field in expected_fields:
                assert field in profile

    @pytest.mark.asyncio
    async def test_get_day_trades_integration(self, robinhood_session):
        """Test get_day_trades with real API call."""
        result = await get_day_trades()

        assert "result" in result
        # May return success or no_data depending on account profile availability
        assert result["result"]["status"] in ["success", "no_data"]
        if result["result"]["status"] == "success":
            day_trade_info = result["result"]
            assert "day_trade_count" in day_trade_info
            assert "remaining_day_trades" in day_trade_info
            assert "pattern_day_trader" in day_trade_info
            assert "day_trade_buying_power" in day_trade_info
            assert "overnight_buying_power" in day_trade_info
            assert isinstance(day_trade_info["day_trade_count"], int)
            assert isinstance(day_trade_info["remaining_day_trades"], int)
            assert isinstance(day_trade_info["pattern_day_trader"], bool)
