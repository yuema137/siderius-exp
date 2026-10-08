"""Task-owned tests for deterministic official-paper result rendering."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from tasks.tidmad.tools import render_official_paper_result as render


def _summary() -> dict:
    return {
        "model_key": "fcnet",
        "model": "TIDMAD official band-split FCNet",
        "file_vector_linear": [5.27],
        "file_vector_log": [1.0],
        "checkpoint_by_file": {"0": "0_4"},
        "inference_seconds": {"0": 2.5},
        "denoising_score": 6.4348,
        "full_scope": True,
        "file_indices": [0],
        "seg_size": 40_000,
        "batch_size": 1,
        "device": "cuda:0",
        "s_max": 295_715_680.14,
        "computed_at": "2026-01-01T00:00:00Z",
        "data_dir": "/external/data",
    }


def test_summary_filename_contract_is_preserved(tmp_path: Path) -> None:
    """A renamed input would make an existing paper score disappear."""
    expected = tmp_path / "tidmad_official_fcnet_banded_score.json"
    expected.write_text(json.dumps(_summary()), encoding="utf-8")

    assert render.load_summary(tmp_path, "fcnet") == _summary()
    assert render.load_summary(tmp_path, "punet") is None


def test_per_model_report_preserves_the_scientific_ruler(tmp_path: Path) -> None:
    """The renderer must not change the frozen score or aggregation statement."""
    output = tmp_path / "fcnet.md"

    render.render_per_model(_summary(), output)

    text = output.read_text(encoding="utf-8")
    assert "Canonical `denoising_score` = 6.434800" in text
    assert "log_5.27" in text
    assert "raw-baseline floor = 1.0007" in text
    assert "ground-truth ceiling = 10.1134" in text
    assert "Per-band or per-subset aggregates are NOT reported" in text


def test_input_and_output_directories_are_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rendering must not read from or write to an ambient repository path."""
    monkeypatch.setattr(sys, "argv", ["render-official-paper-result"])

    with pytest.raises(SystemExit) as exc_info:
        render.parse_args()

    assert exc_info.value.code == 2


def _command(text: str, module: str) -> list[str]:
    """Read the actual emitted shell recipe, including line continuations."""
    import shlex

    for block in text.split("```bash\n")[1:]:
        tokens = shlex.split(block.split("```", 1)[0].replace("\\\n", ""))
        if tokens[:3] == [".venv/bin/python", "-m", module]:
            return tokens
    pytest.fail(f"No module recipe for {module}")


def test_generated_scorer_recipe_supplies_every_required_location(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The former recipe omitted source, checkpoints and the anchor map."""
    from tasks.tidmad.tools import score_tidmad_official_banded as scorer

    output = tmp_path / "fcnet.md"
    render.render_per_model(_summary(), output)
    text = output.read_text()
    command = _command(text, scorer.__name__)
    monkeypatch.setattr(scorer.torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(sys, "argv", command[2:])
    args = scorer.parse_args()

    assert args.models == ["fcnet"]
    assert args.tidmad_repo == Path("/external/TIDMAD-source")
    assert args.checkpoint_dir == Path("/external/TIDMAD-checkpoints")
    assert args.data_dir == Path("/external/TIDMAD-data")
    assert args.anchor_map == Path("tasks/tidmad/reference_data/segment_anchors.json")
    assert args.work_dir == Path("/external/tidmad-reference/new-inference")
    assert args.file_indices is None
    assert args.delete_denoised_after_score is False
    assert "| 0000 | `0_4` | 2.5 | 5.2700e+00 | 1.0000 |" in text
    assert "Inference wall time: 0.0 min (2 s)" in text
    assert "Computed at: 2026-01-01T00:00:00Z" in text
    assert "`/external/data` (raw inputs)" in text


@pytest.mark.parametrize("model", ["fcnet", "transformer"])
@pytest.mark.parametrize("missing_target", [False, True])
def test_health_recipe_preserves_scope_and_requires_layout_choice(
    model: str, missing_target: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Archived partial scans need a flag; old records may lack target_dir."""
    from tasks.tidmad.tools import official_paper_health_scan as scanner

    root = Path(__file__).resolve().parents[4]
    fixture = root / "tasks/tidmad/reference_data/official_paper_result"
    health = json.loads((fixture / f"{model}_health.json").read_text())
    if missing_target:
        health.pop("target_dir", None)
        health["denoised_dir"] = "/external/legacy outputs"
    text = "\n".join(render.render_health_section(health))
    command = _command(text, scanner.__name__)
    monkeypatch.setattr(sys, "argv", command[2:])
    args = scanner.parse_args()

    assert args.model == model
    assert args.denoised_dir == Path(health["denoised_dir"])
    assert args.target_dir == Path(health.get("target_dir", "/external/TIDMAD-data"))
    assert args.peek_samples == 1_000_000
    assert args.allow_partial is (model == "transformer")
    assert args.pattern == "abra_validation_denoised_{model}_{index:04d}.h5"
    assert args.json_out == Path(
        f"/external/tidmad-reference/new-report/{model}_health.json"
    )
    assert "explicitly selects the legacy layout" in text
    assert (
        "abra_validation_denoised_{model}_tidmad_official_banded_{index:04d}.h5" in text
    )
    assert "`unique_int8 > 25`, `std_mv >= 1.0`, `mode_fraction < 0.95`" in text
    if model == "fcnet":
        assert "Healthy on 20 of 20 files" in text
        assert (
            "| 0000 | `0_4` | 0.2797 | 103 | 3.9845 | 2.98 | -0.0062 | 0.0001 | PASS (DSA) |"
            in text
        )
    else:
        assert "Healthy on 0 of 18 files" in text
        assert "Missing denoised outputs: `0018`, `0019`" in text
        assert (
            "| 0000 | `0_4` | 0.2797 | 1 | 0.0000 | 100.00 | — | — | FAIL (dsa) |"
            in text
        )


def test_generated_renderer_recipe_uses_external_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A copyable command must not rewrite the frozen report directory."""
    output = tmp_path / "README.md"
    render.render_readme({"fcnet": _summary()}, output)
    text = output.read_text()
    command = _command(text, render.__name__)
    monkeypatch.setattr(sys, "argv", command[2:])
    args = render.parse_args()

    assert args.summary_dir == Path("/external/tidmad-reference/summaries")
    assert args.out_dir == Path("/external/tidmad-reference/new-report")
    assert (
        "`<model>_health.json` inputs must be placed in that output directory" in text
    )
    assert "| fcnet | **6.4348** | 5.4341 | -3.6786 | *not scanned* |" in text


def test_documented_fresh_scan_pattern_matches_scorer_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The scanner's legacy default does not find fresh banded outputs."""
    from tasks.tidmad.tools import official_paper_health_scan as scanner
    from tasks.tidmad.tools import score_tidmad_official_banded as scorer

    root = Path(__file__).resolve().parents[4]
    guide = root / "tasks/tidmad/reference_data/official_paper_result/reproduction.md"
    command = _command(guide.read_text(), scanner.__name__)
    monkeypatch.setattr(sys, "argv", command[2:])
    args = scanner.parse_args()

    assert (
        args.pattern
        == "abra_validation_denoised_{model}_tidmad_official_banded_{index:04d}.h5"
    )
    assert args.pattern.format(model=args.model, index=0) == scorer.denoised_filename(
        "fcnet", 0
    )
    assert args.target_dir == Path("/external/TIDMAD-data")
    assert args.denoised_dir == Path(
        "/external/tidmad-reference/new-inference/denoised_fcnet"
    )
    assert args.allow_partial is False
