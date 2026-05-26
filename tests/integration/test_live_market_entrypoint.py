"""Read-only live market entrypoint test.

This module provides the first live-market integration test using a low-risk
market-data call.  It requires explicit opt-in (see live_market_harness.py).
"""

import pytest

from tests.integration.live_market_harness import (
    assert_live_market_read_only,
)


@pytest.mark.integration
@pytest.mark.live_market
@pytest.mark.auth_required
@pytest.mark.rate_limited
@pytest.mark.journey_market_data
def test_get_stock_price_aapl(live_robinhood_session: object) -> None:
    """Verify that get_stock_price('AAPL') returns a result dict over a live session."""
    import asyncio

    assert_live_market_read_only("get_stock_price")

    from open_stocks_mcp.tools.stocks.quote import get_stock_price

    result = asyncio.get_event_loop().run_until_complete(get_stock_price("AAPL"))
    assert isinstance(result, dict), "Response must be a dict"
    assert "result" in result, "Response must contain a 'result' key"
    assert isinstance(result["result"], dict), "'result' value must be a dict"
