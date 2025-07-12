"""Stock Trading Agent Configuration.

This module configures Stock_Trader, a specialized agent for handling
stock market operations and interactions with Robin Stocks through our MCP server.

It uses the specified Google model and connects to our open-stocks-mcp server
to provide real-time stock market data and trading capabilities.
"""

import logging
import os
import warnings

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters, StreamableHTTPConnectionParams

from .prompts import agent_instruction

# Initialize environment and logging
# Load .env from project root (two levels up from this file)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
dotenv_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path)
logging.basicConfig(level=logging.ERROR)
warnings.filterwarnings("ignore")


def create_agent() -> Agent:
    """
    Creates and returns a configured Stock Trading agent instance.

    Args:

    Returns:
        Agent: Configured Stock Trading agent with appropriate tools and settings.
    """

    # Create environment for MCP server
    mcp_env = os.environ.copy()
    mcp_env.update(
        {
            "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO"),
        }
    )

    # Check transport type from environment or default to stdio
    transport_type = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    
    if transport_type == "http":
        # Use HTTP transport with the server running separately
        http_url = os.environ.get("MCP_HTTP_URL", "http://localhost:3000/mcp")
        agent_tools = [
            MCPToolset(
                connection_params=StreamableHTTPConnectionParams(
                    url=http_url,
                ),
            ),
        ]
    else:
        # Use STDIO transport (default)
        agent_tools = [
            MCPToolset(
                connection_params=StdioServerParameters(
                    command="uv",
                    args=["run", "open-stocks-mcp-server", "--transport", "stdio"],
                    cwd=project_root,  # Set working directory to project root
                    env=mcp_env,
                ),
            ),
        ]

    return Agent(
        model=os.environ.get("GOOGLE_MODEL") or "gemini-2.0-flash",
        name="Stock_Trader",
        instruction=agent_instruction,
        description="Specialized stock trading agent that can perform Robin Stocks operations through MCP tools.",
        tools=agent_tools,
    )


# Configure specialized Stock Trading operations agent
root_agent = create_agent()
