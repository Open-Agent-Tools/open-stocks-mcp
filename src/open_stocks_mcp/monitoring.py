"""Enhanced monitoring and metrics for the MCP server."""

import asyncio
import math
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any

from open_stocks_mcp.logging_config import logger


class MetricsCollector:
    """Collects and tracks metrics for monitoring."""

    def __init__(self, window_size_minutes: int = 60):
        """Initialize metrics collector.

        Args:
            window_size_minutes: Size of the rolling window for metrics
        """
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

        # Counters
        self.total_calls = 0
        self.total_errors = 0
        self.session_refreshes = 0

        # Cache hit/miss counters, keyed by cache name
        self.cache_hits: dict[str, int] = defaultdict(int)
        self.cache_misses: dict[str, int] = defaultdict(int)

        self._lock = asyncio.Lock()

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

    async def record_session_refresh(self) -> None:
        """Record a session refresh event."""
        async with self._lock:
            self.session_refreshes += 1
            logger.info(f"Session refresh recorded. Total: {self.session_refreshes}")

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

        # Clean per-tool response times
        for tool_durations in self.tool_response_times.values():
            while tool_durations and tool_durations[0][0] < cutoff:
                tool_durations.popleft()

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
                    "calls_per_minute": round(
                        total / (self.window_size.total_seconds() / 60), 2
                    )
                    if total > 0
                    else 0.0,
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
            "# HELP open_stocks_mcp_tool_calls_per_minute Calls per minute per tool.",
            "# TYPE open_stocks_mcp_tool_calls_per_minute gauge",
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
                f'open_stocks_mcp_tool_calls_per_minute{{tool="{escaped_tool}"}} '
                f"{tool_metrics['calls_per_minute']}"
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

        if error_rate > 25:
            health = "unhealthy"
            issues.append(f"Critical error rate: {error_rate}%")
        elif error_rate > 10:
            health = "degraded"
            issues.append(f"High error rate: {error_rate}%")

        if avg_response_time > 10000:  # 10 seconds
            health = "unhealthy"
            issues.append(f"Critical response time: {avg_response_time}ms")
        elif avg_response_time > 5000:  # 5 seconds
            health = "degraded" if health == "healthy" else health
            issues.append(f"High response time: {avg_response_time}ms")

        return {
            "status": health,
            "issues": issues,
            "metrics_summary": {
                "error_rate_percent": error_rate,
                "avg_response_time_ms": avg_response_time,
                "calls_last_hour": metrics["calls_in_window"],
            },
        }


# Global metrics collector instance
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance.

    Returns:
        The global MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
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
                raise

            finally:
                duration = time.time() - start_time
                await self.metrics.record_api_call(
                    self.tool_name, duration, success, error_type
                )

                # Log slow calls
                if duration > 5.0:
                    logger.warning(f"Slow call to {self.tool_name}: {duration:.2f}s")

        return wrapper
