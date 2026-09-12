"""Deterministic contracts for final consumer-pair wrapper boundaries."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SIDERIUS_REVISION = "894a1dd4ca0132d2e12b0629170527349b1a732a"
CASES = {
    "tidmad": (
        ("abra_training_0004.h5", "abra_validation_0004.h5"),
        {
            "--trial_portion": ".01",
            "--train_portion": "1",
            "--eval_portion": ".01",
            "--formal_portion": ".01",
            "--formal_train_portion": "1",
            "--formal_eval_portion": ".01",
            "--max_steps_per_attempt": "1024",
            "--trial_time_budget_minutes": "3",
            "--formal_time_budget_minutes": "5",
            "--trial_vram_budget_gb": "8",
            "--formal_vram_budget_gb": "12",
            "--vram_probe_step_timeout_seconds": "60",
            "--vram_preflight_total_timeout_seconds": "240",
        },
    ),
    "oxford_iiit_pet": (
        ("sample.jpg",),
        {
            "--trial_portion": "1",
            "--train_portion": "1",
            "--eval_portion": "1",
            "--formal_portion": "1",
            "--formal_train_portion": "1",
            "--formal_eval_portion": "1",
            "--max_steps_per_attempt": "370",
            "--trial_time_budget_minutes": "2",
            "--formal_time_budget_minutes": "3",
            "--trial_vram_budget_gb": "8",
            "--formal_vram_budget_gb": "12",
            "--vram_probe_step_timeout_seconds": "60",
            "--vram_preflight_total_timeout_seconds": "180",
            "--vram_preflight_host_memory_limit_gb": "24",
        },
    ),
    "davis_future_prediction": (
        ("DAVIS/JPEGImages/480p/sample.jpg",),
        {
            "--trial_portion": ".05",
            "--train_portion": "1",
            "--eval_portion": ".20",
            "--formal_portion": ".05",
            "--formal_train_portion": "1",
            "--formal_eval_portion": ".20",
            "--max_steps_per_attempt": "3",
            "--trial_time_budget_minutes": "2",
            "--formal_time_budget_minutes": "3",
            "--trial_vram_budget_gb": "10",
            "--formal_vram_budget_gb": "16",
            "--vram_probe_step_timeout_seconds": "60",
            "--vram_preflight_total_timeout_seconds": "240",
            "--vram_preflight_host_memory_limit_gb": "32",
        },
    ),
    "cancer_gene_identification": (
        ("mtg/data.h5",),
        {
            "--trial_portion": "1",
            "--train_portion": "1",
            "--eval_portion": "1",
            "--formal_portion": "1",
            "--formal_train_portion": "1",
            "--formal_eval_portion": "1",
            "--max_steps_per_attempt": "1",
            "--trial_time_budget_minutes": "5",
            "--formal_time_budget_minutes": "8",
            "--trial_vram_budget_gb": "10",
            "--formal_vram_budget_gb": "16",
            "--vram_probe_step_timeout_seconds": "180",
            "--vram_preflight_total_timeout_seconds": "600",
            "--vram_preflight_host_memory_limit_gb": "32",
        },
    ),
}


@pytest.fixture
def fake_checkout(tmp_path: Path) -> tuple[Path, Path]:
    checkout = tmp_path / "siderius"
    (checkout / "scripts/launch").mkdir(parents=True)
    (checkout / "configs/llm").mkdir(parents=True)
    (checkout / "configs/llm/openai_tiered_pro.json").write_text("{}\n")
    (checkout / "scripts/launch/run_chain.sh").write_text(
        "#!/usr/bin/env bash\nset -eu\n"
        '{ for arg in "$@"; do printf "ARG\\t%s\\n" "$arg"; done; '
        'printf "ENV\\tSIDERIUS_GENERATED_LIBRARY_DIR=%s\\n" "${SIDERIUS_GENERATED_LIBRARY_DIR-}"; '
        'printf "ENV\\tSIDERIUS_PLUGIN_DIRS=%s\\n" "${SIDERIUS_PLUGIN_DIRS-}"; '
        'printf "ENV\\tSIDERIUS_LOSS_DIRS=%s\\n" "${SIDERIUS_LOSS_DIRS-}"; '
        'printf "ENV\\tSIDERIUS_PREFLIGHT_WORKER_MEM_GIB=%s\\n" "${SIDERIUS_PREFLIGHT_WORKER_MEM_GIB-}"; '
        'printf "ENV\\tSIDERIUS_SUBPROCESS_RSS_GB=%s\\n" "${SIDERIUS_SUBPROCESS_RSS_GB-}"; } > "$P0_CAPTURE"\n'
    )
    (checkout / "scripts/launch/run_chain.sh").chmod(0o755)
    capture = tmp_path / "capture.tsv"
    return checkout, capture


def _data(root: Path, paths: tuple[str, ...]) -> Path:
    data = root / "data"
    for relative in paths:
        path = data / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
    return data


def _run(
    task: str, checkout: Path, capture: Path, workspace: Path, data: Path, *extra: str
):
    bindir = checkout / "bin"
    bindir.mkdir(exist_ok=True)
    (bindir / "git").write_text(
        '#!/usr/bin/env bash\nif [[ "$1" == "-C" ]]; then shift 2; fi\n'
        'if [[ "$1" == "rev-parse" && "$2" == "HEAD" ]]; then printf "'
        f'{SIDERIUS_REVISION}\\n"; exit 0; fi\nexit 1\n'
    )
    (bindir / "git").chmod(0o755)
    env = os.environ.copy()
    env["P0_CAPTURE"] = str(capture)
    env["PATH"] = f"{bindir}:{env['PATH']}"
    env["SIDERIUS_PLUGIN_DIRS"] = "/ambient/models"
    env["SIDERIUS_LOSS_DIRS"] = "/ambient/losses"
    wrapper = ROOT / "experiments" / task / "p0_final_pair_qualification" / "launch.sh"
    return subprocess.run(
        [
            "bash",
            str(wrapper),
            "--siderius-checkout",
            str(checkout),
            "--workspace",
            str(workspace),
            "--data_dir",
            str(data),
            *extra,
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("task", CASES)
def test_delegated_argv_has_frozen_controls(
    task: str, fake_checkout, tmp_path: Path
) -> None:
    checkout, capture = fake_checkout
    data = _data(tmp_path, CASES[task][0])
    result = _run(task, checkout, capture, tmp_path / "workspace", data)
    assert result.returncode == 0, result.stderr
    rows = capture.read_text().splitlines()
    argv = [r.split("\t", 1)[1] for r in rows if r.startswith("ARG\t")]
    values = {
        argv[i]: argv[i + 1] for i in range(len(argv) - 1) if argv[i].startswith("--")
    }
    for flag, expected in CASES[task][1].items():
        assert values.get(flag) == expected, (task, flag, argv)
    for flag, expected in {
        "--num_iterations": "2",
        "--max_rounds": "2",
        "--max_epochs": "1",
        "--trial_max_epochs": "1",
        "--formal_max_epochs": "1",
        "--attempts_per_round": "2",
        "--attempts_per_formal_round": "2",
        "--max_fail_rounds": "1",
        "--max_failed_iterations": "2",
        "--max_proposal_attempts": "2",
        "--max_impl_attempts": "2",
        "--sampling_seed": "20260912",
    }.items():
        assert values.get(flag) == expected, (task, flag, argv)
    for flag in (
        "--no_auto_resume",
        "--force_formal_round",
        "--no-runtime_watchdog",
        "--no-ml_lit_review_enabled",
        "--no-cleanup_denoised",
    ):
        assert flag in argv, (task, flag, argv)
    assert "--enable_chain_incumbent_formal_gates" not in argv
    assert "--bypass_formal_time_budget_minutes" not in argv
    assert values.get("--formal_strategy") == "snapshot"
    assert values.get("--formal_round_strategy") == "full_clone"
    assert values.get("--min_formal_batch_size") == "1"
    assert values.get("--trial_time_admission_source") == "measured"
    assert values.get("--formal_time_admission_source") == "measured"
    assert (
        values.get("--runtime_verification_max_wall_seconds")
        == {
            "tidmad": "120",
            "oxford_iiit_pet": "120",
            "davis_future_prediction": "120",
            "cancer_gene_identification": "300",
        }[task]
    )
    expected_composition = (
        "tasks/cancer_gene_identification/compositions/mtg_size.yaml"
        if task == "cancer_gene_identification"
        else f"tasks/{task}/compositions/bounded_qualification.yaml"
    )
    assert values.get("--task_composition", "").endswith(expected_composition)
    if task == "tidmad":
        assert values.get("--data_scope") == "4"
        assert values.get("--health_gate_files") == "4"
    if task == "tidmad":
        assert values.get("--validation_max_train_samples") == "1024"
        assert "--validation_max_samples" not in argv
    elif task == "oxford_iiit_pet":
        assert values.get("--validation_max_train_samples") == "370"
        assert values.get("--validation_max_samples") == "74"
    elif task == "davis_future_prediction":
        assert values.get("--validation_max_train_samples") == "3"
        assert values.get("--validation_max_samples") == "3"
    else:
        assert "--validation_max_samples" not in argv
        assert "--validation_max_train_samples" not in argv
    rules = json.loads(values["--workflow_parameter_rules"])
    expected_batch = 16 if task in {"tidmad", "oxford_iiit_pet"} else 1
    assert rules == {
        "train_config.epochs": {"exact": 1},
        "train_config.batch_size": {"exact": expected_batch},
    }
    assert json.loads(values["--plan_overrides"]) == {
        "is_trial": True,
        "trial_strategy": "snapshot",
        "eval_strategy": "snapshot",
        "train_validation_align": True,
    }
    env_rows = {r.split("\t", 1)[1] for r in rows if r.startswith("ENV\t")}
    assert (
        f"SIDERIUS_GENERATED_LIBRARY_DIR={tmp_path / 'workspace' / 'generated_library'}"
        in env_rows
    )
    assert "SIDERIUS_PLUGIN_DIRS=" in env_rows and "SIDERIUS_LOSS_DIRS=" in env_rows
    assert "SIDERIUS_PLUGIN_DIRS=/ambient/models" not in env_rows
    assert "SIDERIUS_LOSS_DIRS=/ambient/losses" not in env_rows
    expected_probe = (
        "32"
        if task in {"davis_future_prediction", "cancer_gene_identification"}
        else "24"
    )
    assert f"SIDERIUS_PREFLIGHT_WORKER_MEM_GIB={expected_probe}" in env_rows
    assert "SIDERIUS_SUBPROCESS_RSS_GB=training=40,inference=60,scoring=24" in env_rows


def test_wrapper_rejects_double_dash_argument_injection(
    fake_checkout, tmp_path: Path
) -> None:
    checkout, capture = fake_checkout
    data = _data(tmp_path, CASES["tidmad"][0])
    result = _run(
        "tidmad",
        checkout,
        capture,
        tmp_path / "workspace",
        data,
        "--",
        "--max_rounds",
        "99",
    )
    assert result.returncode == 2 and "unknown argument" in result.stderr
    assert not capture.exists()


@pytest.mark.parametrize("task", CASES)
def test_wrapper_rejects_user_numeric_override(
    task: str, fake_checkout, tmp_path: Path
) -> None:
    checkout, capture = fake_checkout
    data = _data(tmp_path, CASES[task][0])
    result = _run(
        task, checkout, capture, tmp_path / "workspace", data, "--max_rounds", "99"
    )
    assert result.returncode == 2 and "unknown argument" in result.stderr
    assert not capture.exists()


@pytest.mark.parametrize("task", CASES)
def test_wrapper_rejects_missing_selected_data(
    task: str, fake_checkout, tmp_path: Path
) -> None:
    checkout, capture = fake_checkout
    missing = tmp_path / "missing"
    missing.mkdir()
    if task == "tidmad":
        (missing / "abra_training_0003.h5").write_bytes(b"wrong file")
        (missing / "abra_validation_0003.h5").write_bytes(b"wrong file")
    result = _run(task, checkout, capture, tmp_path / "workspace", missing)
    assert result.returncode == 2 and "required task data is missing" in result.stderr
    assert not capture.exists()


@pytest.mark.parametrize("task", CASES)
def test_wrapper_rejects_nonempty_workspace(
    task: str, fake_checkout, tmp_path: Path
) -> None:
    checkout, capture = fake_checkout
    data = _data(tmp_path, CASES[task][0])
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "old.json").write_text("old")
    result = _run(task, checkout, capture, workspace, data)
    assert result.returncode == 2 and "workspace must be empty" in result.stderr
    assert not capture.exists()


def test_wrapper_rejects_wrong_framework_pin(fake_checkout, tmp_path: Path) -> None:
    checkout, capture = fake_checkout
    bindir = checkout / "bin"
    bindir.mkdir(exist_ok=True)
    (bindir / "git").write_text("#!/usr/bin/env bash\nprintf 'wrong\\n'\n")
    (bindir / "git").chmod(0o755)
    data = _data(tmp_path, CASES["tidmad"][0])
    env = os.environ.copy()
    env["P0_CAPTURE"] = str(capture)
    env["PATH"] = f"{bindir}:{env['PATH']}"
    wrapper = ROOT / "experiments/tidmad/p0_final_pair_qualification/launch.sh"
    result = subprocess.run(
        [
            "bash",
            str(wrapper),
            "--siderius-checkout",
            str(checkout),
            "--workspace",
            str(tmp_path / "workspace"),
            "--data_dir",
            str(data),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2 and "revision mismatch" in result.stderr
    assert not capture.exists()
