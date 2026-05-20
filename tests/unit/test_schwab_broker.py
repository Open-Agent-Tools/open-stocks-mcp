"""Unit tests for Schwab broker implementation."""

import builtins
from pathlib import Path
from unittest.mock import MagicMock, patch

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
    async def test_placeholder_methods(self, schwab_broker: SchwabBroker) -> None:
        """Test placeholder methods in SchwabBroker."""
        # Not available
        schwab_broker._auth_info.status = BrokerAuthStatus.NOT_AUTHENTICATED
        assert (await schwab_broker.get_account_info())["result"][
            "status"
        ] == "broker_unavailable"

        # Available but not implemented
        schwab_broker._auth_info.status = BrokerAuthStatus.AUTHENTICATED
        schwab_broker.client = MagicMock()

        methods = [
            schwab_broker.get_account_info(),
            schwab_broker.get_portfolio(),
            schwab_broker.get_positions(),
            schwab_broker.get_stock_quote("AAPL"),
            schwab_broker.get_stock_price("AAPL"),
            schwab_broker.order_buy_market("AAPL", 1),
            schwab_broker.order_sell_market("AAPL", 1),
        ]

        for coro in methods:
            res = await coro
            assert res["result"]["status"] == "not_implemented"
