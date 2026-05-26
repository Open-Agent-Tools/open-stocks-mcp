# Schwab Setup Guide

This guide walks you through setting up Charles Schwab broker support in Open Stocks MCP, from creating a developer account to verifying live authentication.

---

## Prerequisites

Before you start, you need:

1. **A Charles Schwab brokerage account** — an active account at schwab.com.
2. **A Schwab developer account** — register at [https://developer.schwab.com/](https://developer.schwab.com/).
   - Approval typically takes **3–5 business days**. Schwab reviews applications manually.
   - Once approved, create an application in the developer portal to obtain your API credentials.
3. **Python 3.11+** and `open-stocks-mcp` installed.

---

## Step 1 — Register a Developer Application

1. Go to [https://developer.schwab.com/](https://developer.schwab.com/) and sign in.
2. Navigate to **My Apps → Create App**.
3. Fill in the application details. For the **Callback URL**, use:
   ```
   https://127.0.0.1:8182/
   ```
   This default matches `SCHWAB_CALLBACK_URL`. If you change it, update the env var to match.
4. After creating the app, copy your **API Key** and **App Secret**.

---

## Step 2 — Configure Environment Variables

Add these variables to your `.env` file (or export them in your shell):

```bash
# Required
SCHWAB_API_KEY=your_api_key_here
SCHWAB_APP_SECRET=your_app_secret_here

# Optional — defaults shown
SCHWAB_CALLBACK_URL=https://127.0.0.1:8182/
SCHWAB_TOKEN_PATH=~/.tokens/schwab_token.json

# Enable Schwab alongside Robinhood (or standalone)
ENABLED_BROKERS=robinhood,schwab
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `SCHWAB_API_KEY` | Yes | — | API key from developer.schwab.com |
| `SCHWAB_APP_SECRET` | Yes | — | App secret from developer.schwab.com |
| `SCHWAB_CALLBACK_URL` | No | `https://127.0.0.1:8182/` | OAuth redirect URL; must match your app registration |
| `SCHWAB_TOKEN_PATH` | No | `~/.tokens/schwab_token.json` | Where the OAuth token is persisted |

---

## Step 3 — First-Run OAuth Flow

On the **first run**, the server uses `schwab-py`'s `easy_client()` to initiate an OAuth 2.0 authorization flow:

1. Start the server normally:
   ```bash
   open-stocks-mcp-server --transport http --port 3001
   ```
2. A browser window opens automatically, directing you to Schwab's login page.
3. Log in with your Schwab brokerage credentials and approve the requested permissions.
4. After approval, Schwab redirects to `SCHWAB_CALLBACK_URL` (e.g., `https://127.0.0.1:8182/`). The `schwab-py` library handles this redirect internally.
5. The OAuth token is written to `SCHWAB_TOKEN_PATH` (default: `~/.tokens/schwab_token.json`). The directory is created with `700` permissions automatically.

**Subsequent runs** use the saved token — no browser interaction is needed.

---

## Step 4 — Token Refresh

`schwab-py` manages token refresh automatically:

- Tokens are valid for approximately **7 days**.
- The library refreshes the token transparently before it expires when the server makes API calls.
- Token refresh events are logged at `INFO` level. To find them, filter server logs:
  ```bash
  # Local
  grep -i "schwab\|token" ~/.local/state/mcp-servers/logs/*.log

  # Docker
  docker-compose logs open-stocks-mcp | grep -i "schwab\|token"
  ```

---

## Step 5 — Verify Authentication

After starting the server, call the `broker_status` MCP tool to confirm Schwab is authenticated:

```json
// Tool call
{"tool": "broker_status", "arguments": {}}

// Expected response (Schwab authenticated)
{
  "result": {
    "brokers": {
      "schwab": {
        "status": "authenticated",
        "broker": "schwab"
      }
    },
    "available_brokers": ["schwab"],
    "total_configured": 1,
    "total_authenticated": 1,
    "status": "success"
  }
}
```

If `status` is `not_authenticated` or `not_configured`, check the troubleshooting section below.

---

## Docker Setup

When running in Docker, the Schwab token must be pre-generated outside the container (the OAuth browser flow requires an interactive terminal):

### Pre-generate the token locally

```bash
# Run once on your local machine with the same credentials
SCHWAB_API_KEY=your_key SCHWAB_APP_SECRET=your_secret \
  open-stocks-mcp-server --transport http --port 3001
# Complete the browser OAuth flow, then Ctrl-C
```

The token is written to `~/.tokens/schwab_token.json`.

### Mount the token into Docker

The Docker image mounts `/home/mcp/.tokens` as a named volume (`mcp_tokens`). To seed it with your pre-generated token, copy it into the volume before starting the container:

```bash
# Copy token to Docker volume
docker run --rm \
  -v mcp_tokens:/home/mcp/.tokens \
  -v ~/.tokens/schwab_token.json:/tmp/schwab_token.json \
  alpine cp /tmp/schwab_token.json /home/mcp/.tokens/schwab_token.json

# Set SCHWAB_TOKEN_PATH in your .env
SCHWAB_TOKEN_PATH=/home/mcp/.tokens/schwab_token.json
```

Then start the container:
```bash
cd examples/open-stocks-mcp-docker
docker-compose up -d
docker-compose logs -f  # watch for "Schwab authenticated" in logs
```

See `examples/open-stocks-mcp-docker/.env.example` for the full Docker environment template.

---

## Troubleshooting

### Non-interactive / headless environments

**Error:** OAuth flow cannot open a browser.

The `easy_client()` call requires an interactive terminal with a browser available. In headless environments (CI, Docker, SSH sessions):

1. Generate the token file **interactively** on a machine with a browser.
2. Transfer `~/.tokens/schwab_token.json` to the target environment.
3. Set `SCHWAB_TOKEN_PATH` to the file's location on the target.

### Expired token

**Symptom:** `broker_status` returns `not_authenticated` after previously working.

1. Delete the stale token:
   ```bash
   rm ~/.tokens/schwab_token.json
   ```
2. Restart the server to trigger a fresh OAuth flow.

In Docker, remove the token from the volume:
```bash
docker run --rm -v mcp_tokens:/home/mcp/.tokens alpine rm /home/mcp/.tokens/schwab_token.json
```

### Callback URL mismatch

**Error:** `invalid_client` or redirect URI mismatch during OAuth.

The `SCHWAB_CALLBACK_URL` in your environment **must exactly match** the callback URL registered in [developer.schwab.com](https://developer.schwab.com/). Check both for trailing slashes and protocol (`https://`).

### Missing credentials

**Symptom:** `broker_status` shows `not_configured` for Schwab.

Ensure `SCHWAB_API_KEY` and `SCHWAB_APP_SECRET` are set in your environment before starting the server. Both are required.

### Token permission errors

**Symptom:** Warning in logs: `Could not set secure permissions on ~/.tokens`

The server attempts to create `~/.tokens/` with mode `700` for security. On some systems (Windows, certain NFS mounts), `chmod` may fail. The token is still written; the warning is informational.
