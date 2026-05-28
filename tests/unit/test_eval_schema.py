"""Schema and shape validation for ADK eval JSON fixtures.

Validates that every *schwab*.json file under tests/evals/ adheres to the
expected ADK eval structure and that final_response contains non-empty text.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

EVALS_DIR = Path(__file__).resolve().parents[2] / "tests" / "evals"
SCHWAB_EVAL_FILES = sorted(EVALS_DIR.glob("*schwab*.json"))


def _load(path: Path) -> dict:  # type: ignore[type-arg]
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("eval_file", SCHWAB_EVAL_FILES, ids=lambda p: p.name)
@pytest.mark.unit
@pytest.mark.journey_system
def test_eval_has_required_top_level_fields(eval_file: Path) -> None:
    data = _load(eval_file)
    assert "eval_set_id" in data, f"{eval_file.name}: missing 'eval_set_id'"
    assert "eval_cases" in data, f"{eval_file.name}: missing 'eval_cases'"
    assert isinstance(data["eval_cases"], list), (
        f"{eval_file.name}: 'eval_cases' must be a list"
    )
    assert len(data["eval_cases"]) > 0, (
        f"{eval_file.name}: 'eval_cases' must be non-empty"
    )


@pytest.mark.parametrize("eval_file", SCHWAB_EVAL_FILES, ids=lambda p: p.name)
@pytest.mark.unit
@pytest.mark.journey_system
def test_eval_cases_have_required_fields(eval_file: Path) -> None:
    data = _load(eval_file)
    for idx, case in enumerate(data["eval_cases"]):
        ctx = f"{eval_file.name}[{idx}]"
        assert "eval_id" in case, f"{ctx}: missing 'eval_id'"
        assert "conversation" in case, f"{ctx}: missing 'conversation'"
        assert isinstance(case["conversation"], list), (
            f"{ctx}: 'conversation' must be a list"
        )
        assert len(case["conversation"]) > 0, f"{ctx}: 'conversation' must be non-empty"
        assert "session_input" in case, f"{ctx}: missing 'session_input'"


@pytest.mark.parametrize("eval_file", SCHWAB_EVAL_FILES, ids=lambda p: p.name)
@pytest.mark.unit
@pytest.mark.journey_system
def test_eval_conversation_turns_have_required_fields(eval_file: Path) -> None:
    data = _load(eval_file)
    for case_idx, case in enumerate(data["eval_cases"]):
        for turn_idx, turn in enumerate(case.get("conversation", [])):
            ctx = f"{eval_file.name}[{case_idx}][{turn_idx}]"
            assert "user_content" in turn, f"{ctx}: missing 'user_content'"
            assert "final_response" in turn, f"{ctx}: missing 'final_response'"
            assert "intermediate_data" in turn, f"{ctx}: missing 'intermediate_data'"

            user_content = turn["user_content"]
            assert "parts" in user_content, f"{ctx}: user_content missing 'parts'"
            assert user_content.get("role") == "user", (
                f"{ctx}: user_content role must be 'user'"
            )

            final_response = turn["final_response"]
            assert "parts" in final_response, f"{ctx}: final_response missing 'parts'"
            assert final_response.get("role") == "model", (
                f"{ctx}: final_response role must be 'model'"
            )


@pytest.mark.parametrize("eval_file", SCHWAB_EVAL_FILES, ids=lambda p: p.name)
@pytest.mark.unit
@pytest.mark.journey_system
def test_eval_final_response_has_nonempty_text(eval_file: Path) -> None:
    data = _load(eval_file)
    for case_idx, case in enumerate(data["eval_cases"]):
        for turn_idx, turn in enumerate(case.get("conversation", [])):
            ctx = f"{eval_file.name}[{case_idx}][{turn_idx}]"
            parts = turn.get("final_response", {}).get("parts", [])
            assert len(parts) > 0, f"{ctx}: final_response.parts must be non-empty"
            text = parts[0].get("text", "")
            assert text.strip(), f"{ctx}: final_response text must be non-empty"


@pytest.mark.parametrize("eval_file", SCHWAB_EVAL_FILES, ids=lambda p: p.name)
@pytest.mark.unit
@pytest.mark.journey_system
def test_eval_intermediate_data_has_schwab_tool(eval_file: Path) -> None:
    data = _load(eval_file)
    for case_idx, case in enumerate(data["eval_cases"]):
        for turn_idx, turn in enumerate(case.get("conversation", [])):
            ctx = f"{eval_file.name}[{case_idx}][{turn_idx}]"
            tool_uses = turn.get("intermediate_data", {}).get("tool_uses", [])
            assert len(tool_uses) > 0, (
                f"{ctx}: intermediate_data.tool_uses must be non-empty"
            )
            tool_names = [u.get("name", "") for u in tool_uses]
            schwab_tools = [n for n in tool_names if n.startswith("schwab_")]
            assert schwab_tools, (
                f"{ctx}: at least one tool_use must name a schwab_* tool; got {tool_names}"
            )
