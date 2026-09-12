"""C1 regression for Comparison's production Health policy path."""

from pathlib import Path
import os
import importlib

import pytest


def test_baseline_trial_calls_real_loader_with_production_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from tasks.tidmad.tools import run_comparison as comparison
    from execute_tools.health_checks import config as health_config
    from execute_tools.health_checks import evaluation as health_evaluation

    # Earlier startup tests call comparison._main, which intentionally updates
    # its module globals while checking a foreign checkout. Reload from the
    # explicit environment so this regression observes the production constant
    # assembled by the real module import, without patching that path.
    comparison = importlib.reload(comparison)
    selected_checkout = Path(os.environ["SIDERIUS_CHECKOUT"]).resolve()
    assert Path(comparison.SIDERIUS_ROOT) == selected_checkout
    monkeypatch.setattr(health_config, "SIDERIUS_ROOT", str(selected_checkout))
    runtime_config = tmp_path / "runtime-health.yaml"
    runtime_config.write_text("health_gates: []\n", encoding="utf-8")

    models = tmp_path / "models"
    models.mkdir()

    class StubSandbox:
        def __init__(self, **kwargs: object) -> None:
            self.dirs = {"models": str(models)}

        def execute_training(self, *, exp_id: str, **kwargs: object) -> dict:
            (models / f"model_punet_{exp_id}_agent.pth").write_bytes(b"stub")
            return {
                "status": "success",
                "results": {"final_loss": 1.0, "loss_history": [1.0], "model_params": {}},
            }

        def execute_inference(self, **kwargs: object) -> dict:
            return {"status": "success"}

        def save_record(self, record: dict) -> None:
            pass

    monkeypatch.setattr(comparison, "TidmadSandbox", StubSandbox)
    monkeypatch.setattr(
        comparison,
        "build_sample_set",
        lambda **kwargs: {0: [0]},
    )
    monkeypatch.setattr(
        comparison,
        "load_anchor_map",
        lambda path: {"anchors": {}, "s_max": 1.0},
    )
    monkeypatch.setattr(
        comparison,
        "score_vector",
        lambda **kwargs: ([0.1], 0.1),
    )
    original_loader = health_evaluation.load_health_gates_config
    observed: dict[str, object] = {}

    def spy_loader(path):
        loaded = original_loader(path)
        observed.setdefault("loaded_paths", []).append(str(path))
        return loaded

    monkeypatch.setattr(health_evaluation, "load_health_gates_config", spy_loader)
    monkeypatch.setattr(comparison, "DATA_DIR", str(tmp_path))
    record = comparison.run_baseline_trial(
        "punet", str(tmp_path / "workspace"), health_checks_config=str(runtime_config)
    )

    production_path = selected_checkout / "configs" / "health" / "health_checks.yaml"
    assert observed["loaded_paths"] == [str(runtime_config), str(production_path)]
    assert record["status"] == "success"
    monkeypatch.setattr(comparison, "HEALTH_CHECKS_PATH", str(tmp_path / "missing-policy.yaml"))
    with pytest.raises(FileNotFoundError):
        comparison.run_baseline_trial(
            "punet", str(tmp_path / "workspace-missing"), health_checks_config=str(runtime_config)
        )
