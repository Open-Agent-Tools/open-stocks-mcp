"""Unit tests for monitoring metrics and health thresholds."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock

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
async def test_get_health_status_response_time_thresholds_map_correctly() -> None:
    collector = MetricsCollector()
    now = datetime.now()

    collector.api_calls.extend([(now, "tool", True) for _ in range(20)])
    collector.response_times.extend([(now, 6.0) for _ in range(20)])
    degraded = await collector.get_health_status()
    assert degraded["status"] == "degraded"

    collector.response_times.clear()
    collector.response_times.extend([(now, 12.0) for _ in range(20)])
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


@pytest.mark.asyncio
async def test_metrics_include_broker_and_account_health() -> None:
    collector = MetricsCollector(window_size_minutes=5)
    await collector.record_broker_operation(
        broker="robinhood",
        account_id="acct-1",
        operation="positions",
        success=True,
        duration_ms=10.0,
    )
    await collector.record_broker_operation(
        broker="robinhood",
        account_id="acct-1",
        operation="positions",
        success=False,
        duration_ms=11.0,
        failure_class="authentication",
        error_type="AuthenticationError",
    )
    await collector.record_broker_operation(
        broker="schwab",
        account_id="acct-2",
        operation="quote",
        success=False,
        duration_ms=12.0,
        failure_class="client_pool",
        error_type="PoolTimeout",
    )

    metrics = await collector.get_metrics()
    assert "broker_health" in metrics
    assert "account_health" in metrics
    assert metrics["broker_health"]["robinhood"]["total"] == 2
    assert metrics["broker_health"]["robinhood"]["errors"] == 1
    assert metrics["broker_health"]["schwab"]["failure_classes"]["client_pool"] == 1
    assert (
        metrics["account_health"]["robinhood"]["acct-1"]["failure_classes"][
            "authentication"
        ]
        == 1
    )


@pytest.mark.asyncio
async def test_health_transition_alert_emits_once_for_same_state() -> None:
    hook = AsyncMock()
    collector = MetricsCollector(
        alerts_enabled=True,
        alert_hooks=[hook],
        error_rate_degraded_threshold=10.0,
        error_rate_unhealthy_threshold=25.0,
    )
    now = datetime.now()
    collector.api_calls.extend([(now, "tool", True) for _ in range(20)])
    collector.errors.extend([(now, "tool", "err") for _ in range(3)])

    await collector.get_health_status()
    await collector.get_health_status()

    health_events = [
        call.args[0]
        for call in hook.await_args_list
        if call.args and call.args[0].alert_type == "health_transition"
    ]
    assert len(health_events) == 1
    assert health_events[0].status == "degraded"


@pytest.mark.asyncio
async def test_threshold_alerts_fire_only_when_breached() -> None:
    hook = AsyncMock()
    collector = MetricsCollector(
        alerts_enabled=True,
        alert_hooks=[hook],
        error_rate_degraded_threshold=10.0,
        error_rate_unhealthy_threshold=25.0,
        latency_p95_threshold_ms=100.0,
    )
    now = datetime.now()
    collector.api_calls.extend([(now, "tool", True) for _ in range(20)])
    collector.response_times.extend([(now, 0.09) for _ in range(20)])
    await collector.evaluate_alert_conditions()
    assert hook.await_count == 0

    collector.errors.extend([(now, "tool", "err") for _ in range(3)])
    collector.response_times.clear()
    collector.response_times.extend([(now, 0.2) for _ in range(20)])
    await collector.evaluate_alert_conditions()

    threshold_events = [
        call.args[0]
        for call in hook.await_args_list
        if call.args and call.args[0].alert_type == "threshold_breach"
    ]
    assert len(threshold_events) == 2
    signals = {event.metadata.get("signal") for event in threshold_events}
    assert signals == {"error_rate_percent", "p95_response_time_ms"}
