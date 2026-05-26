# Persistent Data Storage

This directory contains host-backed persistent data for the Open Stocks MCP server:

- **logs/**: Application logs and debugging information

Robinhood session tokens are stored in the Docker-managed `mcp_tokens` named
volume (not on the host filesystem). Run `docker-compose down -v` to remove
all volumes and force re-authentication.

## Security Note
Never commit the contents of these directories to version control.
The .gitignore file should exclude these paths.
