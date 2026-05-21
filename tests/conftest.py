"""Shared pytest fixtures for open-stocks-mcp tests."""

import os
import sys
from typing import Any
from unittest.mock import MagicMock

try:
    import pytest_asyncio  # noqa: F401
except ImportError:
    print(
        "\n\033[91mERROR: pytest-asyncio is not installed.\033[0m\n"
        "Run tests with:  uv run pytest\n"
        "Or install deps: uv sync\n",
        file=sys.stderr,
    )
    sys.exit(1)

import pytest

from tests.fixtures import broker_payloads
from tests.integration.live_market_harness import (
    LIVE_MARKET_ENV_VAR,
    LIVE_MARKET_SKIP_REASON,
)

RATE_LIMITED_SKIP_REASON = (
    "rate_limited test; set RUN_RATE_LIMITED=1 or pass '-m rate_limited' to enable"
)
PERFORMANCE_SKIP_REASON = (
    "performance test; set RUN_PERFORMANCE=1 or pass '-m performance' to enable"
)


def pytest_configure(config: Any) -> None:
    """Configure pytest with journey markers for organized testing."""
    config.addinivalue_line(
        "markers",
        "rate_limited: marks tests that may hit live endpoints with rate limit risk "
        "(skipped by default; opt in with '-m rate_limited' or RUN_RATE_LIMITED=1)",
    )
    config.addinivalue_line(
        "markers",
        "performance: marks tests as performance/benchmark tests "
        "(skipped by default; opt in with '-m performance' or RUN_PERFORMANCE=1)",
    )
    config.addinivalue_line(
        "markers",
        "journey_account: Account management tests (account_info, profiles, settings)",
    )
    config.addinivalue_line(
        "markers",
        "journey_portfolio: Portfolio & holdings tests (portfolio, positions, build_holdings)",
    )
    config.addinivalue_line(
        "markers",
        "journey_market_data: Stock quotes & market info tests (stock_price, market_hours, search)",
    )
    config.addinivalue_line(
        "markers",
        "journey_research: Earnings, ratings, news tests (stock_earnings, dividends, ratings)",
    )
    config.addinivalue_line(
        "markers",
        "journey_watchlists: Watchlist management tests (all_watchlists, add/remove)",
    )
    config.addinivalue_line(
        "markers",
        "journey_options: Options analysis tests (options_chains, positions, market_data)",
    )
    config.addinivalue_line(
        "markers",
        "journey_notifications: Alerts & notifications tests (notifications, margin_calls)",
    )
    config.addinivalue_line(
        "markers",
        "journey_system: Health & monitoring tests (health_check, metrics, session_status)",
    )
    config.addinivalue_line(
        "markers",
        "journey_advanced_data: Level II & premium features tests (pricebook, level2_data)",
    )
    config.addinivalue_line(
        "markers",
        "journey_market_intelligence: Movers & trends tests (top_movers, top_100_stocks)",
    )
    config.addinivalue_line(
        "markers",
        "journey_trading: Trading operations tests (buy/sell orders, cancellation)",
    )


def pytest_addoption(parser: Any) -> None:
    """Register the --run-live-market CLI option."""
    parser.addoption(
        "--run-live-market",
        action="store_true",
        default=False,
        help=(
            "Enable live-market tests. Also requires "
            "OPEN_STOCKS_RUN_LIVE_MARKET=1 and valid Robinhood credentials."
        ),
    )


def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
    """Skip opt-in test groups unless explicitly selected."""
    markexpr = config.option.markexpr or ""

    if "rate_limited" not in markexpr and not os.environ.get("RUN_RATE_LIMITED"):
        skip_rate_limited = pytest.mark.skip(reason=RATE_LIMITED_SKIP_REASON)
        for item in items:
            if list(item.iter_markers(name="rate_limited")):
                item.add_marker(skip_rate_limited)

    if "performance" not in markexpr and not os.environ.get("RUN_PERFORMANCE"):
        skip_performance = pytest.mark.skip(reason=PERFORMANCE_SKIP_REASON)
        for item in items:
            if list(item.iter_markers(name="performance")):
                item.add_marker(skip_performance)

    getoption = getattr(config, "getoption", None)
    run_live = (
        getoption("--run-live-market", default=False)
        if getoption is not None
        else False
    )
    env_live = bool(os.environ.get(LIVE_MARKET_ENV_VAR))
    if not (run_live and env_live):
        skip_live = pytest.mark.skip(reason=LIVE_MARKET_SKIP_REASON)
        for item in items:
            if list(item.iter_markers(name="live_market")):
                item.add_marker(skip_live)


