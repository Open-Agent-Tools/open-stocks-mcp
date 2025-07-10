"""Enhanced monitoring and metrics for the MCP server."""

import asyncio
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
        self.error_types: dict[str, int] = defaultdict(int)

        # Counters
        self.total_calls = 0
        self.total_errors = 0
        self.session_refreshes = 0

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
            p50 = (
                response_times_sorted[len(response_times_sorted) // 2]
                if response_times_sorted
                else 0
            )
            p95 = (
                response_times_sorted[int(len(response_times_sorted) * 0.95)]
                if response_times_sorted
                else 0
            )
            p99 = (
                response_times_sorted[int(len(response_times_sorted) * 0.99)]
                if response_times_sorted
                else 0
            )

            # Tool usage stats
            tool_stats = {}
            for tool, calls in self.tool_usage.items():
                successful = sum(1 for _, success in calls if success)
                total = len(calls)
                tool_stats[tool] = {
                    "calls": total,
                    "success_rate": (successful / total * 100.0) if total > 0 else 0.0,
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
                "timestamp": now.isoformat(),
            }

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

        if error_rate > 10:
            health = "degraded"
            issues.append(f"High error rate: {error_rate}%")
        elif error_rate > 25:
            health = "unhealthy"

        if avg_response_time > 5000:  # 5 seconds
            health = "degraded" if health == "healthy" else health
            issues.append(f"High response time: {avg_response_time}ms")
        elif avg_response_time > 10000:  # 10 seconds
            health = "unhealthy"

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
    """Decorator for monitoring tool execution."""

    def __init__(self, tool_name: str):
        """Initialize monitored tool decorator.

        Args:
            tool_name: Name of the tool for metrics
        """
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
