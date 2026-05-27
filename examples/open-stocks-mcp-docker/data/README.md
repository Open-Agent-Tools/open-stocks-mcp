# Persistent Data Storage

This directory contains host-backed persistent data for the Open Stocks MCP server:

- **logs/**: Application logs and debugging information

Broker session tokens are stored in the Docker-managed `mcp_tokens` named
volume (not on the host filesystem). These include:
- **robinhood.pickle**: Robinhood session data
- **schwab_token.json**: Schwab OAuth2 tokens (if enabled)

Run `docker-compose down -v` to remove all volumes and force re-authentication.

## Security Note
Never commit the contents of these directories to version control.
Both token types are sensitive and provide direct access to your accounts.
The .gitignore file should exclude these paths.
