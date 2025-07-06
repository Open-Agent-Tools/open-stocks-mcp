"""Google ADK Stock Trading Agent Example.

This package demonstrates how to create a Google ADK agent that connects
to the open-stocks-mcp server for stock market operations.
"""

# Expose the root agent and create_agent function at the package level for easier imports
from . import agent
from .agent import create_agent, root_agent

__all__ = ["agent", "create_agent", "root_agent"]
