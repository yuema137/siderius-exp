"""
DS6d — run_comparison DataScope/HealthGate surfaces.

Covers: spec parsing + v17_pregate override pin at main() startup (both fail
before any workspace/phase work), and run_agent forwarding the operator's
raw spec strings to the tuner subprocess CLI.
See docs/design/enable_partial_file_list.md (Commit DS6).
"""

from __future__ import annotations

import os
import sys
from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tasks.tidmad.tools.run_comparison import run_agent


def _main(argv: list[str]) -> None:
    from tasks.tidmad.tools import run_comparison

    required = ["--workspace_root", "/tmp", "--data_dir", "/tmp"]
    with patch.object(sys, "argv", ["run_comparison.py", *required, *argv]):
        run_comparison.main()


class TestMainStartupGuards:
    def test_malformed_data_scope_exits(self):
        with pytest.raises(SystemExit, match="malformed"):
            _main(["--model", "punet", "--data_scope", "4-x"])

    def test_v17_pregate_forbids_health_gate_files(self):
        with pytest.raises(SystemExit, match="pins its HealthGate policy"):
            _main(
                [
                    "--model",
                    "wavenet",
                    "--run_name",
                    "v17_pregate_baseline",
                    "--health_gate_files",
                    "4,7,9",
                ]
            )

    def test_v17_pregate_forbids_disabling_gates(self):
        with pytest.raises(SystemExit, match="pins its HealthGate policy"):
            _main(
                [
                    "--model",
                    "wavenet",
                    "--run_name",
                    "v17_pregate_baseline",
                    "--no-health_gate_enabled",
                ]
            )

    def test_wrong_checkout_revision_refuses_before_dataset_resolution(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A directory with the right files must not substitute for the pinned SHA."""
        from tasks.tidmad.tools import run_comparison

        monkeypatch.setenv("SIDERIUS_CHECKOUT", os.environ["SIDERIUS_CHECKOUT"])
        wrong = SimpleNamespace(returncode=0, stdout="0" * 40 + "\n")
        with (
            patch.object(run_comparison.subprocess, "run", return_value=wrong),
            patch.object(run_comparison, "resolve_dataset_dir") as resolve_data,
            pytest.raises(SystemExit, match="revision mismatch"),
        ):
            _main(["--model", "punet"])
        resolve_data.assert_not_called()

    def test_missing_probe_refuses_without_falling_back(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A src-shaped directory without the real probe is not a checkout authority."""
        from tasks.tidmad.tools import run_comparison

        root = tmp_path / "framework"
        for relative in (
            "src/core/layout.py",
            "src/nodes/ml_hyperparameter_tune_agent/ml_hyperparameter_tune_agent.py",
            ".venv/bin/python",
        ):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        monkeypatch.setenv("SIDERIUS_CHECKOUT", str(root))

        # `_main` validates the selected checkout by assigning module globals
        # before the probe refusal. Restore them so later tests in this process
        # cannot inherit this intentionally foreign fixture root.
        original_root = run_comparison.SIDERIUS_ROOT
        original_health_path = run_comparison.HEALTH_CHECKS_PATH
        try:
            with pytest.raises(SystemExit, match="_import_resolution_probe.py"):
                _main(["--model", "punet"])
        finally:
            run_comparison.SIDERIUS_ROOT = original_root
            run_comparison.HEALTH_CHECKS_PATH = original_health_path


class TestRunAgentForwarding:
    def _call(self, **kwargs):
        with patch("tasks.tidmad.tools.run_comparison.subprocess.run") as mock_run:
            mock_run.return_value = SimpleNamespace(returncode=0)
            with patch(
                "tasks.tidmad.tools.run_comparison._verify_agent_completion",
                create=True,
            ):
                with suppress(SystemExit):
                    run_agent(
                        model_type="punet",
                        agent_workspace="/tmp/ws",
                        agent_run_name="r1",
                        provider="gemini",
                        model_id="m",
                        max_rounds=1,
                        **kwargs,
                    )
                    # Post-subprocess completion verification exits on the empty
                    # workspace; the launched command is all this test needs.
            return mock_run.call_args

    def _cmd(self, **kwargs) -> list[str]:
        return self._call(**kwargs).args[0]

    def test_specs_forwarded_verbatim(self):
        cmd = self._cmd(data_scope_spec="4-9", health_gate_files_spec="4,7,9")
        assert "--data_scope" in cmd and cmd[cmd.index("--data_scope") + 1] == "4-9"
        assert (
            "--health_gate_files" in cmd
            and cmd[cmd.index("--health_gate_files") + 1] == "4,7,9"
        )
        assert "--no-health_gate_enabled" not in cmd

    def test_disabled_gates_forwarded(self):
        cmd = self._cmd(health_gate_enabled=False)
        assert "--no-health_gate_enabled" in cmd
        assert "--data_scope" not in cmd

    def test_defaults_forward_nothing(self):
        cmd = self._cmd()
        assert "--data_scope" not in cmd
        assert "--health_gate_files" not in cmd
        assert "--no-health_gate_enabled" not in cmd

    def test_child_uses_selected_src_checkout_environment_without_pythonpath(self):
        """The comparison child must not execute exp Python or root-layout source."""
        from tasks.tidmad.tools import run_comparison

        call = self._call()
        command = call.args[0]
        environment = call.kwargs["env"]
        checkout = Path(run_comparison.SIDERIUS_ROOT)

        assert Path(command[0]) == checkout / ".venv" / "bin" / "python"
        assert Path(command[1]) == (
            checkout
            / "src"
            / "nodes"
            / "ml_hyperparameter_tune_agent"
            / "ml_hyperparameter_tune_agent.py"
        )
        assert "PYTHONPATH" not in environment
        assert Path(environment["VIRTUAL_ENV"]) == checkout / ".venv"
