"""Unit tests for error handling helpers and retry behavior."""

import asyncio
import inspect
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from mcp.server.fastmcp import FastMCP

from open_stocks_mcp.server.app import mcp as production_mcp
from open_stocks_mcp.tools import rate_limiter, retry
from open_stocks_mcp.tools import session_manager as session_manager_module
from open_stocks_mcp.tools.error_handling import (
    APIError,
    AuthenticationError,
    DataError,
    NetworkError,
    RateLimitError,
    RobinStocksError,
    classify_error,
    create_error_response,
    create_no_data_response,
    create_success_response,
    execute_with_retry,
    handle_robin_stocks_errors,
    handle_robin_stocks_sync_errors,
    handle_schwab_errors,
    log_api_call,
    sanitize_api_response,
    validate_period,
    validate_span,
    validate_symbol,
)

pytestmark = [pytest.mark.unit, pytest.mark.journey_system]


def _patch_retry_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> list[float]:
    session_manager = Mock()
    session_manager.update_last_successful_call = Mock()
    session_manager.refresh_session = Mock()
    session_manager.should_block_auth_retries = Mock(return_value=False)
    monkeypatch.setattr(
        session_manager_module, "get_session_manager", lambda: session_manager
    )
    monkeypatch.setattr(rate_limiter, "get_rate_limiter", lambda: None)
    breaker = Mock()
    breaker.before_request = AsyncMock(return_value=None)
    breaker.record_success = AsyncMock(return_value=None)
    breaker.record_failure = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "open_stocks_mcp.tools.circuit_breaker.get_broker_circuit_breaker",
        lambda: breaker,
    )

    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(retry.asyncio, "sleep", fake_sleep)
    return sleep_calls


def _always_fails(counter: list[int]) -> Callable[[], None]:
    def fail() -> None:
        counter.append(1)
        raise RuntimeError("connection timeout")

    return fail


@pytest.mark.parametrize(
    ("message", "expected_type"),
    [
        ("unauthorized", AuthenticationError),
        ("login expired", AuthenticationError),
        ("token revoked", AuthenticationError),
        ("session timeout", AuthenticationError),
        ("invalid credentials", AuthenticationError),
        ("rate limit hit", RateLimitError),
        ("too many requests", RateLimitError),
        ("429 returned", RateLimitError),
        ("quota exceeded", RateLimitError),
        ("throttled", RateLimitError),
        ("connection reset", NetworkError),
        ("network down", NetworkError),
        ("timeout", NetworkError),
        ("dns failure", NetworkError),
        ("could not resolve", NetworkError),
        ("host unreachable", NetworkError),
        ("json decode error", DataError),
        ("failed to parse", DataError),
        ("decode error", DataError),
        ("invalid data", DataError),
        ("malformed payload", DataError),
    ],
)
def test_classify_error(message: str, expected_type: type[RobinStocksError]) -> None:
    classified = classify_error(RuntimeError(message))
    assert isinstance(classified, expected_type)


def test_classify_error_falls_back_to_api_error() -> None:
    classified = classify_error(RuntimeError("kaboom"))
    assert isinstance(classified, APIError)
    assert "kaboom" in classified.message


def test_exception_types_expose_error_type_and_original_error() -> None:
    original = RuntimeError("root")
    generic = RobinStocksError("oops", "custom", original)
    assert generic.message == "oops"
    assert generic.error_type == "custom"
    assert generic.original_error is original

    assert AuthenticationError().error_type == "authentication"
    assert RateLimitError().error_type == "rate_limit"
    assert NetworkError().error_type == "network"
    assert DataError().error_type == "data"
    assert APIError().error_type == "api"


def test_create_error_response_without_context() -> None:
    response = create_error_response(RuntimeError("unauthorized"))
    assert response["result"]["status"] == "error"
    assert response["result"]["error_type"] == "authentication"
    assert "context" not in response["result"]


def test_create_error_response_with_context() -> None:
    response = create_error_response(RuntimeError("rate limit hit"), "in test")
    assert response["result"]["context"] == "in test"
    assert response["result"]["error_type"] == "rate_limit"


def test_create_success_response_default_and_custom_status() -> None:
    payload = {"symbol": "AAPL"}
    response = create_success_response(payload)
    assert response["result"]["status"] == "success"
    assert response["result"]["symbol"] == "AAPL"

    partial = create_success_response({"status": "partial", "symbol": "MSFT"})
    assert partial["result"]["status"] == "partial"