@pytest.fixture
def mock_robin_stocks() -> MagicMock:
    """Mock robin_stocks module for testing."""
    mock_rh = MagicMock()
    mock_rh.stocks.get_latest_price.return_value = ["100.50"]
    mock_rh.profiles.load_portfolio_profile.return_value = {
        "total_return_today": "25.50",
        "market_value": "1000.00",
    }
    return mock_rh


@pytest.fixture
def sample_stock_data() -> dict[str, float | int | str]:
    """Sample stock data for testing."""
    return {
        "symbol": "AAPL",
        "price": 150.25,
        "change": 2.50,
        "change_percent": 1.69,
        "volume": 50000000,
    }


@pytest.fixture
def sample_portfolio_data() -> dict[str, Any]:
    """Sample portfolio data for testing."""
    return {
        "total_return_today": "25.50",
        "market_value": "1000.00",
        "total_return_today_percent": "2.61",
        "day_trade_buying_power": "0.00",
    }


@pytest.fixture
def robinhood_quote_payload() -> dict[str, Any]:
    """Representative Robinhood quote payload."""
    return broker_payloads.robinhood_quote_payload()


@pytest.fixture
def robinhood_fundamentals_payload() -> dict[str, Any]:
    """Representative Robinhood fundamentals payload."""
    return broker_payloads.robinhood_fundamentals_payload()


@pytest.fixture
def robinhood_instrument_payload() -> dict[str, Any]:
    """Representative Robinhood instrument payload."""
    return broker_payloads.robinhood_instrument_payload()


@pytest.fixture
def robinhood_search_payload() -> list[dict[str, Any]]:
    """Representative Robinhood search payload."""
    return broker_payloads.robinhood_search_payload()


@pytest.fixture
def robinhood_user_profile_payload() -> dict[str, Any]:
    """Representative Robinhood user profile payload."""
    return broker_payloads.robinhood_user_profile_payload()


@pytest.fixture
def robinhood_portfolio_payload() -> dict[str, Any]:
    """Representative Robinhood portfolio payload."""
    return broker_payloads.robinhood_portfolio_payload()


@pytest.fixture
def robinhood_positions_payload() -> list[dict[str, Any]]:
    """Representative Robinhood positions payload."""
    return broker_payloads.robinhood_positions_payload()


@pytest.fixture
def robinhood_phoenix_account_payload() -> dict[str, Any]:
    """Representative Robinhood phoenix account payload."""
    return broker_payloads.robinhood_phoenix_account_payload()


@pytest.fixture
def robinhood_build_holdings_payload() -> dict[str, Any]:
    """Representative Robinhood build_holdings payload."""
    return broker_payloads.robinhood_build_holdings_payload()


@pytest.fixture
def schwab_quote_payload() -> dict[str, Any]:
    """Representative Schwab quote payload."""
    return broker_payloads.schwab_quote_payload()


@pytest.fixture
def schwab_quotes_payload() -> dict[str, Any]:
    """Representative Schwab multi-quote payload."""
    return broker_payloads.schwab_quotes_payload()


@pytest.fixture
def schwab_price_history_payload() -> dict[str, Any]:
    """Representative Schwab price-history payload."""
    return broker_payloads.schwab_price_history_payload()


@pytest.fixture
def schwab_account_numbers_payload() -> list[dict[str, Any]]:
    """Representative Schwab account-number payload."""
    return broker_payloads.schwab_account_numbers_payload()


@pytest.fixture
def schwab_account_payload() -> dict[str, Any]:
    """Representative Schwab account payload."""
    return broker_payloads.schwab_account_payload()


@pytest.fixture
def schwab_accounts_payload() -> list[dict[str, Any]]:
    """Representative Schwab accounts payload."""
    return broker_payloads.schwab_accounts_payload()


