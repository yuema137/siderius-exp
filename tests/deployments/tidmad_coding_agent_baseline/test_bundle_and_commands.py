from __future__ import annotations

import json
import tarfile
from pathlib import Path

import pytest
from deployments.tidmad_coding_agent_baseline.tools import build_bundle as bundle_module
from deployments.tidmad_coding_agent_baseline.tools.agent_command import command_for
from deployments.tidmad_coding_agent_baseline.tools.build_bundle import build_bundle


def test_product_commands_pin_models_effort_and_noninteractive_permissions(tmp_path):
    prompt = tmp_path / "task.md"
    codex = command_for("codex", prompt)
    claude = command_for("claude", prompt)

    assert codex[:5] == ["codex", "-a", "never", "-s", "danger-full-access"]
    assert "gpt-5.6-sol" in codex
    assert 'model_reasoning_effort="medium"' in codex
    assert "--search" in codex
    assert "--skip-git-repo-check" in codex
    assert "--dangerously-skip-permissions" in claude
    assert claude[claude.index("--effort") + 1] == "medium"
    assert "--permission-prompts" not in claude


def test_bundle_splits_public_task_view_from_exact_private_task_snapshot(tmp_path, monkeypatch):
    missing = tmp_path / "missing.md"
    siderius_checkout = tmp_path / "siderius"
    siderius_checkout.mkdir()
    with pytest.raises(ValueError, match="operator-approved"):
        build_bundle(missing, siderius_checkout, tmp_path / "missing.tar.gz")

    def fake_build(_repo, _checkout, output):
        wheel = "siderius-0.2.0rc6-py3-none-any.whl"
        (output / wheel).write_bytes(b"test wheel")
        (output / "siderius-wheel-name.txt").write_text(f"{wheel}\n")
        (output / "requirements.txt").write_text("numpy==2.5.2\n")
        return "1" * 40, "f" * 64

    monkeypatch.setattr(bundle_module, "_build_evaluator", fake_build)

    task = tmp_path / "task.md"
    task.write_text("operator-approved kickoff\n")
    output = build_bundle(task, siderius_checkout, tmp_path / "bundle.tar.gz")
    second = build_bundle(task, siderius_checkout, tmp_path / "bundle-second.tar.gz")
    assert output.read_bytes() == second.read_bytes()
    with tarfile.open(output, "r:gz") as archive:
        names = set(archive.getnames())
        assert "tidmad-coding-agent-baseline/input/task.md" in names
        assert any(name.endswith("/input/tasks/tidmad/resolved/metric_spec.json") for name in names)
        assert not any(
            name.endswith("/input/tasks/tidmad/reference_data/segment_anchors.json")
            for name in names
        )
        assert not any(
            name.endswith("/input/tasks/tidmad/reference_data/tidmad_signal_frequencies.txt")
            for name in names
        )
        assert any(
            name.endswith(
                "/evaluator/task_snapshot/tasks/tidmad/reference_data/segment_anchors.json"
            )
            for name in names
        )
        assert "tidmad-coding-agent-baseline/input/bundle.sha256" in names
        assert (
            "tidmad-coding-agent-baseline/evaluator/siderius-0.2.0rc6-py3-none-any.whl"
        ) in names
        assert "tidmad-coding-agent-baseline/evaluator/requirements.txt" in names
        assert "tidmad-coding-agent-baseline/input/inference-requirements.txt" in names

        repo = Path(__file__).resolve().parents[3]
        task_members = [
            member
            for member in archive.getmembers()
            if member.isfile() and "/input/tasks/tidmad/" in member.name
        ]
        assert task_members
        bundled_paths = {member.name.split("/input/", 1)[1] for member in task_members}
        tracked_paths = {
            str(path.relative_to(repo)) for path in bundle_module._tracked_task_files(repo)
        }
        expected_public = {
            path
            for path in tracked_paths
            if not bundle_module._is_evaluator_only_task_file(repo / path, repo)
        }
        assert bundled_paths == expected_public
        for member in task_members:
            relative = member.name.split("/input/", 1)[1]
            extracted = archive.extractfile(member)
            assert extracted is not None
            assert extracted.read() == (repo / relative).read_bytes()

        provenance_member = archive.getmember("tidmad-coding-agent-baseline/input/provenance.json")
        provenance_file = archive.extractfile(provenance_member)
        assert provenance_file is not None
        provenance = json.load(provenance_file)
        assert provenance["version"] == "tidmad-coding-agent-input-v4"
        assert provenance["task_visibility"] == "agent-public-view-v2"
        assert len(provenance["task_md_sha256"]) == 64


def test_canonical_task_md_separates_score_health_and_segment_model_contract():
    repo = Path(__file__).resolve().parents[3]
    text = (repo / "deployments/tidmad_coding_agent_baseline/task.md").read_text()
    assert "finite raw score alone is **not** a valid result" in text
    assert "health_regression.yaml" in text
    assert "Health error, missing Health evidence" in text
    assert "must be a trained ML denoising model" in text
    assert "learned ML model fitted from the provided" in text
    assert "standalone hand-designed filter" in text
    assert "merely because it is wrapped in model-shaped code" in text
    assert "raw, non-overlapping 40,000-sample" in text
    assert "candidate-specific\nfree-form preprocessing or postprocessing" in text
    assert "TorchScript `model.pt`" in text
    assert "`[B, 40000]`" in text
    assert "`[B, 256, 40000]`" in text
    assert "frequency comb" not in text
    assert "matched filter" not in text
    assert "There is no agent-callable final-scoring command" in text
    assert "raw_and_ground_score.md" in text


def test_vm_install_replaces_same_version_wheel_with_exact_bundle_wheel():
    """A pin change can retain the package version and must still reinstall."""

    repo = Path(__file__).resolve().parents[3]
    install = (
        repo / "deployments" / "tidmad_coding_agent_baseline" / "machine" / "install_vm.sh"
    ).read_text()
    assert "--force-reinstall --no-deps" in install
    assert "SETENV" not in install
    assert "/opt/tidmad-inference/venv" in install
    assert "baseline-inference" in install
    assert "refuse to replace a bundle while the evaluated agent is active" in install
    assert "rm -rf -- /work/harness /work/input" in install


def test_vm_install_binds_noninteractive_agent_state_to_working_disk():
    """Catch systemd losing the CLI and silently using boot-disk HOME/cache state."""

    repo = Path(__file__).resolve().parents[3]
    install = (
        repo / "deployments" / "tidmad_coding_agent_baseline" / "machine" / "install_vm.sh"
    ).read_text()

    assert "usermod --home /baseline/agent/home baseline-agent" in install
    assert "HOME=/baseline/agent/home" in install
    assert "TMPDIR=/baseline/agent/tmp" in install
    assert "XDG_CACHE_HOME=/baseline/agent/cache" in install
    assert "PIP_CACHE_DIR=/baseline/agent/cache/pip" in install
    assert "UV_CACHE_DIR=/baseline/agent/cache/uv" in install
    assert "NPM_CONFIG_CACHE=/baseline/agent/cache/npm" in install
    assert "PATH=/baseline/agent/home/.local/bin:" in install
