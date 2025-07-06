# open-stocks-mcp

## UNDER CONSTRUCTION

MCP Server based on open stock API packages like Robin Stocks

## Overview

This MCP server provides standardized access to stock market data through the Model Context Protocol. It integrates with Robin Stocks and other open-source stock APIs to expose market data, portfolio information, and trading capabilities to LLM applications.

## What is MCP?

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io) lets you build servers that expose data and functionality to LLM applications in a secure, standardized way. MCP servers can:

- Expose data through **Resources** (GET-like endpoints for loading information into the LLM's context)
- Provide functionality through **Tools** (POST-like endpoints for executing code or producing side effects)  
- Define interaction patterns through **Prompts** (reusable templates for LLM interactions)

## Installation

This project uses [UV](https://docs.astral.sh/uv/) for dependency management.

```bash
# Clone the repository
git clone https://github.com/Open-Agent-Tools/open-stocks-mcp.git
cd open-stocks-mcp

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Quick Start

### Development Mode

Test your server with the MCP Inspector:

```bash
uv run mcp dev src/open_stocks_mcp/server/app.py
```

### Claude Desktop Integration

Install the server in Claude Desktop:

```bash
uv run mcp install src/open_stocks_mcp/server/app.py --name "Open Stocks MCP"
```

### Direct Execution

Run the server directly:

```bash
python -m open_stocks_mcp.server.app
```

## Core Concepts

### Tools

Tools let LLMs take actions through your server. They're expected to perform computation and have side effects:

```python
@mcp.tool()
def get_stock_price(symbol: str) -> dict:
    """Get current stock price for a symbol."""
    # Implementation using Robin Stocks
    return {"symbol": symbol, "price": price}
```

### Resources  

Resources expose data to LLMs. They're similar to GET endpoints - they provide data but shouldn't perform significant computation:

```python
@mcp.resource("portfolio://holdings")
def get_portfolio_holdings() -> str:
    """Get current portfolio holdings."""
    # Return portfolio data as JSON
    return json.dumps(holdings)
```

### Prompts

Prompts are reusable templates that help LLMs interact with your server effectively:

```python
@mcp.prompt(title="Analyze Stock")
def analyze_stock_prompt(symbol: str) -> str:
    return f"Please analyze the stock {symbol} including price trends, volume, and key metrics."
```

## Development

### Running Tests

```bash
pytest
```

### Linting and Type Checking

```bash
ruff check .  # Linting
ruff format . # Formatting  
mypy .        # Type checking
```

### Project Structure

```
open-stocks-mcp/
├── src/
│   └── open_stocks_mcp/
│       ├── __init__.py
│       ├── server/          # MCP server implementation
│       ├── tools/           # Stock market tools
│       ├── client/          # Example client
│       └── config.py        # Configuration
├── tests/                   # Test files
├── pyproject.toml          # Project configuration
└── README.md               # This file
```

## Configuration

The server uses environment variables for configuration. Create a `.env` file:

```bash
# Robin Stocks credentials (if needed)
RH_USERNAME=your_username
RH_PASSWORD=your_password

# Server configuration
LOG_LEVEL=INFO
```

## Security Note

Never commit credentials or API keys to the repository. Always use environment variables or secure credential management.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.