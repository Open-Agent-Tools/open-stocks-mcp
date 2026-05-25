"""HTTP transport enhancements for the MCP server"""

import asyncio
import json
import logging
import secrets
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware

from open_stocks_mcp import __version__
from open_stocks_mcp.brokers.session_state import get_session_manager
from open_stocks_mcp.config import load_config
from open_stocks_mcp.health import get_health_service
from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.monitoring import get_metrics_collector
from open_stocks_mcp.server.tool_docs import (
    build_tool_docs_payload,
    build_tool_docs_payload_from_snapshot,
    build_tool_openapi_paths,
)
from open_stocks_mcp.tools.circuit_breaker import get_broker_circuit_breaker
from open_stocks_mcp.tools.rate_limiter import get_rate_limiter

MAX_MCP_REQUEST_BODY_SIZE = 1024 * 1024  # 1 MiB

LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

# Endpoints that may invoke tools, mutate session state, or stream tool output.
# Health/status/root remain open so container orchestrators can probe liveness.
PROTECTED_PATHS = frozenset({"/mcp", "/sse", "/session/refresh", "/tools"})

READ_ONLY_HTTP_TOOL_NAMES = frozenset(
    {
        "account_details",
        "account_features",
        "account_info",
        "account_profile",
        "account_settings",
        "aggregate_option_positions",
        "aggregated_portfolio",
        "all_option_positions",
        "all_watchlists",
        "basic_profile",
        "broker_status",
        "build_holdings",
        "build_user_profile",
        "complete_profile",
        "day_trades",
        "dividends",
        "dividends_by_instrument",
        "find_instruments",
        "find_options",
        "health_check",
        "instruments_by_symbols",
        "interest_payments",
        "investment_profile",
        "latest_notification",
        "list_brokers",
        "list_tools",
        "margin_calls",
        "margin_interest",
        "market_hours",
        "metrics_summary",
        "notifications",
        "open_option_orders",
        "open_option_positions",
        "open_option_positions_with_details",
        "open_stock_orders",
        "option_historicals",
        "option_market_data",
        "options_chains",
        "options_orders",
        "portfolio",
        "positions",
        "price_history",
        "pricebook_by_symbol",
        "rate_limit_status",
        "referrals",
        "schwab_account",
        "schwab_account_balances",
        "schwab_account_numbers",
        "schwab_accounts",
        "schwab_get_order",
        "schwab_instrument",
        "schwab_option_chain",
        "schwab_option_chain_by_expiration",
        "schwab_option_expirations",
        "schwab_options_positions",
        "schwab_orders",
        "schwab_portfolio",
        "schwab_price_history",
        "schwab_quote",
        "schwab_quotes",
        "schwab_search_instruments",
        "search_stocks_tool",
        "security_profile",
        "session_status",
        "stock_earnings",
        "stock_events",
        "stock_info",
        "stock_level2_data",
        "stock_loan_payments",
        "stock_news",
        "stock_orders",
        "stock_price",
        "stock_quote_by_id",
        "stock_ratings",
        "stock_splits",
        "stocks_by_tag",
        "subscription_fees",
        "top_100_stocks",
        "top_movers",
        "top_movers_sp500",
        "total_dividends",
        "user_profile",
        "watchlist_by_name",
        "watchlist_performance",
    }
)


def _mcp_log_value(value: object) -> str:
    if value is None:
        return "null"
    return str(value)


def _log_mcp_request(method: object, request_id: object) -> None:
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "MCP request received method=%s request_id=%s",
            _mcp_log_value(method),
            _mcp_log_value(request_id),
        )


def _mcp_json_response(
    response_data: dict[str, Any],
    *,
    status_code: int,
    method: object,
    request_id: object,
    outcome: str,
    error_code: int | None = None,
    error_type: str | None = None,
) -> Response:
    content = json.dumps(response_data).encode()
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            (
                "MCP response sent method=%s request_id=%s outcome=%s "
                "status_code=%s error_code=%s error_type=%s response_bytes=%s"
            ),
            _mcp_log_value(method),
            _mcp_log_value(request_id),
            outcome,
            status_code,
            _mcp_log_value(error_code),
            _mcp_log_value(error_type),
            len(content),
        )
    return Response(
        content=content,
        status_code=status_code,
        headers={"content-type": "application/json"},
    )


