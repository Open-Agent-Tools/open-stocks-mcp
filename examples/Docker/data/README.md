# Persistent Data Storage

This directory contains persistent data for the Open Stocks MCP server:

- **tokens/**: Robinhood session tokens and authentication data
- **logs/**: Application logs and debugging information

These directories are automatically mounted as Docker volumes to preserve
data across container restarts and updates.

## Security Note
Never commit the contents of these directories to version control.
The .gitignore file should exclude these paths.

