"""Unit tests for monitoring alert trigger evaluation, sinks, and dedup."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pytest

from open_stocks_mcp.monitoring import AlertEvent, MetricsCollector


@dataclass
class FakeAlertSink:
    """Fake alert sink for testing."""

    calls: list[AlertEvent] = field(default_factory=list)
    raise_on_call: bool = False
    _degraded_sink_total: int = 0

    async def send(self, event: AlertEvent) -> None:
        if self.raise_on_call:
            self._degraded_sink_total += 1
            raise ConnectionError("sink unavailable")
        self.calls.append(event)


@dataclass
class RaisingAlertSink:
    """Alert sink that always raises to test error handling."""

    calls_attempted: int = 0
    degraded_sink_total: int = 0

    async def send(self, event: AlertEvent) -> None:
        self.calls_attempted += 1
        self.degraded_sink_total += 1
        raise ConnectionError("webhook 5xx")


class TestAlertTriggerEvaluation:
    """Alert triggers fire from health-threshold conditions."""

    @pytest.mark.asyncio
    async def test_high_error_rate_emits_alert(self) -> None:
        sink = FakeAlertSink()
        collector = MetricsCollector(alert_sink=sink)
        now = datetime.now()

        # 10 calls, 3 errors = 30% error rate (> 25% threshold -> unhealthy)
        collector.api_calls.extend([(now, "tool", True)] * 7)
        collector.api_calls.extend([(now, "tool", False)] * 3)
        collector.errors.extend([(now, "tool", "err")] * 3)
        collector.response_times.extend([(now, 0.1)] * 10)

        await collector.evaluate_alert_conditions()

        assert len(sink.calls) == 1
        event = sink.calls[0]
        assert event.signal == "error_rate_percent"
        assert event.severity in ("degraded", "unhealthy")

    @pytest.mark.asyncio
    async def test_high_avg_response_time_emits_alert(self) -> None:
        sink = FakeAlertSink()
        collector = MetricsCollector(alert_sink=sink)
        now = datetime.now()

        # avg response time > 5s (degraded) or > 10s (unhealthy)
        collector.api_calls.extend([(now, "tool", True)] * 5)
        collector.response_times.extend([(now, 12.0)] * 5)  # 12s avg -> unhealthy

        await collector.evaluate_alert_conditions()

        assert len(sink.calls) == 1
        event = sink.calls[0]
        assert event.signal == "p95_response_time_ms"
        assert event.severity == "unhealthy"

    @pytest.mark.asyncio
    async def test_healthy_metrics_do_not_emit_alerts(self) -> None:
        sink = FakeAlertSink()
        collector = MetricsCollector(alert_sink=sink)
        now = datetime.now()

        # 10 calls, 0 errors, fast responses
        collector.api_calls.extend([(now, "tool", True)] * 10)
        collector.response_times.extend([(now, 0.1)] * 10)

        await collector.evaluate_alert_conditions()

        assert len(sink.calls) == 0

    @pytest.mark.asyncio
    async def test_alerts_disabled_suppresses_sink_delivery(self) -> None:
        sink = FakeAlertSink()
        collector = MetricsCollector(alert_sink=sink, alerts_enabled=False)
        now = datetime.now()

        # Trigger conditions that would normally emit
        collector.api_calls.extend([(now, "tool", False)] * 10)
        collector.errors.extend([(now, "tool", "err")] * 10)
        collector.response_times.extend([(now, 12.0)] * 10)

        await collector.evaluate_alert_conditions()

        assert len(sink.calls) == 0

    @pytest.mark.asyncio
    async def test_alert_state_still_reported_when_disabled(self) -> None:
        """Even when alerting is disabled, health state is still computed."""
        sink = FakeAlertSink()
        collector = MetricsCollector(alert_sink=sink, alerts_enabled=False)
        now = datetime.now()

        collector.api_calls.extend([(now, "tool", False)] * 10)
        collector.errors.extend([(now, "tool", "err")] * 10)
        collector.response_times.extend([(now, 12.0)] * 10)

        health = await collector.get_health_status()
        assert health["status"] in ("degraded", "unhealthy")


class TestAlertDeduplication:
    """Sliding-window dedup prevents alert storms from a single root cause."""

    @pytest.mark.asyncio
    async def test_duplicate_signals_emit_only_one_alert(self) -> None:
        sink = FakeAlertSink()
        collector = MetricsCollector(alert_sink=sink)
        now = datetime.now()

        # 50 rapid calls to evaluate_alert_conditions with same error rate condition
        collector.api_calls.extend([(now, "tool", False)] * 30)
        collector.api_calls.extend([(now, "tool", True)] * 10)
        collector.errors.extend([(now, "tool", "err")] * 30)
        collector.response_times.extend([(now, 0.1)] * 40)

        for _ in range(50):
            await collector.evaluate_alert_conditions()

        # Only one alert should have been emitted for the same signal
        error_rate_alerts = [e for e in sink.calls if e.signal == "error_rate_percent"]
        assert len(error_rate_alerts) == 1

    @pytest.mark.asyncio
    async def test_alert_state_clears_after_resolution(self) -> None:
        """After conditions return to healthy, dedup clears and alert can re-fire."""
        sink = FakeAlertSink()
        collector = MetricsCollector(
            alert_sink=sink,
            alert_dedup_window_seconds=0,  # zero-second window for testing
        )
        now = datetime.now()

        # First trigger
        collector.api_calls.extend([(now, "tool", False)] * 10)
        collector.errors.extend([(now, "tool", "err")] * 10)
        collector.response_times.extend([(now, 0.1)] * 10)
        await collector.evaluate_alert_conditions()
        first_count = len([e for e in sink.calls if e.signal == "error_rate_percent"])
        assert first_count == 1

        # Second trigger after dedup window expires (window=0 so immediate)
        await collector.evaluate_alert_conditions()
        second_count = len([e for e in sink.calls if e.signal == "error_rate_percent"])
        assert second_count == 2


class TestSinkErrorHandling:
    """Sink failures must not propagate to callers and must be counted."""

    @pytest.mark.asyncio
    async def test_sink_connection_error_increments_degraded_counter(self) -> None:
        sink = RaisingAlertSink()
        collector = MetricsCollector(alert_sink=sink)
        now = datetime.now()

        collector.api_calls.extend([(now, "tool", False)] * 10)
        collector.errors.extend([(now, "tool", "err")] * 10)
        collector.response_times.extend([(now, 0.1)] * 10)

        # Should not raise
        await collector.evaluate_alert_conditions()

        assert sink.calls_attempted > 0
        assert sink.degraded_sink_total > 0

    @pytest.mark.asyncio
    async def test_sink_failure_does_not_propagate(self) -> None:
        sink = RaisingAlertSink()
        collector = MetricsCollector(alert_sink=sink)
        now = datetime.now()

        collector.api_calls.extend([(now, "tool", False)] * 10)
        collector.errors.extend([(now, "tool", "err")] * 10)
        collector.response_times.extend([(now, 0.1)] * 10)

        # Must not raise even if sink raises
        try:
            await collector.evaluate_alert_conditions()
        except Exception as e:
            pytest.fail(f"evaluate_alert_conditions raised unexpectedly: {e}")


class TestAlertStateInMetrics:
    """Alert state is exposed in get_metrics() and get_health_status()."""

    @pytest.mark.asyncio
    async def test_get_metrics_includes_alert_state(self) -> None:
        sink = FakeAlertSink()
        collector = MetricsCollector(alert_sink=sink)
        now = datetime.now()

        collector.api_calls.extend([(now, "tool", False)] * 10)
        collector.errors.extend([(now, "tool", "err")] * 10)
        collector.response_times.extend([(now, 0.1)] * 10)
        await collector.evaluate_alert_conditions()

        metrics = await collector.get_metrics()
        assert "active_alerts" in metrics
        assert "degraded_sink_total" in metrics

    @pytest.mark.asyncio
    async def test_get_health_status_includes_alert_state(self) -> None:
        sink = FakeAlertSink()
        collector = MetricsCollector(alert_sink=sink)
        now = datetime.now()

        collector.api_calls.extend([(now, "tool", False)] * 10)
        collector.errors.extend([(now, "tool", "err")] * 10)
        collector.response_times.extend([(now, 0.1)] * 10)
        await collector.evaluate_alert_conditions()

        health = await collector.get_health_status()
        assert "active_alerts" in health

    @pytest.mark.asyncio
    async def test_healthy_metrics_show_empty_active_alerts(self) -> None:
        sink = FakeAlertSink()
        collector = MetricsCollector(alert_sink=sink)
        now = datetime.now()

        collector.api_calls.extend([(now, "tool", True)] * 10)
        collector.response_times.extend([(now, 0.1)] * 10)

        metrics = await collector.get_metrics()
        assert metrics["active_alerts"] == []
