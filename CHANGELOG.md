# Changelog

All notable changes to the Open Stocks MCP project will be documented in this file.

## [0.6.3] - 2025-01-02

### Fixed
- **account_details tool returning N/A values**: Fixed parsing of `rh.load_phoenix_account()` response structure
  - Issue: `load_phoenix_account()` returns data in `results[0]` array, not at top level
  - Solution: Parse `account_response["results"][0]` and extract `amount` from currency objects
  - Impact: All account financial data now shows real values instead of "N/A" placeholders
  - Affected fields: portfolio_equity, total_equity, account_buying_power, options_buying_power, crypto_buying_power, uninvested_cash, withdrawable_cash, cash_available_from_instant_deposits, cash_held_for_orders
- Added proper type annotations to helper function for MyPy compliance

### Technical Details
- Phoenix (Robin Stocks internal account system) API response structure changed
- Currency fields returned as objects with `{amount: "value", currency_code: "USD", currency_id: "..."}` format
- Added `get_currency_amount()` helper to extract amounts from currency objects
- Updated Docker deployment with fixed version

## [0.6.2] - 2025-01-02

### Fixed
- **Health endpoint version reporting**: Fixed hardcoded version "0.4.1" in HTTP transport endpoints
- All HTTP endpoints (`/health`, `/status`, `/info`) now report correct dynamic version from package

## [0.6.1] - 2025-01-01

### Enhanced
- **Options tools**: Enhanced `get_open_option_positions_with_details()` with call/put enrichment
- Added comprehensive options data including Greeks, expiration analysis

## [0.6.0] - 2024-12-31

### Added
- **Enhanced options tools**: Complete options chain analysis and position management
- **Comprehensive testing**: Journey-based testing framework with 11 user categories
- **Production deployment**: HTTP transport with Server-Sent Events on port 3001

### Phases Completed
- ✅ **Phase 0-7**: Foundation → Analytics → Trading → Quality validation
- ✅ **79 MCP tools**: Complete trading functionality across all asset classes
- ✅ **Live trading validation**: All functions tested with real market orders

---

**Note**: This changelog was created retroactively for recent releases. Future releases will maintain detailed changelogs from the beginning.