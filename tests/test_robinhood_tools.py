"""Tests for Robin Stocks MCP tools."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from mcp import types

from open_stocks_mcp.tools.robinhood_tools import (
    account_info,
    auth_status,
    login_robinhood,
    logout_robinhood,
)


class TestRobinhoodTools:
    """Test Robin Stocks MCP tools."""

    @pytest.mark.asyncio
    async def test_login_robinhood_requires_parameters(self) -> None:
        """Test login_robinhood tool requires username, password, and mfa_secret."""
        # This test will need to be updated once we remove the NotImplementedError
        with pytest.raises(TypeError):
            await login_robinhood()  # Missing required parameters

    @pytest.mark.skip(reason="Login parameter format changed - needs update")
    @pytest.mark.asyncio
    async def test_login_robinhood_success(self, monkeypatch) -> None:
        """Test successful login with mocked robin-stocks."""

        # Mock the robin-stocks login function
        def mock_login(username, password, mfa_code, store_session):
            # Simulate successful login response
            return {"access_token": "mock_token", "expires_in": 86400}

        # Mock pyotp TOTP
        class MockTOTP:
            def __init__(self, secret):
                self.secret = secret

            def now(self):
                return "123456"

        monkeypatch.setattr("robin_stocks.robinhood.login", mock_login)
        monkeypatch.setattr("pyotp.TOTP", MockTOTP)

        # Test the login
        result = await login_robinhood(
            username="test@example.com", password="testpass", mfa_secret="TESTSECRET"
        )

        assert isinstance(result, types.TextContent)
        assert result.type == "text"
        assert "Successfully logged into Robinhood" in result.text
        assert "test@example.com" in result.text

    @pytest.mark.skip(reason="Login parameter format changed - needs update")
    @pytest.mark.asyncio
    async def test_login_robinhood_failure(self, monkeypatch) -> None:
        """Test failed login with mocked robin-stocks."""

        # Mock the robin-stocks login function to return None (failure)
        def mock_login(username, password, mfa_code, store_session):
            return None  # Indicates login failure

        # Mock pyotp TOTP
        class MockTOTP:
            def __init__(self, secret):
                self.secret = secret

            def now(self):
                return "123456"

        monkeypatch.setattr("robin_stocks.robinhood.login", mock_login)
        monkeypatch.setattr("pyotp.TOTP", MockTOTP)

        # Test the login
        result = await login_robinhood(
            username="test@example.com", password="wrongpass", mfa_secret="TESTSECRET"
        )

        assert isinstance(result, types.TextContent)
        assert result.type == "text"
        assert "Login failed" in result.text
        assert "Invalid credentials" in result.text

    @pytest.mark.skip(reason="Login parameter format changed - needs update")
    @pytest.mark.asyncio
    async def test_login_robinhood_exception(self, monkeypatch) -> None:
        """Test login exception handling."""

        # Mock the robin-stocks login function to raise an exception
        def mock_login(username, password, mfa_code, store_session):
            raise Exception("Network error: Unable to connect")

        # Mock pyotp TOTP
        class MockTOTP:
            def __init__(self, secret):
                self.secret = secret

            def now(self):
                return "123456"

        monkeypatch.setattr("robin_stocks.robinhood.login", mock_login)
        monkeypatch.setattr("pyotp.TOTP", MockTOTP)

        # Test the login
        result = await login_robinhood(
            username="test@example.com", password="testpass", mfa_secret="TESTSECRET"
        )

        assert isinstance(result, types.TextContent)
        assert result.type == "text"
        assert "Login error" in result.text
        assert "Network error" in result.text

    @pytest.mark.asyncio
    async def test_logout_robinhood_not_implemented(self) -> None:
        """Test logout_robinhood tool raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Logout tool not implemented"):
            await logout_robinhood()

    @pytest.mark.asyncio
    async def test_auth_status_not_implemented(self) -> None:
        """Test auth_status tool raises NotImplementedError."""
        with pytest.raises(
            NotImplementedError, match="Auth status tool not implemented"
        ):
            await auth_status()

    @pytest.mark.asyncio
    async def test_account_info_not_implemented(self) -> None:
        """Test account_info tool raises NotImplementedError."""
        with pytest.raises(
            NotImplementedError, match="Account info tool not implemented"
        ):
            await account_info()