@pytest.fixture
def schwab_balances_payload() -> dict[str, Any]:
    """Representative Schwab balances payload."""
    return broker_payloads.schwab_balances_payload()


@pytest.fixture
def broker_auth_error_payload() -> dict[str, Any]:
    """Structured broker authentication error response."""
    return broker_payloads.broker_auth_error_payload()


# Journey-specific fixtures


@pytest.fixture
def journey_account_data() -> dict[str, Any]:
    """Account management journey fixture data."""
    return {
        "account_number": "12345678",
        "account_type": "cash",
        "deactivated": False,
        "deposit_halted": False,
        "only_position_closing_trades": False,
        "buying_power": "1000.00",
        "cash": "500.00",
        "cash_available_for_withdrawal": "400.00",
        "cash_held_for_orders": "100.00",
        "created_at": "2023-01-01T00:00:00.000000Z",
        "day_trade_buying_power": "2000.00",
        "day_trade_buying_power_held_for_orders": "0.00",
        "day_trade_ratio": "0.00",
        "day_trades_protection": True,
        "instant_eligibility": {
            "reason": "",
            "reinstatement_date": None,
            "reversal": "",
            "state": "ok",
        },
        "margin_balances": {
            "cash": "500.00",
            "cash_available_for_withdrawal": "400.00",
            "cash_held_for_orders": "100.00",
            "day_trade_buying_power": "2000.00",
            "day_trade_buying_power_held_for_orders": "0.00",
            "day_trade_ratio": "0.00",
            "marked_pattern_day_trader_date": None,
            "max_ach_early_access_amount": "1000.00",
            "overnight_buying_power": "1000.00",
            "overnight_buying_power_held_for_orders": "0.00",
            "overnight_ratio": "0.00",
            "unallocated_margin_cash": "500.00",
            "unsettled_debit": "0.00",
        },
        "max_ach_early_access_amount": "1000.00",
        "overnight_buying_power": "1000.00",
        "overnight_buying_power_held_for_orders": "0.00",
        "overnight_ratio": "0.00",
        "portfolio_cash": "500.00",
        "position_buying_power": "1000.00",
        "rhs_account_number": "RH12345678",
        "sma": "1000.00",
        "sma_held_for_orders": "0.00",
        "total_positions_value": "500.00",
        "uncleared_deposits": "0.00",
        "unsettled_funds": "0.00",
        "updated_at": "2023-01-01T12:00:00.000000Z",
        "withdrawal_halted": False,
    }


@pytest.fixture
def journey_portfolio_data() -> dict[str, Any]:
    """Portfolio & holdings journey fixture data."""
    return {
        "results": [
            {
                "account": "https://robinhood.com/accounts/12345678/",
                "average_buy_price": "145.50",
                "created_at": "2023-01-01T10:00:00.000000Z",
                "instrument": "https://robinhood.com/instruments/450dfc6d-5510-4d40-abfb-f633b7d9be3e/",
                "instrument_id": "450dfc6d-5510-4d40-abfb-f633b7d9be3e",
                "pending_average_buy_price": "145.50",
                "quantity": "10.00000000",
                "shares_available_for_exercise": "10.00000000",
                "shares_available_for_closing": "10.00000000",
                "shares_held_for_buys": "0.00000000",
                "shares_held_for_sells": "0.00000000",
                "shares_held_for_stock_grants": "0.00000000",
                "shares_pending_from_options_events": "0.00000000",
                "symbol": "AAPL",
                "updated_at": "2023-01-01T16:00:00.000000Z",
                "url": "https://robinhood.com/positions/12345678/450dfc6d-5510-4d40-abfb-f633b7d9be3e/",
            }
        ]
    }


@pytest.fixture
def journey_market_data() -> dict[str, Any]:
    """Market data journey fixture data."""
    return {
        "ask_price": "150.25",
        "ask_size": 100,
        "bid_price": "150.20",
        "bid_size": 200,
        "last_trade_price": "150.22",
        "last_extended_hours_trade_price": "150.18",
        "previous_close": "148.50",
        "adjusted_previous_close": "148.50",
        "previous_close_date": "2023-12-29",
        "symbol": "AAPL",
        "trading_halted": False,
        "has_traded": True,
        "last_trade_price_source": "consolidated",
        "updated_at": "2023-12-30T20:59:59.000000Z",
        "instrument": "https://robinhood.com/instruments/450dfc6d-5510-4d40-abfb-f633b7d9be3e/",
        "instrument_id": "450dfc6d-5510-4d40-abfb-f633b7d9be3e",
    }


