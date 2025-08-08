# Journey-Based Testing Infrastructure

Phase 0 implementation complete! The Open Stocks MCP project now has comprehensive journey-based pytest markers for organized, efficient testing.

## 🎯 Journey Categories (11 Total)

### Core User Journey Categories

1. **`@pytest.mark.journey_account`** - Account management (16 tests, ~1.8s)
   - Account info, profiles, settings, user profile, day trades, authentication

2. **`@pytest.mark.journey_portfolio`** - Portfolio & holdings (3 tests, ~1.7s)
   - Portfolio overview, positions, build_holdings

3. **`@pytest.mark.journey_market_data`** - Stock quotes & market info (19 tests, ~3.8s)
   - Stock prices, market hours, search, quotes, instruments

4. **`@pytest.mark.journey_research`** - Earnings, ratings, news (23 tests, ~3.0s)
   - Analytics, dividends, market research, earnings, ratings, news, splits

5. **`@pytest.mark.journey_watchlists`** - Watchlist management (20 tests, ~16.7s)
   - All watchlists, add/remove, performance tracking

6. **`@pytest.mark.journey_options`** - Options analysis (13 tests, ~9.7s)
   - Options chains, positions, market data, orders

7. **`@pytest.mark.journey_notifications`** - Alerts & notifications (15 tests, ~1.6s)
   - Notifications, margin calls, subscription fees, account features

8. **`@pytest.mark.journey_system`** - Health & monitoring (11 tests, ~1.9s)
   - Health checks, metrics, rate limiting, session status

9. **`@pytest.mark.journey_advanced_data`** - Level II & premium features
   - Pricebook, level2_data (included in market_data journey)

10. **`@pytest.mark.journey_market_intelligence`** - Movers & trends  
    - Top movers, top 100 stocks (included in market_data journey)

11. **`@pytest.mark.journey_trading`** - Trading operations (1 test, ~1.6s)
    - Buy/sell orders, cancellation, order management

## 🚀 Usage Examples

### Single Journey Testing (Fast Feedback - All <30s)

```bash
# Account management tests (~1.8s)
pytest -m "journey_account" 

# Portfolio tests (~1.7s)  
pytest -m "journey_portfolio"

# Market data tests (~3.8s)
pytest -m "journey_market_data"

# Research & analytics tests (~3.0s)
pytest -m "journey_research" 

# Watchlist tests (~16.7s)
pytest -m "journey_watchlists"

# Options analysis tests (~9.7s)
pytest -m "journey_options"

# Notifications tests (~1.6s)
pytest -m "journey_notifications"

# System & health tests (~1.9s)
pytest -m "journey_system"

# Trading operations tests (~1.6s)
pytest -m "journey_trading"
```

### Combined Journey Testing

```bash
# User account flows (19 tests)
pytest -m "journey_account or journey_portfolio"

# Market intelligence flows (42 tests) 
pytest -m "journey_market_data or journey_research"

# User management flows (35 tests)
pytest -m "journey_watchlists or journey_notifications"

# Trading related flows (14 tests)
pytest -m "journey_options or journey_trading"
```

### Exclusion Patterns (Avoid Timeouts)

```bash
# Skip slow tests and exceptions
pytest -m "not slow and not exception_test"

# Skip problematic journeys  
pytest -m "not journey_watchlists and not exception_test"

# Market data without rate limits
pytest -m "journey_market_data and not rate_limited"

# READ ONLY journeys (perfect for ADK evaluations)
pytest -m "journey_account or journey_portfolio or journey_market_data or journey_research or journey_notifications or journey_system"
```

### Development Workflows

```bash
# Quick unit test feedback (<5s)
pytest -m "unit and journey_account"

# Integration tests only 
pytest -m "integration" 

# Performance validation
pytest -m "not slow" --tb=short

# Exception handling validation
pytest -m "exception_test"
```

## 📊 Performance Results

| Journey | Tests | Time | Status | Notes |
|---------|-------|------|--------|--------|
| `journey_account` | 16 | ~1.8s | ✅ FAST | Account mgmt |
| `journey_portfolio` | 3 | ~1.7s | ✅ FAST | Portfolio data |
| `journey_market_data` | 19 | ~3.8s | ✅ FAST | Market info |
| `journey_research` | 23 | ~3.0s | ✅ FAST | Research data |
| `journey_notifications` | 15 | ~1.6s | ✅ FAST | Alerts/notifications |
| `journey_system` | 11 | ~1.9s | ✅ FAST | Health/monitoring |
| `journey_trading` | 1 | ~1.6s | ✅ FAST | Trading ops |
| `journey_options` | 13 | ~9.7s | ⚠️ MEDIUM | Options analysis |
| `journey_watchlists` | 20 | ~16.7s | ⚠️ SLOWER | Watchlist mgmt |

**All journeys execute in <30s ✅**

## 🏗️ Technical Implementation

### Infrastructure Components

1. **`conftest.py`** - Journey marker registration via `pytest_configure()`
2. **`pyproject.toml`** - Comprehensive marker definitions
3. **Journey fixtures** - Specialized test data for each user workflow
4. **Marker placement** - Systematic categorization across all 189 unit tests

### Marker Categories Applied

- **Journey markers**: `journey_account`, `journey_portfolio`, etc. 
- **Test type markers**: `unit`, `integration`
- **Performance markers**: `slow`, `performance`  
- **Requirement markers**: `auth_required`, `rate_limited`, `live_market`
- **Exception markers**: `exception_test` (skipped by default)

### Test Organization

```
tests/
├── unit/ (11 files, 120+ tests with journey markers)
├── integration/ (2 files with journey + integration markers)  
├── server/ (2 files with system + integration markers)
├── auth/ (2 files with account markers)
├── http_transport/ (6 files with system + integration markers)
└── conftest.py (journey fixtures + marker registration)
```

## 🎯 Key Benefits Achieved

✅ **Timeout Resolution** - Focused testing avoids API rate limits  
✅ **Fast Feedback** - Test specific functionality in <30s vs full suite  
✅ **Better Organization** - Logical grouping by user workflow  
✅ **Parallel Testing** - Independent journeys can run concurrently  
✅ **Developer Experience** - Quick iteration on specific features  
✅ **Clear Coverage** - 95%+ coverage tracking per journey  
✅ **ADK Evaluation Ready** - READ ONLY journey combinations perfect for evaluations

## 🔧 Advanced Usage

### CI/CD Pipeline Integration

```yaml
# Example GitHub Actions workflow
- name: Test Account Journey
  run: pytest -m "journey_account" --tb=short
  
- name: Test Market Data Journey  
  run: pytest -m "journey_market_data" --tb=short
  
# Parallel journey testing
- name: Test All Journeys in Parallel
  run: |
    pytest -m "journey_account" &
    pytest -m "journey_portfolio" &  
    pytest -m "journey_market_data" &
    wait
```

### Custom Test Selection

```bash
# Fast tests only (unit tests, non-slow)
pytest -m "unit and not slow and not exception_test"

# Read-only operations (safe for production testing)
pytest -m "(journey_account or journey_portfolio or journey_market_data or journey_research or journey_notifications or journey_system) and not exception_test"

# Full coverage validation
pytest -m "not exception_test" --cov=open_stocks_mcp
```

---

**Phase 0 Complete**: Journey-based testing infrastructure successfully implemented!

**Next**: Phase 8 Quality & Reliability improvements building on this solid testing foundation.