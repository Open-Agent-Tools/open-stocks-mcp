# TODO - Open Stocks MCP

## Project Status
- ✅ **Base Setup Complete**: FastMCP server scaffolding with echo tool
- ✅ **CI/CD Pipeline**: GitHub Actions for testing and PyPI publishing
- ✅ **Package Publishing**: Successfully published to PyPI as `open-stocks-mcp`
- ✅ **Documentation**: Comprehensive guides in README, CONTRIBUTING, and CLAUDE.md
- ✅ **Code Quality**: Ruff, MyPy, and pytest configured and passing
- ✅ **Server/Client Testing**: MCP communication working via stdio transport

## Immediate Tasks (Next Sprint)

### Robin Stocks Integration

#### Phase 1: Foundation (v0.1.0) - READY TO IMPLEMENT
- [ ] **Authentication & Session Management**
  - [ ] Create Robin Stocks configuration module (`robinhood_config.py`)
  - [ ] Implement environment-based credential handling
  - [ ] Add 2FA/MFA support with `pyotp`
  - [ ] Create `login()` and `logout()` MCP tools for session management
  - [ ] Add session timeout and re-authentication handling
  
- [ ] **Core Market Data Tools** (Read-only operations)
  - [ ] `get_stock_price(symbol)` - Current stock price and basic metrics
  - [ ] `get_stock_info(symbol)` - Company information and fundamentals
  - [ ] `search_stocks(query)` - Search for stocks by symbol or company name
  - [ ] `get_market_hours()` - Trading hours and market status
  - [ ] `get_price_history(symbol, period)` - Historical price data

- [ ] **Infrastructure**
  - [ ] Add async wrapper for Robin Stocks synchronous API
  - [ ] Implement error handling for API failures and rate limits
  - [ ] Create Robin Stocks specific logging and monitoring
  - [ ] Add integration tests (marked with `@pytest.mark.live_market`)

#### Phase 2: Portfolio Management (v0.2.0)
- [ ] **Portfolio Tools**
  - [ ] `get_portfolio()` - Portfolio overview and total value
  - [ ] `get_positions()` - Current stock/crypto/options positions
  - [ ] `get_dividends()` - Dividend history and payments
  - [ ] `get_orders()` - Order history and status
  
- [ ] **Advanced Market Data**
  - [ ] `get_trending_stocks()` - Popular/trending stocks
  - [ ] `get_fundamentals(symbol)` - Detailed company fundamentals
  - [ ] `get_earnings(symbol)` - Earnings data and estimates

#### Phase 3: Advanced Features (v0.3.0)
- [ ] **Multi-Platform Support**
  - [ ] Add Gemini API integration for crypto data
  - [ ] Add TD Ameritrade API support
  - [ ] Unified interface across platforms
  
- [ ] **Trading Capabilities** (Optional - requires explicit user consent)
  - [ ] `place_order(symbol, quantity, side, type)` - Order placement
  - [ ] `cancel_order(order_id)` - Order cancellation
  - [ ] `get_buying_power()` - Available funds for trading

### Testing & Quality
- [ ] **Integration Tests**: Add tests requiring live market data (marked with `@pytest.mark.live_market`)
- [ ] **Mock Testing**: Create comprehensive mocks for Robin Stocks API responses
- [ ] **Error Handling**: Implement proper error handling for API failures and rate limits
- [ ] **Caching Strategy**: Add caching for frequently requested data to avoid rate limits

## Future Enhancements

### Advanced Features
- [ ] **Alerts System**: MCP tools for setting up price alerts
- [ ] **Technical Analysis**: Basic technical indicators (RSI, moving averages)
- [ ] **News Integration**: Stock news and sentiment data if available
- [ ] **Watchlists**: Create and manage stock watchlists

### Developer Experience
- [ ] **Example Notebooks**: Jupyter notebooks demonstrating MCP tool usage
- [ ] **VS Code Extension**: Consider creating VS Code extension for easier testing
- [ ] **Docker Support**: Containerized deployment option
- [ ] **Configuration Management**: Enhanced config system for API keys and preferences

### Documentation
- [ ] **API Documentation**: Auto-generated API docs for all MCP tools
- [ ] **Tutorial Series**: Step-by-step guides for common use cases
- [ ] **Video Demos**: Screen recordings showing MCP tools in action
- [ ] **Integration Examples**: Examples with different MCP clients

## Technical Debt
- [ ] **Version Management**: Consider using bump2version or similar for automated versioning
- [ ] **Security Audit**: Review credential handling and API security
- [ ] **Performance Testing**: Load testing for high-frequency data requests
- [ ] **Logging Enhancement**: Structured logging with correlation IDs

## Dependencies & API Status
- [ ] **Robin Stocks v3.4.0**: ✅ Installed - Monitor for API changes and new features
- [ ] **PyOTP v2.9.0**: ✅ Installed - 2FA/MFA authentication support  
- [ ] **FastMCP**: Track updates to the MCP SDK
- [ ] **Python**: Consider Python 3.12+ features and compatibility

## Security & Authentication Notes
- 🔐 **Environment Variables**: Use `.env` for credentials (never commit secrets)
- 🔐 **2FA Support**: Optional MFA with TOTP codes via `pyotp`
- 🔐 **Session Management**: 24-hour token expiration, auto re-authentication
- 🔐 **Read-Only First**: Start with market data tools, trading tools optional
- 🔐 **Error Handling**: Graceful handling of auth failures and rate limits

## Release Planning

### v0.0.x - Foundation
- ✅ v0.0.1 - Base MCP server (published)
- ✅ v0.0.2 - Client/server communication fixes (published)

### v0.1.x - Robin Stocks Integration
- [ ] v0.1.0 - **Authentication & Core Market Data** 
  - Authentication setup with login/logout tools
  - Basic market data tools (price, info, search, hours, history)
  - Read-only operations with error handling
  
### v0.2.x - Portfolio Management
- [ ] v0.2.0 - **Portfolio & Account Tools**
  - Portfolio viewing and position tracking
  - Order history and dividend information
  - Advanced market data and fundamentals
  
### v0.3.x - Advanced Capabilities  
- [ ] v0.3.0 - **Multi-Platform & Trading**
  - Gemini and TD Ameritrade integration
  - Optional trading capabilities
  - Advanced analytics and technical indicators

## Notes
- **Rate Limiting**: Robin Stocks may have rate limits - implement respectful usage
- **Authentication**: Consider OAuth if Robin Stocks supports it for better security
- **Data Accuracy**: Always include disclaimers about data accuracy and trading risks
- **Legal Compliance**: Ensure all usage complies with Robin Stocks ToS and financial regulations

---
*Last Updated: 2025-07-06*
*Status: Foundation complete with working MCP server/client, ready for Robin Stocks integration*

## Recent Updates (2025-07-06)
- Fixed client command reference in stdio connection
- Improved client output parsing for cleaner text display
- Verified end-to-end MCP communication working
- All code quality checks passing (ruff, mypy, pytest)
- **Planning Complete**: Robin Stocks integration architecture designed
- **Dependencies Ready**: robin-stocks v3.4.0 and pyotp v2.9.0 available
- **Phase 1 Defined**: Authentication + core market data tools for v0.1.0
- **Authentication Scaffolding**: Created auth modules with comprehensive tests
- **MCP Tools Scaffolding**: Added login/logout/status/account_info tools with stubs
- **Updated Design**: Changed to user-supplied credentials with mandatory MFA