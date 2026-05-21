# Notebook Examples

## Setup

1. Install notebook extras:
   `uv sync --extra docs`
2. Export credentials before running live broker-backed cells:
   - `ROBINHOOD_USERNAME`
   - `ROBINHOOD_PASSWORD`
3. Start the local server and launch Jupyter:
   `uv run jupyter lab examples/notebooks`

## Safety

- Keep credentials in environment variables only.
- Never commit secrets into notebooks.
- These notebooks demonstrate MCP workflows and assume a local MCP endpoint (`http://localhost:3001/mcp` by default).
