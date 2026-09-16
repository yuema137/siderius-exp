from __future__ import annotations

import hashlib
import json
import tarfile
from pathlib import Path

import pytest
from deployments.tidmad_coding_agent_baseline.tools import build_bundle as bundle_module
from deployments.tidmad_coding_agent_baseline.tools.agent_command import command_for
from deployments.tidmad_coding_agent_baseline.tools.build_bundle import build_bundle

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TREATMENTS = REPOSITORY_ROOT / "experiments/tidmad/information_treatments"


def _archive_json(archive: tarfile.TarFile, name: str) -> dict:
    stream = archive.extractfile(archive.getmember(name))
    assert stream is not None
    return json.load(stream)


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
        build_bundle(
            missing,
            TREATMENTS / "prerelease-without-advice.yaml",
            siderius_checkout,
            tmp_path / "missing.tar.gz",
        )

    def fake_build(_repo, _checkout, output):
        wheel = "siderius-0.2.0rc6-py3-none-any.whl"
        (output / wheel).write_bytes(b"test wheel")
        (output / "siderius-wheel-name.txt").write_text(f"{wheel}\n")
        (output / "requirements.txt").write_text("numpy==2.5.2\n")
        return "1" * 40, "f" * 64

    monkeypatch.setattr(bundle_module, "_build_evaluator", fake_build)

    task = tmp_path / "task.md"
    task.write_text("operator-approved kickoff\n")
    treatment = TREATMENTS / "prerelease-without-advice.yaml"
    output = build_bundle(task, treatment, siderius_checkout, tmp_path / "bundle.tar.gz")
    second = build_bundle(task, treatment, siderius_checkout, tmp_path / "bundle-second.tar.gz")
    assert output.read_bytes() == second.read_bytes()
    with tarfile.open(output, "r:gz") as archive:
        names = set(archive.getnames())
        assert "tidmad-coding-agent-baseline/input/task.md" in names
        assert "tidmad-coding-agent-baseline/input/treatment.json" in names
        assert "tidmad-coding-agent-baseline/input/advice.json" not in names
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

        repo = REPOSITORY_ROOT
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
        assert provenance["version"] == "tidmad-coding-agent-input-v6"
        assert provenance["task_visibility"] == "agent-public-view-v2"
        assert len(provenance["public_task_view_sha256"]) == 64
        assert len(provenance["information_treatment_sha256"]) == 64
        assert len(provenance["task_md_sha256"]) == 64

        treatment_member = archive.getmember("tidmad-coding-agent-baseline/input/treatment.json")
        treatment_file = archive.extractfile(treatment_member)
        assert treatment_file is not None
        receipt = json.load(treatment_file)
        assert receipt["advice"] == {
            "artifact": None,
            "content_type": None,
            "mode": "disabled",
            "sha256": None,
        }
        assert receipt["modules"] == {"literature_review": "not_applicable"}
        kickoff = archive.extractfile(
            archive.getmember("tidmad-coding-agent-baseline/input/task.md")
        )
        assert kickoff is not None
        kickoff_text = kickoff.read().decode()
        assert "tidmad-prerelease-advice-off-v1" in kickoff_text
        assert "Human advice is disabled" in kickoff_text
        assert provenance["task_md_sha256"] == hashlib.sha256(kickoff_text.encode()).hexdigest()