def is_loopback_host(host: str) -> bool:
    """Return True if ``host`` only accepts connections from the local machine."""
    return host in LOOPBACK_HOSTS


def _require_session_manager() -> Any:
    """Return session manager or raise 503 when unavailable."""
    session_manager = get_session_manager()
    if session_manager is None:
        raise HTTPException(status_code=503, detail="Session manager unavailable")
    return session_manager


def _require_metrics_collector() -> Any:
    """Return metrics collector or raise 503 when unavailable."""
    metrics_collector = get_metrics_collector()
    if metrics_collector is None:
        raise HTTPException(status_code=503, detail="Metrics collector unavailable")
    return metrics_collector


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Require ``Authorization: Bearer <api_key>`` on protected endpoints.

    No-op when ``api_key`` is None — used for loopback-only deployments where
    network-level isolation is the trust boundary.
    """

    def __init__(self, app: Any, api_key: str | None) -> None:
        super().__init__(app)
        self.api_key = api_key

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        if self.api_key and request.url.path in PROTECTED_PATHS:
            auth_header = request.headers.get("authorization", "")
            expected = f"Bearer {self.api_key}"
            if not secrets.compare_digest(auth_header, expected):
                logger.warning(
                    f"Unauthorized request to {request.url.path} from "
                    f"{request.client.host if request.client else 'unknown'}"
                )
                return JSONResponse(
                    status_code=401,
                    content={"error": "Unauthorized"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
        return await call_next(request)  # type: ignore[no-any-return]


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware to handle request timeouts"""

    def __init__(self, app: Any, timeout: float = 120.0) -> None:
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except TimeoutError:
            logger.warning(f"Request timeout after {self.timeout}s: {request.url}")
            return JSONResponse(
                status_code=408,
                content={"error": "Request timeout", "timeout": self.timeout},
            )


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for security enhancements"""

    def __init__(self, app: Any, allowed_origins: list[str] | None = None) -> None:
        super().__init__(app)
        self.allowed_origins = allowed_origins or [
            "http://localhost:*",
            "https://localhost:*",
        ]

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        # Origin validation for non-local requests
        origin = request.headers.get("origin")
        if origin and not self._is_allowed_origin(origin):
            logger.warning(f"Blocked request from unauthorized origin: {origin}")
            return JSONResponse(
                status_code=403,
                content={"error": "Forbidden origin"},
            )

        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        return response  # type: ignore[no-any-return]

    def _is_allowed_origin(self, origin: str) -> bool:
        """Check if origin is allowed"""
        # For local development, allow localhost origins
        if "localhost" in origin or "127.0.0.1" in origin:
            return True

        for allowed in self.allowed_origins:
            if origin.startswith(allowed.replace("*", "")):
                return True

        return False


def create_http_server(
    mcp_server: FastMCP,
    api_key: str | None = None,
    allow_trading: bool = False,
) -> FastAPI:
    """Create FastAPI server with MCP integration and enhancements.

    Args:
        mcp_server: The FastMCP server whose tools should be exposed over HTTP.
        api_key: When set, requests to :data:`PROTECTED_PATHS` must carry an
            ``Authorization: Bearer <api_key>`` header. Required when the
            server is reachable from non-loopback interfaces.
        allow_trading: When False, HTTP ``tools/call`` requests may invoke only
            the known read-only tool registrations.
    """

    def _is_tool_allowed(tool_name: str | None) -> bool:
        """Allow only read-only tools unless trading access is explicitly enabled."""
        if not tool_name:
            return False
        if allow_trading:
            return True
        return tool_name in READ_ONLY_HTTP_TOOL_NAMES

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Lifespan context manager for startup/shutdown"""
        logger.info("Starting HTTP MCP server")

        # Initialize rate limiter and session manager
        get_rate_limiter()
        get_session_manager()
        app.state.tool_docs_payload = await build_tool_docs_payload(mcp_server)

        yield

        logger.info("Shutting down HTTP MCP server")
        # Cleanup session manager
        session_manager = get_session_manager()
        if session_manager is not None:
            try:
                await session_manager.logout()
            except Exception:
                logger.warning(
                    "Logout failed during shutdown; session state already cleared"
                )

    app = FastAPI(
        title="Open Stocks MCP Server",
        description="Model Context Protocol server for stock market data",
        version=__version__,
        lifespan=lifespan,
    )
    default_openapi = app.openapi

    def custom_openapi() -> dict[str, Any]:
        """Merge MCP tool docs into OpenAPI so /docs exposes the full tool registry."""
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = default_openapi()
        payload = getattr(app.state, "tool_docs_payload", None)
        if payload is None:
            payload = build_tool_docs_payload_from_snapshot(mcp_server)
        schema.setdefault("paths", {}).update(build_tool_openapi_paths(payload))
        app.openapi_schema = schema
        return schema

    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost",
            "https://localhost",
            "http://127.0.0.1",
            "https://127.0.0.1",
        ],
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    timeout_config = load_config().timeout
    request_timeout = (
        timeout_config.request_timeout_seconds if timeout_config is not None else 120.0
    )
    app.add_middleware(TimeoutMiddleware, timeout=request_timeout)
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(BearerAuthMiddleware, api_key=api_key)

    # Health check endpoints
    @app.get("/health")
    async def health_check() -> dict[str, Any]:
        """Health check endpoint"""
        try:
            _require_session_manager()
            metrics_collector = _require_metrics_collector()
            health_service = get_health_service()
            health_status = await health_service.get_status()
            metrics = await metrics_collector.get_metrics()

            # The health service snapshot provides status, components, and timestamp.
            # We preserve HTTP metadata: version and transport.
            return {
                "status": health_status["status"],
                "components": health_status["components"],
                "broker_health": metrics.get("broker_health", {}),
                "account_health": metrics.get("account_health", {}),
                "circuit_breaker": get_broker_circuit_breaker().snapshot(),
                "timestamp": health_status.get("timestamp", time.time()),
                "version": __version__,
                "transport": "http",
                "active_alerts": metrics.get("active_alerts", []),
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=503, detail="Service unhealthy") from e

    @app.get("/status")
    async def server_status() -> dict[str, Any]:
        """Detailed server status endpoint"""
        try:
            metrics_collector = _require_metrics_collector()
            metrics = await metrics_collector.get_metrics()

            rate_limiter = get_rate_limiter()
            rate_stats = rate_limiter.get_stats()

            session_manager = _require_session_manager()
            session_info = session_manager.get_session_info()

            return {
                "server": {
                    "status": "running",
                    "version": __version__,
                    "transport": "http",
                    "timestamp": time.time(),
                },
                "session": session_info,
                "rate_limiting": rate_stats,
                "circuit_breaker": get_broker_circuit_breaker().snapshot(),
                "metrics": metrics,
                "broker_health": metrics.get("broker_health", {}),
                "account_health": metrics.get("account_health", {}),
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            raise HTTPException(status_code=500, detail="Status check failed") from e

    @app.get("/")
    async def root() -> dict[str, Any]:
        """Root endpoint with server information"""
        return {
            "name": "Open Stocks MCP Server",
            "version": __version__,
            "transport": "http",
            "endpoints": {
                "mcp": "/mcp",
                "sse": "/sse",
                "health": "/health",
                "status": "/status",
                "metrics": "/metrics",
            },
            "documentation": "/docs",
        }

    @app.get("/info")
    async def info() -> dict[str, Any]:
        """Info endpoint (alias for root)"""
        return await root()

    # Session management endpoints
    @app.post("/session/refresh")
    async def refresh_session() -> dict[str, Any]:
        """Refresh authentication session"""
        try:
            session_manager = _require_session_manager()
            success = await session_manager.ensure_authenticated()

            if success:
                session_info = session_manager.get_session_info()
                return {"status": "success", "session": session_info}
            else:
                raise HTTPException(status_code=401, detail="Authentication failed")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Session refresh failed: {e}")
            raise HTTPException(status_code=500, detail="Session refresh failed") from e

    @app.get("/tools")
    async def list_tools() -> dict[str, Any]:
        """List available MCP tools"""
        try:
            # Import here to avoid circular imports
            from open_stocks_mcp.tools.robinhood_tools import list_available_tools

            tools = await list_available_tools(mcp_server)
            if not isinstance(tools, dict) or "error" in tools or "result" not in tools:
                logger.error(
                    "list_available_tools returned an unexpected or error response"
                )
                raise HTTPException(status_code=500, detail="Failed to list tools")
            return tools
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            raise HTTPException(status_code=500, detail="Failed to list tools") from e

    @app.get("/tools/docs")
    async def tools_docs() -> dict[str, Any]:
        """Return MCP tool docs metadata from the live registry."""
        try:
            payload = await build_tool_docs_payload(mcp_server)
            tools = [
                {"name": t["name"], "description": t["description"]}
                for t in payload["result"]["tools"]
            ]
            return {"result": {"tools": tools, "count": payload["result"]["count"]}}
        except Exception as e:
            logger.error(f"Failed to generate tool docs payload: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to build tool docs"
            ) from e

    @app.get("/metrics")
    async def metrics() -> Response:
        """Prometheus metrics endpoint (no auth required)."""
        try:
            metrics_collector = _require_metrics_collector()
            content = await metrics_collector.format_prometheus_metrics()
            return Response(
                content=content,
                media_type="text/plain; version=0.0.4; charset=utf-8",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to render metrics: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to render metrics"
            ) from e

    # Mount the MCP HTTP endpoints
    # Create a simple MCP endpoint that handles JSON-RPC directly
    @app.post("/mcp")
    async def mcp_endpoint(request: Request) -> Response:
        """Handle MCP JSON-RPC requests directly"""
        try:
            # Get the request body
            body = await request.body()

            if len(body) > MAX_MCP_REQUEST_BODY_SIZE:
                return _mcp_json_response(
                    {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": "Request body too large",
                        },
                        "id": None,
                    },
                    status_code=413,
                    method=None,
                    request_id=None,
                    outcome="error",
                    error_code=-32700,
                    error_type="body_too_large",
                )

            # Parse the JSON-RPC request
            try:
                json_request = json.loads(body.decode())
            except json.JSONDecodeError:
                return _mcp_json_response(
                    {
                        "jsonrpc": "2.0",
                        "error": {"code": -32700, "message": "Parse error"},
                        "id": None,
                    },
                    status_code=400,
                    method=None,
                    request_id=None,
                    outcome="error",
                    error_code=-32700,
                    error_type="parse_error",
                )

            # Handle different MCP methods
            method = json_request.get("method")
            request_id = json_request.get("id")
            params = json_request.get("params", {})
            _log_mcp_request(method, request_id)

            try:
                result: dict[str, Any]
                if method == "initialize":
                    # Return server capabilities
                    result = {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {},
                            "resources": {},
                            "prompts": {},
                            "logging": {},
                        },
                        "serverInfo": {
                            "name": "Open Stocks MCP",
                            "version": __version__,
                        },
                    }
                elif method == "tools/list":
                    # Use FastMCP's built-in list_tools method
                    tools_list = await mcp_server.list_tools()

                    # Convert Tool objects to MCP protocol format
                    serialized_tools = []
                    for tool in tools_list:
                        # Convert Tool object to dictionary format expected by MCP
                        tool_dict = {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema.model_dump()
                            if hasattr(tool.inputSchema, "model_dump")
                            else tool.inputSchema,
                        }
                        serialized_tools.append(tool_dict)

                    result = {"tools": serialized_tools}

                elif method == "tools/call":
                    # Use FastMCP's built-in call_tool method
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})

                    if not tool_name:
                        return _mcp_json_response(
                            {
                                "jsonrpc": "2.0",
                                "error": {
                                    "code": -32602,
                                    "message": "Invalid params: missing 'name'",
                                },
                                "id": request_id,
                            },
                            status_code=200,
                            method=method,
                            request_id=request_id,
                            outcome="error",
                            error_code=-32602,
                            error_type="invalid_params",
                        )

                    if not _is_tool_allowed(tool_name):
                        logger.warning(
                            "Blocked MCP tool call in read-only mode: %s", tool_name
                        )
                        return _mcp_json_response(
                            {
                                "jsonrpc": "2.0",
                                "error": {
                                    "code": -32600,
                                    "message": (
                                        "Tool is not allowed in read-only mode. "
                                        "Enable --allow-trading to permit mutating tools."
                                    ),
                                },
                                "id": request_id,
                            },
                            status_code=403,
                            method=method,
                            request_id=request_id,
                            outcome="error",
                            error_code=-32600,
                            error_type="forbidden_tool",
                        )

                    # Record duration and success/failure for tool calls only.
                    start = time.perf_counter()
                    metrics_collector = _require_metrics_collector()
                    try:
                        tool_result = await mcp_server.call_tool(tool_name, arguments)
                    except Exception as exc:
                        duration = time.perf_counter() - start
                        await metrics_collector.record_api_call(
                            tool_name=tool_name,
                            duration=duration,
                            success=False,
                            error_type=type(exc).__name__,
                        )
                        raise

                    # Convert CallToolResult to MCP protocol format
                    if hasattr(tool_result, "content"):
                        # Convert content objects to dictionaries
                        content_list = []
                        for content_item in tool_result.content:
                            if hasattr(content_item, "model_dump"):
                                content_list.append(content_item.model_dump())
                            elif hasattr(content_item, "type") and hasattr(
                                content_item, "text"
                            ):
                                content_list.append(
                                    {
                                        "type": content_item.type,
                                        "text": content_item.text,
                                    }
                                )
                            else:
                                # Fallback to string representation
                                content_list.append(
                                    {"type": "text", "text": str(content_item)}
                                )

                        result = {"content": content_list}

                        # Add isError if present
                        if hasattr(tool_result, "isError"):
                            result["isError"] = tool_result.isError
                    else:
                        # Fallback to string representation
                        result = {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(
                                        tool_result, default=str, indent=2
                                    ),
                                }
                            ]
                        }

                    duration = time.perf_counter() - start
                    is_error = bool(result.get("isError", False))
                    await metrics_collector.record_api_call(
                        tool_name=tool_name,
                        duration=duration,
                        success=not is_error,
                        error_type="ToolExecutionError" if is_error else None,
                    )

                elif method == "notifications/initialized":
                    # Handle initialization notification (no response needed for notifications)
                    logger.info("Client initialization notification received")
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(
                            "MCP response sent method=%s request_id=%s outcome=%s "
                            "status_code=%s error_code=%s error_type=%s "
                            "response_bytes=%s",
                            _mcp_log_value(method),
                            _mcp_log_value(request_id),
                            "success",
                            200,
                            "null",
                            "null",
                            0,
                        )
                    return Response(status_code=200)

                else:
                    return _mcp_json_response(
                        {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32601,
                                "message": f"Method not found: {method}",
                            },
                            "id": request_id,
                        },
                        status_code=200,
                        method=method,
                        request_id=request_id,
                        outcome="error",
                        error_code=-32601,
                        error_type="method_not_found",
                    )

                # Return successful response
                response_data = {"jsonrpc": "2.0", "result": result, "id": request_id}

                return _mcp_json_response(
                    response_data,
                    status_code=200,
                    method=method,
                    request_id=request_id,
                    outcome="success",
                )

            except Exception as e:
                logger.error(f"MCP method '{method}' failed: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": str(e)},
                    "id": request_id,
                }
                return _mcp_json_response(
                    error_response,
                    status_code=500,
                    method=method,
                    request_id=request_id,
                    outcome="error",
                    error_code=-32603,
                    error_type=type(e).__name__,
                )

        except Exception as e:
            logger.error(f"MCP endpoint error: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Internal error: {e!s}"},
                "id": None,
            }
            return _mcp_json_response(
                error_response,
                status_code=500,
                method=None,
                request_id=None,
                outcome="error",
                error_code=-32603,
                error_type=type(e).__name__,
            )

    # SSE endpoint for server-sent events
    @app.get("/sse")
    async def sse_endpoint(request: Request) -> Response:
        """Server-Sent Events endpoint for MCP streaming"""
        from sse_starlette import EventSourceResponse

        async def event_generator() -> AsyncGenerator[dict[str, Any], None]:
            """Generate SSE events"""
            try:
                # Send initial connection event
                yield {
                    "event": "connected",
                    "data": {
                        "server": "Open Stocks MCP Server",
                        "version": __version__,
                        "timestamp": time.time(),
                    },
                }

                # Keep connection alive with periodic heartbeat
                while True:
                    if await request.is_disconnected():
                        logger.info("SSE client disconnected")
                        break

                    # Send heartbeat every 30 seconds
                    yield {
                        "event": "heartbeat",
                        "data": {"timestamp": time.time()},
                    }
                    await asyncio.sleep(30)

            except asyncio.CancelledError:
                logger.info("SSE connection cancelled")
            except Exception as e:
                logger.error(f"SSE error: {e}")
                yield {
                    "event": "error",
                    "data": {"error": str(e)},
                }

        return EventSourceResponse(event_generator())

    app.openapi = custom_openapi  # type: ignore[method-assign]
    return app


