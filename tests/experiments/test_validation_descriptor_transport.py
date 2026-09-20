import array
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import torch

from experiments.shared.validation_descriptor_transport import (
    receive_snapshots,
    send_snapshots,
)
from experiments.shared.validation_frames import read_frame
from experiments.shared.validation_snapshot import sealed_tensor_state


def test_persistent_child_loads_three_distinct_epoch_snapshots():
    parent, child = socket.socketpair()
    code = """
import os,socket,sys,time,torch
from experiments.shared.validation_descriptor_transport import receive_snapshots
from experiments.shared.validation_frames import write_frame
channel=socket.socket(fileno=int(sys.argv[1]))
for epoch in range(3):
    with receive_snapshots(channel,deadline=time.monotonic()+10,
                           max_metadata_bytes=100,max_snapshot_bytes=8192) as (meta,fds):
        with os.fdopen(os.dup(fds[0]),'rb') as stream:
            state=torch.load(stream,weights_only=True)
        assert state['weight'].item()==epoch
        write_frame(channel.fileno(),meta,max_bytes=100,deadline=time.monotonic()+10)
channel.close()
"""
    process = subprocess.Popen(
        [sys.executable, "-c", code, str(child.fileno())],
        cwd=Path(__file__).resolve().parents[2],
        env={"PATH": os.defpath},
        pass_fds=(child.fileno(),),
    )
    child.close()
    try:
        for epoch in range(3):
            with (
                sealed_tensor_state(
                    {"weight": torch.tensor(epoch)}, max_tensor_bytes=8
                ) as model,
                sealed_tensor_state({}, max_tensor_bytes=0) as objective,
            ):
                metadata = str(epoch).encode()
                send_snapshots(
                    parent,
                    metadata,
                    [model.fd, objective.fd],
                    deadline=time.monotonic() + 10,
                    max_metadata_bytes=100,
                )
                assert (
                    read_frame(
                        parent.fileno(), max_bytes=100, deadline=time.monotonic() + 10
                    )
                    == metadata
                )
        assert process.wait(timeout=5) == 0
    finally:
        parent.close()
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def test_snapshot_descriptors_survive_sender_close_then_receiver_closes_them():
    sender, receiver = socket.socketpair()
    try:
        with (
            sealed_tensor_state(
                {"weight": torch.tensor([3.0])}, max_tensor_bytes=4
            ) as model,
            sealed_tensor_state({}, max_tensor_bytes=0) as loss,
        ):
            send_snapshots(
                sender,
                b'{"epoch":1}',
                [model.fd, loss.fd],
                deadline=time.monotonic() + 2,
                max_metadata_bytes=100,
            )
        with receive_snapshots(
            receiver,
            deadline=time.monotonic() + 2,
            max_metadata_bytes=100,
            max_snapshot_bytes=8192,
        ) as (metadata, descriptors):
            assert metadata == b'{"epoch":1}'
            # This synthetic receiver also stands in for the confined worker;
            # a production coordinator never deserializes candidate weights.
            with os.fdopen(os.dup(descriptors[0]), "rb") as stream:
                assert torch.load(stream, weights_only=True)["weight"].item() == 3
            assert not any(os.get_inheritable(fd) for fd in descriptors)
        for fd in descriptors:
            with pytest.raises(OSError):
                os.fstat(fd)
    finally:
        sender.close()
        receiver.close()


@pytest.mark.parametrize("fault", ["unsealed", "too_many", "oversize", "bad_marker"])
def test_invalid_descriptors_refuse_without_leaking_received_fds(tmp_path, fault):
    sender, receiver = socket.socketpair()
    path = tmp_path / "unsealed"
    path.write_bytes(b"x")
    disk = os.open(path, os.O_RDONLY)
    try:
        with sealed_tensor_state({}, max_tensor_bytes=0) as snapshot:
            fds = [snapshot.fd, snapshot.fd]
            if fault == "unsealed":
                fds[0] = disk
            if fault == "too_many":
                fds = fds * 3
            before = set(os.listdir("/proc/self/fd"))
            sender.sendmsg(
                [b"X" if fault == "bad_marker" else b"S"],
                [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", fds))],
            )
            with (
                pytest.raises((ValueError, OSError)),
                receive_snapshots(
                    receiver,
                    deadline=time.monotonic() + 2,
                    max_metadata_bytes=100,
                    max_snapshot_bytes=1 if fault == "oversize" else 8192,
                ),
            ):
                pytest.fail("invalid descriptors accepted")
            assert set(os.listdir("/proc/self/fd")) == before
    finally:
        os.close(disk)
        sender.close()
        receiver.close()


def test_deadline_while_waiting_for_metadata_closes_received_descriptors():
    sender, receiver = socket.socketpair()
    try:
        with sealed_tensor_state({}, max_tensor_bytes=0) as snapshot:
            before = set(os.listdir("/proc/self/fd"))
            sender.sendmsg(
                [b"S"],
                [
                    (
                        socket.SOL_SOCKET,
                        socket.SCM_RIGHTS,
                        array.array("i", [snapshot.fd] * 2),
                    )
                ],
            )
            with (
                pytest.raises(TimeoutError),
                receive_snapshots(
                    receiver,
                    deadline=time.monotonic() + 0.02,
                    max_metadata_bytes=100,
                    max_snapshot_bytes=8192,
                ),
            ):
                pytest.fail("missing metadata accepted")
            assert set(os.listdir("/proc/self/fd")) == before
    finally:
        sender.close()
        receiver.close()
