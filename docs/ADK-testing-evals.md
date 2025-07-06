# ADK Testing and Evaluations Guide

This guide documents the agent evaluation testing approach for Google ADK agents with the open-stocks-mcp server. The evaluation tests validate that agents work correctly when called by AI models in the Google ADK framework through Model Context Protocol (MCP) integration.

## Overview

The Stock Trading agent uses Google ADK's MCPToolset to connect to our open-stocks-mcp server, providing access to Robin Stocks functionality. Each agent has its own `evals/` directory containing evaluation tests that focus on verifying basic agent functionality, particularly the ability to list available MCP tools and execute them correctly.

## Directory Structure

```
examples/google-adk-agent/
   agent.py                                      # Main agent implementation with MCPToolset
   prompts.py                                    # Agent prompts
   __init__.py                                   # Package initialization
   requirements.txt                              # Dependencies including pytest
   README.md                                     # Usage documentation
   evals/                                        # Agent-specific evaluations
       __init__.py                               # Evals package initialization
       test_config.json                          # ADK evaluation criteria
       list_available_tools_test.json            # Tool listing test case
       echo_test.json                            # Echo tool functionality test
       test_stock_trader_agent_evaluation.py     # Test runner
```

## Implementation Steps

### 1. Create the evals Directory

Create an `evals/` folder inside the agent directory:

```bash
mkdir -p examples/google-adk-agent/evals
```

### 2. Create test_config.json

This file defines the evaluation criteria with scoring thresholds:

```json
{
  "criteria": {
    "tool_trajectory_avg_score": 0.5,
    "response_match_score": 0.5
  }
}
```

- `tool_trajectory_avg_score`: Measures correct tool usage (0.5 = 50% threshold)
- `response_match_score`: Measures response similarity to expected output (0.5 = 50% threshold)

### 3. Create list_available_tools_test.json

This file contains the test case for listing available MCP tools:

```json
{
  "eval_set_id": "list_available_tools_test_set",
  "name": "List Available Tools Test",
  "description": "Test case for listing available MCP tools through agent interaction",
  "eval_cases": [
    {
      "eval_id": "list_available_tools_test",
      "conversation": [
        {
          "invocation_id": "list-tools-001",
          "user_content": {
            "parts": [
              {
                "text": "List all available tools alphabetically as a bulleted list only.\n\n"
              }
            ],
            "role": "user"
          },
          "final_response": {
            "parts": [
              {
                "text": "• echo\n• login_robinhood"
              }
            ],
            "role": "model"
          },
          "intermediate_data": {
            "tool_uses": [],
            "intermediate_responses": []
          }
        }
      ],
      "session_input": {
        "app_name": "stock_trader_agent",
        "user_id": "test_user",
        "state": {}
      }
    }
  ]
}
```

### 4. Create test_stock_trader_agent_evaluation.py

This is the pytest runner for agent evaluations:

```python
"""ADK evaluation tests for Stock Trader agent.

This test suite validates that Stock_Trader's tools work correctly
when called by AI agents in the Google ADK framework.
"""

import asyncio

import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator


class TestStockTraderAgentEvaluation:
    """Agent evaluation tests for Stock Trader."""

    @pytest.mark.agent_evaluation
    @pytest.mark.asyncio
    async def test_list_available_tools_agent(self):
        """Test agent listing available tools."""
        await AgentEvaluator.evaluate(
            agent_module="examples.google_adk_agent",
            eval_dataset_file_path_or_dir="examples/google-adk-agent/evals/list_available_tools_test.json",
        )
        await asyncio.sleep(2)  # Rate limiting delay

    @pytest.mark.agent_evaluation
    @pytest.mark.asyncio
    async def test_echo_functionality_agent(self):
        """Test agent echo tool functionality."""
        await AgentEvaluator.evaluate(
            agent_module="examples.google_adk_agent",
            eval_dataset_file_path_or_dir="examples/google-adk-agent/evals/echo_test.json",
        )
        await asyncio.sleep(2)  # Rate limiting delay
```

### 5. Update Agent's __init__.py

Ensure your agent module exports correctly for ADK evaluation:

```python
"""Google ADK Stock Trading Agent Example."""

# Expose the root agent and create_agent function at the package level for easier imports
from .agent import root_agent, create_agent
from . import agent

__all__ = ["root_agent", "create_agent", "agent"]
```

The `from . import agent` line is crucial - ADK looks for an `agent` attribute in the module.

## MCP Integration

### Agent Configuration

The Stock Trading agent uses MCPToolset to connect to our MCP server:

```python
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

agent_tools = [
    MCPToolset(
        connection_params=StdioServerParameters(
            command="uv",
            args=[
                "run",
                "open-stocks-mcp-server",
                "--transport", 
                "stdio"
            ],
        ),
    ),
]
```

