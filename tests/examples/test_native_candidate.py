"""Exported task assets use explicit current infra, never exp's historical install."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = {
    "tess": "tasks/phyts_tess",
    "pet": "tasks/oxford_iiit_pet",
    "davis": "tasks/davis_future_prediction",
}


@pytest.fixture(params=EXAMPLES)
def project(tmp_path, request):
    example = request.param
    selected = os.environ.get("SIDERIUS_CHECKOUT")
    if not selected:
        pytest.skip(
            "set SIDERIUS_CHECKOUT to the exact framework in the example profile"
        )
    framework = Path(selected).resolve()
    profile = json.loads(
        (ROOT / f"examples/native_candidate/{example}/profile.json").read_text()
    )
    revision = subprocess.check_output(
        ["git", "-C", str(framework), "rev-parse", "HEAD"], text=True
    ).strip()
    assert revision == profile["framework_revision"], (
        "select the example's declared framework, not another local checkout"
    )
    python = framework / ".venv/bin/python"
    assert python.is_file(), "run this framework checkout's own frozen sync first"
    home = tmp_path / f"external {example} project"
    shutil.copytree(
        ROOT / EXAMPLES[example],
        home / EXAMPLES[example],
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copytree(
        ROOT / "examples/native_candidate", home / "examples/native_candidate"
    )
    data = tmp_path / "data path fixture"
    data.mkdir()  # No data validity or real execution is claimed by composition/preparation.
    credentials = tmp_path / "provider.json"
    credentials.write_text("{}\n")
    credentials.chmod(0o600)
    return home, data, framework, python, credentials, example


def recipe(project, *args):
    home, _, _, python, _, _ = project
    return subprocess.run(
        [
            str(python),
            str(home / "examples/native_candidate/materialize.py"),
            *map(str, args),
        ],
        cwd=home.parent,
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )


def inspect(project, profile_path=None):
    home, data, framework, _, _, example = project
    result = recipe(
        project,
        "inspect",
        "--project",
        home,
        "--data",
        data,
        "--framework",
        framework,
        "--profile",
        home / (profile_path or f"examples/native_candidate/{example}/profile.json"),
        "--output",
        home / "inspections/task.json",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return home / "inspections/task.json"


def accept(project, inspection, *args):
    return recipe(
        project,
        "accept",
        "--inspection",
        inspection,
        "--credential-file",
        project[4],
        *args,
    )


def test_inspection_is_not_acceptance_and_missing_flag_cannot_publish(project):
    """Composition success must never silently accept a task or produce runnable source."""
    report = inspect(project)
    home = project[0]
    assert (home / "llm/agents.json").is_file()
    assert not (home / "workflow.py").exists()
    result = accept(project, report)
    assert result.returncode == 2 and "--accept-task" in result.stderr
    assert not (home / "workflow.py").exists()
    assert not (home / "console-token").exists()


def test_bad_port_and_private_file_refuse_before_publication_then_retry(project):
    """Bad configuration must leave a retryable inspection, and secret diagnostics stay private."""
    report = inspect(project)
    home, _, _, _, credentials, _ = project
    result = accept(project, report, "--accept-task", "--port", "1")
    assert result.returncode == 2
    assert not report.with_suffix(".accept-scratch").exists()
    assert not (home / "workflow.py").exists()
    credentials.write_text('{"OPENAI_API_KEY": ["private-marker"]}')
    result = accept(project, report, "--accept-task")
    assert (
        result.returncode == 2 and "private-marker" not in result.stdout + result.stderr
    )
    assert not report.with_suffix(".accept-scratch").exists()
    credentials.write_text("{}")
    result = accept(project, report, "--accept-task")
    assert result.returncode == 0, result.stdout + result.stderr
    before = (home / "workflow.py").read_bytes()
    assert accept(project, report, "--accept-task").returncode == 2
    assert (home / "workflow.py").read_bytes() == before


def test_task_change_after_inspection_cannot_inherit_acceptance(project):
    """A checked report cannot bless changed scientific task text."""
    report = inspect(project)
    declaration = project[0] / EXAMPLES[project[5]] / "declared/task_config.yaml"
    before = declaration.read_text()
    needle = {
        "tess": "single TESS light curve.",
        "pet": "37-way fine-grained",
        "davis": "real-RGB future-frame prediction",
    }[project[5]]
    assert needle in before
    declaration.write_text(before.replace(needle, "Deliberately changed " + needle))
    result = accept(project, report, "--accept-task")
    assert result.returncode == 2 and "task changed after inspection" in result.stderr
    assert not (project[0] / "workflow.py").exists()


def test_native_prepare_captures_same_source_without_candidate_or_training(project):
    """A rendered diagram alone is insufficient: real native preparation must consume this source."""
    report = inspect(project)
    result = accept(project, report, "--accept-task")
    assert result.returncode == 0, result.stdout + result.stderr
    home, _, framework, python, credentials, example = project
    config = json.loads((home / "console.json").read_text())
    facts = json.loads(report.read_text())["observation"]["result"]["task"]
    expected_id, metric, direction, input_dims, output_dims, output_type = {
        "tess": ("phyts_tess_rotation", "r2", "higher", [1, 1024], [1], "regressor"),
        "pet": (
            "oxford_iiit_pet",
            "accuracy",
            "higher",
            [3, 144, 144],
            [37],
            "classifier",
        ),
        "davis": (
            "davis_future_prediction",
            "mse",
            "lower",
            [3, 8, 128, 224],
            [3, 4, 128, 224],
            "regressor",
        ),
    }[example]
    assert facts["task_data_path_id"] == expected_id
    assert facts["primary_metric"]["id"] == metric
    assert facts["primary_metric"]["direction"] == direction
    if example == "davis":
        assert [(m["id"], m["direction"]) for m in facts["secondary_metrics"]] == [
            ("psnr", "higher"),
            ("mae", "lower"),
        ]
    io = facts["task_config"]["forward_contract"]["model_io"]
    for key, dimensions in [("input", input_dims), ("output", output_dims)]:
        assert [
            axis["dimension"]["fixed"] for axis in io[key]["axes"][1:]
        ] == dimensions
        assert io[key]["dtype"]["admissible"] == ["float32"]
    assert config["credential_file"] == str(credentials)
    assert (
        config["tasks"][0]["task_revision"]["semantic_fingerprint"]
        == facts["semantic_fingerprint"]
    )
    assert config["editor_projects"][0]["source_file"] == str(home / "workflow.py")
    result = subprocess.run(
        [
            str(python),
            "-m",
            "tools.candidate_prepare",
            "--reusable-request",
            str(home / "prepare-request.json"),
        ],
        cwd=framework,
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["status"] == "prepared"
    envelope = Path(receipt["envelope"])
    assert (envelope / "workflow.py.snapshot").read_bytes() == (
        home / "workflow.py"
    ).read_bytes()
    candidate = json.loads(Path(receipt["candidate_request_path"]).read_text())
    assert [
        node["capability"]
        for node in candidate["preview"]["document"]["definition"]["nodes"]
    ] == ["proposal", "implementation", "validation"]
    proposal = json.loads(
        (Path(receipt["candidate_request_path"]).parent / "proposal.json").read_text()
    )
    assert proposal["allowed_output_types"] == [output_type]
    if example in {"pet", "davis"}:
        # Resolve trusted task scope metadata only; no image/video loading or training.
        probe = subprocess.run(
            [
                str(python),
                "-c",
                """
