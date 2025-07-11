"""Tests for HTTP transport authentication and session management"""

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from mcp.server.fastmcp import FastMCP

from open_stocks_mcp.server.http_transport import create_http_server


@pytest.fixture
def mcp_server() -> FastMCP:
    """Create a test MCP server instance"""
    server = FastMCP("Test Open Stocks MCP")

    @server.tool()
    async def test_tool() -> dict[str, Any]:
        """A simple test tool"""
        return {"result": {"message": "test successful", "status": "success"}}

    return server


@pytest.fixture
async def http_client(mcp_server: FastMCP) -> Any:
    """Create an HTTP client for testing"""
    from httpx import ASGITransport

    app = create_http_server(mcp_server)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestHTTPAuthentication:
    """Test authentication scenarios for HTTP transport"""

    @patch("open_stocks_mcp.tools.session_manager.get_session_manager")
    async def test_health_check_with_authenticated_session(
        self, mock_get_session_manager: Mock, http_client: httpx.AsyncClient
    ) -> None:
        """Test health check when session is authenticated"""
        # Mock authenticated session
        mock_session_manager = Mock()
        mock_session_manager.get_session_info.return_value = {
            "authenticated": True,
            "session_duration": 3600,
            "username": "test_user",
        }
        mock_get_session_manager.return_value = mock_session_manager

        response = await http_client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["session"]["authenticated"] is True
        assert data["session"]["session_duration"] == 3600

    @patch("open_stocks_mcp.tools.session_manager.get_session_manager")
    async def test_health_check_with_unauthenticated_session(
        self, mock_get_session_manager: Mock, http_client: httpx.AsyncClient
    ) -> None:
        """Test health check when session is not authenticated"""
        # Mock unauthenticated session
        mock_session_manager = Mock()
        mock_session_manager.get_session_info.return_value = {
            "authenticated": False,
            "session_duration": None,
            "username": None,
        }
        mock_get_session_manager.return_value = mock_session_manager

        response = await http_client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["session"]["authenticated"] is False

    @patch("open_stocks_mcp.tools.session_manager.get_session_manager")
    async def test_session_refresh_success(
        self, mock_get_session_manager: Mock, http_client: httpx.AsyncClient
    ) -> None:
        """Test successful session refresh"""
        # Mock successful authentication
        mock_session_manager = AsyncMock()
        mock_session_manager.ensure_authenticated.return_value = True
        mock_session_manager.get_session_info.return_value = {
            "authenticated": True,
            "session_duration": 3600,
            "username": "test_user",
        }
        mock_get_session_manager.return_value = mock_session_manager

        response = await http_client.post("/session/refresh")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["session"]["authenticated"] is True

    @patch("open_stocks_mcp.tools.session_manager.get_session_manager")
    async def test_session_refresh_failure(
        self, mock_get_session_manager: Mock, http_client: httpx.AsyncClient
    ) -> None:
        """Test failed session refresh"""
        # Mock failed authentication
        mock_session_manager = AsyncMock()
        mock_session_manager.ensure_authenticated.return_value = False
        mock_get_session_manager.return_value = mock_session_manager

        response = await http_client.post("/session/refresh")
        assert response.status_code == 401

        data = response.json()
        assert "Authentication failed" in data["detail"]

    @patch("open_stocks_mcp.tools.session_manager.get_session_manager")
    async def test_session_refresh_exception(
        self, mock_get_session_manager: Mock, http_client: httpx.AsyncClient
    ) -> None:
        """Test session refresh with exception"""
        # Mock authentication exception
        mock_session_manager = AsyncMock()
        mock_session_manager.ensure_authenticated.side_effect = Exception(
            "Network error"
        )
        mock_get_session_manager.return_value = mock_session_manager

        response = await http_client.post("/session/refresh")
        assert response.status_code == 500

        data = response.json()
        assert "Session refresh failed" in data["detail"]


