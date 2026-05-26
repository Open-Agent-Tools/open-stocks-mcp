"""Live market test harness: opt-in controls, credential preflight, and safety guards.

Live tests require both the --run-live-market CLI flag and the OPEN_STOCKS_RUN_LIVE_MARKET=1
environment variable.  Credentials (ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD) must also be
present before any broker session or network call is attempted.

Usage (Robinhood):
    OPEN_STOCKS_RUN_LIVE_MARKET=1 uv run pytest tests/integration -m live_market \\
        --run-live-market --maxfail=1

Usage (Schwab):
    OPEN_STOCKS_RUN_LIVE_MARKET=1 RUN_RATE_LIMITED=1 ENABLED_BROKERS=schwab \\
        uv run pytest tests/integration/test_schwab_live_journeys.py \\
        -m "live_market and auth_required and rate_limited" --run-live-market -q
"""

import os
from collections.abc import Generator
from typing import Any

import pytest

LIVE_MARKET_ENV_VAR = "OPEN_STOCKS_RUN_LIVE_MARKET"

LIVE_MARKET_SKIP_REASON = (
    "live_market test; set OPEN_STOCKS_RUN_LIVE_MARKET=1 and pass "
    "--run-live-market to enable"
)
_CRED_SKIP_REASON = (
    "live_market test requires ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD"
)
_SCHWAB_CRED_SKIP_REASON = (
    "Schwab live test requires SCHWAB_API_KEY and SCHWAB_APP_SECRET env vars"
)
_SCHWAB_TOKEN_SKIP_REASON = (
    "Schwab live test requires a pre-existing token at SCHWAB_TOKEN_PATH "
    "(default: ~/.tokens/schwab_token.json). Run interactive auth once first."
)

_PROHIBITED_PREFIXES = ("order_", "cancel_")

_SCHWAB_PROHIBITED_TOOLS = frozenset(
    {
        "schwab_buy_market",
        "schwab_buy_stock_market",
        "schwab_buy_stock_limit",
        "schwab_cancel_order",
        "schwab_sell_market",
        "schwab_sell_stock_market",
        "schwab_sell_stock_limit",
        "schwab_buy_limit",
        "schwab_sell_limit",
        "cancel_schwab_order",
        "schwab_cancel_all_stock_orders",
        "schwab_option_buy_to_open",
        "schwab_option_sell_to_close",
        "schwab_order_sell_stop",
        "schwab_cancel_all_option_orders",
        "schwab_cancel_option_order",
        "schwab_order_option_credit_spread",
        "schwab_order_option_debit_spread",
        "schwab_order_buy_option_limit",
        "schwab_order_sell_option_limit",
        "schwab_replace_order",
        "place_schwab_order",
        "schwab_place_order",
    }
)


def require_live_market_preflight(pytestconfig: Any) -> None:
    """Skip the calling test unless the live-market opt-in is fully satisfied.

    Checks (in order):
    1. --run-live-market CLI flag is set.
    2. OPEN_STOCKS_RUN_LIVE_MARKET env var is set to a truthy value.
    3. ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD are both present.

    Raises pytest.skip.Exception if any condition is not met.
    """
    if not pytestconfig.getoption("--run-live-market", default=False):
        pytest.skip(LIVE_MARKET_SKIP_REASON)

    if not os.environ.get(LIVE_MARKET_ENV_VAR):
        pytest.skip(LIVE_MARKET_SKIP_REASON)

    username = os.environ.get("ROBINHOOD_USERNAME")
    password = os.environ.get("ROBINHOOD_PASSWORD")
    if not username or not password:
        pytest.skip(_CRED_SKIP_REASON)


def require_schwab_live_preflight(pytestconfig: Any) -> None:
    """Skip the calling test unless the Schwab live-market opt-in is fully satisfied.

    Checks (in order):
    1. --run-live-market CLI flag is set.
    2. OPEN_STOCKS_RUN_LIVE_MARKET env var is set to a truthy value.
    3. SCHWAB_API_KEY and SCHWAB_APP_SECRET are both present.
    4. A pre-existing token file is available (non-interactive pytest cannot do OAuth).

    Raises pytest.skip.Exception if any condition is not met.
    """
    if not pytestconfig.getoption("--run-live-market", default=False):
        pytest.skip(LIVE_MARKET_SKIP_REASON)

    if not os.environ.get(LIVE_MARKET_ENV_VAR):
        pytest.skip(LIVE_MARKET_SKIP_REASON)

    api_key = os.environ.get("SCHWAB_API_KEY")
    app_secret = os.environ.get("SCHWAB_APP_SECRET")
    if not api_key or not app_secret:
        pytest.skip(_SCHWAB_CRED_SKIP_REASON)

    from pathlib import Path

    token_path_env = os.environ.get("SCHWAB_TOKEN_PATH")
    token_path = Path(token_path_env) if token_path_env else Path.home() / ".tokens" / "schwab_token.json"
    if not token_path.exists():
        pytest.skip(_SCHWAB_TOKEN_SKIP_REASON)