@pytest.fixture
def journey_research_data() -> dict[str, Any]:
    """Research journey fixture data."""
    return {
        "earnings": [
            {
                "symbol": "AAPL",
                "eps": {"estimate": 1.45, "actual": 1.52},
                "revenue": {"estimate": 117500000000, "actual": 119580000000},
                "year": 2023,
                "quarter": 4,
                "call": {"datetime": "2024-01-25T21:30:00.000Z", "broadcast_url": None},
                "report": {
                    "date": "2024-01-25",
                    "timing": "after_market",
                    "verified": True,
                },
            }
        ],
        "dividends": [
            {
                "account": "https://robinhood.com/accounts/12345678/",
                "amount": "2.30",
                "drip_enabled": True,
                "execution_date": "2023-11-16",
                "id": "div123",
                "instrument": "https://robinhood.com/instruments/450dfc6d-5510-4d40-abfb-f633b7d9be3e/",
                "payable_date": "2023-11-16",
                "position": "10.00000000",
                "rate": "0.23",
                "record_date": "2023-11-13",
                "symbol": "AAPL",
                "withholding": "0.00",
            }
        ],
    }


@pytest.fixture
def journey_watchlist_data() -> dict[str, Any]:
    """Watchlist journey fixture data."""
    return {
        "results": [
            {
                "name": "My First List",
                "url": "https://robinhood.com/midlands/lists/items/abc123/",
                "user": "https://robinhood.com/user/456def/",
                "instruments": [
                    {
                        "symbol": "AAPL",
                        "name": "Apple Inc.",
                        "instrument_url": "https://robinhood.com/instruments/450dfc6d-5510-4d40-abfb-f633b7d9be3e/",
                    },
                    {
                        "symbol": "MSFT",
                        "name": "Microsoft Corporation",
                        "instrument_url": "https://robinhood.com/instruments/50810c35-d215-4866-9758-0ada4ac79ffa/",
                    },
                ],
            }
        ]
    }


@pytest.fixture
def journey_options_data() -> dict[str, Any]:
    """Options journey fixture data."""
    return {
        "results": [
            {
                "chain_id": "abc123",
                "chain_symbol": "AAPL",
                "created_at": "2023-01-01T00:00:00.000000Z",
                "expiration_date": "2024-01-19",
                "id": "opt123",
                "issue_date": "2023-01-01",
                "min_ticks": {
                    "above_tick": "0.05",
                    "below_tick": "0.01",
                    "cutoff_price": "3.00",
                },
                "rhs_tradability": "tradable",
                "state": "active",
                "strike_price": "150.0000",
                "tradability": "tradable",
                "type": "call",
                "updated_at": "2023-01-01T12:00:00.000000Z",
                "url": "https://robinhood.com/options/instruments/opt123/",
            }
        ]
    }


@pytest.fixture
def journey_notifications_data() -> dict[str, Any]:
    """Notifications journey fixture data."""
    return {
        "results": [
            {
                "id": "notif123",
                "title": "Order Executed",
                "body": "Your buy order for 10 shares of AAPL at $150.22 has been executed.",
                "created_at": "2023-12-30T16:00:00.000000Z",
                "updated_at": "2023-12-30T16:00:00.000000Z",
                "category": "order_execution",
                "priority": "normal",
                "seen": False,
                "url": "https://robinhood.com/notifications/notif123/",
            }
        ]
    }


@pytest.fixture
def journey_system_data() -> dict[str, Any]:
    """System & monitoring journey fixture data."""
    return {
        "health_status": "ok",
        "session_active": True,
        "rate_limits": {
            "current_usage": 15,
            "limit_per_minute": 30,
            "limit_per_hour": 1000,
            "reset_time": "2023-12-30T21:01:00.000000Z",
        },
        "metrics": {
            "total_requests": 1500,
            "successful_requests": 1485,
            "failed_requests": 15,
            "average_response_time": 250,
            "uptime": "99.9%",
        },
    }
