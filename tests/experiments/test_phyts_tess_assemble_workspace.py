"""The caller's workspace is assembled byte for byte, never merged.

* ``test_assembly_preserves_every_byte_and_records_it_outside`` — each
  file in the workspace equals its source and appears in a receipt that is
  not inside the workspace; the receipt is the operator's, not the agent's.
* ``test_an_existing_workspace_is_refused`` — merging into a directory
  with prior state is how a stale instruction file survives.
* ``test_a_symlinked_payload_member_is_refused`` — following one could
  copy private material into the agent's view.
* ``test_a_payload_that_already_carries_a_document_is_refused`` — the
  operator's documents must never overwrite toolkit files, or vice versa.
* ``test_a_run_id_instantiates_the_declaration_and_its_settings_only`` —
  the smoke unit runs under its own id; every occurrence in the
  declaration and the run settings moves with it, the task brief does
  not, and the receipt records both ids and the source digests.
* ``test_a_declaration_without_a_run_id_header_is_refused`` — an id that
  cannot be read from the first line cannot be instantiated safely.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from experiments.phyts_tess.main_orchestrator.assemble_workspace import (
    PAYLOAD_RELATIVE,
    assemble_workspace,
)


def _framework(tmp_path: Path) -> Path:
    framework = tmp_path / "framework"
    payload = framework / PAYLOAD_RELATIVE
    skill = payload / ".agents" / "skills" / "siderius-toolkit"
    (skill / "references").mkdir(parents=True)
    (payload / "AGENTS.md").write_text("# toolkit\n", encoding="utf-8")
    (skill / "SKILL.md").write_text(
        "---\nname: siderius-toolkit\n---\n", encoding="utf-8"
    )
    (skill / "references" / "invocation.md").write_text("# invoke\n", encoding="utf-8")
    return framework


def _documents(tmp_path: Path) -> dict[str, Path]:
    docs = tmp_path / "docs"
    docs.mkdir()
    paths = {
        "run_declaration": docs / "SIDERIUS-RUN.md",
        "task_brief": docs / "task.md",
        "treatment_scope": docs / "TREATMENT_SCOPE.md",
    }
    for label, path in paths.items():
        path.write_text(f"# {label}\n", encoding="utf-8")
    paths["run_declaration"].write_text(
        "# run\n\nRun id **`onp_001`**. Candidates at /var/lib/tess-candidates/onp_001.\n",
        encoding="utf-8",
    )
    return paths


def _run_settings(tmp_path: Path) -> Path:
    settings = tmp_path / "run-settings"
    settings.mkdir()
    (settings / "evaluation-settings.json").write_text(
        '{"run_id": "onp_001", "candidate_root": "/var/lib/tess-candidates/onp_001"}\n',
        encoding="utf-8",
    )
    return settings


def _assemble(tmp_path: Path, **overrides):
    docs = _documents(tmp_path)
    arguments = {
        "destination": tmp_path / "workspace",
        "receipt": tmp_path / "records" / "assembly.json",
        **docs,
        **overrides,
    }
    if "framework" not in arguments:
        arguments["framework"] = _framework(tmp_path)
    return assemble_workspace(**arguments)


def test_assembly_preserves_every_byte_and_records_it_outside(tmp_path):
    inventory = _assemble(tmp_path)

    workspace = tmp_path / "workspace"
    expected = {
        "AGENTS.md": "# toolkit\n",
        ".agents/skills/siderius-toolkit/SKILL.md": "---\nname: siderius-toolkit\n---\n",
        ".agents/skills/siderius-toolkit/references/invocation.md": "# invoke\n",
        "SIDERIUS-RUN.md": (
            "# run\n\nRun id **`onp_001`**. Candidates at /var/lib/tess-candidates/onp_001.\n"
        ),
        "task.md": "# task_brief\n",
        "TREATMENT_SCOPE.md": "# treatment_scope\n",
    }
    assert {p for p in inventory["files"]} == set(expected)
    for relative, text in expected.items():
        assert (workspace / relative).read_text(encoding="utf-8") == text
        assert inventory["files"][relative] == hashlib.sha256(text.encode()).hexdigest()
    receipt = json.loads((tmp_path / "records" / "assembly.json").read_text())
    assert receipt["files"] == inventory["files"]
    assert not (workspace / "assembly.json").exists()


def test_an_existing_workspace_is_refused(tmp_path):
    (tmp_path / "workspace").mkdir()
    (tmp_path / "workspace" / "AGENTS.md").write_text("stale\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="refusing to merge"):
        _assemble(tmp_path)
    assert (tmp_path / "workspace" / "AGENTS.md").read_text() == "stale\n"


def test_a_symlinked_payload_member_is_refused(tmp_path):
    framework = _framework(tmp_path)
    private = tmp_path / "private.md"
    private.write_text("truth\n", encoding="utf-8")
    (framework / PAYLOAD_RELATIVE / "LINKED.md").symlink_to(private)

    with pytest.raises(ValueError, match="symlink"):
        _assemble(tmp_path, framework=framework)


def test_a_payload_that_already_carries_a_document_is_refused(tmp_path):
    framework = _framework(tmp_path)
    (framework / PAYLOAD_RELATIVE / "task.md").write_text(
        "payload task\n", encoding="utf-8"
    )

    with pytest.raises(FileExistsError, match="already carries"):
        _assemble(tmp_path, framework=framework)


def test_a_receipt_inside_the_workspace_is_refused(tmp_path):
    with pytest.raises(ValueError, match="outside the workspace"):
        _assemble(tmp_path, receipt=tmp_path / "workspace" / "assembly.json")


def test_a_run_id_instantiates_the_declaration_and_its_settings_only(tmp_path):
    inventory = _assemble(
        tmp_path, run_settings=_run_settings(tmp_path), run_id="onp_smoke_001"
    )

    workspace = tmp_path / "workspace"
    declaration = (workspace / "SIDERIUS-RUN.md").read_text(encoding="utf-8")
    assert "onp_001" not in declaration
    assert "Run id **`onp_smoke_001`**" in declaration
    assert "/var/lib/tess-candidates/onp_smoke_001" in declaration
    settings = json.loads((workspace / "run" / "evaluation-settings.json").read_text())
    assert settings == {
        "run_id": "onp_smoke_001",
        "candidate_root": "/var/lib/tess-candidates/onp_smoke_001",
    }
    assert (workspace / "task.md").read_text(encoding="utf-8") == "# task_brief\n"
    assert (inventory["run_id"], inventory["declared_run_id"]) == (
        "onp_smoke_001",
        "onp_001",
    )
    assert set(inventory["source_sha256"]) == {
        "run_declaration",
        "task_brief",
        "treatment_scope",
        "run/evaluation-settings.json",
    }


def test_a_declaration_without_a_run_id_header_is_refused(tmp_path):
    headless = tmp_path / "headless.md"
    headless.write_text("# run\n\nno id here\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Run id"):
        _assemble(tmp_path, run_declaration=headless)
