"""Tests for Robin Stocks MCP tools."""

import pytest
from mcp import types

from open_stocks_mcp.tools.robinhood_tools import (
    account_info,
    auth_status,
    auto_login,
    logout_robinhood,
    pass_through_mfa,
)


class TestRobinhoodTools:
    """Test Robin Stocks MCP tools."""

    @pytest.mark.asyncio
    async def test_auto_login_no_parameters(self) -> None:
        """Test auto_login tool requires no parameters."""
        # auto_login reads from environment variables
        result = await auto_login()
        assert isinstance(result, types.TextContent)

    @pytest.mark.asyncio
    async def test_pass_through_mfa_requires_parameter(self) -> None:
        """Test pass_through_mfa tool requires mfa_code parameter."""
        with pytest.raises(TypeError):
            await pass_through_mfa()  # Missing required mfa_code parameter

    @pytest.mark.asyncio
    async def test_pass_through_mfa_accepts_string_parameter(self) -> None:
        """Test pass_through_mfa tool accepts string mfa_code parameter."""
        result = await pass_through_mfa("123456")
        assert isinstance(result, types.TextContent)

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


class TestRobinhoodToolsReturnTypes:
    """Test return types and basic structure of Robin Stocks tools."""

    @pytest.mark.asyncio
    async def test_auto_login_returns_text_content(self) -> None:
        """Test auto_login returns TextContent."""
        result = await auto_login()
        assert isinstance(result, types.TextContent)
        assert result.type == "text"
        assert isinstance(result.text, str)
        assert len(result.text) > 0

    @pytest.mark.asyncio
    async def test_pass_through_mfa_returns_text_content(self) -> None:
        """Test pass_through_mfa returns TextContent."""
        result = await pass_through_mfa("123456")
        assert isinstance(result, types.TextContent)
        assert result.type == "text"
        assert isinstance(result.text, str)
        assert len(result.text) > 0