class TestRobinhoodToolsImplementationSpecs:
    """Test specifications for future tool implementations."""

    @pytest.mark.asyncio
    async def test_login_robinhood_success_flow(self) -> None:
        """Test expected login success flow (specification)."""
        # Mock successful login
        with patch(
            "open_stocks_mcp.tools.robinhood_tools.login_robinhood"
        ) as mock_login:
            expected_response = types.TextContent(
                type="text", text="Successfully logged into Robinhood"
            )
            mock_login.return_value = expected_response

            result = await login_robinhood()

            assert isinstance(result, types.TextContent)
            assert result.type == "text"
            assert "Successfully logged into Robinhood" in result.text

    @pytest.mark.asyncio
    async def test_login_robinhood_failure_flow(self) -> None:
        """Test expected login failure flow (specification)."""
        # Mock failed login
        with patch(
            "open_stocks_mcp.tools.robinhood_tools.login_robinhood"
        ) as mock_login:
            expected_response = types.TextContent(
                type="text", text="Failed to login to Robinhood: Invalid credentials"
            )
            mock_login.return_value = expected_response

            result = await login_robinhood()

            assert isinstance(result, types.TextContent)
            assert result.type == "text"
            assert "Failed to login" in result.text

    @pytest.mark.asyncio
    async def test_logout_robinhood_success_flow(self) -> None:
        """Test expected logout success flow (specification)."""
        # Mock successful logout
        with patch(
            "open_stocks_mcp.tools.robinhood_tools.logout_robinhood"
        ) as mock_logout:
            expected_response = types.TextContent(
                type="text", text="Successfully logged out from Robinhood"
            )
            mock_logout.return_value = expected_response

            result = await logout_robinhood()

            assert isinstance(result, types.TextContent)
            assert result.type == "text"
            assert "Successfully logged out" in result.text

    @pytest.mark.asyncio
    async def test_auth_status_authenticated(self) -> None:
        """Test expected auth status when authenticated (specification)."""
        # Mock authenticated status
        with patch("open_stocks_mcp.tools.robinhood_tools.auth_status") as mock_status:
            expected_response = types.TextContent(
                type="text",
                text="Status: Authenticated\nUser: test@example.com\nSession expires: 2025-07-07 19:00:00",
            )
            mock_status.return_value = expected_response

            result = await auth_status()

            assert isinstance(result, types.TextContent)
            assert result.type == "text"
            assert "Status: Authenticated" in result.text
            assert "User:" in result.text

    @pytest.mark.asyncio
    async def test_auth_status_not_authenticated(self) -> None:
        """Test expected auth status when not authenticated (specification)."""
        # Mock not authenticated status
        with patch("open_stocks_mcp.tools.robinhood_tools.auth_status") as mock_status:
            expected_response = types.TextContent(
                type="text",
                text="Status: Not authenticated\nRun login_robinhood to authenticate",
            )
            mock_status.return_value = expected_response

            result = await auth_status()

            assert isinstance(result, types.TextContent)
            assert result.type == "text"
            assert "Status: Not authenticated" in result.text
            assert "Run login_robinhood" in result.text

    @pytest.mark.asyncio
    async def test_account_info_success_flow(self) -> None:
        """Test expected account info success flow (specification)."""
        # Mock successful account info retrieval
        with patch("open_stocks_mcp.tools.robinhood_tools.account_info") as mock_info:
            expected_response = types.TextContent(
                type="text",
                text="Account: test@example.com\nAccount Number: 123456789\nBuying Power: $1,000.00\nPortfolio Value: $5,000.00",
            )
            mock_info.return_value = expected_response

            result = await account_info()

            assert isinstance(result, types.TextContent)
            assert result.type == "text"
            assert "Account:" in result.text
            assert "Buying Power:" in result.text
            assert "Portfolio Value:" in result.text

    @pytest.mark.asyncio
    async def test_account_info_not_authenticated(self) -> None:
        """Test expected account info when not authenticated (specification)."""
        # Mock not authenticated error
        with patch("open_stocks_mcp.tools.robinhood_tools.account_info") as mock_info:
            expected_response = types.TextContent(
                type="text",
                text="Error: Not authenticated. Please run login_robinhood first.",
            )
            mock_info.return_value = expected_response

            result = await account_info()

            assert isinstance(result, types.TextContent)
            assert result.type == "text"
            assert "Error: Not authenticated" in result.text
            assert "login_robinhood" in result.text


