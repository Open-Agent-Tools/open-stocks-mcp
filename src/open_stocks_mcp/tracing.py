"""Optional OpenTelemetry tracing support for Open Stocks MCP.

All opentelemetry imports are lazy and guarded so this module is safely
importable without the tracing extras installed, as long as OTEL_ENABLED
remains false (the default).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider

from open_stocks_mcp.config import ServerConfig

_tracer_provider: TracerProvider | None = None


def setup_tracing(config: ServerConfig) -> TracerProvider | None:
    """Configure OpenTelemetry tracing from server config.

    Returns the configured TracerProvider, or None when tracing is disabled.
    Idempotent: returns the existing provider if already initialised.
    """
    global _tracer_provider

    if not config.otel.enabled:
        return None

    if _tracer_provider is not None:
        return _tracer_provider

    try:
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider as _TracerProvider
    except ImportError as exc:
        raise ImportError(
            "opentelemetry-sdk is required when OTEL_ENABLED=true. "
            "Install with: pip install 'open-stocks-mcp[tracing]'"
        ) from exc

    provider = _TracerProvider(
        resource=Resource.create({"service.name": config.otel.service_name})
    )

    if config.otel.exporter_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            exporter = OTLPSpanExporter(endpoint=config.otel.exporter_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except ImportError:
            pass  # OTLP exporter optional — spans still recorded in-process

    _tracer_provider = provider
    return provider


@asynccontextmanager
async def trace_tool_call(tool_name: str) -> AsyncIterator[None]:
    """Async context manager that wraps an MCP tool call in an OTel span.

    No-ops when tracing has not been set up (default when OTEL_ENABLED=false).
    Sets span attributes: tool.name, tool.outcome, and tool.error_type on error.
    """
    if _tracer_provider is None:
        yield
        return

    from opentelemetry.trace import Status, StatusCode

    tracer = _tracer_provider.get_tracer(__name__)
    with tracer.start_as_current_span(tool_name) as span:
        span.set_attribute("tool.name", tool_name)
        try:
            yield
            span.set_attribute("tool.outcome", "success")
        except Exception as exc:
            span.set_attribute("tool.outcome", "error")
            span.set_attribute("tool.error_type", type(exc).__name__)
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR))
            raise
