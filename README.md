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
- ✅ **Package**: Published to PyPI as `open-stocks-mcp` (v0.0.2)
- ✅ **Communication**: Server/client MCP communication verified working
- 🔄 **In Progress**: Robin Stocks API integration
- 📋 **Next**: Core stock market tools implementation

## Installation

```bash
pip install open-stocks-mcp
```

## Current Functionality (v0.0.2)

The package currently includes a working MCP server/client with echo functionality for testing:

```bash
# Test server/client communication
uv run open-stocks-mcp-client "hello world" --transform upper
# Output: HELLO WORLD

# Start server (for MCP client integration)
uv run open-stocks-mcp-server --transport stdio
```

## License

Apache License 2.0 - see LICENSE file for details.