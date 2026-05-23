"""Unit tests for Schwab broker implementation."""

import builtins
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_stocks_mcp.brokers.base import BrokerAuthStatus
from open_stocks_mcp.brokers.schwab import SchwabBroker


class TestSchwabBroker:
    """Test Schwab broker implementation."""

    @pytest.fixture
    def schwab_broker(self) -> SchwabBroker:
        """Create a Schwab broker instance for testing."""
        # Use a path under ~/.tokens to satisfy validation
        token_path = str(Path.home() / ".tokens" / "test_schwab_token.json")
        return SchwabBroker(
            api_key="test_api_key",
            app_secret="test_app_secret",
            callback_url="https://127.0.0.1:8182/",
            token_path=token_path,
        )

    def test_broker_name(self, schwab_broker: SchwabBroker) -> None:
        """Test broker name property."""
        assert schwab_broker.name == "schwab"

    def test_initial_auth_status(self, schwab_broker: SchwabBroker) -> None:
        """Test initial authentication status."""
        assert schwab_broker._auth_info.status == BrokerAuthStatus.NOT_AUTHENTICATED

    @pytest.mark.asyncio
    async def test_authenticate_with_existing_token(
        self, schwab_broker: SchwabBroker, tmp_path: Path
    ) -> None:
        """Test authentication with existing token file."""
        # Create a temporary token file under ~/.tokens
        token_dir = Path.home() / ".tokens"
        token_dir.mkdir(parents=True, exist_ok=True)
        token_file = token_dir / "schwab_token_test.json"
        token_file.write_text('{"access_token": "test_token"}')
        schwab_broker.token_path = str(token_file)

        try:
            # Mock the schwab auth module
            with patch("schwab.auth.client_from_token_file") as mock_client_from_token:
                mock_client = MagicMock()
                mock_client_from_token.return_value = mock_client

                result = await schwab_broker.authenticate()

                assert result is True
                assert schwab_broker._auth_info.status == BrokerAuthStatus.AUTHENTICATED
                assert schwab_broker.client == mock_client
                mock_client_from_token.assert_called_once()
                mock_client.set_timeout.assert_called_once_with(30.0)
        finally:
            if token_file.exists():
                token_file.unlink()

    @pytest.mark.asyncio
    async def test_authenticate_with_easy_client(
        self, schwab_broker: SchwabBroker
    ) -> None:
        """Test authentication using easy_client (no existing token)."""
        # Mock easy_client and isatty
        with (
            patch("schwab.auth.easy_client") as mock_easy_client,
            patch("os.isatty", return_value=True),
        ):
            mock_client = MagicMock()
            mock_easy_client.return_value = mock_client

            result = await schwab_broker.authenticate()

            assert result is True
            assert schwab_broker._auth_info.status == BrokerAuthStatus.AUTHENTICATED
            assert schwab_broker.client == mock_client
            mock_easy_client.assert_called_once_with(
                api_key=schwab_broker.api_key,
                app_secret=schwab_broker.app_secret,
                callback_url=schwab_broker.callback_url,
                token_path=schwab_broker.token_path,
            )
            mock_client.set_timeout.assert_called_once_with(30.0)

    @pytest.mark.asyncio
    async def test_authenticate_failure(self, schwab_broker: SchwabBroker) -> None:
        """Test authentication failure."""
        # Mock authentication failure and isatty
        with (
            patch("schwab.auth.easy_client", side_effect=Exception("OAuth failed")),
            patch("os.isatty", return_value=True),
        ):
            result = await schwab_broker.authenticate()

            assert result is False
            assert schwab_broker._auth_info.status == BrokerAuthStatus.AUTH_FAILED
            assert schwab_broker.client is None

    @pytest.mark.asyncio
    async def test_authenticate_custom_timeout(
        self, schwab_broker: SchwabBroker
    ) -> None:
        """Test authentication with custom timeout from environment."""
        with (
            patch("schwab.auth.easy_client") as mock_easy_client,
            patch("os.isatty", return_value=True),
            patch.dict(
                "os.environ", {"OPEN_STOCKS_MCP_SCHWAB_REQUEST_TIMEOUT_SECONDS": "2.5"}
            ),
            patch("open_stocks_mcp.config._global_config", None),  # Reset config
        ):
            mock_client = MagicMock()
            mock_easy_client.return_value = mock_client

            result = await schwab_broker.authenticate()

            assert result is True
            mock_client.set_timeout.assert_called_once_with(2.5)

    @pytest.mark.asyncio
    async def test_is_authenticated_true(self, schwab_broker: SchwabBroker) -> None:
        """Test is_authenticated when authenticated."""
        schwab_broker._auth_info.status = BrokerAuthStatus.AUTHENTICATED
        schwab_broker.client = MagicMock()

        result = await schwab_broker.is_authenticated()

        assert result is True

    @pytest.mark.asyncio
    async def test_is_authenticated_false(self, schwab_broker: SchwabBroker) -> None:
        """Test is_authenticated when not authenticated."""
        schwab_broker._auth_info.status = BrokerAuthStatus.NOT_AUTHENTICATED
        schwab_broker.client = None

        result = await schwab_broker.is_authenticated()

        assert result is False

    @pytest.mark.asyncio
    async def test_logout(self, schwab_broker: SchwabBroker, tmp_path: Path) -> None:
        """Test logout clears client and auth status."""
        # Create a dummy token file to cover lines 192-193
        token_dir = Path.home() / ".tokens"
        token_dir.mkdir(parents=True, exist_ok=True)
        token_file = token_dir / "schwab_token_logout_test.json"
        token_file.write_text("{}")
        schwab_broker.token_path = str(token_file)

        try:
            schwab_broker.client = MagicMock()
            schwab_broker._auth_info.status = BrokerAuthStatus.AUTHENTICATED

            await schwab_broker.logout()

            assert schwab_broker.client is None
            assert schwab_broker._auth_info.status == BrokerAuthStatus.NOT_AUTHENTICATED
        finally:
            if token_file.exists():
                token_file.unlink()

    @pytest.mark.asyncio
    async def test_logout_exception(self, schwab_broker: SchwabBroker) -> None:
        """Test logout with an exception."""
        schwab_broker.client = MagicMock()
        with patch(
            "open_stocks_mcp.brokers.schwab.Path",
            side_effect=Exception("Path error"),
        ):
            await schwab_broker.logout()
            # Should log error and return
            assert schwab_broker._auth_info.status == BrokerAuthStatus.NOT_AUTHENTICATED

    def test_default_token_path(self) -> None:
        """Test default token path uses home directory."""
        broker = SchwabBroker(api_key="test", app_secret="test")
        assert ".tokens/schwab_token.json" in broker.token_path

    def test_rejects_token_path_outside_tokens_dir(self) -> None:
        """Test that token_path must be inside ~/.tokens directory."""
        with pytest.raises(ValueError, match="token_path must be under"):
            SchwabBroker(
                api_key="test", app_secret="test", token_path="/tmp/outside_token.json"
            )

    def test_accepts_token_path_inside_tokens_dir(self) -> None:
        """Test that token_path can be inside ~/.tokens directory."""
        token_dir = Path.home() / ".tokens"
        token_path = token_dir / "custom_schwab_token.json"
        broker = SchwabBroker(
            api_key="test", app_secret="test", token_path=str(token_path)
        )
        assert broker.token_path == str(token_path.resolve())

    @pytest.mark.asyncio
    async def test_missing_credentials(self) -> None:
        """Test authentication fails with missing credentials."""
        broker = SchwabBroker(api_key=None, app_secret=None)

        with patch("schwab.auth.easy_client", side_effect=Exception("OAuth failed")):
            result = await broker.authenticate()

        assert result is False
        assert broker._auth_info.status == BrokerAuthStatus.NOT_CONFIGURED

    @pytest.mark.asyncio
    async def test_authenticate_invalid_existing_token(
        self, schwab_broker: SchwabBroker, tmp_path: Path
    ) -> None:
        """Test authentication when existing token file is invalid."""
        token_dir = Path.home() / ".tokens"
        token_dir.mkdir(parents=True, exist_ok=True)
        token_file = token_dir / "schwab_token_invalid_test.json"
        token_file.write_text("invalid json")
        schwab_broker.token_path = str(token_file)

        try:
            with (
                patch(
                    "schwab.auth.client_from_token_file",
                    side_effect=Exception("Invalid token"),
                ),
                patch("os.isatty", return_value=True),
                patch("schwab.auth.easy_client") as mock_easy_client,
            ):
                mock_easy_client.return_value = MagicMock()
                result = await schwab_broker.authenticate()
                assert result is True
                mock_easy_client.assert_called_once()
        finally:
            if token_file.exists():
                token_file.unlink()

    @pytest.mark.asyncio
    async def test_authenticate_non_interactive(
        self, schwab_broker: SchwabBroker
    ) -> None:
        """Test authentication in non-interactive environment."""
        with patch("os.isatty", return_value=False):
            result = await schwab_broker.authenticate()
            assert result is False
            assert schwab_broker._auth_info.status == BrokerAuthStatus.AUTH_FAILED
            assert (
                "Interactive authentication required"
                in schwab_broker._auth_info.error_message
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.journey_account
    @pytest.mark.exception_test
    async def test_authenticate_expired_token_then_bad_oauth_credentials(
        self, schwab_broker: SchwabBroker
    ) -> None:
        token_dir = Path.home() / ".tokens"
        token_dir.mkdir(parents=True, exist_ok=True)
        token_file = token_dir / "schwab_token_expired_test.json"
        token_file.write_text('{"access_token":"expired"}')
        schwab_broker.token_path = str(token_file)

        try:
            with (
                patch(
                    "schwab.auth.client_from_token_file",
                    side_effect=Exception("token expired"),
                ),
                patch(
                    "schwab.auth.easy_client", side_effect=Exception("bad credentials")
                ),
                patch("os.isatty", return_value=True),
            ):
                result = await schwab_broker.authenticate()
        finally:
            if token_file.exists():
                token_file.unlink()

        assert result is False
        assert schwab_broker.client is None
        assert schwab_broker._auth_info.status == BrokerAuthStatus.AUTH_FAILED
        assert schwab_broker._auth_info.error_message is not None
        assert "bad credentials" in schwab_broker._auth_info.error_message

    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.journey_account
    @pytest.mark.exception_test
    async def test_authenticate_bad_credentials_non_interactive_no_browser(
        self, schwab_broker: SchwabBroker
    ) -> None:
        token_dir = Path.home() / ".tokens"
        token_dir.mkdir(parents=True, exist_ok=True)
        token_file = token_dir / "schwab_token_noexist_test.json"
        if token_file.exists():
            token_file.unlink()
        schwab_broker.token_path = str(token_file)

        with (
            patch("os.isatty", return_value=False),
            patch("schwab.auth.easy_client") as mock_easy_client,
        ):
            result = await schwab_broker.authenticate()

        assert result is False
        assert schwab_broker._auth_info.status == BrokerAuthStatus.AUTH_FAILED
        assert schwab_broker.client is None
        assert schwab_broker._auth_info.error_message is not None
        assert (
            "Interactive authentication required"
            in schwab_broker._auth_info.error_message
        )
        mock_easy_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticate_import_error(self, schwab_broker: SchwabBroker) -> None:
        """Test authentication when schwab library is missing."""
        original_import = builtins.__import__

        def mocked_import(name, *args, **kwargs):
            if name == "schwab":
                raise ImportError("No module named 'schwab'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mocked_import):
            # Clear schwab from sys.modules if it's there, to force a re-import attempt
            # But be careful as other tests might need it.
            # Actually, the 'from schwab import auth' is local, so it will call __import__('schwab')
            result = await schwab_broker.authenticate()
            assert result is False
            assert schwab_broker._auth_info.status == BrokerAuthStatus.AUTH_FAILED
            assert (
                "schwab-py library not installed"
                in schwab_broker._auth_info.error_message
            )

    @pytest.mark.asyncio
    async def test_authenticate_generic_exception(
        self, schwab_broker: SchwabBroker
    ) -> None:
        """Test authentication with generic exception."""
        with (
            patch(
                "schwab.auth.client_from_token_file",
                side_effect=RuntimeError("Unexpected error"),
            ),
            patch(
                "schwab.auth.easy_client", side_effect=RuntimeError("Unexpected error")
            ),
            patch("os.isatty", return_value=True),
        ):
            result = await schwab_broker.authenticate()
            assert result is False
            assert schwab_broker._auth_info.status == BrokerAuthStatus.AUTH_FAILED
            assert "Unexpected error" in schwab_broker._auth_info.error_message

    @pytest.mark.asyncio
    async def test_unavailable_state_returns_broker_unavailable(
        self, schwab_broker: SchwabBroker
    ) -> None:
        """All methods return broker_unavailable when not authenticated."""
        schwab_broker._auth_info.status = BrokerAuthStatus.NOT_AUTHENTICATED

        for coro in [
            schwab_broker.get_account_info(),
            schwab_broker.get_portfolio(),
            schwab_broker.get_positions(),
            schwab_broker.get_stock_quote("AAPL"),
            schwab_broker.get_stock_price("AAPL"),
            schwab_broker.order_buy_market("AAPL", 1),
            schwab_broker.order_sell_market("AAPL", 1),
        ]:
            result = await coro
            assert result["result"]["status"] == "broker_unavailable"

    @pytest.mark.asyncio
    async def test_get_account_info_delegates_to_tool(
        self, schwab_broker: SchwabBroker
    ) -> None:
        schwab_broker._auth_info.status = BrokerAuthStatus.AUTHENTICATED
        schwab_broker.client = MagicMock()
        expected = {"result": {"accounts": []}}
        with patch(
            "open_stocks_mcp.tools.schwab_account_tools.get_schwab_accounts",
            new=AsyncMock(return_value=expected),
        ) as mock_tool:
            result = await schwab_broker.get_account_info()
        mock_tool.assert_awaited_once_with(include_positions=False)
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_portfolio_delegates_to_tool(
        self, schwab_broker: SchwabBroker
    ) -> None:
        schwab_broker._auth_info.status = BrokerAuthStatus.AUTHENTICATED
        schwab_broker.client = MagicMock()
        expected = {"result": {"accounts": [{"positions": []}]}}
        with patch(
            "open_stocks_mcp.tools.schwab_account_tools.get_schwab_accounts",
            new=AsyncMock(return_value=expected),
        ) as mock_tool:
            result = await schwab_broker.get_portfolio()
        mock_tool.assert_awaited_once_with(include_positions=True)
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_positions_delegates_to_tool(
        self, schwab_broker: SchwabBroker
    ) -> None:
        schwab_broker._auth_info.status = BrokerAuthStatus.AUTHENTICATED
        schwab_broker.client = MagicMock()
        expected = {"result": {"accounts": []}}
        with patch(
            "open_stocks_mcp.tools.schwab_account_tools.get_schwab_accounts",
            new=AsyncMock(return_value=expected),
        ) as mock_tool:
            result = await schwab_broker.get_positions()
        mock_tool.assert_awaited_once_with(include_positions=True)
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_stock_quote_delegates_to_tool(
        self, schwab_broker: SchwabBroker
    ) -> None:
        schwab_broker._auth_info.status = BrokerAuthStatus.AUTHENTICATED
        schwab_broker.client = MagicMock()
        expected = {"result": {"symbol": "AAPL", "last_price": 175.0}}
        with patch(
            "open_stocks_mcp.tools.schwab_market_tools.get_schwab_quote",
            new=AsyncMock(return_value=expected),
        ) as mock_tool:
            result = await schwab_broker.get_stock_quote("AAPL")
        mock_tool.assert_awaited_once_with("AAPL")
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_stock_price_delegates_to_tool(
        self, schwab_broker: SchwabBroker
    ) -> None:
        schwab_broker._auth_info.status = BrokerAuthStatus.AUTHENTICATED
        schwab_broker.client = MagicMock()
        expected = {"result": {"symbol": "TSLA", "last_price": 200.0}}
        with patch(
            "open_stocks_mcp.tools.schwab_market_tools.get_schwab_quote",
            new=AsyncMock(return_value=expected),
        ) as mock_tool:
            result = await schwab_broker.get_stock_price("TSLA")
        mock_tool.assert_awaited_once_with("TSLA")
        assert result == expected

    @pytest.mark.asyncio
    async def test_order_buy_market_returns_explicit_error(
        self, schwab_broker: SchwabBroker
    ) -> None:
        schwab_broker._auth_info.status = BrokerAuthStatus.AUTHENTICATED
        schwab_broker.client = MagicMock()
        result = await schwab_broker.order_buy_market("AAPL", 5)
        assert result["result"]["status"] == "error"
        assert result["result"]["status"] != "not_implemented"
        assert "account hash" in result["result"]["error"].lower()

    @pytest.mark.asyncio
    async def test_order_sell_market_returns_explicit_error(
        self, schwab_broker: SchwabBroker
    ) -> None:
        schwab_broker._auth_info.status = BrokerAuthStatus.AUTHENTICATED
        schwab_broker.client = MagicMock()
        result = await schwab_broker.order_sell_market("AAPL", 5)
        assert result["result"]["status"] == "error"
        assert result["result"]["status"] != "not_implemented"
        assert "account hash" in result["result"]["error"].lower()
