# API Docs and Notebook Guide

This directory provides generated tool documentation and notebook walkthroughs:

- [tools.md](tools.md) is the generated MCP tool reference.
- `../../examples/notebooks/01_market_data_quickstart.ipynb` covers read-only
  market data.
- `../../examples/notebooks/02_trading_safe_dry_run.ipynb` covers trading
  payload construction without placing orders.

## Prerequisites

Set credentials before using live broker-backed examples:

Robinhood:
- `ROBINHOOD_USERNAME`
- `ROBINHOOD_PASSWORD`

Schwab:
- `SCHWAB_API_KEY`
- `SCHWAB_APP_SECRET`
- `SCHWAB_CALLBACK_URL`
- `SCHWAB_TOKEN_PATH`
- `ENABLED_BROKERS=robinhood,schwab` when both brokers should be available

Notebook connection examples use `MCP_HTTP_URL` and default to
`http://localhost:3001/mcp`.

## Safety Notes

Running trading cells places real orders with real money when they call live
trading tools. The dry-run notebook prints payloads only; converting it to
production trading requires deliberate edits and manual review.

## Regenerate Tool Reference

```bash
uv run python scripts/generate_api_docs.py
```

The command rewrites [tools.md](tools.md) from the server's current MCP tool registry.

## Open Notebook Examples

```bash
uv run jupyter lab examples/notebooks/
```

- `01_market_data_quickstart.ipynb` focuses on read-only workflows.
- `02_trading_safe_dry_run.ipynb` demonstrates dry-run payload construction.

## CI Scope

Notebook execution is intentionally not run in CI by design.
