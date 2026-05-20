"""Fast unit tests for HTTP transport JSON-RPC and endpoint behavior."""

from collections.abc import Iterator
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from mcp.server.fastmcp import FastMCP

from open_stocks_mcp import __version__
from open_stocks_mcp.server.http_transport import (
    MAX_MCP_REQUEST_BODY_SIZE,
    create_http_server,
)


@pytest.fixture(scope="session")
def mcp_server() -> FastMCP:
    """Create a minimal FastMCP server for HTTP transport unit tests."""
    server = FastMCP("Test")

    @server.tool()
    async def account_info() -> dict[str, Any]:
        return {"result": {"status": "ok"}}

    return server


@pytest.fixture
def client(mcp_server: FastMCP) -> Iterator[TestClient]:
    """Create a synchronous TestClient for fast unit testing."""
    with TestClient(create_http_server(mcp_server)) as test_client:
        yield test_client


@pytest.mark.unit
@pytest.mark.journey_system
class TestHttpTransportUnit:
    def test_root_endpoint_returns_server_info(self, client: TestClient) -> None:
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Open Stocks MCP Server"
        assert data["version"] == __version__
        assert data["transport"] == "http"
        assert "endpoints" in data
        assert {"mcp", "sse", "health", "status"} <= set(data["endpoints"])

    def test_mcp_malformed_json_returns_parse_error_minus_32700(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/mcp", content=b"not json", headers={"content-type": "application/json"}
        )
        assert response.status_code == 400
        body = response.json()
        assert body["error"]["code"] == -32700
        assert body["error"]["message"] == "Parse error"
        assert body["id"] is None

    def test_mcp_oversized_body_returns_413_with_parse_error_minus_32700(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/mcp",
            content=b"x" * (MAX_MCP_REQUEST_BODY_SIZE + 1),
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 413
        body = response.json()
        assert body["error"]["code"] == -32700
        assert body["error"]["message"] == "Request body too large"
        assert body["id"] is None

    def test_mcp_unknown_method_returns_method_not_found_minus_32601(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "does/not/exist", "id": 7},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["error"]["code"] == -32601
        assert "method not found" in body["error"]["message"].lower()
        assert body["id"] == 7

    def test_mcp_tools_call_missing_name_returns_invalid_params_minus_32602(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"arguments": {}},
                "id": 8,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["error"]["code"] == -32602
        assert "invalid params" in body["error"]["message"].lower()
        assert body["id"] == 8

    @patch("open_stocks_mcp.server.http_transport.get_session_manager", return_value=None)
    def test_health_returns_503_when_session_manager_unavailable(
        self, _mock_get_session_manager: Any, client: TestClient
    ) -> None:
        response = client.get("/health")
        assert response.status_code == 503
        assert response.json()["detail"] == "Session manager unavailable"

    @patch(
        "open_stocks_mcp.server.http_transport.get_metrics_collector", return_value=None
    )
    def test_health_returns_503_when_metrics_collector_unavailable(
        self, _mock_get_metrics_collector: Any, client: TestClient
    ) -> None:
        response = client.get("/health")
        assert response.status_code == 503
        assert response.json()["detail"] == "Metrics collector unavailable"

    @patch("open_stocks_mcp.server.http_transport.get_metrics_collector", return_value=None)
    def test_status_returns_503_when_metrics_collector_unavailable(
        self, _mock_get_metrics_collector: Any, client: TestClient
    ) -> None:
        response = client.get("/status")
        assert response.status_code == 503
        assert response.json()["detail"] == "Metrics collector unavailable"

    @patch("open_stocks_mcp.server.http_transport.get_session_manager", return_value=None)
    def test_status_returns_503_when_session_manager_unavailable(
        self, _mock_get_session_manager: Any, client: TestClient
    ) -> None:
        response = client.get("/status")
        assert response.status_code == 503
        assert response.json()["detail"] == "Session manager unavailable"

    @patch("open_stocks_mcp.server.http_transport.get_session_manager", return_value=None)
    def test_session_refresh_returns_503_when_session_manager_unavailable(
        self, _mock_get_session_manager: Any, client: TestClient
    ) -> None:
        response = client.post("/session/refresh")
        assert response.status_code == 503
        assert response.json()["detail"] == "Session manager unavailable"

    @patch(
        "open_stocks_mcp.tools.robinhood_tools.list_available_tools",
        side_effect=RuntimeError("boom"),
    )
    def test_tools_endpoint_returns_500_when_list_available_tools_raises(
        self, _mock_list_available_tools: Any, client: TestClient
    ) -> None:
        response = client.get("/tools")
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to list tools"

    def test_cors_preflight_for_mcp_endpoint_allows_post(
        self, client: TestClient
    ) -> None:
        response = client.options(
            "/mcp",
            headers={
                "Origin": "http://localhost:1234",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert response.status_code == 200
        assert "POST" in response.headers.get("access-control-allow-methods", "")
