"""ADK evaluation tests for Stock Trader agent.

This test suite validates that Stock_Trader's tools work correctly
when called by AI agents in the Google ADK framework.

Note: These tests require the Google ADK to be installed:
pip install google-agent-developer-kit
"""

import asyncio

import pytest

try:
    from google.adk.evaluation.agent_evaluator import AgentEvaluator

    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    AgentEvaluator = None


class TestStockTraderAgentEvaluation:
    """Agent evaluation tests for Stock Trader."""

    @pytest.mark.agent_evaluation
    @pytest.mark.skipif(not ADK_AVAILABLE, reason="Google ADK not installed")
    @pytest.mark.asyncio
    async def test_list_available_tools_agent(self):
        """Test agent listing available tools."""
        await AgentEvaluator.evaluate(
            agent_module="examples.google_adk_agent",
            eval_dataset_file_path_or_dir="tests/evals/list_available_tools_test.json",
        )
        await asyncio.sleep(2)  # Rate limiting delay
