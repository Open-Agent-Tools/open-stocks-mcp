"""Tests for the live market harness preflight and safety helpers.

These tests verify harness behavior without live network access or real credentials.
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

from tests.integration.live_market_harness import (
    LIVE_MARKET_ENV_VAR,
    LIVE_MARKET_SKIP_REASON,
    assert_live_market_read_only,
    assert_live_schwab_read_only,
    require_live_market_preflight,
    require_schwab_live_preflight,
)


class TestDefaultOptInRejection:
    """Harness rejects live-market execution when opt-in is missing."""

    def test_skips_without_run_live_market_flag(self) -> None:
        """Skip when --run-live-market CLI flag is absent."""
        config = MagicMock()
        config.getoption.return_value = False
        with pytest.raises(pytest.skip.Exception) as exc_info:
            require_live_market_preflight(config)
        assert "run-live-market" in str(
            exc_info.value
        ).lower() or LIVE_MARKET_SKIP_REASON in str(exc_info.value)

    def test_skips_without_env_var(self, monkeypatch: Any) -> None:
        """Skip when OPEN_STOCKS_RUN_LIVE_MARKET env var is absent."""
        monkeypatch.delenv(LIVE_MARKET_ENV_VAR, raising=False)
        config = MagicMock()
        config.getoption.return_value = True
        with pytest.raises(pytest.skip.Exception):
            require_live_market_preflight(config)

    def test_skips_without_username(self, monkeypatch: Any) -> None:
        """Skip when ROBINHOOD_USERNAME is absent."""
        monkeypatch.setenv(LIVE_MARKET_ENV_VAR, "1")
        monkeypatch.delenv("ROBINHOOD_USERNAME", raising=False)
        monkeypatch.setenv("ROBINHOOD_PASSWORD", "secret")
        config = MagicMock()
        config.getoption.return_value = True
        with pytest.raises(pytest.skip.Exception):
            require_live_market_preflight(config)

    def test_skips_without_password(self, monkeypatch: Any) -> None:
        """Skip when ROBINHOOD_PASSWORD is absent."""
        monkeypatch.setenv(LIVE_MARKET_ENV_VAR, "1")
        monkeypatch.setenv("ROBINHOOD_USERNAME", "user@example.com")
        monkeypatch.delenv("ROBINHOOD_PASSWORD", raising=False)
        config = MagicMock()
        config.getoption.return_value = True
        with pytest.raises(pytest.skip.Exception):
            require_live_market_preflight(config)


class TestAcceptedPreflight:
    """Harness proceeds when all opt-in conditions are satisfied."""

    def test_passes_when_all_inputs_present(self, monkeypatch: Any) -> None:
        """No skip raised when flag, env var, and credentials are all set."""
        monkeypatch.setenv(LIVE_MARKET_ENV_VAR, "1")
        monkeypatch.setenv("ROBINHOOD_USERNAME", "user@example.com")
        monkeypatch.setenv("ROBINHOOD_PASSWORD", "secret")
        config = MagicMock()
        config.getoption.return_value = True
        require_live_market_preflight(config)


class TestReadOnlyGuard:
    """assert_live_market_read_only blocks trading and cancellation tool names."""

    def test_allows_read_only_tool(self) -> None:
        """Read-only tool names pass without error."""
        assert_live_market_read_only("get_stock_price")

    def test_allows_get_prefix(self) -> None:
        """Tools starting with get_ are safe."""
        assert_live_market_read_only("get_positions")

    def test_rejects_order_prefix(self) -> None:
        """Tool names beginning with order_ are prohibited."""
        with pytest.raises(ValueError, match="order_"):
            assert_live_market_read_only("order_buy_market")

    def test_rejects_cancel_prefix(self) -> None:
        """Tool names beginning with cancel_ are prohibited."""
        with pytest.raises(ValueError, match="cancel_"):
            assert_live_market_read_only("cancel_stock_order")

    def test_rejects_order_sell(self) -> None:
        """order_sell_market is also prohibited."""
        with pytest.raises(ValueError):
            assert_live_market_read_only("order_sell_market")

    def test_rejects_cancel_all(self) -> None:
        """cancel_all_stock_orders is also prohibited."""
        with pytest.raises(ValueError):
            assert_live_market_read_only("cancel_all_stock_orders")


class TestSchwabPreflightRejection:
    """Schwab harness rejects live-market execution when opt-in is missing."""

    def test_schwab_skips_without_run_live_market_flag(self) -> None:
        """Skip when --run-live-market CLI flag is absent."""
        config = MagicMock()
        config.getoption.return_value = False
        with pytest.raises(pytest.skip.Exception) as exc_info:
            require_schwab_live_preflight(config)
        assert "run-live-market" in str(
            exc_info.value
        ).lower() or LIVE_MARKET_SKIP_REASON in str(exc_info.value)

    def test_schwab_skips_without_env_var(self, monkeypatch: Any) -> None:
        """Skip when OPEN_STOCKS_RUN_LIVE_MARKET env var is absent."""
        monkeypatch.delenv(LIVE_MARKET_ENV_VAR, raising=False)
        config = MagicMock()
        config.getoption.return_value = True
        with pytest.raises(pytest.skip.Exception):
            require_schwab_live_preflight(config)

    def test_schwab_skips_without_api_key(self, monkeypatch: Any) -> None:
        """Skip when SCHWAB_API_KEY is absent."""
        monkeypatch.setenv(LIVE_MARKET_ENV_VAR, "1")
        monkeypatch.delenv("SCHWAB_API_KEY", raising=False)
        monkeypatch.setenv("SCHWAB_APP_SECRET", "secret")
        config = MagicMock()
        config.getoption.return_value = True
        with pytest.raises(pytest.skip.Exception):
            require_schwab_live_preflight(config)

    def test_schwab_skips_without_app_secret(self, monkeypatch: Any) -> None:
        """Skip when SCHWAB_APP_SECRET is absent."""
        monkeypatch.setenv(LIVE_MARKET_ENV_VAR, "1")
        monkeypatch.setenv("SCHWAB_API_KEY", "key")
        monkeypatch.delenv("SCHWAB_APP_SECRET", raising=False)
        config = MagicMock()
        config.getoption.return_value = True
        with pytest.raises(pytest.skip.Exception):
            require_schwab_live_preflight(config)

    def test_schwab_skips_without_token_file(self, monkeypatch: Any, tmp_path: Any) -> None:
        """Skip when no token file exists at the configured path."""
        monkeypatch.setenv(LIVE_MARKET_ENV_VAR, "1")
        monkeypatch.setenv("SCHWAB_API_KEY", "key")
        monkeypatch.setenv("SCHWAB_APP_SECRET", "secret")
        monkeypatch.setenv("SCHWAB_TOKEN_PATH", str(tmp_path / "nonexistent_token.json"))
        config = MagicMock()
        config.getoption.return_value = True
        with pytest.raises(pytest.skip.Exception):
            require_schwab_live_preflight(config)


class TestSchwabReadOnlyGuard:
    """assert_live_schwab_read_only blocks Schwab trading and cancellation helpers."""

    def test_allows_get_schwab_quote(self) -> None:
        """Read-only Schwab tools pass without error."""
        assert_live_schwab_read_only("get_schwab_quote")

    def test_allows_get_schwab_orders(self) -> None:
        """get_schwab_orders is a read-only query and is permitted."""
        assert_live_schwab_read_only("get_schwab_orders")

    def test_allows_get_schwab_option_chain(self) -> None:
        """get_schwab_option_chain is a read-only query and is permitted."""
        assert_live_schwab_read_only("get_schwab_option_chain")

    def test_rejects_schwab_buy_market(self) -> None:
        """schwab_buy_market places an order and is prohibited."""
        with pytest.raises(ValueError, match="schwab_buy_market"):
            assert_live_schwab_read_only("schwab_buy_market")

    def test_rejects_schwab_sell_limit(self) -> None:
        """schwab_sell_limit places an order and is prohibited."""
        with pytest.raises(ValueError, match="schwab_sell_limit"):
            assert_live_schwab_read_only("schwab_sell_limit")

    def test_rejects_cancel_schwab_order(self) -> None:
        """cancel_schwab_order cancels a live order and is prohibited."""
        with pytest.raises(ValueError, match="cancel_schwab_order"):
            assert_live_schwab_read_only("cancel_schwab_order")

    def test_rejects_schwab_cancel_all_stock_orders(self) -> None:
        """schwab_cancel_all_stock_orders cancels live orders and is prohibited."""
        with pytest.raises(ValueError, match="schwab_cancel_all_stock_orders"):
            assert_live_schwab_read_only("schwab_cancel_all_stock_orders")

    def test_rejects_schwab_option_buy_to_open(self) -> None:
        """schwab_option_buy_to_open places an option order and is prohibited."""
        with pytest.raises(ValueError, match="schwab_option_buy_to_open"):
            assert_live_schwab_read_only("schwab_option_buy_to_open")

    def test_rejects_schwab_option_sell_to_close(self) -> None:
        """schwab_option_sell_to_close places an option order and is prohibited."""
        with pytest.raises(ValueError, match="schwab_option_sell_to_close"):
            assert_live_schwab_read_only("schwab_option_sell_to_close")