def test_create_no_data_response() -> None:
    no_context = create_no_data_response("no data")
    assert no_context == {"result": {"message": "no data", "status": "no_data"}}

    with_context = create_no_data_response("no data", {"symbol": "AAPL"})
    assert with_context["result"]["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_handle_robin_stocks_errors_async_behavior_and_metadata() -> None:
    async def sample(symbol: str, span: str = "day") -> dict[str, str]:
        return {"symbol": symbol, "span": span}

    decorated = handle_robin_stocks_errors(sample)
    assert await decorated("AAPL", span="week") == {"symbol": "AAPL", "span": "week"}
    assert getattr(decorated, "__wrapped__", None) is sample
    assert decorated.__name__ == "sample"
    assert (
        inspect.signature(decorated).parameters == inspect.signature(sample).parameters
    )
    assert inspect.iscoroutinefunction(decorated) is True


@pytest.mark.asyncio
async def test_handle_robin_stocks_errors_classifies_exception() -> None:
    async def boom() -> dict[str, Any]:
        raise RuntimeError("rate limit hit")

    decorated = handle_robin_stocks_errors(boom)
    assert await decorated() == {
        "result": {
            "error": "Rate limit exceeded",
            "error_type": "rate_limit",
            "status": "error",
            "context": "in boom",
        }
    }


def test_handle_robin_stocks_sync_errors_behavior_and_metadata() -> None:
    def sample(symbol: str, span: str = "day") -> dict[str, str]:
        return {"symbol": symbol, "span": span}

    decorated = handle_robin_stocks_sync_errors(sample)
    assert decorated("AAPL") == {"symbol": "AAPL", "span": "day"}
    assert getattr(decorated, "__wrapped__", None) is sample
    assert decorated.__name__ == "sample"
    assert (
        inspect.signature(decorated).parameters == inspect.signature(sample).parameters
    )
    assert inspect.iscoroutinefunction(decorated) is False


def test_handle_robin_stocks_sync_errors_classifies_exception() -> None:
    def boom() -> dict[str, Any]:
        raise RuntimeError("rate limit hit")

    decorated = handle_robin_stocks_sync_errors(boom)
    assert decorated() == {
        "result": {
            "error": "Rate limit exceeded",
            "error_type": "rate_limit",
            "status": "error",
            "context": "in boom",
        }
    }


@pytest.mark.asyncio
async def test_handle_schwab_errors_behavior_and_metadata() -> None:
    async def sample(symbol: str) -> dict[str, str]:
        return {"symbol": symbol}

    decorated = handle_schwab_errors(sample)
    assert await decorated("AAPL") == {"symbol": "AAPL"}
    assert getattr(decorated, "__wrapped__", None) is sample
    assert decorated.__name__ == "sample"
    assert (
        inspect.signature(decorated).parameters == inspect.signature(sample).parameters
    )
    assert inspect.iscoroutinefunction(decorated) is True


@pytest.mark.asyncio
async def test_handle_schwab_errors_classifies_exception() -> None:
    async def boom() -> dict[str, Any]:
        raise RuntimeError("network down")

    decorated = handle_schwab_errors(boom)
    assert await decorated() == {
        "result": {
            "error": "Network connectivity issue",
            "error_type": "network",
            "status": "error",
            "context": "in boom",
        }
    }


@pytest.mark.asyncio
async def test_decorated_tool_schema_is_not_collapsed() -> None:
    test_mcp = FastMCP("test")

    @test_mcp.tool()
    @handle_robin_stocks_errors
    async def decorated_price(symbol: str) -> dict[str, Any]:
        return {"result": {"symbol": symbol}}

    tools = await test_mcp.list_tools()
    entry = next(tool for tool in tools if tool.name == "decorated_price")
    schema = (
        entry.inputSchema.model_dump()
        if hasattr(entry.inputSchema, "model_dump")
        else entry.inputSchema
    )
    assert schema["properties"]["symbol"]["type"] == "string"


@pytest.mark.asyncio
async def test_production_stock_price_tool_schema_includes_symbol() -> None:
    tools = await production_mcp.list_tools()
    stock_price_tool = next(tool for tool in tools if tool.name == "stock_price")
    schema = (
        stock_price_tool.inputSchema.model_dump()
        if hasattr(stock_price_tool.inputSchema, "model_dump")
        else stock_price_tool.inputSchema
    )
    assert schema["properties"]["symbol"]["type"] == "string"


@pytest.fixture
def retry_patch(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    fake_session = Mock()
    fake_session.update_last_successful_call = Mock()
    fake_session.refresh_session = AsyncMock(return_value=True)
    fake_session.should_block_auth_retries = Mock(return_value=False)

    fake_rate_limiter = SimpleNamespace(acquire=AsyncMock())
    fake_breaker = Mock()
    fake_breaker.before_request = AsyncMock(return_value=None)
    fake_breaker.record_success = AsyncMock(return_value=None)
    fake_breaker.record_failure = AsyncMock(return_value=None)
    sleep_mock = AsyncMock()

    monkeypatch.setattr(
        "open_stocks_mcp.tools.session_manager.get_session_manager",
        lambda: fake_session,
    )
    monkeypatch.setattr(
        "open_stocks_mcp.tools.rate_limiter.get_rate_limiter",
        lambda: fake_rate_limiter,
    )
    monkeypatch.setattr(
        "open_stocks_mcp.tools.circuit_breaker.get_broker_circuit_breaker",
        lambda: fake_breaker,
    )
    monkeypatch.setattr("open_stocks_mcp.tools.retry.asyncio.sleep", sleep_mock)

    return {
        "session": fake_session,
        "rate_limiter": fake_rate_limiter,
        "breaker": fake_breaker,
        "sleep": sleep_mock,
    }


@pytest.mark.asyncio
async def test_execute_with_retry_uses_configured_retry_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPEN_STOCKS_MCP_RETRY_MAX_RETRIES", "2")
    monkeypatch.setenv("OPEN_STOCKS_MCP_RETRY_INITIAL_DELAY", "0.25")
    monkeypatch.setenv("OPEN_STOCKS_MCP_RETRY_BACKOFF_FACTOR", "3.0")
    sleep_calls = _patch_retry_dependencies(monkeypatch)
    attempts: list[int] = []

    with pytest.raises(NetworkError):
        await execute_with_retry(_always_fails(attempts))

    assert len(attempts) == 3
    assert sleep_calls == [0.25, 0.75]


@pytest.mark.asyncio
async def test_execute_with_retry_uses_per_error_class_retry_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPEN_STOCKS_MCP_RETRY_MAX_RETRIES", "0")
    monkeypatch.setenv("OPEN_STOCKS_MCP_RETRY_NETWORK_MAX_RETRIES", "2")
    sleep_calls = _patch_retry_dependencies(monkeypatch)
    attempts: list[int] = []

    with pytest.raises(NetworkError):
        await execute_with_retry(_always_fails(attempts))

    assert len(attempts) == 3
    assert sleep_calls == [1.0, 2.0]


@pytest.mark.asyncio
async def test_execute_with_retry_explicit_arguments_override_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPEN_STOCKS_MCP_RETRY_MAX_RETRIES", "3")
    monkeypatch.setenv("OPEN_STOCKS_MCP_RETRY_NETWORK_MAX_RETRIES", "3")
    sleep_calls = _patch_retry_dependencies(monkeypatch)
    attempts: list[int] = []

    with pytest.raises(NetworkError):
        await execute_with_retry(
            _always_fails(attempts),
            max_retries=0,
            delay=0.5,
            backoff_factor=10.0,
        )

    assert len(attempts) == 1
    assert sleep_calls == []


@pytest.mark.asyncio
async def test_execute_with_retry_blocks_auth_retry_when_pickle_clear_failures_persist() -> (
    None
):
    """Auth retries should short-circuit when session cache clear keeps failing."""

    def auth_fail() -> None:
        raise Exception("authentication token expired")

    mock_session_manager = MagicMock()
    mock_session_manager.should_block_auth_retries.return_value = True
    mock_session_manager.refresh_session = AsyncMock(return_value=False)

    with (
        patch(
            "open_stocks_mcp.tools.session_manager.get_session_manager",
            return_value=mock_session_manager,
        ),
        patch("open_stocks_mcp.tools.rate_limiter.get_rate_limiter", return_value=None),
        pytest.raises(AuthenticationError, match="Session cache clear failures"),
    ):
        await execute_with_retry(auth_fail, max_retries=0)

    mock_session_manager.refresh_session.assert_not_called()


@pytest.mark.asyncio
async def test_execute_with_retry_attempts_reauth_when_not_blocked() -> None:
    """Auth retries should still attempt reauth when not blocked."""

    def auth_fail() -> None:
        raise Exception("authentication token expired")

    mock_session_manager = MagicMock()
    mock_session_manager.should_block_auth_retries.return_value = False
    mock_session_manager.refresh_session = AsyncMock(return_value=False)

    with (
        patch(
            "open_stocks_mcp.tools.session_manager.get_session_manager",
            return_value=mock_session_manager,
        ),
        patch("open_stocks_mcp.tools.rate_limiter.get_rate_limiter", return_value=None),
        pytest.raises(AuthenticationError),
    ):
        await execute_with_retry(auth_fail, max_retries=0)

    mock_session_manager.refresh_session.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_with_retry_uses_registry_single_flight_for_auth_refresh() -> (
    None
):
    calls = 0

    def auth_fail_then_success_factory() -> Callable[[], str]:
        state = {"attempts": 0}

        def runner() -> str:
            state["attempts"] += 1
            if state["attempts"] == 1:
                raise Exception("authentication token expired")
            return "ok"

        return runner

    async def coordinated_refresh(
        *, broker_name: str, account_id: str | None, refresh_coro: Callable[[], Any]
    ) -> bool:
        nonlocal calls
        calls += 1
        return await refresh_coro()

    registry = Mock()
    registry.coordinated_refresh = AsyncMock(side_effect=coordinated_refresh)
    breaker = Mock()
    breaker.before_request = AsyncMock(return_value=None)
    breaker.record_success = AsyncMock(return_value=None)
    breaker.record_failure = AsyncMock(return_value=None)

    session = Mock()
    session.should_block_auth_retries = Mock(return_value=False)
    session.refresh_session = AsyncMock(return_value=True)
    session.update_last_successful_call = Mock()

    with (
        patch(
            "open_stocks_mcp.tools.session_manager.get_session_manager",
            return_value=session,
        ),
        patch("open_stocks_mcp.tools.rate_limiter.get_rate_limiter", return_value=None),
        patch(
            "open_stocks_mcp.tools.circuit_breaker.get_broker_circuit_breaker",
            return_value=breaker,
        ),
        patch(
            "open_stocks_mcp.brokers.registry.get_broker_registry",
            AsyncMock(return_value=registry),
        ),
    ):
        results = await asyncio.gather(
            *[
                execute_with_retry(
                    auth_fail_then_success_factory(),
                    max_retries=1,
                    broker_name="robinhood",
                    account_id="acct-1",
                )
                for _ in range(20)
            ]
        )

    assert results == ["ok"] * 20
    assert calls == 20
    assert registry.coordinated_refresh.await_count == 20


@pytest.mark.asyncio
async def test_execute_with_retry_returns_value_on_first_success(
    retry_patch: dict[str, Any],
) -> None:
    async def ok() -> str:
        return "ok"

    result = await execute_with_retry(ok)
    assert result == "ok"
    retry_patch["session"].update_last_successful_call.assert_called_once()
    retry_patch["sleep"].assert_not_awaited()


@pytest.mark.asyncio
async def test_execute_with_retry_runs_sync_in_executor(
    retry_patch: dict[str, Any],
) -> None:
    def add(a: int, b: int = 1) -> int:
        return a + b

    result = await execute_with_retry(add, 2, b=3)
    assert result == 5


@pytest.mark.asyncio
async def test_execute_with_retry_retries_then_succeeds(
    retry_patch: dict[str, Any],
) -> None:
    calls = {"count": 0}

    async def flaky() -> str:
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("connection refused")
        return "ok"

    result = await execute_with_retry(
        flaky, max_retries=3, delay=0.1, backoff_factor=2.0
    )
    assert result == "ok"
    assert calls["count"] == 3
    retry_patch["sleep"].assert_any_await(0.1)
    retry_patch["sleep"].assert_any_await(0.2)


@pytest.mark.asyncio
async def test_execute_with_retry_raises_after_max_retries(
    retry_patch: dict[str, Any],
) -> None:
    calls = {"count": 0}

    async def always_fails() -> str:
        calls["count"] += 1
        raise RuntimeError("connection refused")

    with pytest.raises(NetworkError):
        await execute_with_retry(always_fails, max_retries=2, delay=0.01)

    assert calls["count"] == 3


@pytest.mark.asyncio
async def test_execute_with_retry_does_not_retry_on_data_error(
    retry_patch: dict[str, Any],
) -> None:
    calls = {"count": 0}

    async def bad_data() -> str:
        calls["count"] += 1
        raise RuntimeError("json decode error")

    with pytest.raises(DataError):
        await execute_with_retry(bad_data, max_retries=3)

    assert calls["count"] == 1
    retry_patch["sleep"].assert_not_awaited()


@pytest.mark.asyncio
async def test_execute_with_retry_reauth_on_authentication_error(
    retry_patch: dict[str, Any],
) -> None:
    calls = {"count": 0}

    async def auth_once() -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("unauthorized")
        return "ok"

    result = await execute_with_retry(auth_once, max_retries=1)
    assert result == "ok"
    retry_patch["session"].refresh_session.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_with_retry_raises_when_reauth_fails(
    retry_patch: dict[str, Any],
) -> None:
    retry_patch["session"].refresh_session = AsyncMock(return_value=False)

    async def auth_fails() -> str:
        raise RuntimeError("token expired")

    with pytest.raises(AuthenticationError):
        await execute_with_retry(auth_fails, max_retries=1)

    retry_patch["session"].refresh_session.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_with_retry_skips_rate_limiter_when_disabled(
    retry_patch: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    get_rate_limiter = Mock(side_effect=AssertionError("should not be called"))
    monkeypatch.setattr(
        "open_stocks_mcp.tools.rate_limiter.get_rate_limiter", get_rate_limiter
    )

    async def ok() -> str:
        return "ok"

    assert await execute_with_retry(ok, rate_limit=False) == "ok"
    get_rate_limiter.assert_not_called()


@pytest.mark.parametrize("symbol", ["A", "AAPL", "GOOGL", "BRK", "abc", "BRK1"])
def test_validate_symbol_valid(symbol: str) -> None:
    assert validate_symbol(symbol) is True


@pytest.mark.parametrize(
    "symbol",
    ["", "TOOLONG", "BR-K", "  ", "BR.K"],
)
def test_validate_symbol_invalid(symbol: str) -> None:
    assert validate_symbol(symbol) is False


def test_validate_symbol_invalid_none() -> None:
    assert validate_symbol(None) is False  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "period", ["day", "week", "month", "3month", "year", "5year", "all"]
)
def test_validate_period_valid(period: str) -> None:
    assert validate_period(period) is True


@pytest.mark.parametrize("period", ["hour", "decade", "", "DAY"])
def test_validate_period_invalid(period: str) -> None:
    assert validate_period(period) is False


@pytest.mark.parametrize(
    "span", ["day", "week", "month", "3month", "year", "5year", "all"]
)
def test_validate_span_valid(span: str) -> None:
    assert validate_span(span) is True


@pytest.mark.parametrize("span", ["hour", "decade", "", "DAY"])
def test_validate_span_invalid(span: str) -> None:
    assert validate_span(span) is False


def test_sanitize_api_response_redacts_recursive_values() -> None:
    payload = {
        "Token": "abc",
        "user": {"password": "pw", "nested": [{"SSN": "123"}]},
        "safe": 7,
    }
    sanitized = sanitize_api_response(payload)
    assert sanitized["Token"] == "[REDACTED]"
    assert sanitized["user"]["password"] == "[REDACTED]"
    assert sanitized["user"]["nested"][0]["SSN"] == "[REDACTED]"
    assert sanitized["safe"] == 7


def test_sanitize_api_response_preserves_scalars() -> None:
    assert sanitize_api_response("x") == "x"
    assert sanitize_api_response(5) == 5
    assert sanitize_api_response(None) is None


def test_log_api_call_excludes_sensitive_kwargs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO")
    log_api_call(
        "stock_price", symbol="AAPL", token="secret", include_extended_hours=True
    )
    message = caplog.records[-1].message
    assert "stock_price" in message
    assert "AAPL" in message
    assert "token" not in message
    assert "include_extended_hours" in message
