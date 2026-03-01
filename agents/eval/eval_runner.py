"""ADK Evaluation runner — validates agent routing and response quality.

Loads test cases from JSON datasets and verifies:
- Expected agent routing (e.g., ProposicaoAgent, EleitorAgent)
- Expected tool calls (e.g., buscar_proposicoes, registrar_voto)
- Expected intent classification
- Expected response substring matching (for conversational tests)

Usage as pytest:
    pytest agents/eval/test_eval_runner.py -v

Usage standalone:
    python -m agents.eval.eval_runner
"""

from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from app.logging import get_logger

logger = get_logger(__name__)

EVAL_DIR = Path(__file__).parent


@dataclass
class EvalCase:
    """A single evaluation test case."""

    name: str
    initial_prompt: str
    expected_agent: str | None = None
    expected_tool_calls: list[str] = field(default_factory=list)
    expected_intent: str | None = None
    expected_response_contains: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class EvalResult:
    """Result of a single evaluation."""

    case: EvalCase
    passed: bool
    response_text: str
    agent_matched: bool | None = None
    tools_matched: bool | None = None
    intent_matched: bool | None = None
    response_matched: bool | None = None
    errors: list[str] = field(default_factory=list)


def load_eval_cases(filename: str) -> list[EvalCase]:
    """Load evaluation cases from a JSON file.

    Args:
        filename: Name of the JSON file in the eval directory.

    Returns:
        List of EvalCase objects.
    """
    filepath = EVAL_DIR / filename
    with open(filepath) as f:
        data = json.load(f)

    return [
        EvalCase(
            name=item["name"],
            initial_prompt=item["initial_prompt"],
            expected_agent=item.get("expected_agent"),
            expected_tool_calls=item.get("expected_tool_calls", []),
            expected_intent=item.get("expected_intent"),
            expected_response_contains=item.get("expected_response_contains", []),
            tags=item.get("tags", []),
        )
        for item in data
    ]


def load_all_eval_cases() -> list[EvalCase]:
    """Load all evaluation cases from all JSON datasets.

    Returns:
        Combined list of all EvalCases across all datasets.
    """
    all_cases: list[EvalCase] = []
    for json_file in sorted(EVAL_DIR.glob("*_eval.json")):
        cases = load_eval_cases(json_file.name)
        all_cases.extend(cases)
        logger.info("eval.loaded", file=json_file.name, count=len(cases))
    return all_cases


def check_response_contains(
    response: str, expected_substrings: list[str]
) -> bool:
    """Check if the response contains at least one of the expected substrings.

    Case-insensitive matching.

    Args:
        response: The agent response text.
        expected_substrings: Substrings to look for (any match = pass).

    Returns:
        True if at least one substring is found in the response.
    """
    if not expected_substrings:
        return True
    response_lower = response.lower()
    return any(sub.lower() in response_lower for sub in expected_substrings)


def evaluate_case(
    case: EvalCase,
    response_text: str,
    routed_agent: str | None = None,
    called_tools: list[str] | None = None,
    detected_intent: str | None = None,
) -> EvalResult:
    """Evaluate a single test case against actual results.

    Args:
        case: The eval test case.
        response_text: The agent's response text.
        routed_agent: Name of the agent that handled the request.
        called_tools: List of tool names that were called.
        detected_intent: The detected intent (if available).

    Returns:
        EvalResult with pass/fail and details.
    """
    errors: list[str] = []

    # Check response content
    response_matched = None
    if case.expected_response_contains:
        response_matched = check_response_contains(
            response_text, case.expected_response_contains
        )
        if not response_matched:
            errors.append(
                f"Response does not contain any of: {case.expected_response_contains}"
            )

    # Check agent routing
    agent_matched = None
    if case.expected_agent and routed_agent:
        agent_matched = case.expected_agent == routed_agent
        if not agent_matched:
            errors.append(
                f"Expected agent {case.expected_agent}, got {routed_agent}"
            )

    # Check tool calls
    tools_matched = None
    if case.expected_tool_calls and called_tools is not None:
        tools_matched = all(
            tool in called_tools for tool in case.expected_tool_calls
        )
        if not tools_matched:
            errors.append(
                f"Expected tools {case.expected_tool_calls}, "
                f"got {called_tools}"
            )

    # Check intent
    intent_matched = None
    if case.expected_intent and detected_intent:
        intent_matched = case.expected_intent == detected_intent
        if not intent_matched:
            errors.append(
                f"Expected intent {case.expected_intent}, got {detected_intent}"
            )

    # Overall pass if no validation errors were generated
    # (skip checks where we don't have actual data to compare)
    passed = len(errors) == 0

    return EvalResult(
        case=case,
        passed=passed,
        response_text=response_text,
        agent_matched=agent_matched,
        tools_matched=tools_matched,
        intent_matched=intent_matched,
        response_matched=response_matched,
        errors=errors,
    )


def generate_eval_report(results: list[EvalResult]) -> dict[str, Any]:
    """Generate a summary report from evaluation results.

    Args:
        results: List of EvalResult objects.

    Returns:
        Summary dict with pass rate, failures, and per-tag metrics.
    """
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    # Per-tag metrics
    tag_results: dict[str, dict[str, int]] = {}
    for result in results:
        for tag in result.case.tags:
            if tag not in tag_results:
                tag_results[tag] = {"total": 0, "passed": 0}
            tag_results[tag]["total"] += 1
            if result.passed:
                tag_results[tag]["passed"] += 1

    failures = [
        {
            "name": r.case.name,
            "prompt": r.case.initial_prompt,
            "errors": r.errors,
            "response_preview": r.response_text[:200],
        }
        for r in results
        if not r.passed
    ]

    report = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
        "by_tag": {
            tag: {
                **stats,
                "pass_rate": round(stats["passed"] / stats["total"] * 100, 1),
            }
            for tag, stats in sorted(tag_results.items())
        },
        "failures": failures,
    }

    return report


if __name__ == "__main__":
    """Standalone runner — loads all cases and shows them (dry run)."""
    cases = load_all_eval_cases()
    print(f"Loaded {len(cases)} evaluation cases:")
    for case in cases:
        print(f"  [{', '.join(case.tags)}] {case.name}: {case.initial_prompt}")
