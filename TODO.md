# TODO - Open Stocks MCP

## Project Status
- ✅ **Base Setup Complete**: FastMCP server scaffolding with echo tool
- ✅ **CI/CD Pipeline**: GitHub Actions for testing and PyPI publishing
- ✅ **Package Publishing**: Successfully published to PyPI as `open-stocks-mcp`
- ✅ **Documentation**: Comprehensive guides in README, CONTRIBUTING, and CLAUDE.md
- ✅ **Code Quality**: Ruff, MyPy, and pytest configured and passing

## Immediate Tasks (Next Sprint)

### Robin Stocks Integration
- [ ] **Research Robin Stocks API**: Study available endpoints and data structures
- [ ] **Authentication Setup**: Implement secure credential handling for Robin Stocks
- [ ] **Basic Stock Tools**: Create MCP tools for fundamental stock operations
  - [ ] `get_stock_price(symbol)` - Current stock price
  - [ ] `get_stock_info(symbol)` - Company information and metrics
  - [ ] `search_stocks(query)` - Search for stocks by symbol or name

### Core MCP Tools Development
- [ ] **Portfolio Tools**: If Robin Stocks supports portfolio access
  - [ ] `get_portfolio()` - Portfolio overview and holdings
  - [ ] `get_positions()` - Current stock positions
- [ ] **Market Data Tools**:
  - [ ] `get_market_hours()` - Trading hours and market status
  - [ ] `get_trending_stocks()` - Popular/trending stocks
- [ ] **Historical Data Tools**:
  - [ ] `get_historical_prices(symbol, period)` - Price history

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

## Dependencies to Monitor
- [ ] **Robin Stocks**: Monitor for API changes and new features
- [ ] **FastMCP**: Track updates to the MCP SDK
- [ ] **Python**: Consider Python 3.12+ features and compatibility

## Release Planning

### v0.1.x - Foundation
- ✅ v0.0.1 - Base MCP server (published)
- [ ] v0.1.0 - First Robin Stocks integration with basic tools

### v0.2.x - Enhanced Features  
- [ ] v0.2.0 - Portfolio management tools
- [ ] v0.2.1 - Historical data and caching

### v0.3.x - Advanced Capabilities
- [ ] v0.3.0 - Technical analysis and alerts
- [ ] v0.3.1 - News and sentiment integration

## Notes
- **Rate Limiting**: Robin Stocks may have rate limits - implement respectful usage
- **Authentication**: Consider OAuth if Robin Stocks supports it for better security
- **Data Accuracy**: Always include disclaimers about data accuracy and trading risks
- **Legal Compliance**: Ensure all usage complies with Robin Stocks ToS and financial regulations

---
*Last Updated: 2025-07-06*
*Status: Foundation complete, ready for Robin Stocks integration*