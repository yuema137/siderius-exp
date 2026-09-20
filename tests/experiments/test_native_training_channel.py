import json
import os
import subprocess
import sys
from contextlib import ExitStack
from pathlib import Path

import pytest
from execute_tools.validation_execution import ValidationDeployment

from experiments.shared.native_training_channel import (
    launch_native_training_channel,
    native_channel_command,
)


def deployment():
    return ValidationDeployment(
        factory="trusted.client:create", settings={"scope": "operator-owned"}
    )


@pytest.mark.parametrize("equals", [False, True])
@pytest.mark.parametrize("module_entry", [False, True])
def test_two_real_children_get_independent_channels_and_protected_settings(
    tmp_path, equals, module_entry
):
    entrypoint = tmp_path / "native_fixture.py"
    entrypoint.write_text("""import argparse,json,os,socket
from execute_tools.validation_execution import ValidationDeployment
p=argparse.ArgumentParser()
p.add_argument('--validation_executor_json',required=True)
config=ValidationDeployment.model_validate_json(p.parse_args().validation_executor_json)
assert config.factory=='trusted.client:create'
assert config.settings['scope']=='operator-owned'
s=socket.socket(fileno=config.settings['channel_fd'])
s.settimeout(5)
for i in range(2):
    message=s.recv(128).decode()
    s.sendall(json.dumps({'message':message,'pid':os.getpid()}).encode())
s.close()
""")
    binding = ["--validation_executor_json", '{"untrusted":true}']
    if equals:
        binding = ["--validation_executor_json=" + binding[1]]
    with ExitStack() as stack:
        sessions = [
            stack.enter_context(
                launch_native_training_channel(
                    [sys.executable, str(entrypoint), *binding],
                    python=Path(sys.executable),
                    entrypoint=entrypoint,
                    deployment=deployment(),
                    environment={"PATH": os.defpath},
                    cwd=tmp_path,
                    entry_module=entrypoint.stem if module_entry else None,
                )
            )
            for _ in range(2)
        ]
        for index, session in enumerate(sessions):
            session.channel.settimeout(5)
            for epoch in range(2):
                message = f"session-{index}-epoch-{epoch}"
                session.channel.sendall(message.encode())
                result = json.loads(session.channel.recv(4096))
                assert result == {"message": message, "pid": session.process.pid}
            assert session.process.wait(timeout=5) == 0
        assert sessions[0].process.pid != sessions[1].process.pid
    assert all(session.channel.fileno() == -1 for session in sessions)


@pytest.mark.parametrize(
    "command",
    [
        ["python", "-c", "print('not native')"],
        ["python", "native.py"],
        ["python", "native.py", "--validation_executor_json"],
        [
            "python",
            "native.py",
            "--validation_executor_json=a",
            "--validation_executor_json=b",
        ],
    ],
)
def test_wrong_entrypoint_or_ambiguous_binding_refuses(command):
    with pytest.raises(ValueError):
        native_channel_command(
            command,
            python=Path("python"),
            entrypoint=Path("native.py"),
            deployment=deployment(),
            channel_fd=3,
        )


def test_context_failure_reaps_direct_child_and_closes_channel(tmp_path):
    entrypoint = tmp_path / "sleep.py"
    entrypoint.write_text("import time\ntime.sleep(60)\n")
    with (
        pytest.raises(RuntimeError, match="abort"),
        launch_native_training_channel(
            [sys.executable, str(entrypoint), "--validation_executor_json={}"],
            python=Path(sys.executable),
            entrypoint=entrypoint,
            deployment=deployment(),
            environment={"PATH": os.defpath},
            cwd=tmp_path,
        ) as session,
    ):
        raise RuntimeError("abort")
    assert session.process.poll() is not None
    assert session.channel.fileno() == -1


def test_deployment_module_entry_reaches_installed_native_cli():
    result = subprocess.run(
        [sys.executable, "-m", "experiments.shared.native_training_entry", "--help"],
        cwd=Path(__file__).resolve().parents[2],
        env={"PATH": os.defpath},
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--validation_executor_json" in result.stdout
    assert "--model_cfg" in result.stdout