def assert_live_market_read_only(tool_name: str) -> None:
    """Raise ValueError if tool_name is a prohibited trading or cancellation helper.

    Trading and cancellation tools are financially unsafe in automated tests.
    Any tool name beginning with ``order_`` or ``cancel_`` is rejected.
    """
    for prefix in _PROHIBITED_PREFIXES:
        if tool_name.startswith(prefix):
            raise ValueError(
                f"Live market tests may not call '{tool_name}': "
                f"tools beginning with '{prefix}' are prohibited in automated runs. "
                "Use manual testing only for order placement and cancellation."
            )


def assert_live_schwab_read_only(tool_name: str) -> None:
    """Raise ValueError if tool_name is a prohibited Schwab trading or cancellation helper.

    Order placement and cancellation tools are financially unsafe in automated tests.
    The full list of prohibited Schwab tool names is maintained in _SCHWAB_PROHIBITED_TOOLS.
    """
    if tool_name in _SCHWAB_PROHIBITED_TOOLS:
        raise ValueError(
            f"Schwab live market tests may not call '{tool_name}': "
            "order placement and cancellation tools are prohibited in automated runs. "
            "Use manual testing only for order placement and cancellation."
        )
    for prefix in _PROHIBITED_PREFIXES:
        if tool_name.startswith(prefix):
            raise ValueError(
                f"Schwab live market tests may not call '{tool_name}': "
                f"tools beginning with '{prefix}' are prohibited in automated runs."
            )


@pytest.fixture(scope="module")
def live_robinhood_session(request: Any) -> Any:
    """Module-scoped fixture that opens a real Robinhood session.

    Skips the test module when the live-market opt-in is absent or credentials
    are missing.  Logs out automatically after all tests in the module complete.
    """
    require_live_market_preflight(request.config)

    username = os.environ["ROBINHOOD_USERNAME"]
    password = os.environ["ROBINHOOD_PASSWORD"]

    import robin_stocks.robinhood as rh

    login_result = rh.login(username, password)
    if not login_result:
        pytest.skip("Robinhood login failed — check credentials")

    yield

    rh.logout()


@pytest.fixture(scope="module")
def live_schwab_broker(request: Any) -> Generator[Any, None, None]:
    """Module-scoped fixture that creates an authenticated SchwabBroker instance.

    Skips the entire test module when:
    - --run-live-market flag is absent
    - OPEN_STOCKS_RUN_LIVE_MARKET env var is not set
    - SCHWAB_API_KEY or SCHWAB_APP_SECRET are missing
    - No pre-existing token file is found (non-interactive auth is not possible in pytest)

    The broker is registered in an isolated BrokerRegistry and monkeypatched into
    the tool layer so direct Schwab tool calls use this authenticated instance.
    """
    require_schwab_live_preflight(request.config)

    from pathlib import Path

    api_key = os.environ["SCHWAB_API_KEY"]
    app_secret = os.environ["SCHWAB_APP_SECRET"]
    callback_url = os.environ.get("SCHWAB_CALLBACK_URL", "https://127.0.0.1:8182/")
    token_path_env = os.environ.get("SCHWAB_TOKEN_PATH")
    token_path = str(token_path_env) if token_path_env else str(Path.home() / ".tokens" / "schwab_token.json")

    from open_stocks_mcp.brokers.registry import BrokerRegistry
    from open_stocks_mcp.brokers.schwab import SchwabBroker

    broker = SchwabBroker(
        api_key=api_key,
        app_secret=app_secret,
        callback_url=callback_url,
        token_path=token_path,
    )

    import asyncio

    auth_ok = asyncio.get_event_loop().run_until_complete(broker.authenticate())
    if not auth_ok:
        pytest.skip("Schwab authentication failed — check token file and credentials")

    registry = BrokerRegistry()
    registry.register(broker)

    # Replace the function reference tools use via broker_utils
    import open_stocks_mcp.tools.broker_utils as broker_utils_module
    from open_stocks_mcp.brokers import registry as registry_module

    registry_module._registry = registry  # type: ignore[attr-defined]
    broker_utils_module.__dict__["_patched_registry_active"] = True

    yield broker

    # Restore original global registry state
    registry_module._registry = None  # type: ignore[attr-defined]
    broker_utils_module.__dict__.pop("_patched_registry_active", None)
