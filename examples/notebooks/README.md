# Open Stocks MCP Notebook Examples

This directory contains Jupyter notebooks demonstrating end-to-end workflows using the underlying Python functions of the Open Stocks MCP tools.

## Installation

To run these notebooks, you must install the optional `docs` dependency group:

```bash
uv sync --extra docs
```

## Credentials

The examples use the local broker integrations directly. You must configure your Robinhood credentials via environment variables:

- `ROBINHOOD_USERNAME`: Your Robinhood login email.
- `ROBINHOOD_PASSWORD`: Your Robinhood login password.

You can set these in a `.env` file in the project root or export them in your terminal.

## Launching

Launch Jupyter Lab to run the notebooks interactively:

```bash
uv run jupyter lab examples/notebooks
```

## Security Warning

**Never commit secrets!**
- Do not hardcode `ROBINHOOD_USERNAME` or `ROBINHOOD_PASSWORD` into notebook cells.
- **Never commit notebook outputs containing your live account data, positions, or balances.** Before committing, always clear all cell outputs (`Edit -> Clear All Outputs` in Jupyter).
