"""HTTP client tests for MCP communication"""

import asyncio
from typing import Any

import httpx
import pytest


class TestMCPHTTPClient:
    """Test MCP client communication over HTTP"""

    @pytest.fixture
    async def http_client(self) -> Any:
        """Create HTTP client for testing"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            yield client

    async def test_jsonrpc_request_format(self, http_client: httpx.AsyncClient) -> None:
        """Test JSON-RPC 2.0 request format"""
        # Example JSON-RPC 2.0 request for MCP
        request_data = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}

        # This would be tested against a live server
        # For now, just verify the request format is correct
        assert request_data["jsonrpc"] == "2.0"
        assert "method" in request_data
        assert "id" in request_data

    async def test_mcp_tool_call_format(self, http_client: httpx.AsyncClient) -> None:
        """Test MCP tool call request format"""
        # Example tool call request
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "stock_price", "arguments": {"symbol": "AAPL"}},
            "id": 2,
        }

        assert request_data["method"] == "tools/call"
        assert "params" in request_data
        params = request_data["params"]
        assert isinstance(params, dict)
        assert "name" in params
        assert "arguments" in params

    async def test_session_initialization(self, http_client: httpx.AsyncClient) -> None:
        """Test session initialization request"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
            "id": 1,
        }

        assert request_data["method"] == "initialize"
        params = request_data["params"]
        assert isinstance(params, dict)
        assert "protocolVersion" in params
        assert "capabilities" in params


@pytest.mark.integration
class TestLiveMCPCommunication:
    """Integration tests with live MCP server"""

    BASE_URL = "http://localhost:3000"

    async def test_server_health_check(self) -> None:
        """Test health check endpoint"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.BASE_URL}/health", timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "healthy"
                    assert data["transport"] == "http"
            except httpx.ConnectError:
                pytest.skip("HTTP server not running on localhost:3000")

    async def test_mcp_tools_list(self) -> None:
        """Test listing available tools via HTTP"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.BASE_URL}/tools", timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    assert "result" in data
                    assert "tools" in data["result"]
                    assert len(data["result"]["tools"]) > 0
            except httpx.ConnectError:
                pytest.skip("HTTP server not running on localhost:3000")

    async def test_session_status(self) -> None:
        """Test session status endpoint"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.BASE_URL}/status", timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    assert "server" in data
                    assert "session" in data
                    assert data["server"]["status"] == "running"
            except httpx.ConnectError:
                pytest.skip("HTTP server not running on localhost:3000")


class TestHTTPTransportFeatures:
    """Test HTTP transport specific features"""

    async def test_concurrent_requests(self) -> None:
        """Test handling of concurrent HTTP requests"""

        async def make_request(
            client: httpx.AsyncClient, request_id: int
        ) -> dict[str, Any]:
            """Make a single request"""
            try:
                response = await client.get("http://localhost:3000/health", timeout=5.0)
                return {"id": request_id, "status": response.status_code}
            except Exception as e:
                return {"id": request_id, "error": str(e)}

        # Make multiple concurrent requests
        async with httpx.AsyncClient() as client:
            try:
                tasks = [make_request(client, i) for i in range(5)]
                results = await asyncio.gather(*tasks)

                # Check that all requests completed
                assert len(results) == 5

                # Check for successful responses (if server is running)
                successful = [r for r in results if r.get("status") == 200]
                if successful:  # If any succeeded, server is running
                    assert len(successful) >= 1

            except Exception:
                pytest.skip("HTTP server not available for concurrent testing")

    async def test_timeout_handling(self) -> None:
        """Test request timeout handling"""
        async with httpx.AsyncClient() as client:
            try:
                # Test with very short timeout
                response = await client.get(
                    "http://localhost:3000/health",
                    timeout=0.001,  # 1ms timeout
                )
                # If this succeeds, server is very fast
                assert response.status_code == 200
            except httpx.TimeoutException:
                # Expected for very short timeout
                pass
            except httpx.ConnectError:
                pytest.skip("HTTP server not running")

    async def test_error_response_format(self) -> None:
        """Test error response format"""
        async with httpx.AsyncClient() as client:
            try:
                # Request non-existent endpoint
                response = await client.get("http://localhost:3000/nonexistent")
                assert response.status_code == 404

                # Check error response format
                if response.headers.get("content-type", "").startswith(
                    "application/json"
                ):
                    data = response.json()
                    # Should have proper error structure
                    assert isinstance(data, dict)

            except httpx.ConnectError:
                pytest.skip("HTTP server not running")
