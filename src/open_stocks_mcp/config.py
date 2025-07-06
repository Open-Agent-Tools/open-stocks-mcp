"""Server configuration for Open Stocks MCP MCP server"""

import os
from dataclasses import dataclass


@dataclass
class ServerConfig:
    """Configuration for the MCP server"""

    name: str = "Open Stocks MCP"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


def load_config() -> ServerConfig:
    """Load server configuration from environment or defaults"""
    return ServerConfig(
        name=os.getenv("MCP_SERVER_NAME", "Open Stocks MCP"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
