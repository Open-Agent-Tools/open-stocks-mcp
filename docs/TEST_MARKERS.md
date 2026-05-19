# Test Marker Taxonomy

Pytest markers used in this project to categorize and filter tests.

## Marker Definitions

### Exclusion Categories (excluded by default)

| Marker | Purpose | When to use |
|--------|---------|-------------|
| `rate_limited` | Tests that call live broker APIs and may trigger rate limiting | Any test making real API calls to Robinhood or Schwab |
| `live_market` | Tests that require an active market connection or real-time data | Tests verifying live quote feeds, streaming data, or market-hours-sensitive logic |
| `performance` | Benchmark and throughput tests | Tests measuring latency, throughput, or resource usage |

These three markers are excluded from the **default** `pytest` invocation via `addopts` in `pyproject.toml`. Running `pytest` without arguments will never collect tests with these markers.

### Opt-In Categories

| Marker | Purpose |
|--------|---------|
| `auth_required` | Tests that require valid broker credentials in env vars |
| `integration` | Tests that exercise multiple real components together |
| `slow` | Tests that take more than ~5 seconds |
| `exception_test` | Error/edge-case paths, often verbose |
| `login_flow` | Full credential-round-trip tests |
| `agent_evaluation` | ADK agent evaluation harness tests |

### Unit / Journey Categories

| Marker | Purpose |
|--------|---------|
| `unit` | Fast, isolated, no network |
| `journey_account` | Account management flows |
| `journey_portfolio` | Portfolio and positions |
| `journey_market_data` | Stock quotes and market info |
| `journey_research` | Earnings, ratings, news |
| `journey_watchlists` | Watchlist CRUD |
| `journey_options` | Options chains and positions |
| `journey_notifications` | Alerts and margin calls |
| `journey_system` | Health checks and metrics |
| `journey_advanced_data` | Level II and premium data |
| `journey_market_intelligence` | Movers and trending stocks |
| `journey_trading` | Buy/sell order workflows |

---

## Default Behavior

Running `pytest` with no arguments applies:

```
not rate_limited and not live_market and not performance
```

This ensures the default test suite is safe for CI and local development without broker credentials.

---

## CI-Safe Invocation Paths

### Local development — fast feedback loop
```bash
pytest                             # default: excludes rate_limited, live_market, performance
pytest -m unit                     # only unit tests
pytest tests/unit/                 # all unit tests by directory
pytest -m "not slow and not exception_test"  # skip slow/noisy tests
```

### CI pipeline — safe default
```bash
uv run pytest -m 'not rate_limited and not live_market and not performance'
uv run ruff check src tests
```

### Full suite — requires credentials
```bash
# Set ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD first
pytest -m ""                       # override addopts, run everything
pytest -m "rate_limited"           # only rate-limited tests
pytest -m "live_market"            # only live-market tests
pytest -m "auth_required"          # only auth-required tests
```

### Journey-based runs (no credentials needed)
```bash
pytest -m "journey_account or journey_portfolio"
pytest -m "journey_market_data or journey_research"
pytest -m "journey_account or journey_portfolio or journey_market_data or journey_research or journey_notifications or journey_system"  # read-only journeys
```

---

## Applying Markers to New Tests

```python
import pytest

@pytest.mark.rate_limited
def test_my_api_call():
    """Hits live broker API — excluded from default runs."""
    ...

@pytest.mark.live_market
def test_live_quote():
    """Requires active market feed."""
    ...

@pytest.mark.performance
def test_throughput():
    """Measures request throughput — run manually."""
    ...
```

Multiple markers can be stacked:

```python
@pytest.mark.rate_limited
@pytest.mark.auth_required
def test_live_order():
    ...
```
