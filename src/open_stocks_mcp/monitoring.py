"""Enhanced monitoring and metrics for the MCP server."""

import asyncio
import math
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any

from open_stocks_mcp.alerting import (
    AlertEvent,
    AlertHook,
    AlertManager,
    AlertSink,
    LogAlertSink,
    WebhookAlertSink,
)
from open_stocks_mcp.logging_config import logger


class MetricsCollector:
    """Collects and tracks metrics for monitoring."""

    def __init__(
        self,
        window_size_minutes: int = 60,
        alerts_enabled: bool = True,
        alert_dedup_window_seconds: float = 300.0,
        alert_hooks: list[AlertHook] | None = None,
        alert_sink: AlertSink | None = None,
        webhook_url: str | None = None,
        error_rate_degraded_threshold: float = 10.0,
        error_rate_unhealthy_threshold: float = 25.0,
        avg_response_time_unhealthy_ms: float = 10000.0,
        latency_p95_threshold_ms: float = 5000.0,
    ):
        """Initialize metrics collector."""
        self.window_size = timedelta(minutes=window_size_minutes)

        # Metrics storage
        self.api_calls: deque[tuple[datetime, str, bool]] = deque()
        self.errors: deque[tuple[datetime, str, str | None]] = deque()
        self.response_times: deque[tuple[datetime, float]] = deque()
        self.tool_usage: dict[str, deque[tuple[datetime, bool]]] = defaultdict(deque)
        self.tool_response_times: dict[str, deque[tuple[datetime, float]]] = (
            defaultdict(deque)
        )
        self.error_types: dict[str, int] = defaultdict(int)
        self.broker_operations: deque[dict[str, Any]] = deque()

        # Counters
        self.total_calls = 0
        self.total_errors = 0
        self.session_refreshes = 0

        # Cache hit/miss counters, keyed by cache name
        self.cache_hits: dict[str, int] = defaultdict(int)
        self.cache_misses: dict[str, int] = defaultdict(int)

        self._lock = asyncio.Lock()

        # Alerting
        self._alerts_enabled = alerts_enabled
        self._alert_dedup_window = timedelta(seconds=alert_dedup_window_seconds)
        sinks: list[AlertSink] = [LogAlertSink()]
        if alert_sink is not None:
            sinks.append(alert_sink)
        if webhook_url:
            sinks.append(WebhookAlertSink(webhook_url))
        self._alert_manager = AlertManager(
            enabled=alerts_enabled, hooks=alert_hooks, sinks=sinks
        )
        self._error_rate_degraded_threshold = error_rate_degraded_threshold
        self._error_rate_unhealthy_threshold = error_rate_unhealthy_threshold
        self._avg_response_time_unhealthy_ms = avg_response_time_unhealthy_ms
        self._latency_p95_threshold_ms = latency_p95_threshold_ms
        # Maps signal -> timestamp of last emission (for dedup)
        self._last_alert_at: dict[str, datetime] = {}
        # Current active alerts keyed by signal name
        self._active_alerts: dict[str, AlertEvent] = {}
        self._last_health_status = "healthy"
        # Counter for sink delivery failures
        self.degraded_sink_total = 0

    async def record_api_call(
        self,
        tool_name: str,
        duration: float,
        success: bool,
        error_type: str | None = None,
    ) -> None:
        """Record an API call metric.

        Args:
            tool_name: Name of the tool called
            duration: Duration of the call in seconds
            success: Whether the call was successful
            error_type: Type of error if failed
        """
        async with self._lock:
            now = datetime.now()

            # Clean old entries
            self._clean_old_entries(now)

            # Record call
            self.api_calls.append((now, tool_name, success))
            self.total_calls += 1

            # Record response time
            self.response_times.append((now, duration))

            # Record tool usage
            self.tool_usage[tool_name].append((now, success))
            self.tool_response_times[tool_name].append((now, duration))

            # Record error if failed
            if not success:
                self.errors.append((now, tool_name, error_type))
                self.total_errors += 1
                if error_type:
                    self.error_types[error_type] += 1

        # Evaluate alert conditions after every recorded call so live traffic
        # drives both `active_alerts` state and sink delivery. Runs outside the
        # lock so `get_metrics()` (which acquires it) does not deadlock.
        try:
            await self.evaluate_alert_conditions()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"Alert evaluation failed: {exc}")

    async def record_session_refresh(self) -> None:
        """Record a session refresh event."""
        async with self._lock:
            self.session_refreshes += 1
            logger.info(f"Session refresh recorded. Total: {self.session_refreshes}")

    async def record_broker_operation(
        self,
        *,
        broker: str,
        account_id: str | None,
        operation: str,
        success: bool,
        duration_ms: float | None = None,
        duration: float | None = None,
        failure_class: str | None = None,
        error_type: str | None = None,
    ) -> None:
        """Record broker/account operation telemetry."""
        async with self._lock:
            now = datetime.now()
            self._clean_old_entries(now)
            duration_ms_val = (
                duration_ms if duration_ms is not None else ((duration or 0.0) * 1000.0)
            )
            self.broker_operations.append(
                {
                    "timestamp": now,
                    "broker": broker,
                    "account_id": account_id or "default",
                    "operation": operation,
                    "success": success,
                    "duration_ms": duration_ms_val,
                    "failure_class": failure_class,
                    "error_type": error_type,
                }
            )

    async def record_cache_hit(self, name: str) -> None:
        """Record a cache hit for the named cache."""
        async with self._lock:
            self.cache_hits[name] += 1

    async def record_cache_miss(self, name: str) -> None:
        """Record a cache miss for the named cache."""
        async with self._lock:
            self.cache_misses[name] += 1

    def _clean_old_entries(self, now: datetime) -> None:
        """Remove entries older than the window size."""
        cutoff = now - self.window_size

        # Clean api_calls
        while self.api_calls and self.api_calls[0][0] < cutoff:
            self.api_calls.popleft()

        # Clean errors
        while self.errors and self.errors[0][0] < cutoff:
            self.errors.popleft()

        # Clean response_times
        while self.response_times and self.response_times[0][0] < cutoff:
            self.response_times.popleft()

        # Clean tool_usage
        for tool_calls in self.tool_usage.values():
            while tool_calls and tool_calls[0][0] < cutoff:
                tool_calls.popleft()
        empty_tools = [t for t, d in self.tool_usage.items() if not d]
        for t in empty_tools:
            del self.tool_usage[t]

        # Clean per-tool response times
        for tool_durations in self.tool_response_times.values():
            while tool_durations and tool_durations[0][0] < cutoff:
                tool_durations.popleft()
        empty_tools = [t for t, d in self.tool_response_times.items() if not d]
        for t in empty_tools:
            del self.tool_response_times[t]

        while (
            self.broker_operations and self.broker_operations[0]["timestamp"] < cutoff
        ):
            self.broker_operations.popleft()

        # Clean alert deduplication map
        dedup_cutoff = now - self._alert_dedup_window
        signals_to_remove = [
            signal
            for signal, last_sent in self._last_alert_at.items()
            if last_sent < dedup_cutoff
        ]
        for signal in signals_to_remove:
            del self._last_alert_at[signal]

    @staticmethod
    def _percentile(samples: list[float], quantile: float) -> float:
        """Return percentile for a sorted sample list."""
        if not samples:
            return 0.0
        rank = max(1, math.ceil(quantile * len(samples)))
        index = min(len(samples) - 1, rank - 1)
        return samples[index]

    @staticmethod
    def _escape_prometheus_label_value(value: str) -> str:
        """Escape a label value according to Prometheus text format."""
        return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')

    async def get_metrics(self) -> dict[str, Any]:
        """Get current metrics summary.

        Returns:
            Dictionary containing metrics summary
        """
        async with self._lock:
            now = datetime.now()
            self._clean_old_entries(now)

            # Calculate metrics
            total_calls_window = len(self.api_calls)
            total_errors_window = len(self.errors)
            error_rate = (
                (total_errors_window / total_calls_window * 100)
                if total_calls_window > 0
                else 0
            )

            # Calculate average response time
            avg_response_time = 0.0
            if self.response_times:
                avg_response_time = sum(t[1] for t in self.response_times) / len(
                    self.response_times
                )

            # Calculate percentiles
            response_times_sorted = (
                sorted(t[1] for t in self.response_times) if self.response_times else []
            )
            p50 = self._percentile(response_times_sorted, 0.50)
            p95 = self._percentile(response_times_sorted, 0.95)
            p99 = self._percentile(response_times_sorted, 0.99)

            # Tool usage stats
            tool_stats = {}
            for tool, calls in self.tool_usage.items():
                successful = sum(1 for _, success in calls if success)
                total = len(calls)
                durations = sorted(
                    duration for _, duration in self.tool_response_times.get(tool, [])
                )
                tool_stats[tool] = {
                    "calls": total,
                    "success_rate": (successful / total * 100.0) if total > 0 else 0.0,
                    "avg_calls_per_minute": (
                        round(total / (self.window_size.total_seconds() / 60), 2)
                        if total > 0
                        else 0.0
                    ),
                    "p50_response_time_ms": round(
                        self._percentile(durations, 0.50) * 1000, 2
                    ),
                    "p95_response_time_ms": round(
                        self._percentile(durations, 0.95) * 1000, 2
                    ),
                    "p99_response_time_ms": round(
                        self._percentile(durations, 0.99) * 1000, 2
                    ),
                }

            cache_hit_rate: dict[str, float] = {}
            for name in set(self.cache_hits) | set(self.cache_misses):
                hits = self.cache_hits.get(name, 0)
                misses = self.cache_misses.get(name, 0)
                total = hits + misses
                cache_hit_rate[name] = (
                    round(hits / total * 100.0, 2) if total > 0 else 0.0
                )

            broker_health: dict[str, dict[str, Any]] = {}
            account_health: dict[str, dict[str, dict[str, Any]]] = {}
            for item in self.broker_operations:
                broker_key = item["broker"]
                acct = str(item["account_id"])
                state = broker_health.setdefault(
                    broker_key,
                    {
                        "total": 0,
                        "success": 0,
                        "errors": 0,
                        "last_error_type": None,
                        "failure_classes": defaultdict(int),
                    },
                )
                state["total"] += 1
                if item["success"]:
                    state["success"] += 1
                else:
                    state["errors"] += 1
                    state["last_error_type"] = item["error_type"]
                    if item["failure_class"]:
                        state["failure_classes"][item["failure_class"]] += 1

                broker_accounts = account_health.setdefault(broker_key, {})
                account_state = broker_accounts.setdefault(
                    acct,
                    {
                        "total": 0,
                        "success": 0,
                        "errors": 0,
                        "last_error_type": None,
                        "failure_classes": defaultdict(int),
                    },
                )
                account_state["total"] += 1
                if item["success"]:
                    account_state["success"] += 1
                else:
                    account_state["errors"] += 1
                    account_state["last_error_type"] = item["error_type"]
                    if item["failure_class"]:
                        account_state["failure_classes"][item["failure_class"]] += 1

            broker_health_out = {}
            for key, state in broker_health.items():
                broker_health_out[key] = {
                    "status": "healthy" if state["errors"] == 0 else "degraded",
                    "total": state["total"],
                    "success": state["success"],
                    "errors": state["errors"],
                    "last_error_type": state["last_error_type"],
                    "failure_classes": dict(state["failure_classes"]),
                }
            account_health_out: dict[str, dict[str, dict[str, Any]]] = {}
            for broker_name, accounts in account_health.items():
                account_health_out[broker_name] = {}
                for account_id_key, state in accounts.items():
                    account_health_out[broker_name][account_id_key] = {
                        "status": "healthy" if state["errors"] == 0 else "degraded",
                        "total": state["total"],
                        "success": state["success"],
                        "errors": state["errors"],
                        "last_error_type": state["last_error_type"],
                        "failure_classes": dict(state["failure_classes"]),
                    }

            return {
                "window_minutes": self.window_size.total_seconds() / 60,
                "total_calls": self.total_calls,
                "total_errors": self.total_errors,
                "calls_in_window": total_calls_window,
                "errors_in_window": total_errors_window,
                "error_rate_percent": round(error_rate, 2),
                "avg_response_time_ms": round(avg_response_time * 1000, 2),
                "p50_response_time_ms": round(p50 * 1000, 2),
                "p95_response_time_ms": round(p95 * 1000, 2),
                "p99_response_time_ms": round(p99 * 1000, 2),
                "session_refreshes": self.session_refreshes,
                "error_types": dict(self.error_types),
                "tool_usage": tool_stats,
                "cache_hits": dict(self.cache_hits),
                "cache_misses": dict(self.cache_misses),
                "cache_hit_rate_percent": cache_hit_rate,
                "broker_health": broker_health_out,
                "account_health": account_health_out,
                "active_alerts": [
                    {
                        "signal": e.signal,
                        "severity": e.severity,
                        "message": e.message,
                        "timestamp": e.timestamp,
                    }
                    for e in self._active_alerts.values()
                ],
                "degraded_sink_total": self.degraded_sink_total,
                "timestamp": now.isoformat(),
            }

    async def format_prometheus_metrics(self) -> str:
        """Return metrics in Prometheus exposition format."""
        metrics = await self.get_metrics()

        lines = [
            "# HELP open_stocks_mcp_total_calls Total API calls observed.",
            "# TYPE open_stocks_mcp_total_calls counter",
            f"open_stocks_mcp_total_calls {metrics['total_calls']}",
            "# HELP open_stocks_mcp_total_errors Total API errors observed.",
            "# TYPE open_stocks_mcp_total_errors counter",
            f"open_stocks_mcp_total_errors {metrics['total_errors']}",
            "# HELP open_stocks_mcp_calls_in_window API calls in rolling window.",
            "# TYPE open_stocks_mcp_calls_in_window gauge",
            f"open_stocks_mcp_calls_in_window {metrics['calls_in_window']}",
            "# HELP open_stocks_mcp_errors_in_window API errors in rolling window.",
            "# TYPE open_stocks_mcp_errors_in_window gauge",
            f"open_stocks_mcp_errors_in_window {metrics['errors_in_window']}",
            "# HELP open_stocks_mcp_tool_calls_total Total calls per tool.",
            "# TYPE open_stocks_mcp_tool_calls_total counter",
            "# HELP open_stocks_mcp_tool_avg_calls_per_minute Average calls per minute over the rolling window.",
            "# TYPE open_stocks_mcp_tool_avg_calls_per_minute gauge",
            "# HELP open_stocks_mcp_tool_latency_ms Tool latency percentile in milliseconds.",
            "# TYPE open_stocks_mcp_tool_latency_ms gauge",
        ]

        for tool_name, tool_metrics in metrics["tool_usage"].items():
            escaped_tool = self._escape_prometheus_label_value(tool_name)
            lines.append(
                f'open_stocks_mcp_tool_calls_total{{tool="{escaped_tool}"}} '
                f"{tool_metrics['calls']}"
            )
            lines.append(
                f'open_stocks_mcp_tool_avg_calls_per_minute{{tool="{escaped_tool}"}} '
                f"{tool_metrics['avg_calls_per_minute']}"
            )
            lines.append(
                f'open_stocks_mcp_tool_latency_ms{{tool="{escaped_tool}",quantile="0.50"}} '
                f"{tool_metrics['p50_response_time_ms']}"
            )
            lines.append(
                f'open_stocks_mcp_tool_latency_ms{{tool="{escaped_tool}",quantile="0.95"}} '
                f"{tool_metrics['p95_response_time_ms']}"
            )
            lines.append(
                f'open_stocks_mcp_tool_latency_ms{{tool="{escaped_tool}",quantile="0.99"}} '
                f"{tool_metrics['p99_response_time_ms']}"
            )

        return "\n".join(lines) + "\n"

    async def get_health_status(self) -> dict[str, Any]:
        """Get health status based on metrics.

        Returns:
            Dictionary containing health status
        """
        metrics = await self.get_metrics()

        # Define health thresholds
        error_rate = metrics["error_rate_percent"]
        avg_response_time = metrics["avg_response_time_ms"]

        health = "healthy"
        issues = []

        if error_rate > self._error_rate_unhealthy_threshold:
            health = "unhealthy"
            issues.append(f"Critical error rate: {error_rate}%")
        elif error_rate > self._error_rate_degraded_threshold:
            health = "degraded"
            issues.append(f"High error rate: {error_rate}%")

        if avg_response_time > self._avg_response_time_unhealthy_ms:
            health = "unhealthy"
            issues.append(f"Critical response time: {avg_response_time}ms")
        elif avg_response_time > self._latency_p95_threshold_ms:
            health = "degraded" if health == "healthy" else health
            issues.append(f"High response time: {avg_response_time}ms")

        if health != self._last_health_status and health != "healthy":
            event = AlertEvent(
                alert_type="health_transition",
                status=health,
                message=f"Health transitioned to {health}",
                metadata={"signal": "health_status"},
            )
            try:
                await self._alert_manager.emit(event)
            except Exception as exc:
                self.degraded_sink_total += 1
                logger.warning(f"Health transition alert failed: {exc}")
        self._last_health_status = health

        return {
            "status": health,
            "issues": issues,
            "active_alerts": metrics["active_alerts"],
            "metrics_summary": {
                "error_rate_percent": error_rate,
                "avg_response_time_ms": avg_response_time,
                "calls_last_hour": metrics["calls_in_window"],
            },
        }

    async def evaluate_alert_conditions(self) -> None:
        """Evaluate current metrics against alert thresholds and emit events.

        This method is idempotent and safe to call repeatedly; deduplication
        prevents duplicate alerts within the configured window.  Sink failures
        are caught and counted in `degraded_sink_total` — they never propagate.
        """
        metrics = await self.get_metrics()
        error_rate = metrics["error_rate_percent"]
        p95_rt_ms = metrics["p95_response_time_ms"]

        now = datetime.now()

        candidates: list[AlertEvent] = []

        if error_rate > self._error_rate_unhealthy_threshold:
            candidates.append(
                AlertEvent(
                    alert_type="threshold_breach",
                    status="unhealthy",
                    message=f"Critical error rate: {error_rate}%",
                    metric_value=error_rate,
                    threshold_value=self._error_rate_unhealthy_threshold,
                    metadata={"signal": "error_rate_percent"},
                )
            )
        elif error_rate > self._error_rate_degraded_threshold:
            candidates.append(
                AlertEvent(
                    alert_type="threshold_breach",
                    status="degraded",
                    message=f"High error rate: {error_rate}%",
                    metric_value=error_rate,
                    threshold_value=self._error_rate_degraded_threshold,
                    metadata={"signal": "error_rate_percent"},
                )
            )

        if p95_rt_ms > self._avg_response_time_unhealthy_ms:
            candidates.append(
                AlertEvent(
                    alert_type="threshold_breach",
                    status="unhealthy",
                    message=f"Critical p95 response time: {p95_rt_ms}ms",
                    metric_value=p95_rt_ms,
                    threshold_value=self._avg_response_time_unhealthy_ms,
                    metadata={"signal": "p95_response_time_ms"},
                )
            )
        elif p95_rt_ms > self._latency_p95_threshold_ms:
            candidates.append(
                AlertEvent(
                    alert_type="threshold_breach",
                    status="degraded",
                    message=f"High p95 response time: {p95_rt_ms}ms",
                    metric_value=p95_rt_ms,
                    threshold_value=self._latency_p95_threshold_ms,
                    metadata={"signal": "p95_response_time_ms"},
                )
            )

        # Clear resolved signals from active_alerts
        active_signals = {e.signal for e in candidates}
        for signal in list(self._active_alerts.keys()):
            if signal not in active_signals:
                del self._active_alerts[signal]

        if not self._alerts_enabled:
            # Still update active alerts state, but skip sink delivery
            for event in candidates:
                self._active_alerts[event.signal] = event
            return

        for event in candidates:
            self._active_alerts[event.signal] = event

            last_sent = self._last_alert_at.get(event.signal)
            if last_sent is not None and (now - last_sent) < self._alert_dedup_window:
                continue

            self._last_alert_at[event.signal] = now

            try:
                await self._alert_manager.emit(event)
            except Exception as exc:
                self.degraded_sink_total += 1
                logger.warning(f"Alert sink delivery failed for {event.signal}: {exc}")