class TestHTTPSessionStatus:
    """Test session status reporting"""

    @patch("open_stocks_mcp.tools.session_manager.get_session_manager")
    @patch("open_stocks_mcp.tools.rate_limiter.get_rate_limiter")
    @patch("open_stocks_mcp.monitoring.get_metrics_collector")
    async def test_server_status_comprehensive(
        self,
        mock_get_metrics_collector: Mock,
        mock_get_rate_limiter: Mock,
        mock_get_session_manager: Mock,
        http_client: httpx.AsyncClient,
    ) -> None:
        """Test comprehensive server status reporting"""
        # Mock all components
        mock_session_manager = Mock()
        mock_session_manager.get_session_info.return_value = {
            "authenticated": True,
            "session_duration": 3600,
            "username": "test_user",
        }
        mock_get_session_manager.return_value = mock_session_manager

        mock_rate_limiter = Mock()
        mock_rate_limiter.get_stats.return_value = {
            "total_requests": 100,
            "rate_limited_requests": 5,
            "current_tokens": 95,
        }
        mock_get_rate_limiter.return_value = mock_rate_limiter

        mock_metrics_collector = AsyncMock()
        mock_metrics_collector.get_metrics.return_value = {
            "tool_calls": 50,
            "success_rate": 0.98,
            "average_response_time": 45.2,
        }
        mock_get_metrics_collector.return_value = mock_metrics_collector

        response = await http_client.get("/status")
        assert response.status_code == 200

        data = response.json()
        assert data["server"]["status"] == "running"
        assert data["server"]["version"] == "0.4.0"
        assert data["server"]["transport"] == "http"
        assert data["session"]["authenticated"] is True
        assert data["rate_limiting"]["total_requests"] == 100
        assert data["metrics"]["tool_calls"] == 50

    @patch("open_stocks_mcp.tools.robinhood_tools.list_available_tools")
    async def test_tools_endpoint_success(
        self, mock_list_tools: AsyncMock, http_client: httpx.AsyncClient
    ) -> None:
        """Test tools listing endpoint success"""
        mock_list_tools.return_value = {
            "result": {
                "tools": [
                    {"name": "stock_price", "description": "Get stock price"},
                    {"name": "portfolio", "description": "Get portfolio"},
                ],
                "count": 2,
                "status": "success",
            }
        }

        response = await http_client.get("/tools")
        assert response.status_code == 200

        data = response.json()
        assert "result" in data
        assert "tools" in data["result"]
        assert len(data["result"]["tools"]) == 2

    @patch("open_stocks_mcp.tools.robinhood_tools.list_available_tools")
    async def test_tools_endpoint_failure(
        self, mock_list_tools: AsyncMock, http_client: httpx.AsyncClient
    ) -> None:
        """Test tools listing endpoint failure"""
        mock_list_tools.side_effect = Exception("Tools listing failed")

        response = await http_client.get("/tools")
        assert response.status_code == 500

        data = response.json()
        assert "Failed to list tools" in data["detail"]


class TestHTTPSecurity:
    """Test HTTP transport security features"""

    async def test_security_headers_present(
        self, http_client: httpx.AsyncClient
    ) -> None:
        """Test that security headers are properly set"""
        response = await http_client.get("/health")
        assert response.status_code == 200

        headers = response.headers
        assert headers.get("x-content-type-options") == "nosniff"
        assert headers.get("x-frame-options") == "DENY"
        assert headers.get("x-xss-protection") == "1; mode=block"

    async def test_root_endpoint_info(self, http_client: httpx.AsyncClient) -> None:
        """Test root endpoint provides correct server information"""
        response = await http_client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Open Stocks MCP Server"
        assert data["version"] == "0.4.0"
        assert data["transport"] == "http"
        assert "endpoints" in data
        assert data["endpoints"]["mcp"] == "/mcp"
        assert data["endpoints"]["sse"] == "/sse"
        assert data["endpoints"]["health"] == "/health"

    async def test_invalid_json_handling(self, http_client: httpx.AsyncClient) -> None:
        """Test handling of invalid JSON requests"""
        response = await http_client.post(
            "/session/refresh",
            content="invalid json",
            headers={"content-type": "application/json"},
        )
        # Should handle gracefully, not crash
        assert response.status_code in [400, 422, 500]  # Various valid error responses


class TestHTTPErrorHandling:
    """Test error handling scenarios"""

    @patch("open_stocks_mcp.monitoring.get_metrics_collector")
    async def test_health_check_service_error(
        self, mock_get_metrics_collector: Mock, http_client: httpx.AsyncClient
    ) -> None:
        """Test health check when service components fail"""
        mock_metrics_collector = AsyncMock()
        mock_metrics_collector.get_health_status.side_effect = Exception("Service down")
        mock_get_metrics_collector.return_value = mock_metrics_collector

        response = await http_client.get("/health")
        assert response.status_code == 503  # Service Unavailable

        data = response.json()
        assert "Service unhealthy" in data["detail"]

    async def test_nonexistent_endpoint_404(
        self, http_client: httpx.AsyncClient
    ) -> None:
        """Test that nonexistent endpoints return 404"""
        response = await http_client.get("/this-does-not-exist")
        assert response.status_code == 404

    async def test_method_not_allowed(self, http_client: httpx.AsyncClient) -> None:
        """Test method not allowed responses"""
        # Try POST on GET-only endpoint
        response = await http_client.post("/health")
        assert response.status_code == 405  # Method Not Allowed
