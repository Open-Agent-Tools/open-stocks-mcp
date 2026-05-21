"""Live market test harness: opt-in controls, credential preflight, and safety guards.

Live tests require both the --run-live-market CLI flag and the OPEN_STOCKS_RUN_LIVE_MARKET=1
environment variable.  Credentials (ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD) must also be
present before any broker session or network call is attempted.

Usage:
    OPEN_STOCKS_RUN_LIVE_MARKET=1 uv run pytest tests/integration -m live_market \\
        --run-live-market --maxfail=1
"""

import os
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

_PROHIBITED_PREFIXES = ("order_", "cancel_")


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


@pytest.fixture(scope="module")
def live_robinhood_session(request: Any) -> Any:  # type: ignore[misc]
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
