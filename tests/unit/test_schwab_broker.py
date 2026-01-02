"""Unit tests for Schwab broker implementation."""

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
        return SchwabBroker(
            api_key="test_api_key",
            app_secret="test_app_secret",
            callback_url="https://127.0.0.1:8182/",
            token_path="/tmp/test_schwab_token.json",
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
        # Create a temporary token file
        token_file = tmp_path / "schwab_token.json"
        token_file.write_text('{"access_token": "test_token"}')
        schwab_broker.token_path = str(token_file)

        # Mock the schwab auth module
        with patch("schwab.auth.client_from_token_file") as mock_client_from_token:
            mock_client = MagicMock()
            mock_client_from_token.return_value = mock_client

            result = await schwab_broker.authenticate()

            assert result is True
            assert schwab_broker._auth_info.status == BrokerAuthStatus.AUTHENTICATED
            assert schwab_broker.client == mock_client
            mock_client_from_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_with_easy_client(
        self, schwab_broker: SchwabBroker
    ) -> None:
        """Test authentication using easy_client (no existing token)."""
        # Mock easy_client
        with patch("schwab.auth.easy_client") as mock_easy_client:
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
        # Mock authentication failure
        with patch("schwab.auth.easy_client", side_effect=Exception("OAuth failed")):
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
    async def test_logout(self, schwab_broker: SchwabBroker) -> None:
        """Test logout clears client and auth status."""
        schwab_broker.client = MagicMock()
        schwab_broker._auth_info.status = BrokerAuthStatus.AUTHENTICATED

        await schwab_broker.logout()

        assert schwab_broker.client is None
        assert schwab_broker._auth_info.status == BrokerAuthStatus.NOT_AUTHENTICATED

    def test_default_token_path(self) -> None:
        """Test default token path uses home directory."""
        broker = SchwabBroker(api_key="test", app_secret="test")

        assert ".tokens/schwab_token.json" in broker.token_path
        assert (
            Path(broker.token_path).expanduser().exists()
            or not Path(broker.token_path).expanduser().exists()
        )

    @pytest.mark.asyncio
    async def test_missing_credentials(self) -> None:
        """Test authentication fails with missing credentials."""
        broker = SchwabBroker(api_key=None, app_secret=None)

        result = await broker.authenticate()

        assert result is False
        assert broker._auth_info.status == BrokerAuthStatus.NOT_CONFIGURED
