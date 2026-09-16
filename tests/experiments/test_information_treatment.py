from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
import yaml
from experiments.shared.information_treatment import (
    AdviceMode,
    ModuleState,
    resolve_information_treatment,
)
from pydantic import ValidationError


def _write_treatment(
    root: Path,
    *,
    mode: str,
    artifact: str | None,
    digest: str | None,
    modules: dict[str, dict[str, str]] | None = None,
) -> Path:
    (root / "tasks/demo").mkdir(parents=True)
    manifest = root / "experiments/demo/treatment.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        yaml.safe_dump(
            {
                "version": "siderius-exp-information-treatment-v1",
                "treatment_id": "demo-treatment-v1",
                "task_package": "tasks/demo",
                "advice": {"mode": mode, "artifact": artifact, "sha256": digest},
                "modules": modules
                or {
                    "literature_review": {
                        "siderius": "disabled",
                        "coding_agent": "not_applicable",
                    }
                },
            },
            sort_keys=False,
        )
    )
    return manifest


def test_enabled_treatment_certifies_one_artifact_and_renders_both_adapters(tmp_path):
    advice = tmp_path / "experiments/demo/advice.json"
    advice.parent.mkdir(parents=True)
    advice.write_text('{"propose": "Use the evidence."}\n')
    digest = hashlib.sha256(advice.read_bytes()).hexdigest()
    manifest = _write_treatment(
        tmp_path,
        mode="enabled",
        artifact="experiments/demo/advice.json",
        digest=digest,
    )

    siderius = resolve_information_treatment(
        manifest,
        repository_root=tmp_path,
        adapter="siderius",
        required_modules=("literature_review",),
    )
    coding = resolve_information_treatment(
        manifest,
        repository_root=tmp_path,
        adapter="coding_agent",
        required_modules=("literature_review",),
    )

    assert siderius.declaration.advice.mode is AdviceMode.ENABLED
    assert siderius.siderius_args() == [
        "--experiment_arm",
        "demo-treatment-v1",
        "--no-ml_lit_review_enabled",
        "--advice",
        str(advice),
        "--advice_sha256",
        digest,
    ]
    assert coding.receipt()["advice"] == {
        "mode": "enabled",
        "artifact": "advice.json",
        "sha256": digest,
    }
    assert siderius.manifest_sha256 == coding.manifest_sha256
    assert siderius.task_package_path == coding.task_package_path
    assert coding.module_states == {"literature_review": ModuleState.NOT_APPLICABLE}


def test_disabled_treatment_materializes_absence_without_collapsing_module_state(tmp_path):
    manifest = _write_treatment(tmp_path, mode="disabled", artifact=None, digest=None)
    coding = resolve_information_treatment(
        manifest,
        repository_root=tmp_path,
        adapter="coding_agent",
        required_modules=("literature_review",),
    )

    siderius = resolve_information_treatment(
        manifest,
        repository_root=tmp_path,
        adapter="siderius",
        required_modules=("literature_review",),
    )

    assert siderius.siderius_args() == [
        "--experiment_arm",
        "demo-treatment-v1",
        "--no-ml_lit_review_enabled",
    ]
    assert coding.receipt()["advice"] == {
        "mode": "disabled",
        "artifact": None,
        "sha256": None,
    }
    assert coding.receipt()["modules"] == {"literature_review": "not_applicable"}


def test_siderius_adapter_refuses_unrepresentable_module_state(tmp_path):
    manifest = _write_treatment(
        tmp_path,
        mode="disabled",
        artifact=None,
        digest=None,
        modules={"literature_review": {"siderius": "not_applicable"}},
    )
    resolved = resolve_information_treatment(
        manifest,
        repository_root=tmp_path,
        adapter="siderius",
        required_modules=("literature_review",),
    )

    with pytest.raises(ValueError, match="cannot be represented"):
        resolved.siderius_args()


@pytest.mark.parametrize(
    ("mode", "artifact", "digest", "message"),
    [
        ("enabled", None, None, "enabled advice requires"),
        ("disabled", "experiments/demo/advice.json", "a" * 64, "disabled advice requires"),
    ],
)
def test_incoherent_advice_declarations_fail_closed(tmp_path, mode, artifact, digest, message):
    manifest = _write_treatment(
        tmp_path,
        mode=mode,
        artifact=artifact,
        digest=digest,
    )
    with pytest.raises(ValidationError, match=message):
        resolve_information_treatment(
            manifest,
            repository_root=tmp_path,
            adapter="siderius",
        )


def test_changed_advice_bytes_refuse_before_adapter_use(tmp_path):
    advice = tmp_path / "advice.json"
    advice.write_text("original")
    digest = hashlib.sha256(advice.read_bytes()).hexdigest()
    manifest = _write_treatment(
        tmp_path,
        mode="enabled",
        artifact="advice.json",
        digest=digest,
    )
    advice.write_text("changed")

    with pytest.raises(ValueError, match="identity mismatch"):
        resolve_information_treatment(
            manifest,
            repository_root=tmp_path,
            adapter="siderius",
        )


@pytest.mark.parametrize("path", ["/absolute/task", "../outside", "tasks/../outside"])
def test_repository_paths_cannot_escape(tmp_path, path):
    manifest = _write_treatment(tmp_path, mode="disabled", artifact=None, digest=None)
    payload = yaml.safe_load(manifest.read_text())
    payload["task_package"] = path
    manifest.write_text(yaml.safe_dump(payload))

    with pytest.raises(ValueError, match="repository-relative"):
        resolve_information_treatment(
            manifest,
            repository_root=tmp_path,
            adapter="siderius",
        )


def test_required_adapter_module_state_cannot_be_silently_defaulted(tmp_path):
    manifest = _write_treatment(
        tmp_path,
        mode="disabled",
        artifact=None,
        digest=None,
        modules={"literature_review": {"siderius": "disabled"}},
    )

    with pytest.raises(ValueError, match=r"literature_review.*coding_agent"):
        resolve_information_treatment(
            manifest,
            repository_root=tmp_path,
            adapter="coding_agent",
            required_modules=("literature_review",),
        )


def test_receipt_includes_every_module_declared_for_the_adapter(tmp_path):
    manifest = _write_treatment(
        tmp_path,
        mode="disabled",
        artifact=None,
        digest=None,
        modules={
            "literature_review": {"coding_agent": "not_applicable"},
            "future_module": {
                "coding_agent": "enabled",
                "siderius": "disabled",
            },
        },
    )
    resolved = resolve_information_treatment(
        manifest,
        repository_root=tmp_path,
        adapter="coding_agent",
        required_modules=("literature_review",),
    )

    assert resolved.receipt()["modules"] == {
        "future_module": "enabled",
        "literature_review": "not_applicable",
    }


def test_cli_receipt_is_stable_json(tmp_path):
    manifest = _write_treatment(tmp_path, mode="disabled", artifact=None, digest=None)
    completed = subprocess.run(
        [
            str(Path(__file__).resolve().parents[2] / ".venv/bin/python"),
            "-m",
            "experiments.shared.information_treatment",
            "receipt",
            "--manifest",
            str(manifest),
            "--repository-root",
            str(tmp_path),
            "--adapter",
            "coding_agent",
            "--require-module",
            "literature_review",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    receipt = json.loads(completed.stdout)
    assert receipt["advice"]["mode"] == "disabled"
    assert receipt["treatment_id"] == "demo-treatment-v1"
    assert receipt["modules"]["literature_review"] == "not_applicable"
