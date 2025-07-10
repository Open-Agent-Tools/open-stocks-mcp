# ADK Testing and Evaluations Guide

This guide covers testing and evaluation procedures for the Stock Trading Agent using Google ADK framework.

**Note**: This documentation and evaluation tests have been moved from `examples/google-adk-agent/evals/` to `tests/evals/` for better organization alongside the main test suite.

## Prerequisites

### 1. Environment Setup
```bash
# Set required environment variables
export GOOGLE_API_KEY="your-google-api-key"
export GOOGLE_MODEL="gemini-2.0-flash"  # Optional, defaults to gemini-2.0-flash

# For Robinhood authentication (optional - enables environment-based login)
export ROBINHOOD_USERNAME="your_email@example.com"
export ROBINHOOD_PASSWORD="your_robinhood_password"
```

Or create a `.env` file in the project root:
```
GOOGLE_API_KEY=your-google-api-key
ROBINHOOD_USERNAME=your_email@example.com
ROBINHOOD_PASSWORD=your_robinhood_password
```

### 2. Install Dependencies
```bash
# From the google-adk-agent directory
pip install -r requirements.txt

# Verify ADK installation
adk --help
```

## Running ADK Evaluations

> **⚠️ Important**: Always run ADK evaluations from the **project root directory** (`/Users/wes/Development/open-stocks-mcp/`). The ADK expects the agent module path relative to the current working directory.

### ✅ Correct Way (From Project Root)
```bash
# Navigate to project root first
cd /Users/wes/Development/open-stocks-mcp

# Basic evaluation command (with recommended config)
adk eval examples/google-adk-agent tests/evals/list_available_tools_test.json --config_file_path tests/evals/test_config.json

# With custom configuration
adk eval examples/google-adk-agent tests/evals/list_available_tools_test.json --config_file_path tests/evals/test_config.json

# With detailed results output
adk eval examples/google-adk-agent tests/evals/list_available_tools_test.json --config_file_path tests/evals/test_config.json --print_detailed_results

# With specific run ID for tracking
adk eval examples/google-adk-agent tests/evals/list_available_tools_test.json --config_file_path tests/evals/test_config.json --run_id stock_trader_test_$(date +%s)

# With custom model
GOOGLE_MODEL="gemini-2.0-flash-exp" adk eval examples/google-adk-agent tests/evals/list_available_tools_test.json --config_file_path tests/evals/test_config.json
```

### ❌ Wrong Way (From Agent Directory)
```bash
# Don't do this - will cause path errors
cd examples/google-adk-agent
adk eval agent.py ../../tests/evals/list_available_tools_test.json  # ❌ Incorrect syntax
```

### 📋 Prerequisites Checklist
Before running evaluations, ensure:

1. **✅ Google ADK Installed**
   ```bash
   pip install google-agent-developer-kit
   adk --help  # Verify installation
   ```

2. **✅ Environment Variables Set**
   ```bash
   export GOOGLE_API_KEY="your-google-api-key"
   export ROBINHOOD_USERNAME="your_email@example.com"
   export ROBINHOOD_PASSWORD="your_robinhood_password"
   ```

3. **✅ Correct Working Directory**
   ```bash
   pwd  # Should show: /Users/wes/Development/open-stocks-mcp
   ```

4. **✅ Agent Module Available**
   ```bash
   ls examples/google-adk-agent/  # Should show: agent.py, __init__.py, etc.
   ```

### 🎯 Expected Results
A successful evaluation will show:
```
Using evaluation criteria: {'tool_trajectory_avg_score': 0.5, 'response_match_score': 0.5}
Running Eval: list_available_tools_test_set:list_available_tools_test
Result: ✅ Passed

*********************************************************************
Eval Run Summary
list_available_tools_test_set:
  Tests passed: 1
  Tests failed: 0
```

**Last Successful Run**: 2025-07-10T15:01:40Z

## Available Evaluation Tests

### 1. List Available Tools Test
**File**: `tests/evals/list_available_tools_test.json`  
**Purpose**: Validates that the agent can successfully list all available MCP tools  
**Expected Output**: Alphabetically sorted bullet list of 60 MCP tools

```bash
adk eval examples/google-adk-agent tests/evals/list_available_tools_test.json --config_file_path tests/evals/test_config.json
```

### 2. Creating Custom Evaluation Tests

