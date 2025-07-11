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
- ✅ **Package**: Published to PyPI as `open-stocks-mcp` (v0.3.0)
- ✅ **Authentication**: Robin Stocks authentication with device verification support
- ✅ **Containerization**: Production-ready Docker deployment with security features
- ✅ **Communication**: Server/client MCP communication verified working
- ✅ **Core Tools**: 56 MCP tools implemented across 10 categories
- ✅ **Advanced Data**: Market intelligence, dividend tracking, and system monitoring
- ✅ **Phase 3**: Options trading, watchlist management, account features, and user profiles
- 📋 **Next**: Trading capabilities and order placement

## Installation

Install the Open Stocks MCP server via pip:

```bash
pip install open-stocks-mcp
```

For development installation from source:

```bash
git clone https://github.com/Open-Agent-Tools/open-stocks-mcp.git
cd open-stocks-mcp
uv pip install -e .
```

## Credential Management

The Open Stocks MCP server uses Robin Stocks for market data access, which requires Robinhood account credentials.

### Setting Up Credentials

1. Create a `.env` file in your project root:

```bash
ROBINHOOD_USERNAME=your_email@example.com
ROBINHOOD_PASSWORD=your_password
```

2. Secure your credentials:
   - Never commit the `.env` file to version control
   - Ensure proper file permissions: `chmod 600 .env`
   - Consider using a password manager or secure credential storage

### Device Verification and MFA

The Open Stocks MCP server includes enhanced authentication that handles Robinhood's device verification requirements:

**Device Verification Process:**
- When logging in for the first time, Robinhood may require device verification
- Check your Robinhood mobile app for verification prompts
- Approve the device when prompted
- The server will automatically handle the verification workflow

**Multi-Factor Authentication (MFA):**
- If your account has MFA enabled, you'll receive a push notification in the Robinhood mobile app
- Keep your mobile app accessible during the login process
- The server supports both SMS and app-based verification methods

**Troubleshooting Authentication:**
- **"Device verification required"**: Check your mobile app and approve the device
- **"Interactive verification required"**: Ensure you have access to your mobile device
- **Session persistence**: Authentication sessions are cached to reduce verification frequency

## Starting the MCP Server Locally

### Via Command Line

**STDIO Transport (Default)**
Start the server in stdio transport mode (for MCP clients):

```bash
# Using the installed package
open-stocks-mcp-server --transport stdio

# For development with auto-reload
uv run open-stocks-mcp-server --transport stdio
```

**HTTP Transport (New in v0.4.0)**
Start the server with HTTP transport for better reliability and session management:

```bash
# Using the installed package with default settings (localhost:3000)
open-stocks-mcp-server --transport http

# Custom host and port
open-stocks-mcp-server --transport http --host localhost --port 3000

# For development with auto-reload
uv run open-stocks-mcp-server --transport http --port 3000
```

**Available Endpoints (HTTP Transport):**
- JSON-RPC 2.0: `http://localhost:3000/mcp`
- Server-Sent Events: `http://localhost:3000/sse`
- Health Check: `http://localhost:3000/health`
- Server Status: `http://localhost:3000/status`
- API Documentation: `http://localhost:3000/docs`

### Testing the Server

Use the MCP Inspector for interactive testing:

```bash
# Run the inspector with the server (mcp CLI required)
uv run mcp dev src/open_stocks_mcp/server/app.py
```

Note: The `mcp` command is installed with the `mcp[cli]` package dependency.

## Adding the MCP Client to an ADK Agent

To integrate Open Stocks MCP with your ADK (Agent Development Kit) agent:

### 1. Update MCP Settings

**STDIO Transport (Legacy)**
Add the server to your MCP settings configuration:

```json
{
  "mcpServers": {
    "open-stocks": {
      "command": "open-stocks-mcp-server",
      "args": ["--transport", "stdio"],
      "env": {}
    }
  }
}
```

**HTTP Transport (Recommended)**
For better reliability and session management:

```json
{
  "mcpServers": {
    "open-stocks": {
      "command": "http://localhost:3000/mcp",
      "transport": "http"
    }
  }
}
```

### 2. Claude Desktop Integration

For Claude Desktop app, add to your configuration:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**STDIO Transport:**
```json
{
  "mcpServers": {
    "open-stocks": {
      "command": "open-stocks-mcp-server",
      "args": ["--transport", "stdio"]
    }
  }
}
```

