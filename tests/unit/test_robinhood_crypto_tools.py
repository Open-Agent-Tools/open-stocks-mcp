"""Unit tests for robinhood_crypto_tools — ensures stubs raise, not silently return."""

import pytest

from open_stocks_mcp.tools.robinhood_crypto_tools import get_crypto_positions


class TestCryptoPositionsStub:
    """get_crypto_positions must raise NotImplementedError, not return not_implemented."""

    @pytest.mark.unit
    @pytest.mark.journey_system
    @pytest.mark.asyncio
    async def test_raises_not_implemented(self) -> None:
        with pytest.raises(
            NotImplementedError, match="Crypto positions are not yet implemented"
        ):
            await get_crypto_positions()

    @pytest.mark.unit
    @pytest.mark.journey_system
    @pytest.mark.asyncio
    async def test_is_not_registered_as_mcp_tool(self) -> None:
        """Confirm crypto_tools is not imported by the server module."""
        import open_stocks_mcp.server.app as app_module

        app_src = app_module.__file__
        assert app_src is not None

        with open(app_src) as fh:
            src = fh.read()

        assert "robinhood_crypto_tools" not in src, (
            "robinhood_crypto_tools should not be imported in server/app.py"
        )
