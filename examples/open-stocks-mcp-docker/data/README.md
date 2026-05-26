# Persistent Data Storage

This directory contains host-backed persistent data for the Open Stocks MCP server:

- **logs/**: Application logs and debugging information

Broker tokens are stored in the Docker-managed `mcp_tokens` named volume
(mounted at `/home/mcp/.tokens` inside the container):

- **robinhood.pickle** — Robinhood session token (pickle format)
- **schwab_token.json** — Schwab OAuth token (JSON, written after first-run browser flow)

Both files contain sensitive authentication material. Run
`docker-compose down -v` to remove all volumes and force re-authentication
for both brokers.

## Security Note
Never commit the contents of these directories to version control.
The .gitignore file should exclude these paths.
