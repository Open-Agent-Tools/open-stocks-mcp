# API Docs and Notebook Examples

This directory provides generated tool documentation and notebook walkthroughs.

## Prerequisites

Set credentials before using live broker-backed examples:

- `ROBINHOOD_USERNAME`
- `ROBINHOOD_PASSWORD`

## Safety Notes

Trading tools can place real orders with real money. Review every cell before running it.

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

Notebook execution is intentionally not run in CI for this issue. CI workflow changes are out of scope.
