"""Build one deterministic input/harness bundle for both agent products."""

from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from .io import atomic_write_json, sha256_file
from .model import BANDS


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _tracked_task_files(repo: Path) -> list[Path]:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", "tasks/tidmad"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        raise RuntimeError(
            "tasks/tidmad has uncommitted changes; refuse a drifting snapshot"
        )
    output = subprocess.run(
        ["git", "ls-files", "-z", "tasks/tidmad"],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout
    return [repo / item.decode() for item in output.split(b"\0") if item]


def _copy_relative(source: Path, repo: Path, destination: Path) -> None:
    relative = source.relative_to(repo)
    target = destination / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _build_evaluator(
    repo: Path, siderius_checkout: Path, output: Path
) -> tuple[str, str]:
    expected = (repo / "SIDERIUS_REVISION").read_text().strip()
    actual = _git(siderius_checkout, "rev-parse", "HEAD")
    if actual != expected:
        raise ValueError(
            f"SIDERIUS checkout is {actual[:12]}, but siderius-exp pins {expected[:12]}"
        )
    if _git(siderius_checkout, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("SIDERIUS checkout has tracked changes")
    source_dir = output / "source-build"
    source_dir.mkdir()
    archived_source = subprocess.run(
        ["git", "archive", "--format=tar", "HEAD"],
        cwd=siderius_checkout,
        check=True,
        capture_output=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archived_source), mode="r:") as archive:
        archive.extractall(source_dir, filter="data")
    wheel_dir = output / "wheel-build"
    wheel_dir.mkdir()
    environment = os.environ.copy()
    environment["SOURCE_DATE_EPOCH"] = _git(
        siderius_checkout, "show", "-s", "--format=%ct", "HEAD"
    )
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(wheel_dir)],
        cwd=source_dir,
        check=True,
        env=environment,
    )
    wheels = list(wheel_dir.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"expected one SIDERIUS wheel, found {len(wheels)}")
    wheel_name = wheels[0].name
    shutil.copy2(wheels[0], output / wheel_name)
    (output / "siderius-wheel-name.txt").write_text(f"{wheel_name}\n")
    requirements = subprocess.run(
        [
            "uv",
            "export",
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--no-emit-package",
            "siderius",
            "--no-hashes",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    (output / "requirements.txt").write_text(requirements)
    shutil.rmtree(wheel_dir)
    shutil.rmtree(source_dir)
    return actual, sha256_file(output / wheel_name)


def _write_checksums(root: Path, output: Path) -> None:
    lines = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path != output:
            lines.append(f"{sha256_file(path)}  {path.relative_to(root)}")
    output.write_text("\n".join(lines) + "\n")


def _write_full_evaluation_scopes(input_root: Path, evaluator_root: Path) -> None:
    """Derive canonical full-band scopes from the frozen task profile."""

    profile = json.loads(
        (input_root / "tasks/tidmad/resolved/dataset_profile.json").read_text()
    )
    count = int(profile["dataset"]["segments_per_file"])
    scopes = evaluator_root / "evaluation_scopes"
    scopes.mkdir()
    all_scope: dict[str, list[int]] = {}
    for band in BANDS:
        low, high = (int(value) for value in band.split("-"))
        sample_set = {str(index): list(range(count)) for index in range(low, high + 1)}
        atomic_write_json(scopes / f"band-{band}-full.json", sample_set)
        all_scope.update(sample_set)
    atomic_write_json(scopes / "all-full.json", all_scope)


def build_bundle(
    task_md: Path,
    siderius_checkout: Path,
    output: Path,
    repo: Path | None = None,
) -> Path:
    repo = (repo or _repo_root()).resolve()
    if not task_md.is_file() or not task_md.read_text().strip():
        raise ValueError("an operator-approved, non-empty task.md is required")
    if not siderius_checkout.is_dir():
        raise ValueError("an exact-pin SIDERIUS checkout is required")
    deployment = repo / "deployments" / "tidmad_coding_agent_baseline"
    data_manifest = (
        repo / "campaigns" / "tidmad_gold" / "inputs" / "q3_data_manifest.sha256"
    )
    with tempfile.TemporaryDirectory(prefix="tidmad-coding-agent-bundle-") as raw:
        staging = Path(raw) / "tidmad-coding-agent-baseline"
        input_root = staging / "input"
        harness_root = staging / "harness" / "baseline_harness"
        input_root.mkdir(parents=True)
        harness_root.mkdir(parents=True)
        for source in _tracked_task_files(repo):
            _copy_relative(source, repo, input_root)
        shutil.copy2(task_md, input_root / "task.md")
        for source in sorted((deployment / "tools").glob("*.py")):
            shutil.copy2(source, harness_root / source.name)
        shutil.copytree(deployment / "systemd", staging / "harness" / "systemd")
        shutil.copytree(deployment / "machine", staging / "harness" / "machine")
        evaluator_root = staging / "evaluator"
        evaluator_root.mkdir()
        shutil.copy2(data_manifest, evaluator_root / "data_manifest.sha256")
        _write_full_evaluation_scopes(input_root, evaluator_root)
        siderius_revision, wheel_sha = _build_evaluator(
            repo, siderius_checkout.resolve(), evaluator_root
        )
        _write_checksums(evaluator_root, evaluator_root / "SHA256")
        atomic_write_json(
            input_root / "provenance.json",
            {
                "version": "tidmad-coding-agent-input-v2",
                "siderius_exp_revision": _git(repo, "rev-parse", "HEAD"),
                "siderius_revision": siderius_revision,
                "task_tree": _git(repo, "rev-parse", "HEAD:tasks/tidmad"),
                "siderius_wheel_sha256": wheel_sha,
                "task_md_sha256": sha256_file(task_md),
            },
        )
        _write_checksums(input_root, input_root / "bundle.sha256")
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(f".{output.name}.tmp")
        with (
            temporary.open("wb") as raw_output,
            gzip.GzipFile(
                filename="", mode="wb", fileobj=raw_output, mtime=0
            ) as compressed,
            tarfile.open(
                fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT
            ) as archive,
        ):
            archive.add(
                staging,
                arcname=staging.name,
                filter=_canonical_tar_info,
            )
        os.replace(temporary, output)
    return output


def _canonical_tar_info(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mtime = 0
    return info


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-md", type=Path, required=True)
    parser.add_argument("--siderius-checkout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(build_bundle(args.task_md, args.siderius_checkout, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