def test_advice_enabled_bundle_contains_one_certified_canonical_artifact(tmp_path, monkeypatch):
    siderius_checkout = tmp_path / "siderius"
    siderius_checkout.mkdir()

    def fake_build(_repo, _checkout, output):
        wheel = "siderius-test.whl"
        (output / wheel).write_bytes(b"test wheel")
        (output / "siderius-wheel-name.txt").write_text(f"{wheel}\n")
        (output / "requirements.txt").write_text("numpy==2.5.2\n")
        return "1" * 40, "f" * 64

    monkeypatch.setattr(bundle_module, "_build_evaluator", fake_build)
    task = tmp_path / "task.md"
    task.write_text("operator-approved kickoff\n")
    output = build_bundle(
        task,
        TREATMENTS / "prerelease-with-advice.yaml",
        siderius_checkout,
        tmp_path / "bundle.tar.gz",
    )
    off_output = build_bundle(
        task,
        TREATMENTS / "prerelease-without-advice.yaml",
        siderius_checkout,
        tmp_path / "bundle-off.tar.gz",
    )

    with (
        tarfile.open(output, "r:gz") as archive,
        tarfile.open(off_output, "r:gz") as off_archive,
    ):
        advice_name = "tidmad-coding-agent-baseline/input/advice.json"
        advice_file = archive.extractfile(archive.getmember(advice_name))
        assert advice_file is not None
        assert (
            advice_file.read()
            == (
                REPOSITORY_ROOT
                / "experiments/tidmad/prerelease-tidmad-proof-of-function/advice.json"
            ).read_bytes()
        )
        receipt = _archive_json(archive, "tidmad-coding-agent-baseline/input/treatment.json")
        assert receipt["advice"]["mode"] == "enabled"
        assert receipt["advice"]["artifact"] == "advice.json"
        kickoff = archive.extractfile(
            archive.getmember("tidmad-coding-agent-baseline/input/task.md")
        )
        assert kickoff is not None
        kickoff_text = kickoff.read().decode()
        assert "tidmad-prerelease-advice-on-v1" in kickoff_text
        assert "Human advice is enabled" in kickoff_text
        assert "/work/input/advice.json" in kickoff_text
        on_provenance = _archive_json(archive, "tidmad-coding-agent-baseline/input/provenance.json")
        off_provenance = _archive_json(
            off_archive, "tidmad-coding-agent-baseline/input/provenance.json"
        )
        assert on_provenance["public_task_view_sha256"] == off_provenance["public_task_view_sha256"]

        advice_sentinel = b"10M-500M trainable-parameter range"
        for member in off_archive.getmembers():
            if not member.isfile() or "/input/" not in member.name:
                continue
            stream = off_archive.extractfile(member)
            assert stream is not None
            assert advice_sentinel not in stream.read(), member.name


def test_advice_prose_is_not_duplicated_into_kickoff_or_adapter_source():
    sentinel = "10M-500M trainable-parameter range"
    task_md = (REPOSITORY_ROOT / "deployments/tidmad_coding_agent_baseline/task.md").read_text()
    adapter = (
        REPOSITORY_ROOT / "deployments/tidmad_coding_agent_baseline/tools/build_bundle.py"
    ).read_text()

    assert sentinel not in task_md
    assert sentinel not in adapter


def test_canonical_task_md_separates_score_health_and_segment_model_contract():
    repo = Path(__file__).resolve().parents[3]
    text = (repo / "deployments/tidmad_coding_agent_baseline/task.md").read_text()
    assert "finite raw score alone is **not** a valid result" in text
    assert "health_regression.yaml" in text
    assert "Health error, missing Health evidence" in text
    assert "must be a trained ML denoising model" in text
    assert "trained ML model fitted from the provided" in text
    assert "Model architecture, fitting method and research process" in text
    assert "raw, non-overlapping 40,000-sample" in text
    assert "candidate-specific\nfree-form preprocessing or postprocessing" in text
    assert "You may inspect clean training targets" in text
    assert "per-file or absolute-time signal schedule" in text
    assert "call order, persistent counters or other state" in text
    assert "`eligible_for_selection=true` receipt does not certify" in text
    assert "TorchScript `model.pt`" in text
    assert "`[B, 40000]`" in text
    assert "`[B, 256, 40000]`" in text
    assert "frequency comb" not in text
    assert "matched filter" not in text
    assert "There is no agent-callable final-scoring command" in text
    assert "raw_and_ground_score.md" in text


def test_candidate_scopes_cover_every_file_in_each_band(tmp_path):
    task_root = tmp_path / "task"
    resolved = task_root / "tasks/tidmad/resolved"
    resolved.mkdir(parents=True)
    (resolved / "dataset_profile.json").write_text(
        json.dumps({"dataset": {"segments_per_file": 2}})
    )
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()

    bundle_module._write_evaluation_scopes(task_root, evaluator)

    expected = {
        "0-3": {"0", "1", "2", "3"},
        "4-9": {"4", "5", "6", "7", "8", "9"},
        "10-14": {"10", "11", "12", "13", "14"},
        "15-19": {"15", "16", "17", "18", "19"},
    }
    for band, files in expected.items():
        scope = json.loads(
            (evaluator / "evaluation_scopes" / f"band-{band}-candidate.json").read_text()
        )
        assert set(scope) == files
        assert all(segments == [0, 1] for segments in scope.values())


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


def test_vm_install_makes_inference_session_reachable_without_results_membership():
    """Catch a correct child directory made unreachable by its parent mode."""

    repo = Path(__file__).resolve().parents[3]
    install = (
        repo / "deployments" / "tidmad_coding_agent_baseline" / "machine" / "install_vm.sh"
    ).read_text()

    assert "baseline-evaluator -g baseline-results -m 2751" in install
    assert "usermod -a -G baseline-results baseline-inference" not in install
