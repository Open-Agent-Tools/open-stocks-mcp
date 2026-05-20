"""Unit tests for OpenTelemetry tracing support."""

from __future__ import annotations

import pytest

import open_stocks_mcp.tracing as tracing_module
from open_stocks_mcp.config import OtelConfig, ServerConfig, load_config
from open_stocks_mcp.tracing import setup_tracing, trace_tool_call


@pytest.fixture(autouse=True)
def reset_tracer_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset the module-level tracer provider before each test."""
    monkeypatch.setattr(tracing_module, "_tracer_provider", None)


# ---------------------------------------------------------------------------
# Task 1: disabled-by-default behaviour
# ---------------------------------------------------------------------------


def test_otel_disabled_by_default_returns_none() -> None:
    """When OTEL_ENABLED is not set, setup_tracing returns None."""
    config = load_config()
    assert config.otel.enabled is False
    result = setup_tracing(config)
    assert result is None


def test_otel_config_defaults() -> None:
    """OtelConfig has correct defaults."""
    cfg = OtelConfig()
    assert cfg.enabled is False
    assert cfg.service_name == "open-stocks-mcp"
    assert cfg.exporter_endpoint is None


def test_load_config_otel_truthy_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """OTEL_ENABLED accepts common truthy strings case-insensitively."""
    for truthy in ("1", "true", "True", "TRUE", "yes", "YES"):
        monkeypatch.setenv("OTEL_ENABLED", truthy)
        cfg = load_config()
        assert cfg.otel.enabled is True, f"Expected True for OTEL_ENABLED={truthy!r}"


def test_load_config_otel_falsy_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """OTEL_ENABLED treats non-truthy strings as False."""
    for falsy in ("0", "false", "False", "no", ""):
        monkeypatch.setenv("OTEL_ENABLED", falsy)
        cfg = load_config()
        assert cfg.otel.enabled is False, f"Expected False for OTEL_ENABLED={falsy!r}"


def test_load_config_otel_service_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """OTEL_SERVICE_NAME is read from environment."""
    monkeypatch.setenv("OTEL_SERVICE_NAME", "my-custom-service")
    cfg = load_config()
    assert cfg.otel.service_name == "my-custom-service"


def test_load_config_otel_exporter_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """OTEL_EXPORTER_OTLP_ENDPOINT is read from environment."""
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4317")
    cfg = load_config()
    assert cfg.otel.exporter_endpoint == "http://collector:4317"


def test_load_config_otel_exporter_endpoint_empty_is_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty OTEL_EXPORTER_OTLP_ENDPOINT is normalised to None."""
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    cfg = load_config()
    assert cfg.otel.exporter_endpoint is None


async def test_trace_tool_call_noop_when_disabled() -> None:
    """trace_tool_call is a no-op when tracing was not set up."""
    executed = False
    async with trace_tool_call("dummy_tool"):
        executed = True
    assert executed


async def test_trace_tool_call_propagates_exception_when_disabled() -> None:
    """trace_tool_call re-raises exceptions even when tracing is disabled."""
    with pytest.raises(ValueError, match="boom"):
        async with trace_tool_call("dummy_tool"):
            raise ValueError("boom")


# ---------------------------------------------------------------------------
# Task 2: enabled tracing with in-memory exporter (requires opentelemetry-sdk)
# ---------------------------------------------------------------------------


def _require_otel() -> None:
    pytest.importorskip(
        "opentelemetry.sdk.trace",
        reason="opentelemetry-sdk not installed; skipping enabled-tracing tests",
    )


async def test_traced_tool_emits_span_with_attributes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When tracing is enabled, trace_tool_call emits a span with correct attributes."""
    _require_otel()
    from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import-not-found]
    from opentelemetry.sdk.trace.export import (
        SimpleSpanProcessor,  # type: ignore[import-not-found]
    )
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,  # type: ignore[import-not-found]
    )

    monkeypatch.setenv("OTEL_ENABLED", "true")
    provider = setup_tracing(load_config())
    assert provider is not None
    assert isinstance(provider, TracerProvider)

    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    async with trace_tool_call("dummy_tool"):
        pass

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "dummy_tool"
    assert span.attributes is not None
    assert span.attributes["tool.name"] == "dummy_tool"
    assert span.attributes["tool.outcome"] == "success"


async def test_traced_tool_records_error_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On exception, trace_tool_call sets error attributes and re-raises."""
    _require_otel()
    from opentelemetry.sdk.trace.export import (
        SimpleSpanProcessor,  # type: ignore[import-not-found]
    )
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,  # type: ignore[import-not-found]
    )

    monkeypatch.setenv("OTEL_ENABLED", "true")
    provider = setup_tracing(load_config())
    assert provider is not None

    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    with pytest.raises(RuntimeError, match="test error"):
        async with trace_tool_call("failing_tool"):
            raise RuntimeError("test error")

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.attributes is not None
    assert span.attributes["tool.outcome"] == "error"
    assert span.attributes["tool.error_type"] == "RuntimeError"


async def test_setup_tracing_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Calling setup_tracing twice returns the same provider."""
    _require_otel()
    monkeypatch.setenv("OTEL_ENABLED", "true")
    config = load_config()
    provider_a = setup_tracing(config)
    provider_b = setup_tracing(config)
    assert provider_a is provider_b


def test_setup_tracing_sets_service_name_resource(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configured OTEL_SERVICE_NAME is applied to the provider resource."""
    _require_otel()
    monkeypatch.setenv("OTEL_ENABLED", "true")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "custom-service")
    provider = setup_tracing(load_config())
    assert provider is not None
    assert provider.resource.attributes["service.name"] == "custom-service"


def test_setup_tracing_missing_sdk_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """When enabled but SDK not importable, setup_tracing raises ImportError."""
    import builtins
    import sys

    real_import = builtins.__import__

    def _blocking_import(name: str, *args: object, **kwargs: object) -> object:
        if name.startswith("opentelemetry"):
            raise ImportError(f"Mocked missing: {name}")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setenv("OTEL_ENABLED", "true")
    # Remove cached modules so our mock import fires
    cached = [k for k in sys.modules if k.startswith("opentelemetry")]
    for key in cached:
        monkeypatch.delitem(sys.modules, key, raising=False)

    monkeypatch.setattr(builtins, "__import__", _blocking_import)
    config = load_config()
    with pytest.raises(ImportError, match="opentelemetry-sdk is required"):
        setup_tracing(config)


def test_server_config_has_otel_field() -> None:
    """ServerConfig exposes an otel field of type OtelConfig."""
    cfg = ServerConfig()
    assert isinstance(cfg.otel, OtelConfig)
    assert cfg.otel.enabled is False