**HTTP Transport (Recommended):**
```json
{
  "mcpServers": {
    "open-stocks": {
      "command": "http://localhost:3000/mcp"
    }
  }
}
```

**Note**: When using HTTP transport, start the server first:
```bash
open-stocks-mcp-server --transport http
```


### 3. Available Tools

Once connected, your agent will have access to 61 MCP tools across 10 categories covering account management, market data, options trading, watchlists, user profiles, and system monitoring. Use the `list_tools` command for the complete current list.

## Docker Deployment

The Open Stocks MCP server includes production-ready Docker containerization with enhanced security features.

### Quick Start with Docker

```bash
# Clone the repository
git clone https://github.com/Open-Agent-Tools/open-stocks-mcp.git
cd open-stocks-mcp/examples/Docker

# Create credentials file
cp .env.example .env
# Edit .env with your Robinhood credentials

# Start the server
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop the server
docker-compose down
```

### Docker Features

**Security:**
- Non-root user execution (UID 1001)
- Health checks with automatic restart
- Resource limits and reservations
- Environment variable isolation

**Production Ready:**
- Automatic session persistence
- Device verification handling
- Comprehensive logging
- Port exposure (3001) for MCP clients

**See the [Docker Example README](examples/Docker/README.md) for complete documentation.**

## Current Functionality (v0.4.0)

### Core Features
- **61 MCP Tools**: Complete trading and analysis toolkit
- **HTTP Transport**: New HTTP transport with SSE for better reliability and session management
- **Enhanced Authentication**: Device verification, MFA support, session persistence
- **Production Ready**: Docker deployment, comprehensive error handling
- **Advanced Analytics**: Portfolio analysis, dividend tracking, options trading
- **Real-time Data**: Market data, news, earnings, analyst ratings
- **Health Monitoring**: Built-in health checks and status endpoints

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

## Development Roadmap

**Current Status (v0.4.0)**: 61 MCP tools, HTTP transport with SSE, complete read-only functionality  
**Next Phase**: Live trading capabilities (order placement and management)

For detailed development history and roadmap, see `TODO.md`.

## Intentionally Excluded

The following Robin Stocks API functionality is **deliberately excluded** from the Open Stocks MCP server as it falls outside the project's scope and intent:

### **Cryptocurrency Functions**
- `get_crypto_positions()` - Current crypto holdings
- `get_crypto_quote(symbol)` - Real-time crypto prices  
- `get_crypto_historicals(symbol)` - Historical crypto data
- `get_crypto_info(symbol)` - Crypto asset information
- `get_crypto_currency_pairs()` - Available trading pairs
- `load_crypto_profile()` - Crypto account profile
- `get_crypto_id(symbol)` - Get crypto asset ID

**Rationale**: This project focuses specifically on **stock and options trading**. Cryptocurrency trading represents a different asset class with distinct regulatory, technical, and market characteristics that would significantly expand the project scope beyond its core mission.

### **Document Management Functions**
- `get_documents()` - Account documents list
- `download_document()` - Download specific document
- `download_all_documents()` - Download all documents

**Rationale**: Document management is primarily an administrative function rather than a trading or analysis tool. The MCP protocol is designed for real-time data and trading operations, not file management.

### **Banking & Transfer Functions**
- `get_wire_transfers()` - Wire transfer history
- `get_card_transactions()` - Card transaction history  
- `get_linked_bank_accounts()` - Connected bank accounts
- `get_unified_transfers()` - Unified transfer history

**Rationale**: Banking and transfer functions are account management features that fall outside the scope of market data analysis and trading operations. These functions are better handled through Robinhood's native interface.

### **Currency Trading Functions**
- `get_currency_pairs()` - Forex currency pairs
- Foreign exchange trading capabilities

**Rationale**: Forex trading is a specialized market with different characteristics from stock and options trading. Including forex would require additional expertise and significantly expand the project's complexity.

## Project Scope

The Open Stocks MCP server is intentionally focused on:
- ✅ **Stock market data and analysis**
- ✅ **Options trading and analysis**
- ✅ **Portfolio management and tracking**
- ✅ **Dividend and income analysis**
- ✅ **Account and user profile management**
- ✅ **Trading order placement and management** (Phase 4)

This focused approach ensures the project remains manageable, maintainable, and aligned with its core mission of providing comprehensive **stock and options trading capabilities** through the MCP protocol.

## License

Apache License 2.0 - see LICENSE file for details.