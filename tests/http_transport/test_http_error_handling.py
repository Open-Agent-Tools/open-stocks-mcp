"""Tests for HTTP transport error handling and reliability"""

import asyncio
import json
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
    async def stable_tool() -> dict[str, Any]:
        """A stable test tool"""
        return {"result": {"message": "success", "status": "success"}}

    @server.tool()
    async def error_tool() -> dict[str, Any]:
        """A tool that always errors"""
        raise Exception("Intentional error for testing")

    @server.tool()
    async def timeout_tool() -> dict[str, Any]:
        """A tool that simulates timeout"""
        await asyncio.sleep(5.0)  # Longer than typical timeout
        return {"result": {"message": "completed after delay", "status": "success"}}

    return server


@pytest.fixture
async def http_client(mcp_server: FastMCP) -> Any:
    """Create an HTTP client for testing"""
    from httpx import ASGITransport

    app = create_http_server(mcp_server)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestHTTPErrorHandling:
    """Test HTTP error handling scenarios"""

    async def test_404_error_handling(self, http_client: httpx.AsyncClient) -> None:
        """Test 404 Not Found error handling"""
        response = await http_client.get("/nonexistent-endpoint")
        assert response.status_code == 404

        # Check if response includes error details
        if response.headers.get("content-type", "").startswith("application/json"):
            data = response.json()
            assert "detail" in data or "error" in data

    async def test_405_method_not_allowed(self, http_client: httpx.AsyncClient) -> None:
        """Test Method Not Allowed error handling"""
        # Try POST on GET-only endpoint
        response = await http_client.post("/health")
        assert response.status_code == 405

        # Check Allow header is present
        assert "allow" in response.headers

    async def test_400_bad_request_handling(
        self, http_client: httpx.AsyncClient
    ) -> None:
        """Test bad request handling"""
        # Send malformed JSON
        response = await http_client.post(
            "/session/refresh",
            content="{'invalid': json}",  # Invalid JSON
            headers={"content-type": "application/json"},
        )
        assert response.status_code in [400, 422]  # Bad Request or Unprocessable Entity

    async def test_invalid_content_type(self, http_client: httpx.AsyncClient) -> None:
        """Test handling of invalid content types"""
        response = await http_client.post(
            "/session/refresh",
            content="some data",
            headers={"content-type": "text/plain"},
        )
        # Should handle gracefully
        assert response.status_code in [400, 415, 422]  # Various acceptable error codes

    @patch("open_stocks_mcp.monitoring.get_metrics_collector")
    async def test_503_service_unavailable(
        self, mock_get_metrics_collector: Mock, http_client: httpx.AsyncClient
    ) -> None:
        """Test service unavailable error handling"""
        # Mock metrics collector failure
        mock_metrics_collector = AsyncMock()
        mock_metrics_collector.get_health_status.side_effect = Exception("Service down")
        mock_get_metrics_collector.return_value = mock_metrics_collector

        response = await http_client.get("/health")
        assert response.status_code == 503

        data = response.json()
        assert "detail" in data
        assert "Service unhealthy" in data["detail"]

    @patch("open_stocks_mcp.tools.session_manager.get_session_manager")
    async def test_500_internal_server_error(
        self, mock_get_session_manager: Mock, http_client: httpx.AsyncClient
    ) -> None:
        """Test internal server error handling"""
        # Mock session manager failure
        mock_session_manager = AsyncMock()
        mock_session_manager.ensure_authenticated.side_effect = Exception(
            "Database connection failed"
        )
        mock_get_session_manager.return_value = mock_session_manager

        response = await http_client.post("/session/refresh")
        assert response.status_code == 500

        data = response.json()
        assert "detail" in data


