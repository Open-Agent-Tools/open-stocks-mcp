"""CI-safe benchmarks for representative MCP tool wrappers."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from open_stocks_mcp.server.app import account_info, portfolio, stock_price


@pytest.mark.performance
def test_benchmark_account_info(benchmark: Any) -> None:
    mock_get_account_info = AsyncMock(
        return_value={"result": {"username": "benchmark-user", "status": "success"}}
    )

    with patch(
        "open_stocks_mcp.server.app.get_account_info",
        mock_get_account_info,
    ):
        result = benchmark(lambda: asyncio.run(account_info()))

    assert result["result"]["username"] == "benchmark-user"
    mock_get_account_info.assert_awaited()


@pytest.mark.performance
def test_benchmark_portfolio(benchmark: Any) -> None:
    mock_get_portfolio = AsyncMock(
        return_value={"result": {"market_value": "1000.00", "status": "success"}}
    )

    with patch("open_stocks_mcp.server.app.get_portfolio", mock_get_portfolio):
        result = benchmark(lambda: asyncio.run(portfolio()))

    assert result["result"]["market_value"] == "1000.00"
    mock_get_portfolio.assert_awaited()


@pytest.mark.performance
def test_benchmark_stock_price(benchmark: Any) -> None:
    mock_get_stock_price = AsyncMock(
        return_value={
            "result": {"symbol": "AAPL", "price": 150.25, "status": "success"}
        }
    )

    with patch("open_stocks_mcp.server.app.get_stock_price", mock_get_stock_price):
        result = benchmark(lambda: asyncio.run(stock_price("AAPL")))

    assert result["result"]["symbol"] == "AAPL"
    mock_get_stock_price.assert_any_await("AAPL")
