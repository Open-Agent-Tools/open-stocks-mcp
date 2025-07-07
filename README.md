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
- ✅ **Package**: Published to PyPI as `open-stocks-mcp` (v0.1.1)
- ✅ **Communication**: Server/client MCP communication verified working
- 🔄 **In Progress**: Robin Stocks API integration
- 📋 **Next**: Core stock market tools implementation

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

### Multi-Factor Authentication (MFA)

If your Robinhood account has MFA enabled you will have a pop up in the mobile app, 
it is recommended to have your app open during login.

## Starting the MCP Server Locally

### Via Command Line

Start the server in stdio transport mode (for MCP clients):

```bash
# Using the installed package
open-stocks-mcp-server --transport stdio

# For development with auto-reload
uv run open-stocks-mcp-server --transport stdio
```

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

Add the server to your MCP settings configuration (typically in `mcp_settings.json` or similar):

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

### 2. Claude Desktop Integration

For Claude Desktop app, add to your configuration:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

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


### 3. Available Tools

Once connected, your agent will have access to tools like:
- `get_portfolio` - Retrieve current portfolio holdings and values
- `get_stock_orders` - Get list of stock orders and their status
- (More tools coming in future versions)

## Current Functionality (v0.1.1)

The package currently includes:

### Robin Stocks Authentication
- **Environment-based login**: Stores credentials in `.env` file
- **Auto-login flow**: Automatic credential detection and login on server startup
- **MFA Support**: Mobile app notification for accounts with MFA enabled

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