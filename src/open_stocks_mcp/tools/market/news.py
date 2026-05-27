"""Stock news tools."""

from typing import Any

import robin_stocks.robinhood as rh

from open_stocks_mcp.brokers.session_state import get_session_manager
from open_stocks_mcp.logging_config import logger
from open_stocks_mcp.tools.error_handling import (
    create_error_response,
    create_no_data_response,
    create_success_response,
    execute_with_retry,
    handle_robin_stocks_errors,
    log_api_call,
    validate_symbol,
)


@handle_robin_stocks_errors
async def get_stock_news(symbol: str) -> dict[str, Any]:
    """Get news stories for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        JSON object with news stories in "result" field:
        {
            "result": {
                "symbol": "AAPL",
                "news": [
                    {
                        "title": "Apple Reports Strong Q2 Results",
                        "author": "Tech News Reporter",
                        "published_at": "2024-07-09T14:30:00Z",
                        "source": "TechCrunch",
                        "summary": "Apple exceeded expectations...",
                        "url": "https://...",
                        "preview_image_url": "https://...",
                        "num_clicks": 1250
                    }
                ],
                "count": 20
            }
        }
    """
    try:
        # Input validation
        if not validate_symbol(symbol):
            return create_error_response(
                ValueError(f"Invalid symbol format: {symbol}"), "symbol validation"
            )

        symbol = symbol.strip().upper()

        # Ensure authenticated
        session_mgr = get_session_manager()
        if not await session_mgr.ensure_authenticated():
            return create_error_response(
                ValueError("Authentication required"), "authentication"
            )

        log_api_call("get_stock_news", symbol=symbol)

        # Get news with retry logic
        news_data = await execute_with_retry(rh.get_news, symbol)

        if not news_data:
            return create_no_data_response(
                f"No news data found for symbol: {symbol}", {"symbol": symbol}
            )

        return create_success_response(
            {"symbol": symbol, "news": news_data, "count": len(news_data)}
        )

    except Exception as e:
        logger.error(f"Failed to get news for {symbol}: {e}")
        return create_error_response(e, "get_stock_news")