# Global metrics collector instance
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance.

    Returns:
        The global MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        # Local import to avoid circular dependency at module load.
        from open_stocks_mcp.config import load_config

        alerts = load_config().alerts
        _metrics_collector = MetricsCollector(
            alerts_enabled=alerts.enabled,
            webhook_url=alerts.webhook_url,
            alert_dedup_window_seconds=alerts.dedup_window_seconds,
            error_rate_degraded_threshold=alerts.error_rate_degraded_threshold_percent,
            error_rate_unhealthy_threshold=alerts.error_rate_unhealthy_threshold_percent,
            avg_response_time_unhealthy_ms=alerts.avg_response_time_unhealthy_ms,
            latency_p95_threshold_ms=alerts.latency_p95_threshold_ms,
        )
    return _metrics_collector


class MonitoredTool:
    """Decorator for monitoring tool execution.

    NOTE: This decorator is deprecated for MCP tools as it interferes with
    MCP framework registration. Use only for core trading service functions.
    For MCP tools, metrics are collected via the metrics_summary() tool instead.
    """

    def __init__(self, tool_name: str):
        """Initialize monitored tool decorator.

        Args:
            tool_name: Name of the tool for metrics

        Warning:
            Do not use this decorator on functions decorated with @mcp.tool()
            as it prevents proper MCP registration.
        """
        import warnings

        warnings.warn(
            "MonitoredTool is deprecated for MCP tools. Use only for core trading service functions.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.tool_name = tool_name
        self.metrics = get_metrics_collector()

    def __call__(self, func: Any) -> Any:
        """Decorate the function."""

        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            success = False
            error_type = None

            try:
                result = await func(*args, **kwargs)

                # Check if result indicates success
                if isinstance(result, dict) and "result" in result:
                    status = result["result"].get("status", "success")
                    success = status != "error"
                    if not success:
                        error_type = result["result"].get("error_type", "unknown")
                else:
                    success = True

                return result

            except Exception as e:
                error_type = type(e).__name__
                raise RuntimeError(f"Monitored tool {self.tool_name} failed") from e

            finally:
                duration = time.time() - start_time
                await self.metrics.record_api_call(
                    self.tool_name, duration, success, error_type
                )

                # Log slow calls
                if duration > 5.0:
                    logger.warning(f"Slow call to {self.tool_name}: {duration:.2f}s")

        return wrapper
