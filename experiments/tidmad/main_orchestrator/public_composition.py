"""Additional public composition for the original protected candidate scorer."""

from pathlib import Path

from experiments.tidmad.information_treatments.prior_binding import composition_overlay


def public_candidate_composition(
    frozen_input: Path, analysis_path: Path | None = None
) -> dict:
    """Reference frozen task bytes and select complete candidate evaluation.

    The caller writes the returned manifest outside the frozen input tree and
    binds its candidate evaluator in the process invoking the native tuner.
    Prior authorization and publication remain the treatment/deployment owner's
    responsibility; no analysis is enabled by default.
    """
    payload = composition_overlay(frozen_input, analysis_path)
    payload["task_data_path"] = {
        "file": str(Path(__file__).with_name("compact_training.py").resolve()),
        "symbol": "CompactFrozenPoolDataPath",
        "id": "tidmad_compact_frozen_training_pool",
        "config": {
            "frozen_manifest": str(
                (
                    frozen_input
                    / "tasks/tidmad/compositions/continuous_regression_frozen_pool.yaml"
                ).resolve()
            )
        },
    }
    payload["metric"]["implementation"] = {
        "module": "execute_tools.evaluation_metric",
        "symbol": "CandidateEvaluationMetric",
    }
    return payload


def public_analysis_composition(frozen_input: Path, analysis_path: Path) -> dict:
    """Bind Full analysis to the original task identity and frozen policy.

    This separate manifest is for analysis against an input-only physical data
    view. The compact training adapter retains its own identity and manifest.
    """
    payload = composition_overlay(frozen_input, analysis_path)
    payload["metric"]["implementation"] = {
        "module": "execute_tools.evaluation_metric",
        "symbol": "CandidateEvaluationMetric",
    }
    return payload