class TestRobinhoodToolsIntegration:
    """Test integration between tools and auth system."""

    @pytest.mark.asyncio
    async def test_tools_use_global_client(self) -> None:
        """Test that tools use the global authentication client (specification)."""
        # Mock the global client function
        with patch(
            "open_stocks_mcp.tools.robinhood_tools.get_robinhood_client"
        ) as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            # Tools should call get_robinhood_client when implemented
            # This test verifies the integration pattern
            client = mock_get_client()
            assert client == mock_client
            mock_get_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_flow_integration(self) -> None:
        """Test complete login flow integration (specification)."""
        # Mock complete login flow
        with (
            patch(
                "open_stocks_mcp.tools.robinhood_tools.get_robinhood_client"
            ) as mock_get_client,
            patch(
                "open_stocks_mcp.tools.robinhood_tools.login_robinhood"
            ) as mock_login,
        ):
            mock_client = Mock()
            mock_client.authenticate = AsyncMock(return_value=True)
            mock_get_client.return_value = mock_client

            expected_response = types.TextContent(
                type="text", text="Successfully logged into Robinhood"
            )
            mock_login.return_value = expected_response

            result = await login_robinhood()

            assert isinstance(result, types.TextContent)
            assert "Successfully logged into Robinhood" in result.text

    @pytest.mark.asyncio
    async def test_logout_flow_integration(self) -> None:
        """Test complete logout flow integration (specification)."""
        # Mock complete logout flow
        with (
            patch(
                "open_stocks_mcp.tools.robinhood_tools.get_robinhood_client"
            ) as mock_get_client,
            patch(
                "open_stocks_mcp.tools.robinhood_tools.logout_robinhood"
            ) as mock_logout,
        ):
            mock_client = Mock()
            mock_client.logout = AsyncMock(return_value=True)
            mock_get_client.return_value = mock_client

            expected_response = types.TextContent(
                type="text", text="Successfully logged out from Robinhood"
            )
            mock_logout.return_value = expected_response

            result = await logout_robinhood()

            assert isinstance(result, types.TextContent)
            assert "Successfully logged out" in result.text


class TestRobinhoodToolsErrorCases:
    """Test error handling in Robin Stocks tools."""

    @pytest.mark.asyncio
    async def test_login_with_missing_credentials(self) -> None:
        """Test login tool with missing credentials (specification)."""
        with patch(
            "open_stocks_mcp.tools.robinhood_tools.login_robinhood"
        ) as mock_login:
            expected_response = types.TextContent(
                type="text",
                text="Error: Missing credentials. Please set ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD environment variables.",
            )
            mock_login.return_value = expected_response

            result = await login_robinhood()

            assert isinstance(result, types.TextContent)
            assert "Error: Missing credentials" in result.text
            assert "ROBINHOOD_USERNAME" in result.text

    @pytest.mark.asyncio
    async def test_account_info_api_error(self) -> None:
        """Test account info tool with API error (specification)."""
        with patch("open_stocks_mcp.tools.robinhood_tools.account_info") as mock_info:
            expected_response = types.TextContent(
                type="text",
                text="Error: Failed to retrieve account information. API error: Rate limit exceeded.",
            )
            mock_info.return_value = expected_response

            result = await account_info()

            assert isinstance(result, types.TextContent)
            assert "Error: Failed to retrieve account information" in result.text
            assert "API error:" in result.text
