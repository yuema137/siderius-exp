"""Ordering experiment controls must not change the reference baseline.

Transferred from SIDERIUS's test_ordering_override_surface at the PR #422
test-ownership closeout. This protects the task-owned comparison launcher;
framework lock consistency and permutation preservation remain in SIDERIUS.
"""

import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[3] / "tasks/tidmad/tools/run_comparison.py"


def test_comparison_forwards_only_explicit_ordering_overrides():
    source = SOURCE.read_text()
    assert '"--order_strategy_override", order_strategy_override' in source
    assert "if order_strategy_override is not None:" in source
    assert "if file_order_override is not None:" in source


def test_reference_baseline_never_consumes_agent_ordering_override():
    tree = ast.parse(SOURCE.read_text())
    baseline = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "run_baseline_trial"
    )
    names = {node.id for node in ast.walk(baseline) if isinstance(node, ast.Name)}
    strings = {
        node.value
        for node in ast.walk(baseline)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert not any(
        "order_strategy" in name or "file_order" in name for name in names | strings
    )
