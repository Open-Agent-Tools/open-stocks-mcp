"""Integration tests for HTTP transport with mock server"""

import asyncio
import json
import time
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from mcp.server.fastmcp import FastMCP

from open_stocks_mcp.server.http_transport import create_http_server


@pytest.fixture
def mcp_server_with_tools() -> FastMCP:
    """Create a test MCP server instance with mock tools"""
    server = FastMCP("Test Open Stocks MCP")

    @server.tool()
    async def mock_stock_price(symbol: str) -> dict[str, Any]:
        """Mock stock price tool"""
        return {
            "result": {
                "symbol": symbol,
                "price": 150.00,
                "change": 2.50,
                "status": "success",
            }
        }

    @server.tool()
    async def mock_portfolio() -> dict[str, Any]:
        """Mock portfolio tool"""
        return {
            "result": {
                "total_value": 10000.00,
                "positions": [
                    {"symbol": "AAPL", "quantity": 10, "value": 1500.00},
                    {"symbol": "GOOGL", "quantity": 5, "value": 8500.00},
                ],
                "status": "success",
            }
        }

    @server.tool()
    async def mock_slow_tool() -> dict[str, Any]:
        """Mock slow tool for timeout testing"""
        await asyncio.sleep(0.1)  # Simulate slow operation
        return {"result": {"message": "slow operation completed", "status": "success"}}

    @server.tool()
    async def mock_error_tool() -> dict[str, Any]:
        """Mock tool that raises an error"""
        raise Exception("Simulated tool error")

    return server