import json, sys
from contextlib import redirect_stdout
# Trusted task composition may print plugin diagnostics; keep JSON stdout distinct.
with redirect_stdout(sys.stderr):
    from workflows.task_composition import compose_run_task_bindings
    from execute_tools.task_data_path import ScopeBuildRequest
    c = compose_run_task_bindings(sys.argv[1])
    r = ScopeBuildRequest(round_kind="formal", selection_strategy="snapshot", portion=1.0)
    train = c.task_data_path.build_training_scope(r)
    validation = c.task_data_path.build_eval_scope(r)
def identity(row):
    return row.image_id if sys.argv[2] == "pet" else [row.sequence_name, row.start_frame]
print(json.dumps({"objective": c.objective.model_dump(mode="json"),
    "custom_loss": c.task_owned_custom_loss.model_dump(mode="json") if c.task_owned_custom_loss else None,
    "train": [identity(row) for row in train.rows],
    "validation": [identity(row) for row in validation.rows]}))
""",
                str(
                    home / EXAMPLES[example] / "compositions/bounded_qualification.yaml"
                ),
                example,
            ],
            cwd=framework,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        assert probe.returncode == 0, probe.stdout + probe.stderr
        resolved = json.loads(probe.stdout)
        if example == "pet":
            assert resolved["objective"]["loss_type"] == "ce"
            assert resolved["custom_loss"] is None
            assert len(resolved["train"]) == 370 and len(resolved["validation"]) == 74
            assert set(resolved["train"]).isdisjoint(resolved["validation"])
        else:
            assert resolved["objective"]["loss_type"] == "custom"
            assert resolved["objective"]["loss_name"] == "davis_exact_l1"
            descriptor = resolved["custom_loss"]
            loss_file = home / EXAMPLES[example] / "plugins/davis_exact_l1_loss.py"
            assert descriptor["name"] == "davis_exact_l1"
            prepared_loss = proposal["task_composition_ref"]["task_owned_custom_loss"]
            assert prepared_loss["name"] == descriptor["name"]
            assert prepared_loss["content_sha256"] == descriptor["content_sha256"]
            assert descriptor["file_path"] == str(loss_file)
            assert (
                descriptor["content_sha256"]
                == hashlib.sha256(loss_file.read_bytes()).hexdigest()
            )
            assert len(resolved["train"]) == 60 and len(resolved["validation"]) == 15
            assert {row[0] for row in resolved["train"]}.isdisjoint(
                row[0] for row in resolved["validation"]
            )
        for role, filename in [
            ("train", "gate2_train.csv"),
            ("validation", "gate2_validation.csv"),
        ]:
            with (
                ROOT / EXAMPLES[example] / "data/manifests" / filename
            ).open() as stream:
                expected = [
                    row["image_id"]
                    if example == "pet"
                    else [row["sequence_name"], int(row["start_frame"])]
                    for row in csv.DictReader(stream)
                ]
            assert resolved[role] == expected
    assert not (envelope / "workspace").exists()
    assert not (
        home / "state/operations"
    ).exists()  # Direct preparation never submits a candidate.


def test_code_edit_invalidates_original_preparation_request(project):
    """A GUI/code source edit must not run through the old captured source identity."""
    report = inspect(project)
    assert accept(project, report, "--accept-task").returncode == 0
    home, _, framework, python, _, _ = project
    source = home / "workflow.py"
    source.write_text(source.read_text() + "\n# deliberate code edit\n")
    request = json.loads((home / "prepare-request.json").read_text())
    result = subprocess.run(
        [
            str(python),
            "-m",
            "tools.candidate_prepare",
            "--reusable-request",
            str(home / "prepare-request.json"),
        ],
        cwd=framework,
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )
    assert result.returncode != 0
    assert not (home / "runs" / request["run_id"] / "workspace").exists()
    assert not (home / "state/operations").exists()


FANOUT_PROFILE = "examples/native_candidate/tess/fanout/profile.json"


def fanout_source(project, mutate=None):
    """Select copied declarative profile data, leaving the ordinary fixture unchanged."""
    if mutate is not None:
        path = project[0] / FANOUT_PROFILE
        profile = json.loads(path.read_text())
        mutate(profile["workflow"])
        path.write_text(json.dumps(profile))
    report = inspect(project, FANOUT_PROFILE)
    result = accept(project, report, "--accept-task")
    assert result.returncode == 0, result.stdout + result.stderr
    return project[0] / "workflow.py"


def prepare_source(project):
    home, _, framework, python, _, _ = project
    return subprocess.run(
        [
            str(python),
            "-m",
            "tools.candidate_prepare",
            "--reusable-request",
            str(home / "prepare-request.json"),
        ],
        cwd=framework,
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )


@pytest.mark.parametrize("project", ["tess"], indirect=True)
def test_fanout_prepares_one_seed_and_two_branch_owned_stores(project):
    """A five-node picture must materialize the same native branch lineage and stores."""
    source = fanout_source(project)
    result = prepare_source(project)
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["status"] == "prepared"
    envelope = Path(receipt["envelope"])
    assert (envelope / "workflow.py.snapshot").read_bytes() == source.read_bytes()
    inputs = Path(receipt["candidate_request_path"]).parent
    candidate = json.loads((inputs / "candidate_request.json").read_text())
    assert candidate["preview"]["execution_profile"] == "native-proposal-fanout/v1"
    definition = candidate["preview"]["document"]["definition"]
    assert [node["id"] for node in definition["nodes"]] == [
        "proposal",
        "build_left",
        "check_left",
        "build_right",
        "check_right",
    ]
    index = json.loads((inputs / "preparation/child.json").read_text())
    assert [
        Path(item["path"]).relative_to(inputs).as_posix() for item in index["files"]
    ] == [
        "preparation/interpretation_input.json",
        "interpretation.json",
        "proposal.json",
        "storage.build_left.json",
        "storage.build_right.json",
        "llm.json",
        "workflow.json",
        "workflow.resolved.py",
    ]
    seed = json.loads((inputs / "proposal.json").read_text())
    assert seed["allowed_output_types"] == ["regressor"]
    stores = {}
    for side in ["left", "right"]:
        store = json.loads((inputs / f"storage.build_{side}.json").read_text())
        stores[side] = store["local"]["workspace"]
        assert f"/graph_instances/build_{side}/" in stores[side]
        validator = next(
            node for node in definition["nodes"] if node["id"] == f"check_{side}"
        )
        refs = {arg["name"]: arg["source"] for arg in validator["request"]["arguments"]}
        assert refs["proposal"]["node"] == "proposal"
        assert refs["implementation"]["node"] == f"build_{side}"
        assert refs["storage"]["binding"] == f"slot_{side}"
    assert stores["left"] != stores["right"]
    assert not (envelope / "workspace").exists()
    assert not (project[0] / "state/operations").exists()


@pytest.mark.parametrize("project", ["tess"], indirect=True)
@pytest.mark.parametrize(
    "malformation", ["cross_branch_storage", "missing_validator", "missing_profile"]
)
def test_fanout_native_admission_refuses_incomplete_or_shared_branch(
    project, malformation
):
    """Neither node count nor a shared alias can authorize a graph without its native profile."""

    def change(workflow):
        if malformation == "missing_profile":
            workflow.pop("execution_profile")
        elif malformation == "missing_validator":
            workflow["definition"]["nodes"] = [
                node
                for node in workflow["definition"]["nodes"]
                if node["id"] != "check_right"
            ]
        else:
            # Keep every binding used so the refusal specifically tests shared ownership.
            workflow["definition"]["externals"] = [
                item
                for item in workflow["definition"]["externals"]
                if item["id"] != "slot_right"
            ]
            for node in workflow["definition"]["nodes"]:
                if node["id"] in {"build_right", "check_right"}:
                    for argument in node["request"]["arguments"]:
                        if argument["name"] == "storage":
                            argument["source"]["binding"] = "slot_left"

    fanout_source(project, change)
    result = prepare_source(project)
    assert result.returncode != 0
    if malformation == "cross_branch_storage":
        assert (
            "Graph storage binding is shared across implementation owners"
            in result.stdout + result.stderr
        )
    assert not (project[0] / "state/operations").exists()
    assert not list((project[0] / "runs").glob("*/workspace"))


@pytest.mark.parametrize("project", ["tess"], indirect=True)
def test_fanout_edited_graph_cannot_use_old_preparation_request(project):
    """The source identity includes explicit graph lineage, not just the accepted task."""
    source = fanout_source(project)
    before = source.read_text()
    # Valid Python code edit changes the graph instance label, invalidating old request bytes.
    assert "build_left" in before
    source.write_text(before.replace("build_left", "build_edited"))
    result = prepare_source(project)
    assert result.returncode != 0
    assert not (project[0] / "state/operations").exists()
    assert not list((project[0] / "runs").glob("*/workspace"))
