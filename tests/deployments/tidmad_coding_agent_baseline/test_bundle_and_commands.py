from __future__ import annotations

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
    assert "--dangerously-skip-permissions" in claude
    assert claude[claude.index("--effort") + 1] == "medium"
    assert claude[claude.index("--permission-prompts") + 1] == "none"


def test_bundle_requires_task_md_and_snapshots_existing_task_unchanged(
    tmp_path, monkeypatch
):
    missing = tmp_path / "missing.md"
    siderius_checkout = tmp_path / "siderius"
    siderius_checkout.mkdir()
    with pytest.raises(ValueError, match="operator-approved"):
        build_bundle(missing, siderius_checkout, tmp_path / "missing.tar.gz")

    def fake_build(_repo, _checkout, output):
        (output / "siderius.whl").write_bytes(b"test wheel")
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
        assert any(
            name.endswith("/input/tasks/tidmad/resolved/metric_spec.json")
            for name in names
        )
        assert "tidmad-coding-agent-baseline/input/bundle.sha256" in names
        assert "tidmad-coding-agent-baseline/evaluator/siderius.whl" in names
        assert "tidmad-coding-agent-baseline/evaluator/requirements.txt" in names

        repo = Path(__file__).resolve().parents[3]
        task_members = [
            member
            for member in archive.getmembers()
            if member.isfile() and "/input/tasks/tidmad/" in member.name
        ]
        assert task_members
        bundled_paths = {member.name.split("/input/", 1)[1] for member in task_members}
        tracked_paths = {
            str(path.relative_to(repo))
            for path in bundle_module._tracked_task_files(repo)
        }
        assert bundled_paths == tracked_paths
        for member in task_members:
            relative = member.name.split("/input/", 1)[1]
            extracted = archive.extractfile(member)
            assert extracted is not None
            assert extracted.read() == (repo / relative).read_bytes()
