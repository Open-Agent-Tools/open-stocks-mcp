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

