"""Identity assertions for market data module split compatibility."""

from open_stocks_mcp.tools.market.movers import (
    get_stocks_by_tag as movers_get_stocks_by_tag,
)
from open_stocks_mcp.tools.market.movers import (
    get_top_100 as movers_get_top_100,
)
from open_stocks_mcp.tools.market.movers import (
    get_top_movers as movers_get_top_movers,
)
from open_stocks_mcp.tools.market.movers import (
    get_top_movers_sp500 as movers_get_top_movers_sp500,
)
from open_stocks_mcp.tools.market.news import (
    get_stock_news as news_get_stock_news,
)
from open_stocks_mcp.tools.market.ratings import (
    get_stock_ratings as ratings_get_stock_ratings,
)
from open_stocks_mcp.tools.robinhood_market_data_tools import (
    get_stock_news as legacy_get_stock_news,
)
from open_stocks_mcp.tools.robinhood_market_data_tools import (
    get_stock_ratings as legacy_get_stock_ratings,
)
from open_stocks_mcp.tools.robinhood_market_data_tools import (
    get_stocks_by_tag as legacy_get_stocks_by_tag,
)
from open_stocks_mcp.tools.robinhood_market_data_tools import (
    get_top_100 as legacy_get_top_100,
)
from open_stocks_mcp.tools.robinhood_market_data_tools import (
    get_top_movers as legacy_get_top_movers,
)
from open_stocks_mcp.tools.robinhood_market_data_tools import (
    get_top_movers_sp500 as legacy_get_top_movers_sp500,
)


class TestMarketDataModuleSplit:
    """Verify legacy re-exports are the same objects as the new module exports."""

    def test_get_top_movers_sp500_identity(self) -> None:
        assert legacy_get_top_movers_sp500 is movers_get_top_movers_sp500

    def test_get_top_100_identity(self) -> None:
        assert legacy_get_top_100 is movers_get_top_100

    def test_get_top_movers_identity(self) -> None:
        assert legacy_get_top_movers is movers_get_top_movers

    def test_get_stocks_by_tag_identity(self) -> None:
        assert legacy_get_stocks_by_tag is movers_get_stocks_by_tag

    def test_get_stock_ratings_identity(self) -> None:
        assert legacy_get_stock_ratings is ratings_get_stock_ratings

    def test_get_stock_news_identity(self) -> None:
        assert legacy_get_stock_news is news_get_stock_news