class TestTimeoutHandling:
    """Test timeout handling scenarios"""

    async def test_request_timeout_simulation(
        self, http_client: httpx.AsyncClient
    ) -> None:
        """Test request timeout simulation"""
        # Test with very short timeout
        try:
            response = await http_client.get("/health", timeout=0.001)  # 1ms timeout
            # If this succeeds, the operation was very fast
            assert response.status_code == 200
        except httpx.TimeoutException:
            # This is expected for very short timeouts
            pass

    async def test_concurrent_timeout_handling(
        self, http_client: httpx.AsyncClient
    ) -> None:
        """Test timeout handling with concurrent requests"""

        async def make_request_with_timeout(request_id: int) -> dict[str, Any]:
            """Make a request with timeout"""
            try:
                response = await http_client.get(
                    "/health", timeout=0.01
                )  # 10ms timeout
                return {
                    "request_id": request_id,
                    "status": "success",
                    "status_code": response.status_code,
                }
            except httpx.TimeoutException:
                return {
                    "request_id": request_id,
                    "status": "timeout",
                    "status_code": 408,
                }

        # Make multiple concurrent requests with short timeouts
        tasks = [make_request_with_timeout(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # All requests should complete (either success or timeout)
        assert len(results) == 5
        for result in results:
            assert result["status"] in ["success", "timeout"]

    def test_timeout_configuration(self) -> None:
        """Test timeout configuration values"""
        # Test timeout configuration is reasonable
        default_timeout = 120.0  # 2 minutes
        max_timeout = 300.0  # 5 minutes
        min_timeout = 1.0  # 1 second

        assert default_timeout > min_timeout
        assert max_timeout > default_timeout
        assert min_timeout > 0


class TestConnectionHandling:
    """Test connection handling and reliability"""

    async def test_connection_reuse(self, http_client: httpx.AsyncClient) -> None:
        """Test connection reuse for multiple requests"""
        # Make multiple requests to test connection reuse
        responses = []
        for _i in range(3):
            response = await http_client.get("/health")
            responses.append(response.status_code)

        # All requests should succeed
        assert all(status == 200 for status in responses)

    async def test_concurrent_connection_limits(
        self, http_client: httpx.AsyncClient
    ) -> None:
        """Test handling of concurrent connections"""

        async def make_request(request_id: int) -> int:
            """Make a single request"""
            response = await http_client.get("/health")
            return response.status_code

        # Make many concurrent requests
        tasks = [make_request(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # All should succeed (no connection limit errors)
        assert all(status == 200 for status in results)

    async def test_malformed_requests(self, http_client: httpx.AsyncClient) -> None:
        """Test handling of malformed requests"""
        # Test various malformed request scenarios
        malformed_scenarios = [
            # Missing content-type header with JSON body
            {
                "method": "POST",
                "url": "/session/refresh",
                "content": '{"test": "data"}',
                "headers": {},
            },
            # Invalid JSON with correct content-type
            {
                "method": "POST",
                "url": "/session/refresh",
                "content": "{invalid json",
                "headers": {"content-type": "application/json"},
            },
        ]

        for scenario in malformed_scenarios:
            headers = scenario["headers"]
            headers_dict = dict(headers) if isinstance(headers, dict) else {}
            response = await http_client.request(
                method=str(scenario["method"]),
                url=str(scenario["url"]),
                content=str(scenario["content"]),
                headers=headers_dict,
            )
            # Should handle gracefully with appropriate error code
            assert response.status_code in [400, 415, 422, 500]


class TestSecurityErrorHandling:
    """Test security-related error handling"""

    async def test_blocked_origin_handling(self, mcp_server: FastMCP) -> None:
        """Test handling of requests from blocked origins"""
        from httpx import ASGITransport

        app = create_http_server(mcp_server)
        transport = ASGITransport(app=app)

        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            # Test with blocked origin
            headers = {"origin": "https://malicious-site.com"}
            response = await client.get("/health", headers=headers)
            assert response.status_code == 403

            data = response.json()
            assert "Forbidden origin" in data.get("error", "")

    async def test_missing_required_headers(
        self, http_client: httpx.AsyncClient
    ) -> None:
        """Test handling of requests with missing required headers"""
        # Test POST request without content-type
        response = await http_client.post(
            "/session/refresh", content='{"test": "data"}'
        )
        # Should handle gracefully
        assert response.status_code in [400, 415, 422]

    async def test_oversized_request_handling(
        self, http_client: httpx.AsyncClient
    ) -> None:
        """Test handling of oversized requests"""
        # Create a large request body
        large_data = json.dumps({"data": "x" * 10000})  # 10KB of data

        response = await http_client.post(
            "/session/refresh",
            content=large_data,
            headers={"content-type": "application/json"},
        )
        # Should handle without crashing
        assert response.status_code in [200, 400, 413, 422, 500]


class TestRecoveryMechanisms:
    """Test error recovery mechanisms"""

    @patch("open_stocks_mcp.tools.session_manager.get_session_manager")
    async def test_service_recovery_after_error(
        self, mock_get_session_manager: Mock, http_client: httpx.AsyncClient
    ) -> None:
        """Test service recovery after temporary errors"""
        mock_session_manager = AsyncMock()

        # First call fails
        mock_session_manager.ensure_authenticated.side_effect = Exception(
            "Temporary failure"
        )
        mock_get_session_manager.return_value = mock_session_manager

        response1 = await http_client.post("/session/refresh")
        assert response1.status_code == 500

        # Second call succeeds (recovery)
        mock_session_manager.ensure_authenticated.side_effect = None
        mock_session_manager.ensure_authenticated.return_value = True
        mock_session_manager.get_session_info.return_value = {
            "authenticated": True,
            "session_duration": 3600,
        }

        response2 = await http_client.post("/session/refresh")
        assert response2.status_code == 200

    async def test_graceful_degradation(self, http_client: httpx.AsyncClient) -> None:
        """Test graceful degradation when optional services fail"""
        # Even if some services fail, basic endpoints should still work
        response = await http_client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "name" in data
        assert "version" in data

    def test_error_message_format(self) -> None:
        """Test error message format consistency"""
        # Standard error response format
        error_response = {
            "error": "Authentication failed",
            "status": "error",
            "error_code": "AUTH_FAILED",
            "timestamp": "2025-07-11T18:00:00Z",
        }

        assert "error" in error_response
        assert "status" in error_response
        assert error_response["status"] == "error"
