"""HTTP transport enhancements for the MCP server"""

import asyncio
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware

from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.monitoring import get_metrics_collector
from open_stocks_mcp.tools.rate_limiter import get_rate_limiter
from open_stocks_mcp.tools.session_manager import get_session_manager


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


def create_http_server(mcp_server: FastMCP) -> FastAPI:
    """Create FastAPI server with MCP integration and enhancements"""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Lifespan context manager for startup/shutdown"""
        logger.info("Starting HTTP MCP server")

        # Initialize rate limiter and session manager
        get_rate_limiter()
        get_session_manager()

        yield

        logger.info("Shutting down HTTP MCP server")
        # Cleanup session manager
        session_manager = get_session_manager()
        await session_manager.logout()

    app = FastAPI(
        title="Open Stocks MCP Server",
        description="Model Context Protocol server for stock market data",
        version="0.4.0",
        lifespan=lifespan,
    )

    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:*", "https://localhost:*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    app.add_middleware(TimeoutMiddleware, timeout=120.0)
    app.add_middleware(SecurityMiddleware)

    # Health check endpoints
    @app.get("/health")
    async def health_check() -> dict[str, Any]:
        """Health check endpoint"""
        try:
            metrics_collector = get_metrics_collector()
            health_status = await metrics_collector.get_health_status()

            session_manager = get_session_manager()
            session_info = session_manager.get_session_info()

            return {
                "status": "healthy",
                "timestamp": time.time(),
                "version": "0.4.0",
                "transport": "http",
                "session": {
                    "authenticated": session_info.get("authenticated", False),
                    "session_duration": session_info.get("session_duration"),
                },
                "health": health_status,
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=503, detail="Service unhealthy") from e

    @app.get("/status")
    async def server_status() -> dict[str, Any]:
        """Detailed server status endpoint"""
        try:
            metrics_collector = get_metrics_collector()
            metrics = await metrics_collector.get_metrics()

            rate_limiter = get_rate_limiter()
            rate_stats = rate_limiter.get_stats()

            session_manager = get_session_manager()
            session_info = session_manager.get_session_info()

            return {
                "server": {
                    "status": "running",
                    "version": "0.4.0",
                    "transport": "http",
                    "timestamp": time.time(),
                },
                "session": session_info,
                "rate_limiting": rate_stats,
                "metrics": metrics,
            }
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            raise HTTPException(status_code=500, detail="Status check failed") from e

    @app.get("/")
    async def root() -> dict[str, Any]:
        """Root endpoint with server information"""
        return {
            "name": "Open Stocks MCP Server",
            "version": "0.4.0",
            "transport": "http",
            "endpoints": {
                "mcp": "/mcp",
                "sse": "/sse",
                "health": "/health",
                "status": "/status",
            },
            "documentation": "/docs",
        }

    # Session management endpoints
    @app.post("/session/refresh")
    async def refresh_session() -> dict[str, Any]:
        """Refresh authentication session"""
        try:
            session_manager = get_session_manager()
            success = await session_manager.ensure_authenticated()

            if success:
                session_info = session_manager.get_session_info()
                return {"status": "success", "session": session_info}
            else:
                raise HTTPException(status_code=401, detail="Authentication failed")
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
            return tools
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            raise HTTPException(status_code=500, detail="Failed to list tools") from e

    # Mount the MCP server apps
    mcp_server.settings.host = "0.0.0.0"  # Allow external connections in HTTP mode

    # Mount the MCP HTTP endpoints
    app.mount("/mcp", mcp_server.streamable_http_app)  # type: ignore[arg-type]
    app.mount("/sse", mcp_server.sse_app)  # type: ignore[arg-type]

    return app


async def run_http_server(
    mcp_server: FastMCP,
    host: str = "localhost",
    port: int = 3000,
) -> None:
    """Run the HTTP server with the MCP server mounted"""
    import uvicorn

    # Configure MCP server for HTTP
    mcp_server.settings.host = host
    mcp_server.settings.port = port

    # Create the FastAPI app with our enhancements
    app = create_http_server(mcp_server)

    logger.info(f"Starting HTTP MCP server on {host}:{port}")
    logger.info("Available endpoints:")
    logger.info(f"  - MCP JSON-RPC: http://{host}:{port}/mcp")
    logger.info(f"  - SSE Events: http://{host}:{port}/sse")
    logger.info(f"  - Health Check: http://{host}:{port}/health")
    logger.info(f"  - Server Status: http://{host}:{port}/status")
    logger.info(f"  - Tools List: http://{host}:{port}/tools")
    logger.info(f"  - API Documentation: http://{host}:{port}/docs")

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
