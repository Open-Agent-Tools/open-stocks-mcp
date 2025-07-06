"""MCP server package initialization"""

from open_stocks_mcp.config import load_config
from open_stocks_mcp.server.app import create_mcp_server

# Create server instance with default configuration
server = create_mcp_server(load_config())

__all__ = ["create_mcp_server", "server"]
