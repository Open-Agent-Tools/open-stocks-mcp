"""Tests for server.tool_helpers extracted system-tool helpers."""

from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp import FastMCP

from open_stocks_mcp.server.tool_helpers import (
    get_broker_status_data,
    get_health_check_data,
    get_list_brokers_data,
    get_list_tools_data,
    get_metrics_summary_data,
    get_rate_limit_status_data,
    get_session_status_data,
)


@pytest.mark.journey_system
class TestSessionStatusHelper:
    """Tests for get_session_status_data."""

    @pytest.mark.asyncio
    async def test_returns_result_with_session_info(self) -> None:
        fake_session_info = {"authenticated": True, "username": "test@example.com"}
        with patch(
            "open_stocks_mcp.server.tool_helpers.get_session_manager"
        ) as mock_get_sm:
            sm = MagicMock()
            sm.get_session_info.return_value = fake_session_info
            mock_get_sm.return_value = sm

            response = await get_session_status_data()

        assert "result" in response
        assert response["result"]["status"] == "success"
        assert response["result"]["authenticated"] is True
        assert response["result"]["username"] == "test@example.com"


@pytest.mark.journey_system
class TestBrokerStatusHelper:
    """Tests for get_broker_status_data."""

    @pytest.mark.asyncio
    async def test_returns_broker_status_on_success(self) -> None:
        fake_registry = MagicMock()
        fake_registry.get_auth_status.return_value = {"robinhood": "authenticated"}
        fake_registry.get_available_brokers.return_value = ["robinhood"]
        fake_registry.list_brokers.return_value = ["robinhood"]
        fake_registry.get_broker_health.return_value = {
            "broker_health": {"robinhood": {"status": "healthy"}},
            "account_health": {"robinhood": {"default": {"status": "healthy"}}},
        }

        async def fake_get_registry() -> MagicMock:
            return fake_registry

        with patch(
            "open_stocks_mcp.server.tool_helpers.get_broker_registry",
            side_effect=fake_get_registry,
        ):
            response = await get_broker_status_data()

        assert response["result"]["status"] == "success"
        assert response["result"]["brokers"] == {"robinhood": "authenticated"}
        assert response["result"]["total_configured"] == 1
        assert response["result"]["total_authenticated"] == 1
        assert response["result"]["broker_health"]["robinhood"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_returns_error_when_registry_raises(self) -> None:
        async def fake_get_registry() -> MagicMock:
            raise RuntimeError("boom")

        with patch(
            "open_stocks_mcp.server.tool_helpers.get_broker_registry",
            side_effect=fake_get_registry,
        ):
            response = await get_broker_status_data()

        assert response["result"]["status"] == "error"
        assert response["result"]["error"] == "boom"


@pytest.mark.journey_system
class TestListBrokersHelper:
    """Tests for get_list_brokers_data."""

    @pytest.mark.asyncio
    async def test_returns_broker_list_on_success(self) -> None:
        fake_broker = MagicMock()
        fake_broker.auth_info.status.value = "authenticated"
        fake_broker.is_configured.return_value = True

        fake_registry = MagicMock()
        fake_registry.list_brokers.return_value = ["robinhood"]
        fake_registry.get_available_brokers.return_value = ["robinhood"]
        fake_registry.get_broker.return_value = fake_broker

        async def fake_get_registry() -> MagicMock:
            return fake_registry

        with patch(
            "open_stocks_mcp.server.tool_helpers.get_broker_registry",
            side_effect=fake_get_registry,
        ):
            response = await get_list_brokers_data()

        assert response["result"]["status"] == "success"
        assert response["result"]["count"] == 1
        assert response["result"]["brokers"][0]["name"] == "robinhood"
        assert response["result"]["brokers"][0]["available"] is True
        assert response["result"]["brokers"][0]["status"] == "authenticated"
        assert response["result"]["brokers"][0]["configured"] is True

    @pytest.mark.asyncio
    async def test_returns_error_when_registry_raises(self) -> None:
        async def fake_get_registry() -> MagicMock:
            raise RuntimeError("kaboom")

        with patch(
            "open_stocks_mcp.server.tool_helpers.get_broker_registry",
            side_effect=fake_get_registry,
        ):
            response = await get_list_brokers_data()

        assert response["result"]["status"] == "error"
        assert response["result"]["error"] == "kaboom"


@pytest.mark.journey_system
class TestRateLimitStatusHelper:
    """Tests for get_rate_limit_status_data."""

    @pytest.mark.asyncio
    async def test_returns_rate_limiter_stats(self) -> None:
        with patch(
            "open_stocks_mcp.server.tool_helpers.get_rate_limiter"
        ) as mock_get_rl:
            rl = MagicMock()
            rl.get_stats.return_value = {"requests_made": 5, "limit": 100}
            mock_get_rl.return_value = rl

            response = await get_rate_limit_status_data()

        mock_get_rl.assert_called_once_with("robinhood")

        assert response["result"]["status"] == "success"
        assert response["result"]["requests_made"] == 5
        assert response["result"]["limit"] == 100


@pytest.mark.journey_system
class TestMetricsSummaryHelper:
    """Tests for get_metrics_summary_data."""

    @pytest.mark.asyncio
    async def test_returns_metrics(self) -> None:
        fake_metrics = {"uptime": 123.4, "request_count": 42}

        async def fake_get_metrics() -> dict:
            return fake_metrics

        with patch(
            "open_stocks_mcp.server.tool_helpers.get_metrics_collector"
        ) as mock_get_mc:
            mc = MagicMock()
            mc.get_metrics.side_effect = fake_get_metrics
            mock_get_mc.return_value = mc

            response = await get_metrics_summary_data()

        assert response["result"]["status"] == "success"
        assert response["result"]["uptime"] == 123.4
        assert response["result"]["request_count"] == 42


@pytest.mark.journey_system
class TestHealthCheckHelper:
    """Tests for get_health_check_data."""

    @pytest.mark.asyncio
    async def test_returns_health_status(self) -> None:
        fake_health = {
            "status": "degraded",
            "components": {"metrics": {"status": "healthy", "last_checked": "x"}},
            "timestamp": 123.0,
        }

        async def fake_get_health() -> dict:
            return fake_health

        with patch(
            "open_stocks_mcp.server.tool_helpers.get_health_service"
        ) as mock_get_hs:
            hs = MagicMock()
            hs.get_status.side_effect = fake_get_health
            mock_get_hs.return_value = hs

            response = await get_health_check_data()

        assert response["result"]["status"] == "success"
        assert response["result"]["health_status"] == "degraded"
        assert "components" in response["result"]
        assert "broker_health" in response["result"]
        assert "account_health" in response["result"]


@pytest.mark.journey_system
class TestListToolsHelper:
    """Tests for get_list_tools_data."""

    @pytest.mark.asyncio
    async def test_returns_empty_tool_list_for_fresh_server(self) -> None:
        fresh_mcp = FastMCP("test-empty")

        response = await get_list_tools_data(fresh_mcp)

        assert "result" in response
        assert response["result"]["count"] == 0
        assert response["result"]["tools"] == []