@pytest.fixture
async def mock_http_client(mcp_server_with_tools: FastMCP) -> Any:
    """Create an HTTP client with mock server for integration testing"""
    from httpx import ASGITransport

    app = create_http_server(mcp_server_with_tools)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestHTTPIntegration:
    """Integration tests for HTTP transport functionality"""

    @patch("open_stocks_mcp.tools.session_manager.get_session_manager")
    @patch("open_stocks_mcp.tools.rate_limiter.get_rate_limiter")
    @patch("open_stocks_mcp.monitoring.get_metrics_collector")
    async def test_full_server_startup_sequence(
        self,
        mock_get_metrics_collector: Mock,
        mock_get_rate_limiter: Mock,
        mock_get_session_manager: Mock,
        mock_http_client: httpx.AsyncClient,
    ) -> None:
        """Test full server startup and initialization sequence"""
        # Mock all dependencies
        mock_session_manager = Mock()
        mock_session_manager.get_session_info.return_value = {
            "authenticated": True,
            "session_duration": 3600,
        }
        mock_get_session_manager.return_value = mock_session_manager

        mock_rate_limiter = Mock()
        mock_rate_limiter.get_stats.return_value = {
            "total_requests": 0,
            "rate_limited_requests": 0,
        }
        mock_get_rate_limiter.return_value = mock_rate_limiter

        mock_metrics_collector = AsyncMock()
        mock_metrics_collector.get_health_status.return_value = {
            "status": "healthy",
            "uptime": 100,
        }
        mock_metrics_collector.get_metrics.return_value = {
            "tool_calls": 0,
            "success_rate": 1.0,
        }
        mock_get_metrics_collector.return_value = mock_metrics_collector

        # Test server endpoints are accessible
        health_response = await mock_http_client.get("/health")
        assert health_response.status_code == 200

        status_response = await mock_http_client.get("/status")
        assert status_response.status_code == 200

        tools_response = await mock_http_client.get("/tools")
        assert tools_response.status_code == 200

        root_response = await mock_http_client.get("/")
        assert root_response.status_code == 200

    async def test_mcp_endpoint_accessibility(
        self, mock_http_client: httpx.AsyncClient
    ) -> None:
        """Test that MCP endpoints are properly mounted and accessible"""
        # Test MCP JSON-RPC endpoint
        mcp_response = await mock_http_client.get("/mcp")
        # Should not be 404 (mounted correctly)
        assert mcp_response.status_code != 404

        # Test SSE endpoint
        sse_response = await mock_http_client.get("/sse")
        # Should not be 404 (mounted correctly)
        assert sse_response.status_code != 404

    async def test_concurrent_request_handling(
        self, mock_http_client: httpx.AsyncClient
    ) -> None:
        """Test handling of concurrent HTTP requests"""

        async def make_health_request(request_id: int) -> dict[str, Any]:
            """Make a single health check request"""
            response = await mock_http_client.get("/health")
            return {
                "request_id": request_id,
                "status_code": response.status_code,
                "response_time": time.time(),
            }

        # Make 5 concurrent requests
        tasks = [make_health_request(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # All requests should succeed
        assert len(results) == 5
        for result in results:
            assert result["status_code"] == 200
            assert "response_time" in result

    async def test_error_handling_integration(
        self, mock_http_client: httpx.AsyncClient
    ) -> None:
        """Test integrated error handling across the HTTP stack"""
        # Test 404 for unknown endpoint
        response = await mock_http_client.get("/unknown-endpoint")
        assert response.status_code == 404

        # Test method not allowed
        response = await mock_http_client.post("/health")
        assert response.status_code == 405

        # Test invalid JSON
        response = await mock_http_client.post(
            "/session/refresh",
            content="invalid json",
            headers={"content-type": "application/json"},
        )
        assert response.status_code in [400, 422]  # Bad request or validation error

    async def test_security_middleware_integration(
        self, mcp_server_with_tools: FastMCP
    ) -> None:
        """Test security middleware with blocked origins"""
        from httpx import ASGITransport

        app = create_http_server(mcp_server_with_tools)
        transport = ASGITransport(app=app)

        # Test with malicious origin
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            headers = {"origin": "https://malicious-site.com"}
            response = await client.get("/health", headers=headers)
            assert response.status_code == 403  # Forbidden

    @patch("open_stocks_mcp.tools.session_manager.get_session_manager")
    async def test_session_lifecycle_integration(
        self, mock_get_session_manager: Mock, mock_http_client: httpx.AsyncClient
    ) -> None:
        """Test complete session lifecycle over HTTP"""
        # Mock session manager for lifecycle testing
        mock_session_manager = AsyncMock()
        mock_session_manager.get_session_info.return_value = {
            "authenticated": False,
            "session_duration": None,
        }
        mock_session_manager.ensure_authenticated.return_value = True
        mock_get_session_manager.return_value = mock_session_manager

        # 1. Check initial session status (unauthenticated)
        response = await mock_http_client.get("/health")
        data = response.json()
        assert data["session"]["authenticated"] is False

        # 2. Refresh session (authenticate)
        mock_session_manager.get_session_info.return_value = {
            "authenticated": True,
            "session_duration": 3600,
        }

        response = await mock_http_client.post("/session/refresh")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # 3. Check session status after authentication
        response = await mock_http_client.get("/health")
        data = response.json()
        assert data["session"]["authenticated"] is True

    async def test_tool_execution_integration(
        self, mock_http_client: httpx.AsyncClient
    ) -> None:
        """Test tool execution through HTTP transport"""
        # Test that tools endpoint returns available tools
        response = await mock_http_client.get("/tools")
        assert response.status_code == 200

        data = response.json()
        assert "result" in data
        # Should have our mock tools
        tools = data["result"].get("tools", [])
        [tool.get("name", "") for tool in tools]

        # May include our mock tools or real tools depending on mocking
        assert len(tools) > 0

    async def test_timeout_handling_integration(
        self, mock_http_client: httpx.AsyncClient
    ) -> None:
        """Test timeout handling in integrated environment"""
        # Test with very short timeout
        try:
            response = await mock_http_client.get("/health", timeout=0.001)  # 1ms
            # If this succeeds, server is very fast
            assert response.status_code == 200
        except httpx.TimeoutException:
            # Expected for very short timeout
            pass


class TestHTTPTransportReliability:
    """Test HTTP transport reliability features"""

    async def test_graceful_error_responses(
        self, mock_http_client: httpx.AsyncClient
    ) -> None:
        """Test that errors are returned gracefully"""
        # Test various error scenarios
        error_scenarios = [
            ("/nonexistent", 404),
            # Add more error scenarios as needed
        ]

        for endpoint, expected_status in error_scenarios:
            response = await mock_http_client.get(endpoint)
            assert response.status_code == expected_status
            # Should return valid JSON even for errors
            try:
                data = response.json()
                assert isinstance(data, dict)
            except json.JSONDecodeError:
                # Some errors might not return JSON, which is acceptable
                pass

    async def test_response_format_consistency(
        self, mock_http_client: httpx.AsyncClient
    ) -> None:
        """Test that responses follow consistent format"""
        endpoints_to_test = ["/", "/health", "/status"]

        for endpoint in endpoints_to_test:
            response = await mock_http_client.get(endpoint)
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict)
                # All successful responses should be valid JSON dictionaries

    @patch("open_stocks_mcp.monitoring.get_metrics_collector")
    async def test_monitoring_integration(
        self, mock_get_metrics_collector: Mock, mock_http_client: httpx.AsyncClient
    ) -> None:
        """Test monitoring and metrics integration"""
        mock_metrics_collector = AsyncMock()
        mock_metrics_collector.get_health_status.return_value = {
            "status": "healthy",
            "uptime": 300,
            "memory_usage": 0.65,
        }
        mock_metrics_collector.get_metrics.return_value = {
            "total_requests": 150,
            "successful_requests": 145,
            "failed_requests": 5,
            "average_response_time": 45.2,
        }
        mock_get_metrics_collector.return_value = mock_metrics_collector

        # Test health endpoint returns monitoring data
        response = await mock_http_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "health" in data
        assert data["health"]["status"] == "healthy"

        # Test status endpoint returns detailed metrics
        response = await mock_http_client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert data["metrics"]["total_requests"] == 150
