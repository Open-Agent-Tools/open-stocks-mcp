import unittest
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from open_stocks_mcp.brokers.request_policy import install_robinhood_request_timeout


@pytest.fixture(autouse=True)
def _patch_broker_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    limiter = Mock()
    limiter.acquire = AsyncMock(return_value=None)
    registry = Mock()
    registry.get_rate_limiter = Mock(return_value=limiter)
    monkeypatch.setattr(
        "open_stocks_mcp.brokers.registry.get_broker_registry",
        AsyncMock(return_value=registry),
    )


class TestBrokerRequestPolicy(unittest.TestCase):
    def test_install_robinhood_request_timeout(self):
        # Create a mock session that behaves like requests.Session
        import requests

        session = requests.Session()
        # Mock the request method directly
        mock_request = MagicMock(return_value=MagicMock())
        session.request = mock_request

        # Configure timeout
        timeout = 1.0

        # Install policy
        install_robinhood_request_timeout(timeout, session=session)

        # Call session.request directly
        session.request("GET", "https://example.test")
        _args, kwargs = mock_request.call_args
        self.assertEqual(kwargs.get("timeout"), timeout)

        # Call session.get
        session.get("https://example.test")
        # requests.Session.get calls request(method='GET', ...)
        _args, kwargs = mock_request.call_args
        self.assertEqual(kwargs.get("timeout"), timeout)

        # Call session.post with an explicit timeout (should be overridden)
        session.post("https://example.test", timeout=16)
        _, kwargs = mock_request.call_args
        self.assertEqual(kwargs.get("timeout"), timeout)

    def test_install_robinhood_request_timeout_idempotent(self):
        import requests

        session = requests.Session()
        original_request = session.request

        timeout = 2.0

        # Install twice
        install_robinhood_request_timeout(timeout, session=session)
        wrapped_once = session.request
        install_robinhood_request_timeout(timeout, session=session)
        wrapped_twice = session.request

        # Should be the same wrapper
        self.assertEqual(wrapped_once, wrapped_twice)
        self.assertNotEqual(original_request, wrapped_once)
        self.assertTrue(hasattr(session.request, "_is_timeout_wrapper"))


@pytest.mark.asyncio
async def test_execute_broker_request_retries():
    from open_stocks_mcp.brokers.request_policy import execute_broker_request
    from open_stocks_mcp.config import BrokerRequestConfig

    mock_func = MagicMock()
    # Fail twice, succeed on third
    mock_func.side_effect = [
        Exception("Transient error"),
        Exception("Transient error"),
        "Success",
    ]

    policy = BrokerRequestConfig(
        retry_max_retries=3, retry_initial_delay=0.01, retry_backoff_factor=1.0
    )

    result = await execute_broker_request(mock_func, policy=policy, retry_safe=True)

    assert result == "Success"
    assert mock_func.call_count == 3


@pytest.mark.asyncio
async def test_execute_broker_request_no_retry_unsafe():
    from open_stocks_mcp.brokers.request_policy import execute_broker_request
    from open_stocks_mcp.config import BrokerRequestConfig

    mock_func = MagicMock()
    mock_func.side_effect = Exception("Mutation error")

    policy = BrokerRequestConfig(retry_max_retries=3)

    with pytest.raises(Exception, match="Mutation error"):
        await execute_broker_request(mock_func, policy=policy, retry_safe=False)

    assert mock_func.call_count == 1


@pytest.mark.asyncio
async def test_execute_broker_request_deadline():
    import time

    from open_stocks_mcp.brokers.request_policy import execute_broker_request
    from open_stocks_mcp.config import BrokerRequestConfig

    mock_func = MagicMock()
    mock_func.side_effect = Exception("Timeout error")

    # Policy with 0.1s deadline
    policy = BrokerRequestConfig(
        retry_max_retries=10,
        retry_initial_delay=0.05,
        retry_backoff_factor=2.0,
        total_deadline_seconds=0.1,
    )

    start_time = time.time()
    with pytest.raises(Exception, match="Timeout error"):
        await execute_broker_request(mock_func, policy=policy, retry_safe=True)

    elapsed = time.time() - start_time
    # Should stop before second retry (0.05 delay + 0.1 next delay > 0.1 budget)
    # Wait, 1st call at 0s. Failed. Delay 0.05s.
    # 2nd call at 0.05s. Failed. Delay 0.1s.
    # Total would be 0.15s which exceeds 0.1s.
    assert mock_func.call_count <= 3
    assert elapsed < 0.2


@pytest.mark.asyncio
async def test_execute_broker_request_uses_broker_limiter(
    monkeypatch: pytest.MonkeyPatch,
):
    from open_stocks_mcp.brokers.request_policy import execute_broker_request

    limiter = Mock()
    limiter.acquire = AsyncMock(return_value=None)
    registry = Mock()
    registry.get_rate_limiter = Mock(return_value=limiter)
    monkeypatch.setattr(
        "open_stocks_mcp.brokers.registry.get_broker_registry",
        AsyncMock(return_value=registry),
    )

    fn = MagicMock(return_value="ok")
    result = await execute_broker_request(fn, broker_name="schwab")
    assert result == "ok"
    registry.get_rate_limiter.assert_called_once_with("schwab")
    limiter.acquire.assert_awaited_once()
