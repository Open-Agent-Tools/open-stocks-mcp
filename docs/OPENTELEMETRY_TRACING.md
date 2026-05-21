# OpenTelemetry Tracing

OpenTelemetry tracing is disabled by default. Enable it only when you want to export MCP tool-call spans to an OTLP-compatible backend.

## Environment Variables

- `OTEL_ENABLED` (default: `false`)
- `OTEL_SERVICE_NAME` (default: `open-stocks-mcp`)
- `OTEL_EXPORTER_OTLP_ENDPOINT` (optional, for remote export)

## Enable Tracing

```bash
export OTEL_ENABLED=true
export OTEL_SERVICE_NAME=open-stocks-mcp
```

When enabled, each MCP `tools/call` invocation creates a span with:

- `tool.name`
- `tool.outcome` (`success` or `error`)
- `tool.error_type` (error path only)

## Jaeger (OTLP gRPC) Example

Start Jaeger with OTLP enabled and point the server at it:

```bash
export OTEL_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
open-stocks-mcp-server --transport http --port 3001
```

## Grafana Tempo (OTLP gRPC) Example

Use the Tempo OTLP gRPC endpoint:

```bash
export OTEL_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317
open-stocks-mcp-server --transport http --port 3001
```

## Notes

- If `OTEL_ENABLED` is not `true`, tracing is a no-op.
- If no OTLP endpoint is set, spans are still created in-process but are not exported.
