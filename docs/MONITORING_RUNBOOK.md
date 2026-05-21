# Monitoring Runbook: Open Stocks MCP

This runbook describes the alerting system, supported alerts, configuration, and operator responses for the Open Stocks MCP server.

## Overview

The alerting system evaluates metric thresholds on the rolling window observed by `MetricsCollector` and emits `AlertEvent` objects through a configurable sink. By default, alerting is **disabled** and no events are sent externally. When enabled, alerts fire on high error rate or high average response time, with deduplication to prevent alert storms.

Alert state is always surfaced in monitoring endpoints regardless of whether external delivery is enabled:
- HTTP `GET /health` → `active_alerts` field
- HTTP `GET /status` → `metrics.active_alerts` field
- MCP `metrics_summary` tool → `result.active_alerts` field

---

## Configuration

All configuration is via environment variables. Default values are safe for production with external delivery disabled.

| Variable | Default | Description |
|---|---|---|
| `ALERTS_ENABLED` | `false` | Set to `true` to enable external alert delivery. Alert state in monitoring endpoints is always available regardless of this setting. |
| `ALERT_WEBHOOK_URL` | _(none)_ | Webhook endpoint for alert delivery. Required when `ALERTS_ENABLED=true` and custom sink is implemented. |
| `ALERT_ERROR_RATE_DEGRADED_THRESHOLD` | `10.0` | Error rate % that triggers a `degraded` alert. |
| `ALERT_ERROR_RATE_UNHEALTHY_THRESHOLD` | `25.0` | Error rate % that triggers an `unhealthy` alert. |
| `ALERT_AVG_RESPONSE_TIME_DEGRADED_MS` | `5000.0` | Average response time (ms) that triggers a `degraded` alert. |
| `ALERT_AVG_RESPONSE_TIME_UNHEALTHY_MS` | `10000.0` | Average response time (ms) that triggers an `unhealthy` alert. |
| `ALERT_DEDUP_WINDOW_SECONDS` | `300.0` | Minimum seconds between repeated alerts for the same signal. Prevents alert storms from a single root cause. |

### Example: Enable alerting

```bash
export ALERTS_ENABLED=true
export ALERT_WEBHOOK_URL=https://hooks.example.com/mcp-alerts
export ALERT_DEDUP_WINDOW_SECONDS=300
```

---

## Supported Alerts

### `high_error_rate`

**Trigger**: The rolling-window error rate exceeds a configured threshold.

| Condition | Severity |
|---|---|
| Error rate > `ALERT_ERROR_RATE_DEGRADED_THRESHOLD` (default 10%) | `degraded` |
| Error rate > `ALERT_ERROR_RATE_UNHEALTHY_THRESHOLD` (default 25%) | `unhealthy` |

**Operator response**:
1. Check `/status` → `metrics.error_types` to identify which error class is elevated.
2. If `authentication` errors dominate, call `POST /session/refresh` to force a session re-auth.
3. If `rate_limit` errors dominate, the upstream broker API is throttling. Reduce request frequency or wait for the rate limit window to expire.
4. If `network` errors dominate, check broker API reachability and network connectivity from the container.
5. If the error rate remains elevated after the above, check application logs for stack traces.

---

### `high_avg_response_time`

**Trigger**: The rolling-window average tool response time exceeds a configured threshold.

| Condition | Severity |
|---|---|
| Avg response time > `ALERT_AVG_RESPONSE_TIME_DEGRADED_MS` (default 5000ms) | `degraded` |
| Avg response time > `ALERT_AVG_RESPONSE_TIME_UNHEALTHY_MS` (default 10000ms) | `unhealthy` |

**Operator response**:
1. Check `/status` → `metrics.tool_usage` for per-tool p95/p99 latency to identify slow tools.
2. If a single tool is slow, that broker endpoint may be degraded. Check broker status pages.
3. If all tools are slow, the server or its network path to the broker may be resource-constrained.
4. Check container CPU and memory; if near limits, scale up or reduce concurrent request load.
5. Consider reducing `CACHE_QUOTES_TTL` and `CACHE_ACCOUNT_TTL` to increase cache hit rates and reduce live API calls.

---

## Deduplication

The dedup window (`ALERT_DEDUP_WINDOW_SECONDS`, default 300s) prevents repeated alerts for the same signal within the window. A single auth-expiration or rate-limit event can trigger across many concurrent tool invocations; dedup ensures only one alert event reaches the sink per 5-minute window.

When the window expires and the condition is still met, a new alert is emitted. When conditions return to normal, the signal is removed from `active_alerts`.

---

## Sink Failures

If the alert sink fails (network error, webhook 5xx, timeout), the failure is:
- Caught and never propagated to the caller
- Counted in `degraded_sink_total` (visible in `GET /status` → `metrics.degraded_sink_total`)
- Logged at WARNING level

Monitor `degraded_sink_total` to detect persistent sink delivery problems. If it grows steadily, check `ALERT_WEBHOOK_URL` reachability.

---

## Testing with a Fake Sink

For integration testing without network calls, inject a `FakeAlertSink` directly into `MetricsCollector`:

```python
from dataclasses import dataclass, field
from open_stocks_mcp.monitoring import AlertEvent, MetricsCollector

@dataclass
class FakeAlertSink:
    calls: list[AlertEvent] = field(default_factory=list)

    async def send(self, event: AlertEvent) -> None:
        self.calls.append(event)

sink = FakeAlertSink()
collector = MetricsCollector(
    alert_sink=sink,
    alerts_enabled=True,
    alert_dedup_window_seconds=0,  # instant re-fire for tests
)

# Simulate high error rate
from datetime import datetime
now = datetime.now()
collector.api_calls.extend([(now, "tool", False)] * 10)
collector.errors.extend([(now, "tool", "err")] * 10)
collector.response_times.extend([(now, 0.1)] * 10)

await collector.evaluate_alert_conditions()

assert sink.calls[0].signal == "high_error_rate"
```

Set `alerts_enabled=False` to verify alert state is computed but sink is not called:

```python
collector = MetricsCollector(alert_sink=sink, alerts_enabled=False)
# ... populate metrics ...
await collector.evaluate_alert_conditions()
assert len(sink.calls) == 0  # no delivery
health = await collector.get_health_status()
assert "active_alerts" in health  # state still reported
```

---

## Monitoring Endpoint Reference

### `GET /health`

Returns service health with active alert state:

```json
{
  "status": "degraded",
  "components": { "metrics": {"status": "healthy"}, "session": {"status": "healthy"} },
  "active_alerts": [
    {
      "signal": "high_error_rate",
      "severity": "degraded",
      "message": "High error rate: 15.0%",
      "timestamp": "2026-01-01T00:00:00"
    }
  ],
  "version": "0.6.4",
  "transport": "http"
}
```

### `GET /status`

Returns full server status. Alert state is in `metrics.active_alerts` and `metrics.degraded_sink_total`.

### MCP `metrics_summary` tool

Returns `{"result": { ..., "active_alerts": [...], "degraded_sink_total": 0, ... }}`.

---

## Alert Event Shape

```python
@dataclass
class AlertEvent:
    signal: str       # "high_error_rate" | "high_avg_response_time"
    severity: str     # "degraded" | "unhealthy"
    message: str      # Human-readable description
    timestamp: str    # ISO8601 timestamp of event creation
    metadata: dict    # Signal-specific context (e.g., error_rate_percent)
```
