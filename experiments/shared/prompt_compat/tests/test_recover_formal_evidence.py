"""Recovery must prove source identity rather than invent a passing verdict.

Set SIDERIUS_CHECKOUT to the clean candidate checkout under qualification. Each
CLI subprocess uses that checkout's own interpreter, never this test's imports.
"""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from core.scientific_authority import ScientificAuthority
from execute_tools.health_checks._composition import HealthBindingState
from execute_tools.health_checks.config import materialize_effective_config


@pytest.fixture
def recovery_case(tmp_path):
    configured = os.environ.get("SIDERIUS_CHECKOUT")
    if not configured:
        pytest.skip(
            "Set SIDERIUS_CHECKOUT to the candidate infra for recovery qualification"
        )
    infra = Path(configured).resolve()
    revision = subprocess.check_output(
        ["git", "-C", str(infra), "rev-parse", "HEAD"], text=True
    ).strip()
    policy, policy_hash = materialize_effective_config(
        None,
        None,
        str(tmp_path / "original"),
        task_health_binding=HealthBindingState.EXPLICIT_NONE,
    )
    authority = ScientificAuthority.from_context(
        healthgate_mode="blocking",
        declared_result_authority="scientific",
        formal_validity="valid",
    ).model_dump()
    source = {
        "run_name": "original_run",
        "model_type": "synthetic_model",
        "file_index": 0,
        "status": "completed",
        "completed_rounds": 1,
        "total_attempts": 1,
        "started_at": "2026-01-01T00:00:00Z",
        "finished_at": "2026-01-01T00:00:01Z",
        "health_config_sha256": policy_hash,
        "healthgate_mode": "blocking",
        "result_authority": "scientific",
        "metric_spec": {
            "id": "example",
            "direction": "higher",
            "aggregation": "mean",
            "references": [],
            "scoreability": {"contract_id": "example"},
        },
        "all_records": [
            {
                "exp_id": "formal_1",
                "model_type": "synthetic_model",
                "status": "success",
                "timestamp": "2026-01-01T00:00:01Z",
                "params": {},
                "is_trial": False,
                "denoising_score": 3.0,
                "health_gate_enabled": True,
                "health_gate_results": [],
                "scientific_authority": authority,
            }
        ],
    }
    artifact = {
        "model_types": ["synthetic_model"],
        "model_descriptions": {},
        "total_experiments": 1,
        "key_findings": [],
        "bottlenecks": [],
        "take_home_message": "Preserved archived text",
        "model_knowledge_cache": {
            "synthetic_model": {
                "key_findings": ["Original finding"],
                "_stats": {
                    "formal_score": 3.0,
                    "scientific_authority": authority,
                },
            }
        },
    }
    source_path = tmp_path / "run_output.json"
    source_path.write_text(json.dumps(source))
    input_path = tmp_path / "interpretation.json"
    input_path.write_text(json.dumps(artifact))

    def reference(path):
        return {
            "path": str(path),
            "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        }

    request = {
        "interpretation": reference(input_path),
        "health_policy": reference(policy),
        "run_outputs": [reference(source_path)],
    }

    def invoke():
        request_path = tmp_path / "request.json"
        request_path.write_text(json.dumps(request))
        environment = {
            k: v
            for k, v in os.environ.items()
            if k
            not in {
                "PYTHONPATH",
                "OPENAI_API_KEY",
                "GEMINI_API_KEY",
                "DEEPSEEK_API_KEY",
            }
        }
        return subprocess.run(
            [
                str(infra / ".venv/bin/python"),
                str(Path(__file__).resolve().parents[1] / "recover_formal_evidence.py"),
                "--expected-revision",
                revision,
                "--request",
                str(request_path),
                "--output",
                str(tmp_path / "recovered"),
            ],
            check=False,
            cwd=infra,
            env=environment,
            capture_output=True,
            text=True,
        )

    return request, artifact, source, source_path, input_path, invoke, reference


def test_recovery_adds_only_independent_evidence_and_preserves_archive(
    tmp_path, recovery_case
):
    request, original, _, _, path, invoke, _ = recovery_case
    before = path.read_bytes()
    result = invoke()
    assert result.returncode == 0, result.stderr
    restored = json.loads((tmp_path / "recovered/interpretation.json").read_text())
    stats = restored["model_knowledge_cache"]["synthetic_model"]["_stats"]
    assert stats.pop("run_name") == "original_run"
    evidence = stats.pop("formal_evidence")
    assert evidence["exp_id"] == "formal_1"
    assert evidence["required_gate_ids"] == []
    assert restored == original
    assert path.read_bytes() == before
    receipt = json.loads((tmp_path / "recovered/receipt.json").read_text())
    assert receipt["recovered"][0]["source"] == request["run_outputs"][0]
    assert invoke().returncode != 0  # Existing recovery output is never overwritten.


@pytest.mark.parametrize(
    "defect", ["modified_source", "ambiguous", "score", "policy", "verdict"]
)
def test_recovery_refuses_unproven_or_contradictory_sources(
    tmp_path, recovery_case, defect
):
    request, _, source, path, _, invoke, reference = recovery_case
    if defect == "modified_source":
        path.write_text(path.read_text() + " ")  # Do not update its pinned digest.
    elif defect == "ambiguous":
        request["run_outputs"] *= 2
    else:
        if defect == "score":
            source["all_records"][0]["denoising_score"] = 9.0
        elif defect == "policy":
            source["health_config_sha256"] = "f" * 64
        else:
            source["all_records"][0]["scientific_authority"] = None
        path.write_text(json.dumps(source))
        request["run_outputs"][0] = reference(path)
    result = invoke()
    assert result.returncode != 0
    assert not (tmp_path / "recovered").exists()


@pytest.mark.parametrize("mismatch", ["id", "direction", "aggregation"])
def test_recovery_refuses_mixed_metric_sources(tmp_path, recovery_case, mismatch):
    import copy

    request, artifact, source, _, input_path, invoke, reference = recovery_case
    second = copy.deepcopy(source)
    second["model_type"] = "second_model"
    second["all_records"][0]["model_type"] = "second_model"
    second["metric_spec"][mismatch] = {
        "id": "other_metric",
        "direction": "lower",
        "aggregation": "other_aggregation",
    }[mismatch]
    second_path = tmp_path / "second.json"
    second_path.write_text(json.dumps(second))
    request["run_outputs"].append(reference(second_path))
    artifact["model_knowledge_cache"]["second_model"] = copy.deepcopy(
        artifact["model_knowledge_cache"]["synthetic_model"]
    )
    artifact["model_types"].append("second_model")
    input_path.write_text(json.dumps(artifact))
    request["interpretation"] = reference(input_path)
    result = invoke()
    assert result.returncode != 0
    assert "metric" in result.stderr.lower()
    assert not (tmp_path / "recovered").exists()