#### Test File Structure
```json
{
  "eval_set_id": "your_test_set_id",
  "name": "Your Test Name",
  "description": "Description of what this test validates",
  "eval_cases": [
    {
      "eval_id": "your_test_case_id",
      "conversation": [
        {
          "invocation_id": "unique-invocation-id",
          "user_content": {
            "parts": [
              {
                "text": "Your test prompt here"
              }
            ],
            "role": "user"
          },
          "final_response": {
            "parts": [
              {
                "text": "Expected response from agent"
              }
            ],
            "role": "model"
          },
          "intermediate_data": {
            "tool_uses": [
              {
                "id": "adk-tool-use-id",
                "args": {"param": "value"},
                "name": "tool_name"
              }
            ],
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

#### Example Test Cases to Create

1. **Portfolio Analysis Test**
```bash
# Test prompt: "Show me my current portfolio holdings"
# Expected tools: portfolio, positions, account_details
```

2. **Stock Research Test**
```bash
# Test prompt: "Tell me about Apple's stock performance and analyst ratings"
# Expected tools: stock_info, stock_price, stock_ratings, stock_news
```

3. **Market Overview Test**
```bash
# Test prompt: "What are the top S&P 500 movers today?"
# Expected tools: top_movers_sp500, market_hours
```

4. **Dividend Analysis Test**
```bash
# Test prompt: "How much have I earned in dividends this year?"
# Expected tools: total_dividends, dividends
```

## Evaluation Configuration

### Test Configuration File
**File**: `tests/evals/test_config.json`

```json
{
  "criteria": {
    "tool_trajectory_avg_score": 0.5,
    "response_match_score": 0.5
  }
}
```

### Scoring Criteria
- **tool_trajectory_avg_score**: Measures if the agent uses the correct tools in the right sequence
- **response_match_score**: Measures if the agent's response matches the expected output

## Troubleshooting

### Common Issues

#### 1. MCP Server Connection Issues
```bash
# Test MCP server directly
uv run open-stocks-mcp-server --transport stdio

# Check if server responds to list_tools
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | uv run open-stocks-mcp-server --transport stdio
```

#### 2. Authentication Errors
```bash
# Verify environment variables are set
echo "GOOGLE_API_KEY: ${GOOGLE_API_KEY:0:10}..."
echo "ROBINHOOD_USERNAME: $ROBINHOOD_USERNAME"

# Test Google API key
python3 -c "
import os
from google import genai
genai.configure(api_key=os.environ['GOOGLE_API_KEY'])
print('Google API key is valid')
"
```

#### 3. ADK Command Not Found
```bash
# Reinstall Google ADK
pip install --upgrade google-adk

# Verify installation
python3 -c "import google.adk; print('ADK installed successfully')"
```

#### 4. Tool Connection Issues
```bash
# Check if MCP server is accessible
python3 -c "
from examples.google_adk_agent.agent import create_agent
agent = create_agent()
print('Agent created successfully')
"
```



### Local Testing Script
```bash
#!/bin/bash
# test-all-evals.sh

set -e

echo "Running all ADK evaluations..."

# List available tools test
echo "Testing tool listing..."
adk eval examples/google-adk-agent tests/evals/list_available_tools_test.json --config_file_path tests/evals/test_config.json

# Add more tests as they are created
# echo "Testing portfolio analysis..."
# adk eval examples/google-adk-agent tests/evals/portfolio_analysis_test.json --config_file_path tests/evals/test_config.json

echo "All evaluations completed successfully!"
```

## Performance Monitoring

### Evaluation Metrics to Track
- **Tool Selection Accuracy**: How often the agent chooses the correct tools
- **Response Quality**: How well the agent's responses match expected outputs
- **Execution Time**: How long evaluations take to complete
- **Error Rate**: Frequency of evaluation failures

### Monitoring Script
```python
#!/usr/bin/env python3
"""Monitor ADK evaluation performance over time."""

import json
import time
import subprocess
from datetime import datetime

def run_evaluation(test_file):
    """Run a single evaluation and return results."""
    start_time = time.time()
    try:
        result = subprocess.run(
            ["adk", "eval", "examples/google-adk-agent", test_file, "--config_file_path", "tests/evals/test_config.json"],
            capture_output=True,
            text=True,
            check=True
        )
        duration = time.time() - start_time
        return {
            "success": True,
            "duration": duration,
            "output": result.stdout
        }
    except subprocess.CalledProcessError as e:
        duration = time.time() - start_time
        return {
            "success": False,
            "duration": duration,
            "error": e.stderr
        }

if __name__ == "__main__":
    tests = ["tests/evals/list_available_tools_test.json"]
    
    for test in tests:
        print(f"Running {test}...")
        result = run_evaluation(test)
        
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] {test}: {'PASS' if result['success'] else 'FAIL'} ({result['duration']:.2f}s)")
        
        if not result['success']:
            print(f"Error: {result['error']}")
```

## Best Practices

### 1. Test Design
- Create tests that cover all major tool categories
- Include both positive and negative test cases
- Test edge cases and error conditions
- Validate tool parameter usage

### 2. Evaluation Maintenance
- Run evaluations regularly (CI/CD)
- Update expected outputs when tools change
- Monitor evaluation performance trends
- Add new tests for new features

### 3. Debugging
- Use verbose output for failing tests
- Check MCP server logs for connection issues
- Verify environment variables are correctly set
- Test individual tools outside of ADK framework

## Additional Resources

- [Google ADK Documentation](https://developers.google.com/agent-development-kit)
- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [Open Stocks MCP Documentation](../../README.md)
- [Stock Trading Agent Documentation](README.md)