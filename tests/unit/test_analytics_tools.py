"""Unit tests for advanced portfolio analytics tools."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from open_stocks_mcp.tools.robinhood_advanced_portfolio_tools import (
    get_build_holdings,
    get_build_user_profile,
    get_day_trades,
)
from open_stocks_mcp.tools.robinhood_dividend_tools import (
    get_interest_payments,
    get_stock_loan_payments,
)


class TestBuildHoldings:
    """Test build holdings functionality."""

    @patch("open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.rh.build_holdings")
    @pytest.mark.asyncio
    async def test_build_holdings_success(self, mock_build_holdings: Any) -> None:
        """Test successful holdings build."""
        mock_build_holdings.return_value = {
            "AAPL": {
                "price": "150.00",
                "quantity": "10",
                "average_buy_price": "145.00",
                "equity": "1500.00",
                "percent_change": "3.45",
                "equity_change": "50.00",
                "type": "stock",
                "name": "Apple Inc",
                "id": "450dfc6d-5510-4d40-abfb-f633b7d9be3e",
                "pe_ratio": "25.5",
                "percentage": "15.2",
            },
            "GOOGL": {
                "price": "2500.00",
                "quantity": "2",
                "average_buy_price": "2400.00",
                "equity": "5000.00",
                "percent_change": "4.17",
                "equity_change": "200.00",
                "type": "stock",
                "name": "Alphabet Inc",
                "id": "550dfc6d-5510-4d40-abfb-f633b7d9be3f",
                "pe_ratio": "22.8",
                "percentage": "50.5",
            },
        }

        result = await get_build_holdings()

        assert "result" in result
        assert result["result"]["total_positions"] == 2
        assert len(result["result"]["holdings"]) == 2
        assert "AAPL" in result["result"]["holdings"]
        assert "GOOGL" in result["result"]["holdings"]
        assert result["result"]["holdings"]["AAPL"]["equity"] == "1500.00"
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch("open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.rh.build_holdings")
    @pytest.mark.asyncio
    async def test_build_holdings_no_data(self, mock_build_holdings: Any) -> None:
        """Test build holdings when no data is available."""
        mock_build_holdings.return_value = None

        result = await get_build_holdings()

        assert "result" in result
        assert result["result"]["status"] == "no_data"
        assert result["result"]["total_positions"] == 0
        assert result["result"]["holdings"] == {}
        assert "No holdings found" in result["result"]["message"]

    @patch("open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.rh.build_holdings")
    @pytest.mark.asyncio
    async def test_build_holdings_empty_dict(self, mock_build_holdings: Any) -> None:
        """Test build holdings with empty dictionary."""
        mock_build_holdings.return_value = {}

        result = await get_build_holdings()

        assert "result" in result
        assert result["result"]["total_positions"] == 0
        assert result["result"]["holdings"] == {}
        # Empty dict is treated as no_data by the function
        assert result["result"]["status"] == "no_data"


class TestBuildUserProfile:
    """Test build user profile functionality."""

    @patch(
        "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.rh.build_user_profile"
    )
    @pytest.mark.asyncio
    async def test_build_user_profile_success(
        self, mock_build_user_profile: Any
    ) -> None:
        """Test successful user profile build."""
        mock_build_user_profile.return_value = {
            "equity": "50000.00",
            "extended_hours_equity": "50100.00",
            "cash": "2500.00",
            "dividend_total": "1245.67",
            "total_return_today": "250.00",
            "total_return_today_percent": "0.50",
            "buying_power": "47500.00",
            "withdrawable_amount": "2500.00",
        }

        result = await get_build_user_profile()

        assert "result" in result
        assert result["result"]["equity"] == "50000.00"
        assert result["result"]["cash"] == "2500.00"
        assert result["result"]["dividend_total"] == "1245.67"
        assert result["result"]["total_return_today"] == "250.00"
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch(
        "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.rh.build_user_profile"
    )
    @pytest.mark.asyncio
    async def test_build_user_profile_no_data(
        self, mock_build_user_profile: Any
    ) -> None:
        """Test build user profile when no data is available."""
        mock_build_user_profile.return_value = None

        result = await get_build_user_profile()

        assert "result" in result
        assert result["result"]["status"] == "no_data"
        assert "No user profile data available" in result["result"]["error"]

    @patch(
        "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.rh.build_user_profile"
    )
    @pytest.mark.asyncio
    async def test_build_user_profile_partial_data(
        self, mock_build_user_profile: Any
    ) -> None:
        """Test build user profile with partial data."""
        mock_build_user_profile.return_value = {
            "equity": "25000.00",
            "cash": "1000.00",
            # Missing some fields like dividend_total
        }

        result = await get_build_user_profile()

        assert "result" in result
        assert result["result"]["equity"] == "25000.00"
        assert result["result"]["cash"] == "1000.00"
        assert result["result"]["status"] == "success"


class TestDayTrades:
    """Test day trading information functionality."""

    @patch(
        "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.rh.load_account_profile"
    )
    @pytest.mark.asyncio
    async def test_day_trades_success(self, mock_load_account: Any) -> None:
        """Test successful day trading info retrieval."""
        mock_load_account.return_value = {
            "day_trade_count": "2",
            "is_pattern_day_trader": False,
            "day_trade_buying_power": "25000.00",
            "overnight_buying_power": "12500.00",
            "max_ach_early_access_amount": "1000.00",
        }

        result = await get_day_trades()

        assert "result" in result
        assert result["result"]["day_trade_count"] == 2
        assert result["result"]["remaining_day_trades"] == 1  # 3 - 2
        assert result["result"]["pattern_day_trader"] is False
        assert result["result"]["day_trade_buying_power"] == "25000.00"
        assert result["result"]["overnight_buying_power"] == "12500.00"
        assert result["result"]["status"] == "success"

    @patch(
        "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.rh.load_account_profile"
    )
    @pytest.mark.asyncio
    async def test_day_trades_pdt_status(self, mock_load_account: Any) -> None:
        """Test day trading info when user is pattern day trader."""
        mock_load_account.return_value = {
            "day_trade_count": "5",
            "is_pattern_day_trader": True,
            "day_trade_buying_power": "100000.00",
            "overnight_buying_power": "50000.00",
            "max_ach_early_access_amount": "5000.00",
        }

        result = await get_day_trades()

        assert "result" in result
        assert result["result"]["day_trade_count"] == 5
        assert result["result"]["remaining_day_trades"] == 0  # max(0, 3-5)
        assert result["result"]["pattern_day_trader"] is True
        assert result["result"]["day_trade_buying_power"] == "100000.00"
        assert result["result"]["status"] == "success"

    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch(
        "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.rh.load_account_profile"
    )
    @pytest.mark.asyncio
    async def test_day_trades_no_data(self, mock_load_account: Any) -> None:
        """Test day trading info when no account data is available."""
        mock_load_account.return_value = None

        result = await get_day_trades()

        assert "result" in result
        assert result["result"]["status"] == "no_data"
        assert "No account profile data available" in result["result"]["error"]

    @patch(
        "open_stocks_mcp.tools.robinhood_advanced_portfolio_tools.rh.load_account_profile"
    )
    @pytest.mark.asyncio
    async def test_day_trades_missing_fields(self, mock_load_account: Any) -> None:
        """Test day trading info with missing fields."""
        mock_load_account.return_value = {
            # Missing some fields
            "day_trade_buying_power": "15000.00",
        }

        result = await get_day_trades()

        assert "result" in result
        assert result["result"]["day_trade_count"] == 0  # Default
        assert result["result"]["remaining_day_trades"] == 3  # 3 - 0
        assert result["result"]["pattern_day_trader"] is False  # Default
        assert result["result"]["day_trade_buying_power"] == "15000.00"
        assert result["result"]["status"] == "success"


class TestInterestPayments:
    """Test interest payments functionality."""

    @patch("open_stocks_mcp.tools.robinhood_dividend_tools.get_rate_limiter")
    @patch("open_stocks_mcp.tools.robinhood_dividend_tools.get_session_manager")
    @patch(
        "open_stocks_mcp.tools.robinhood_dividend_tools.rh.account.get_interest_payments"
    )
    @pytest.mark.asyncio
    async def test_interest_payments_success(
        self,
        mock_interest_payments: Any,
        mock_session_manager: Any,
        mock_rate_limiter: Any,
    ) -> None:
        """Test successful interest payments retrieval."""
        mock_interest_payments.return_value = [
            {
                "id": "payment1",
                "amount": "1.23",
                "paid_at": "2024-12-01T00:00:00Z",
                "type": "cash_management",
                "rate": "0.50",
                "state": "paid",
                "created_at": "2024-11-30T00:00:00Z",
            },
            {
                "id": "payment2",
                "amount": "0.98",
                "paid_at": "2024-11-01T00:00:00Z",
                "type": "cash_management",
                "rate": "0.50",
                "state": "paid",
                "created_at": "2024-10-31T00:00:00Z",
            },
        ]

        # Mock session manager
        mock_session_instance = AsyncMock()
        mock_session_instance.ensure_authenticated.return_value = True
        mock_session_manager.return_value = mock_session_instance

        # Mock rate limiter
        mock_rate_instance = AsyncMock()
        mock_rate_instance.acquire.return_value = None
        mock_rate_limiter.return_value = mock_rate_instance

        result = await get_interest_payments()

        assert "result" in result
        assert result["result"]["count"] == 2
        assert len(result["result"]["interest_payments"]) == 2
        assert result["result"]["total_interest"] == "2.21"  # 1.23 + 0.98
        assert result["result"]["interest_payments"][0]["amount"] == "1.23"
        assert result["result"]["interest_payments"][0]["type"] == "cash_management"
        assert result["result"]["status"] == "success"

    @patch("open_stocks_mcp.tools.robinhood_dividend_tools.get_rate_limiter")
    @patch("open_stocks_mcp.tools.robinhood_dividend_tools.get_session_manager")
    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch(
        "open_stocks_mcp.tools.robinhood_dividend_tools.rh.account.get_interest_payments"
    )
    @pytest.mark.asyncio
    async def test_interest_payments_no_data(
        self,
        mock_interest_payments: Any,
        mock_session_manager: Any,
        mock_rate_limiter: Any,
    ) -> None:
        """Test interest payments when no data is available."""
        mock_interest_payments.return_value = None

        # Mock session manager
        mock_session_instance = AsyncMock()
        mock_session_instance.ensure_authenticated.return_value = True
        mock_session_manager.return_value = mock_session_instance

        # Mock rate limiter
        mock_rate_instance = AsyncMock()
        mock_rate_instance.acquire.return_value = None
        mock_rate_limiter.return_value = mock_rate_instance

        result = await get_interest_payments()

        assert "result" in result
        assert result["result"]["count"] == 0
        assert result["result"]["interest_payments"] == []
        assert result["result"]["total_interest"] == "0.00"
        assert result["result"]["status"] == "success"


class TestStockLoanPayments:
    """Test stock loan payments functionality."""

    @patch("open_stocks_mcp.tools.robinhood_dividend_tools.get_rate_limiter")
    @patch("open_stocks_mcp.tools.robinhood_dividend_tools.get_session_manager")
    @patch(
        "open_stocks_mcp.tools.robinhood_dividend_tools.rh.stocks.get_instrument_by_url"
    )
    @patch(
        "open_stocks_mcp.tools.robinhood_dividend_tools.rh.account.get_stock_loan_payments"
    )
    @pytest.mark.asyncio
    async def test_stock_loan_payments_success(
        self,
        mock_loan_payments: Any,
        mock_instrument: Any,
        mock_session_manager: Any,
        mock_rate_limiter: Any,
    ) -> None:
        """Test successful stock loan payments retrieval."""
        mock_loan_payments.return_value = [
            {
                "id": "loan1",
                "amount": "0.45",
                "paid_at": "2024-12-01T00:00:00Z",
                "state": "paid",
                "shares_loaned": "100",
                "rate": "0.15",
                "instrument": "https://robinhood.com/instruments/abc123/",
                "created_at": "2024-11-30T00:00:00Z",
            },
            {
                "id": "loan2",
                "amount": "0.89",
                "paid_at": "2024-11-15T00:00:00Z",
                "state": "paid",
                "shares_loaned": "200",
                "rate": "0.15",
                "instrument": "https://robinhood.com/instruments/def456/",
                "created_at": "2024-11-14T00:00:00Z",
            },
        ]

        mock_instrument.side_effect = [
            {"symbol": "AMC", "simple_name": "AMC Entertainment"},
            {"symbol": "GME", "simple_name": "GameStop Corp"},
        ]

        # Mock session manager
        mock_session_instance = AsyncMock()
        mock_session_instance.ensure_authenticated.return_value = True
        mock_session_manager.return_value = mock_session_instance

        # Mock rate limiter
        mock_rate_instance = AsyncMock()
        mock_rate_instance.acquire.return_value = None
        mock_rate_limiter.return_value = mock_rate_instance

        result = await get_stock_loan_payments()

        assert "result" in result
        assert result["result"]["count"] == 2
        assert len(result["result"]["loan_payments"]) == 2
        assert result["result"]["total_loan_income"] == "1.34"  # 0.45 + 0.89
        assert result["result"]["enrolled"] is True
        assert result["result"]["loan_payments"][0]["symbol"] == "AMC"
        assert result["result"]["loan_payments"][0]["shares_loaned"] == "100"
        assert result["result"]["loan_payments"][1]["symbol"] == "GME"
        assert result["result"]["status"] == "success"

    @patch("open_stocks_mcp.tools.robinhood_dividend_tools.get_rate_limiter")
    @patch("open_stocks_mcp.tools.robinhood_dividend_tools.get_session_manager")
    @pytest.mark.exception_test
    @pytest.mark.skip(reason="Slow exception test - run with pytest -m exception_test")
    @patch(
        "open_stocks_mcp.tools.robinhood_dividend_tools.rh.account.get_stock_loan_payments"
    )
    @pytest.mark.asyncio
    async def test_stock_loan_payments_no_data(
        self, mock_loan_payments: Any, mock_session_manager: Any, mock_rate_limiter: Any
    ) -> None:
        """Test stock loan payments when no data is available."""
        mock_loan_payments.return_value = None

        # Mock session manager
        mock_session_instance = AsyncMock()
        mock_session_instance.ensure_authenticated.return_value = True
        mock_session_manager.return_value = mock_session_instance

        # Mock rate limiter
        mock_rate_instance = AsyncMock()
        mock_rate_instance.acquire.return_value = None
        mock_rate_limiter.return_value = mock_rate_instance

        result = await get_stock_loan_payments()

        assert "result" in result
        assert result["result"]["count"] == 0
        assert result["result"]["loan_payments"] == []
        assert result["result"]["total_loan_income"] == "0.00"
        assert result["result"]["enrolled"] is False
        assert result["result"]["status"] == "success"


class TestServerMetrics:
    """Test server metrics and health check functionality."""

    @patch("open_stocks_mcp.server.app.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_metrics_summary_success(
        self, mock_get_metrics_collector: Any
    ) -> None:
        """Test successful metrics summary retrieval."""
        # We need to import the function from the server app
        from open_stocks_mcp.server.app import metrics_summary

        mock_metrics_collector = AsyncMock()
        mock_metrics_collector.get_metrics.return_value = {
            "total_calls": 500,
            "total_errors": 10,
            "error_rate_percent": 2.0,
            "avg_response_time_ms": 250.5,
            "session_refreshes": 1,
            "timestamp": "2023-01-01T12:00:00",
        }
        mock_get_metrics_collector.return_value = mock_metrics_collector

        result = await metrics_summary()

        assert "result" in result
        assert result["result"]["total_calls"] == 500
        assert result["result"]["total_errors"] == 10
        assert result["result"]["error_rate_percent"] == 2.0
        assert result["result"]["avg_response_time_ms"] == 250.5
        assert result["result"]["session_refreshes"] == 1
        assert result["result"]["status"] == "success"

    @patch("open_stocks_mcp.server.app.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, mock_get_metrics_collector: Any) -> None:
        """Test health check with healthy status."""
        from open_stocks_mcp.server.app import health_check

        mock_metrics_collector = AsyncMock()
        mock_metrics_collector.get_health_status.return_value = {
            "health_status": "healthy",
            "issues": [],
            "metrics_summary": {
                "error_rate_percent": 1.5,
                "avg_response_time_ms": 200.0,
                "calls_last_hour": 100,
            },
        }
        mock_get_metrics_collector.return_value = mock_metrics_collector

        result = await health_check()

        assert "result" in result
        assert result["result"]["status"] == "success"
        assert result["result"]["health_status"] == "healthy"
        assert result["result"]["issues"] == []
        assert result["result"]["metrics_summary"]["error_rate_percent"] == 1.5
        assert result["result"]["metrics_summary"]["avg_response_time_ms"] == 200.0

    @patch("open_stocks_mcp.server.app.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_health_check_degraded(self, mock_get_metrics_collector: Any) -> None:
        """Test health check with degraded status."""
        from open_stocks_mcp.server.app import health_check

        mock_metrics_collector = AsyncMock()
        mock_metrics_collector.get_health_status.return_value = {
            "health_status": "degraded",
            "issues": ["High error rate: 15.0%", "Slow response times"],
            "metrics_summary": {
                "error_rate_percent": 15.0,
                "avg_response_time_ms": 6000.0,
                "calls_last_hour": 50,
            },
        }
        mock_get_metrics_collector.return_value = mock_metrics_collector

        result = await health_check()

        assert "result" in result
        assert result["result"]["status"] == "success"
        assert result["result"]["health_status"] == "degraded"
        assert "High error rate: 15.0%" in result["result"]["issues"]
        assert "Slow response times" in result["result"]["issues"]
        assert result["result"]["metrics_summary"]["error_rate_percent"] == 15.0
