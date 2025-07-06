# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP (Model Context Protocol) Server that provides access to stock market data through open-source APIs, particularly Robin Stocks. The server uses FastMCP for simplified MCP server development.

## Development Commands

This project uses UV for dependency management and virtual environments.

### Virtual Environment Setup
```bash
uv venv  # Creates .venv
source .venv/bin/activate  # Activate the environment
```

### Dependency Installation
```bash
uv pip install -e .  # Install project in editable mode
uv pip install -e ".[dev]"  # Install with dev dependencies
```

### Running Tests
```bash
pytest
```

### Linting and Type Checking
```bash
ruff check .  # Linting
ruff format .  # Formatting
black .  # Alternative formatting
mypy .  # Type checking
```

### Adding Dependencies
```bash
# Add to pyproject.toml dependencies section, then:
uv pip install -e .
```

## Architecture

### MCP Server Structure

The project uses FastMCP, which provides a high-level interface to the MCP protocol:

```python
from mcp.server.fastmcp import FastMCP

# Create server instance
mcp = FastMCP("Open Stocks MCP")

# Tools are functions that can have side effects
@mcp.tool()
def get_stock_price(symbol: str) -> dict:
    """Get current stock price."""
    return {"symbol": symbol, "price": 100.00}

# Resources provide data without side effects  
@mcp.resource("portfolio://holdings")
def get_holdings() -> str:
    """Get portfolio holdings."""
    return json.dumps({"AAPL": 10, "GOOGL": 5})

# Prompts are reusable templates
@mcp.prompt(title="Stock Analysis")
def analyze_stock(symbol: str) -> str:
    return f"Analyze {symbol} stock performance"
```

### Key MCP Patterns

1. **Structured Output**: Tools can return Pydantic models, TypedDicts, or regular dicts for structured data
2. **Context Access**: Tools can access MCP context for logging, progress reporting, and session data
3. **Async Support**: Use async functions for I/O operations
4. **Error Handling**: Raise exceptions with meaningful messages - they'll be properly formatted for clients

### Robin Stocks Integration

Robin Stocks is synchronous, so wrap calls in async functions:

```python
import asyncio
import robin_stocks.robinhood as rh

@mcp.tool()
async def get_stock_quote(symbol: str) -> dict:
    """Get stock quote asynchronously."""
    loop = asyncio.get_event_loop()
    quote = await loop.run_in_executor(None, rh.stocks.get_latest_price, symbol)
    return {"symbol": symbol, "price": float(quote[0])}
```

### Development Guidelines

1. **Tools vs Resources**: 
   - Tools: Functions that perform actions (place orders, fetch live data)
   - Resources: Static or cached data (portfolio snapshot, watchlists)

2. **Authentication**: Handle Robin Stocks auth in server lifecycle:
   ```python
   from contextlib import asynccontextmanager
   
   @asynccontextmanager
   async def app_lifespan(server: FastMCP):
       # Login on startup
       rh.login(username, password)
       yield
       # Logout on shutdown
       rh.logout()
   
   mcp = FastMCP("Open Stocks", lifespan=app_lifespan)
   ```

3. **Error Handling**: Always handle API errors gracefully
4. **Rate Limiting**: Implement caching to avoid hitting API limits
5. **Security**: Never log or return sensitive data (passwords, full account numbers)

## Testing MCP Tools

Test tools with the MCP Inspector:
```bash
uv run mcp dev src/open_stocks_mcp/server/app.py
```

Or write unit tests:
```python
def test_stock_tool():
    result = get_stock_price("AAPL")
    assert "symbol" in result
    assert "price" in result
```