### Available MCP Tools

Currently available through the open-stocks-mcp server:

- **`echo`**: Test connectivity with optional case transformation
- **`login_robinhood`**: Authenticate with Robinhood using SMS MFA

## Running Evaluations

### Prerequisites

1. **Install Dependencies**:
   ```bash
   cd examples/google-adk-agent
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**:
   ```bash
   export GOOGLE_API_KEY="your-google-api-key"
   export GOOGLE_MODEL="gemini-2.0-flash"  # Optional
   ```

3. **Ensure MCP Server is Available**:
   ```bash
   # Test that the MCP server can be started
   uv run open-stocks-mcp-server --transport stdio
   ```

### Manual Evaluation (From Project Root)

Run evaluation for the stock trading agent using the ADK CLI:

```bash
PYTHONPATH=.:$PYTHONPATH adk eval \
  --config_file_path examples/google-adk-agent/evals/test_config.json \
  --print_detailed_results \
  examples/google-adk-agent \
  examples/google-adk-agent/evals/list_available_tools_test.json
```

### Individual Test Files

Test specific functionality:

```bash
# Test tool listing
PYTHONPATH=.:$PYTHONPATH adk eval \
  examples/google-adk-agent \
  examples/google-adk-agent/evals/list_available_tools_test.json

# Test echo functionality  
PYTHONPATH=.:$PYTHONPATH adk eval \
  examples/google-adk-agent \
  examples/google-adk-agent/evals/echo_test.json
```

### Automated Testing with pytest

Run all agent evaluation tests:

```bash
# All tests including agent evaluations (requires GOOGLE_API_KEY)
python3 -m pytest examples/google-adk-agent/evals/ -v -m "agent_evaluation"

# Skip agent evaluations (no API key needed)
python3 -m pytest examples/google-adk-agent/evals/ -v -m "not agent_evaluation"
```

## Example: Stock Trading Agent Implementation

Here's the complete implementation for the Stock Trading agent:

1. **Agent Setup** - The agent uses MCPToolset to connect to our MCP server:
   ```python
   agent_tools = [
       MCPToolset(
           connection_params=StdioServerParameters(
               command="uv",
               args=["run", "open-stocks-mcp-server", "--transport", "stdio"],
           ),
       ),
   ]
   ```

2. **Expected Response** - The test expects the agent to list MCP tools:
   ```
   • echo
   • login_robinhood
   ```

3. **Running the Test**:
   ```bash
   PYTHONPATH=.:$PYTHONPATH adk eval \
     --config_file_path examples/google-adk-agent/evals/test_config.json \
     --print_detailed_results \
     examples/google-adk-agent \
     examples/google-adk-agent/evals/list_available_tools_test.json
   ```

## Troubleshooting

### Common Issues

1. **AttributeError: module 'agent' has no attribute 'agent'**
   - Ensure your agent's `__init__.py` includes `from . import agent`

2. **MCP Server Connection Issues**
   - Verify the MCP server starts correctly: `uv run open-stocks-mcp-server --transport stdio`
   - Check that `uv` is available in the PATH
   - Ensure the open-stocks-mcp package is properly installed

3. **API Quota Exceeded**
   - Tests include 2-second delays between evaluations
   - Run tests sequentially, not in parallel
   - Free tier allows 15 requests/minute

4. **Response Match Score Too Low**
   - Update the expected response in test JSON files
   - Agent responses may include formatting - adjust expectations accordingly
   - The threshold is 0.5 (50%) so exact matches aren't required

5. **Import Errors**
   - Ensure `PYTHONPATH=.:$PYTHONPATH` is set when running evaluations
   - Check that all dependencies are installed
   - Verify the agent module structure matches ADK expectations

### MCP-Specific Issues

1. **Tool Discovery Failures**
   - Verify MCP server exposes tools correctly
   - Check server logs for connection issues
   - Test tools individually with MCP client

2. **Authentication Issues**
   - SMS MFA codes expire quickly - use fresh codes
   - Validate Robinhood credentials separately
   - Check rate limiting from Robin Stocks API

## Best Practices

1. **Focus on Tool Listing** - The most reliable evaluation pattern tests the agent's ability to list its available MCP tools

2. **Update Expected Responses** - When MCP server tools change, update the expected response in test files

3. **Agent Instructions** - Keep prompts concise and focused on core functionality

4. **Sequential Execution** - Always run evaluations sequentially with delays to avoid API rate limits

5. **Environment Setup** - Ensure `GOOGLE_API_KEY` is set and MCP server is accessible

6. **MCP Server Stability** - Test MCP server independently before running agent evaluations

7. **Authentication Flow** - For login tests, use test credentials or mock responses to avoid real API calls