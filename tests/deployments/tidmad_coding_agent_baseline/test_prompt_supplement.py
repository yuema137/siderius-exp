"""Exercise delivery at the real subprocess boundary without an external model."""

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from deployments.tidmad_coding_agent_baseline.tools import supervisor
from deployments.tidmad_coding_agent_baseline.tools.prompt_supplement import (
    append_verified_supplement,
)


def supplement(tmp_path):
    artifact = tmp_path / "strategy.md"
    artifact.write_text(
        "# Strategy\nCoordinate independent work and reserve time to finish.\n"
    )
    manifest = tmp_path / "supplement.json"
    manifest.write_text(
        json.dumps(
            {
                "artifact": artifact.name,
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            }
        )
    )
    return manifest, artifact


def test_two_fresh_processes_receive_strategy_and_tamper_stops_third(
    tmp_path, monkeypatch
):
    manifest, artifact = supplement(tmp_path)
    prompt = tmp_path / "prompt.md"
    prompt.write_bytes(b"Original task and limits.\n")
    # A real child records precisely the stdin the production supervisor sends.
    monkeypatch.setattr(
        supervisor,
        "command_for",
        lambda *_: [
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())",
        ],
    )
    kwargs = {
        "product": "codex",
        "prompt": prompt,
        "deadline_epoch": int(time.time()) + 30,
        "run_id": "smoke",
        "prompt_supplement": manifest,
    }
    for number in (1, 2):
        log = tmp_path / f"{number}.log"
        assert supervisor._run_once(
            **kwargs, log_path=log, invocation_id=str(number)
        ) == (0, False)
        delivered = log.read_bytes()
        assert delivered.startswith(prompt.read_bytes())
        assert delivered.endswith(artifact.read_bytes())
        assert str(artifact).encode() in delivered
        assert b"After context recovery" in delivered
    artifact.write_text("changed after first session")
    with pytest.raises(ValueError, match="checksum mismatch"):
        supervisor._run_once(**kwargs, log_path=tmp_path / "3.log", invocation_id="3")
    assert not (tmp_path / "3.log").exists()


def test_missing_supplement_does_not_start_scientific_clock(tmp_path):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("task")
    with pytest.raises(ValueError, match="manifest must be a regular file"):
        supervisor.supervise(
            product="codex",
            work_root=tmp_path / "work",
            prompt=prompt,
            scheduled_start_epoch=1,
            prompt_supplement=tmp_path / "missing.json",
        )
    assert not (tmp_path / "work").exists()


def test_baseline_prompt_bytes_unchanged():
    original = b"Task\n\x00limits\n"
    assert append_verified_supplement(original, None) == original


def test_deployed_harness_remains_standard_library_only(tmp_path):
    # install_vm.sh creates a bare harness venv. The optional feature must not
    # make either baseline startup or strategy delivery require site-packages.
    manifest, artifact = supplement(tmp_path)
    root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            "from pathlib import Path; from deployments.tidmad_coding_agent_baseline.tools import supervisor; import sys; sys.stdout.buffer.write(supervisor.append_verified_supplement(b'task', Path(sys.argv[1])))",
            str(manifest),
        ],
        cwd=root,
        capture_output=True,
        check=True,
    )
    assert result.stdout.endswith(artifact.read_bytes())


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"artifact": "x", "sha256": "bad"},
        {"artifact": 7, "sha256": "a" * 64},
        {"artifact": "x", "sha256": "a" * 64, "extra": True},
    ],
)
def test_invalid_manifest_fails_before_delivery(tmp_path, payload):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        append_verified_supplement(b"task", manifest)


@pytest.mark.parametrize("invalid", ["../outside.md", "/tmp/outside.md"])
def test_reject_path_escape(tmp_path, invalid):
    manifest, _ = supplement(tmp_path)
    manifest.write_text(json.dumps({"artifact": invalid, "sha256": "a" * 64}))
    with pytest.raises(ValueError, match="must be relative"):
        append_verified_supplement(b"task", manifest)


def test_reject_symlink(tmp_path):
    manifest, artifact = supplement(tmp_path)
    content = artifact.read_bytes()
    artifact.unlink()
    other = tmp_path / "other.md"
    other.write_bytes(content)
    artifact.symlink_to(other)
    with pytest.raises(ValueError, match="confined regular file"):
        append_verified_supplement(b"task", manifest)
