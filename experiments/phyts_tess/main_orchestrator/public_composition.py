"""The composition an external caller receives: declaration without arithmetic.

Three substitutions turn the task's own manifest into a public one, and each
is one half of a boundary recorded in
[EXECUTION_BOUNDARY.md](EXECUTION_BOUNDARY.md):

1. the data path is sourced from the answer-free agent view;
2. the metric keeps its DECLARATION and loses its implementation, becoming
   the framework's `CandidateEvaluationMetric`, which refuses to score
   without an explicitly bound evaluator;
3. the observational secondary metrics are dropped, because carrying them
   would mean shipping the same arithmetic for values the caller never
   orders candidates by.

The scoreability contracts stay. They validate deliverable FORMAT and carry
no truth, and a caller that cannot check its own output well-formedness
submits malformed deliverables instead of asking.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "CANDIDATE_METRIC_IMPLEMENTATION",
    "COMPOSITION_RELATIVE_PATH",
    "public_composition",
]

COMPOSITION_RELATIVE_PATH = Path(
    "tasks/phyts_tess/compositions/rotation_regression.yaml"
)

#: The framework's declaration-only metric. Not an `EvaluationMetric`: it
#: advertises no local arithmetic, and `require_executor()` raises
#: `NoRunMetricError` unless a complete evaluator is bound in the process.
CANDIDATE_METRIC_IMPLEMENTATION = {
    "module": "execute_tools.evaluation_metric",
    "symbol": "CandidateEvaluationMetric",
}


_REFERENCE_KEYS = {"file", "config", "declaration", "dir"}


def _absolutize(node: Any, base: Path, rebase: tuple[Path, Path] | None) -> None:
    """Resolve every manifest-relative reference, optionally onto a copy.

    The published manifest lives outside the task tree, so a relative `file:`
    or `config:` would resolve against the wrong directory — silently, and
    only at compose time.

    `rebase` maps `(repository_root, task_tree)`. Without it the references
    point back into siderius-exp, which a caller must not need: that
    repository carries the scoring arithmetic and the committed identity
    manifest. With it they point at the bundle's own copy.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if key in _REFERENCE_KEYS and isinstance(value, str):
                resolved = (base / value).resolve()
                if rebase is not None:
                    root, tree = rebase
                    if resolved.is_relative_to(root):
                        resolved = tree / resolved.relative_to(root)
                node[key] = str(resolved)
            else:
                _absolutize(value, base, rebase)
    elif isinstance(node, list):
        for item in node:
            _absolutize(item, base, rebase)


def public_composition(
    root: Path, agent_view: Path, task_tree: Path | None = None
) -> dict[str, Any]:
    """Build the caller-visible manifest from the task's own declaration.

    `root` is the siderius-exp checkout, read for the declaration.
    `task_tree` is where the bundle's copy of the public subset lives; when
    given, every reference points there instead of back into the repository.
    """
    source = (root / COMPOSITION_RELATIVE_PATH).resolve()
    payload: dict[str, Any] = yaml.safe_load(source.read_text(encoding="utf-8"))
    rebase = (root.resolve(), task_tree.resolve()) if task_tree is not None else None
    _absolutize(payload, source.parent, rebase)

    public_path = Path(__file__).with_name("public_data_path.py").resolve()
    if task_tree is not None:
        # Published beside the package it subclasses, so its absolute import
        # resolves with only the bundle on the path.
        public_path = (
            task_tree / "tasks" / "phyts_tess" / "runtime" / "public_data_path.py"
        )
    payload["task_data_path"] = {
        "file": str(public_path),
        "symbol": "PublicTessTaskDataPath",
        "id": "phyts_tess_rotation_public",
        "config": {"agent_view": str(Path(agent_view).resolve())},
    }

    if "metric" not in payload:
        raise ValueError(f"{source} declares no metric to publish")
    payload["metric"]["implementation"] = dict(CANDIDATE_METRIC_IMPLEMENTATION)

    # Observational only, and never an ordering input. Dropping them is a
    # boundary decision, not an oversight: see EXECUTION_BOUNDARY.md.
    payload.pop("secondary_metrics", None)

    # No-prior is the condition under study here. An analysis binding would
    # be a second information channel, which is the thing the contrast holds
    # fixed.
    payload["data_analysis"] = {"enabled": False}
    return payload


def write_public_composition(root: Path, agent_view: Path, destination: Path) -> Path:
    """Serialize the public manifest, refusing to overwrite."""
    if destination.exists():
        raise ValueError(f"refusing to overwrite an existing manifest: {destination}")
    destination.write_text(
        yaml.safe_dump(public_composition(root, agent_view), sort_keys=False),
        encoding="utf-8",
    )
    return destination
