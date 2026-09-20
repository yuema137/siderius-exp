import os
import subprocess
import sys

import pytest
import torch

from experiments.shared.validation_snapshot import sealed_tensor_state


def test_snapshot_is_immutable_independent_and_readable_by_worker():
    state = {"weight": torch.arange(12).reshape(3, 4).t()}
    with sealed_tensor_state(state, max_tensor_bytes=96) as snapshot:
        state["weight"].zero_()
        with pytest.raises(OSError):
            os.pwrite(snapshot.fd, b"x", 0)
        with pytest.raises(OSError):
            os.ftruncate(snapshot.fd, 0)
        code = """
import os,sys,torch
with os.fdopen(int(sys.argv[1]), 'rb') as stream:
    state = torch.load(stream, weights_only=True)
assert torch.equal(state['weight'], torch.arange(12).reshape(3,4).t())
"""
        subprocess.run(
            [sys.executable, "-c", code, str(snapshot.fd)],
            pass_fds=(snapshot.fd,),
            check=True,
            timeout=30,
        )
        assert snapshot.size_bytes > 96
    with pytest.raises(OSError):
        os.fstat(snapshot.fd)


@pytest.mark.parametrize(
    "state,limit,error",
    [
        ({"x": torch.ones(3)}, 11, ValueError),
        ({"x": torch.nn.Parameter(torch.ones(1))}, 100, TypeError),
        ({"x": torch.empty(1, device="meta")}, 100, ValueError),
        ({"x": torch.ones(1)}, True, ValueError),
    ],
)
def test_invalid_snapshot_refuses_before_allocation(state, limit, error):
    with pytest.raises(error), sealed_tensor_state(state, max_tensor_bytes=limit):
        pytest.fail("invalid state was admitted")
