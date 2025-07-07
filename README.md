# open-stocks-mcp

**🚧 UNDER CONSTRUCTION 🚧**

An MCP (Model Context Protocol) server providing access to stock market data through open-source APIs like Robin Stocks.

## Project Intent

This project aims to create a standardized interface for LLM applications to access stock market data, portfolio information, and trading capabilities through the Model Context Protocol.

### Planned Features
- Real-time stock price data
- Portfolio management tools  
- Market analysis capabilities
- Historical data access
- Trading alerts and notifications

## Status

- ✅ **Foundation**: MCP server scaffolding complete
- ✅ **Infrastructure**: CI/CD, testing, and publishing pipeline established
- ✅ **Package**: Published to PyPI as `open-stocks-mcp` (v0.0.3)
- ✅ **Communication**: Server/client MCP communication verified working
- 🔄 **In Progress**: Robin Stocks API integration
- 📋 **Next**: Core stock market tools implementation

## Installation

```bash
pip install open-stocks-mcp
```

## Current Functionality (v0.0.3)

The package currently includes:

### Robin Stocks Authentication
- **Environment-based login**: Stores credentials in `.env` file
- **SMS MFA support**: Interactive MFA token flow
- **Auto-login flow**: Automatic credential detection and MFA triggering

```bash
# Set up credentials in .env file:
ROBINHOOD_USERNAME=your_email@example.com
ROBINHOOD_PASSWORD=your_password

# Test login flow
uv run open-stocks-mcp-client auto_login
uv run open-stocks-mcp-client "pass_through_mfa mfa_code=123456"

# Start server (for MCP client integration)
uv run open-stocks-mcp-server --transport stdio
```

## Testing

### Basic Tests
Run the basic test suite:

```bash
uv run pytest
```

### Login Flow Integration Tests
Test the complete login flow with real credentials from `.env`:

```bash
# Run all tests including integration tests
uv run pytest -m integration

# Run specific login flow tests
uv run pytest tests/test_server_login_flow.py -v

# Run without integration tests (no credentials needed)
uv run pytest -m "not integration"
```

**Note**: Integration tests require valid `ROBINHOOD_USERNAME` and `ROBINHOOD_PASSWORD` in your `.env` file. These tests mock the actual Robin Stocks API calls to avoid real authentication attempts.

### Test Categories
- **Unit tests**: Basic functionality without external dependencies
- **Integration tests**: Login flow tests using real credentials (but mocked API calls)
- **Slow tests**: Performance and stress tests (marked with `@pytest.mark.slow`)

For development with auto-reloading:

```bash
uv run pytest --watch
```

## License

Apache License 2.0 - see LICENSE file for details.