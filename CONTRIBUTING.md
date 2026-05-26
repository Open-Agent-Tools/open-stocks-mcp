# Contributing

This guide covers the local setup, quality checks, test journeys, and debugging recipes used for `open-stocks-mcp` development.

## Setup

Use Python >=3.11 and `uv` for dependency management. The repository is configured as a `uv` managed project, and `uv sync` creates the default `.venv` that the VS Code workspace settings use.

```bash
uv sync
```

Create a local `.env` file when you need live broker or evaluation flows. The required Robinhood, Schwab, and Google ADK variables are documented in [README.md](README.md). Never commit credentials or token files.

## Code Quality

Run the same tools locally that the project guidance expects:

```bash
uv run ruff check . --fix
uv run ruff format .
uv run mypy .
```

The VS Code task list in `.vscode/tasks.json` exposes those commands as one-shot tasks, along with `uv sync` and the fast pytest loop.

## Testing

The default pytest configuration skips live market and performance tests. Rate-limited live endpoint tests are also skipped unless selected explicitly with `-m rate_limited` or `RUN_RATE_LIMITED=1`.

| Workflow | Command |
| --- | --- |
| Fast local loop | `uv run pytest -m "not slow and not exception_test"` |
| Unit tests | `uv run pytest tests/unit/` |
| Account journey | `uv run pytest -m "journey_account"` |
| Portfolio journey | `uv run pytest -m "journey_portfolio"` |
| Market data journey | `uv run pytest -m "journey_market_data"` |
| Research journey | `uv run pytest -m "journey_research"` |
| Watchlists journey | `uv run pytest -m "journey_watchlists"` |
| Options journey | `uv run pytest -m "journey_options"` |
| Notifications journey | `uv run pytest -m "journey_notifications"` |
| System journey | `uv run pytest -m "journey_system"` |
| Trading journey | `uv run pytest -m "journey_trading"` |
| Integration tests | `uv run pytest tests/integration/ -m integration` |
| Rate-limited live tests | `RUN_RATE_LIMITED=1 uv run pytest -m rate_limited` |
| Schwab live journeys | `OPEN_STOCKS_RUN_LIVE_MARKET=1 RUN_RATE_LIMITED=1 ENABLED_BROKERS=schwab uv run pytest tests/integration/test_schwab_live_journeys.py -m "live_market and auth_required and rate_limited" --run-live-market -q` |

The Schwab live journey tests require `SCHWAB_API_KEY`, `SCHWAB_APP_SECRET`, and a
pre-created OAuth token at `SCHWAB_TOKEN_PATH` (default: `~/.tokens/schwab_token.json`).
Run interactive authentication from the terminal once before using these tests in pytest.
They never place or cancel orders; trading coverage is read-only. See
[docs/TEST_MARKERS.md](docs/TEST_MARKERS.md) for the full Schwab marker requirements.

VS Code Test Explorer uses `python.testing.pytestArgs` from `.vscode/settings.json`, so it discovers `tests/` and then applies the project-level marker defaults from `pyproject.toml`.

## Debugging

The workspace launch file `.vscode/launch.json` provides two common entry points:

- `Run MCP server (HTTP)` starts `open_stocks_mcp.server.app` with `--transport http --host 127.0.0.1 --port 3001 --debug` in the integrated terminal.
- `Pytest: current file` runs the currently open test file through `pytest -v`.

For command-line debugging, use `--debug` for one invocation or `DEBUG=true` for environment-driven DEBUG logging. An explicit `LOG_LEVEL` value takes precedence over `DEBUG=true`, while `--debug` forces DEBUG logging for that command.

```bash
uv run python -X dev -m open_stocks_mcp.server.app --transport http --host 127.0.0.1 --port 3001 --debug
DEBUG=true uv run open-stocks-mcp-server --transport http --host 127.0.0.1 --port 3001
```

Inspect the local server from another terminal:

```bash
curl -sf http://127.0.0.1:3001/health
curl http://127.0.0.1:3001/metrics
```

Use the standard debugger by setting `PYTHONBREAKPOINT` before running a focused test or server command:

```bash
PYTHONBREAKPOINT=pdb.set_trace uv run pytest tests/unit/test_health_service.py -q
```

If you prefer `ipdb`, install it in your local environment and use:

```bash
PYTHONBREAKPOINT=ipdb.set_trace uv run pytest tests/unit/test_health_service.py -q
```

Then place `breakpoint()` in the code path you are investigating. Remove breakpoints before committing.

## Editor Setup

The recommended VS Code extensions live in `.vscode/extensions.json`; install them from the Extensions prompt or run the `Extensions: Show Recommended Extensions` command. The workspace also includes:

- `.vscode/settings.json` for the `.venv/bin/python` interpreter, Ruff formatting on save, pytest discovery, and mypy configuration.
- `.vscode/tasks.json` for repeatable setup, lint, format, typecheck, and fast test commands.
- `.vscode/launch.json` for server and current-file pytest debugging.

If your virtual environment is not named `.venv`, either run `uv sync` at the repository root or update the interpreter path locally in VS Code without committing that personal override.