async def run_http_server(
    mcp_server: FastMCP,
    host: str = "127.0.0.1",
    port: int = 3000,
    api_key: str | None = None,
    allow_trading: bool = False,
) -> None:
    """Run the HTTP server with the MCP server mounted.

    When ``host`` is not a loopback address, ``api_key`` must be provided so
    bearer-token authentication is enforced on :data:`PROTECTED_PATHS`. The
    server refuses to start otherwise — exposing the MCP endpoint to the
    network without auth would let any reachable host invoke trading tools
    against an authenticated broker session.
    """
    import uvicorn

    if not is_loopback_host(host) and not api_key:
        raise RuntimeError(
            f"Refusing to bind HTTP MCP transport to non-loopback host '{host}' "
            "without an API key. Either bind to 127.0.0.1/localhost for "
            "loopback-only access, or set --api-key (or the MCP_API_KEY "
            "environment variable) to require bearer-token auth on the "
            "/mcp endpoint."
        )

    # Configure MCP server for HTTP
    mcp_server.settings.host = host
    mcp_server.settings.port = port

    # Create the FastAPI app with our enhancements
    app = create_http_server(
        mcp_server,
        api_key=api_key,
        allow_trading=allow_trading,
    )

    auth_status = "bearer-token auth enabled" if api_key else "no auth (loopback only)"
    logger.info(f"Starting HTTP MCP server on {host}:{port} ({auth_status})")
    logger.info("Available endpoints:")
    logger.info(f"  - MCP JSON-RPC: http://{host}:{port}/mcp")
    logger.info(f"  - SSE Events: http://{host}:{port}/sse")
    logger.info(f"  - Health Check: http://{host}:{port}/health")
    logger.info(f"  - Server Status: http://{host}:{port}/status")
    logger.info(f"  - Metrics: http://{host}:{port}/metrics")
    logger.info(f"  - Tools List: http://{host}:{port}/tools")
    logger.info(f"  - API Documentation: http://{host}:{port}/docs")
    logger.info(
        "  - Tool Authorization Mode: %s",
        "full access" if allow_trading else "read-only allow-list",
    )

    # Configure uvicorn
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
        timeout_keep_alive=30,
        timeout_graceful_shutdown=10,
    )

    server = uvicorn.Server(config)
    await server.serve()
