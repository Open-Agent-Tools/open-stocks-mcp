"""Unit tests for monitoring metrics and health thresholds."""

from datetime import datetime, timedelta

import pytest

from open_stocks_mcp.monitoring import MetricsCollector


@pytest.mark.asyncio
async def test_get_health_status_thresholds_map_correctly() -> None:
    collector = MetricsCollector()
    now = datetime.now()

    collector.api_calls.extend(
        [
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
            (now, "tool", True),
        ]
    )

    collector.errors.extend([(now, "tool", "err")])
    healthy = await collector.get_health_status()
    assert healthy["status"] == "healthy"

    collector.errors.extend([(now, "tool", "err"), (now, "tool", "err")])
    degraded = await collector.get_health_status()
    assert degraded["status"] == "degraded"

    collector.errors.extend(
        [(now, "tool", "err"), (now, "tool", "err"), (now, "tool", "err")]
    )
    unhealthy = await collector.get_health_status()
    assert unhealthy["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_get_metrics_includes_per_tool_latency_and_throughput() -> None:
    collector = MetricsCollector(window_size_minutes=1)

    await collector.record_api_call("tool_a", 0.10, True)
    await collector.record_api_call("tool_a", 0.20, False, error_type="RuntimeError")
    await collector.record_api_call("tool_a", 0.30, True)
    await collector.record_api_call("tool_b", 0.40, True)

    metrics = await collector.get_metrics()
    tool_usage = metrics["tool_usage"]

    assert "tool_a" in tool_usage
    assert "tool_b" in tool_usage
    assert tool_usage["tool_a"]["calls"] == 3
    assert tool_usage["tool_a"]["success_rate"] == pytest.approx(66.666, rel=1e-2)
    assert tool_usage["tool_a"]["calls_per_minute"] == pytest.approx(3.0)
    assert tool_usage["tool_a"]["p50_response_time_ms"] == 200.0
    assert tool_usage["tool_a"]["p95_response_time_ms"] == 300.0
    assert tool_usage["tool_a"]["p99_response_time_ms"] == 300.0
    assert tool_usage["tool_b"]["calls"] == 1
    assert tool_usage["tool_b"]["calls_per_minute"] == pytest.approx(1.0)
    assert metrics["total_errors"] == 1
    assert metrics["error_types"]["RuntimeError"] == 1


@pytest.mark.asyncio
async def test_prometheus_output_contains_tool_metrics() -> None:
    collector = MetricsCollector(window_size_minutes=1)
    await collector.record_api_call('tool"name\\x', 0.10, True)

    output = await collector.format_prometheus_metrics()

    assert "open_stocks_mcp_tool_calls_total" in output
    assert "open_stocks_mcp_tool_calls_per_minute" in output
    assert "open_stocks_mcp_tool_latency_ms" in output
    assert 'tool="tool\\"name\\\\x"' in output
    assert 'quantile="0.50"' in output
    assert 'quantile="0.95"' in output
    assert 'quantile="0.99"' in output


@pytest.mark.asyncio
async def test_get_metrics_cleans_stale_tool_samples() -> None:
    collector = MetricsCollector(window_size_minutes=1)
    now = datetime.now()
    stale = now - timedelta(minutes=2)

    collector.api_calls.append((stale, "old_tool", True))
    collector.response_times.append((stale, 1.0))
    collector.tool_usage["old_tool"].append((stale, True))
    collector.tool_response_times["old_tool"].append((stale, 1.0))

    await collector.record_api_call("new_tool", 0.05, True)
    metrics = await collector.get_metrics()

    assert metrics["calls_in_window"] == 1
    assert metrics["tool_usage"]["new_tool"]["calls"] == 1
    assert metrics["tool_usage"]["old_tool"]["calls"] == 0
