"""A native budget stop must reach the private relay as cancellation, not EOF."""

import socket
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from execute_tools.training_budget_execution import TrainingAllocationRejected
from execute_tools.validation_execution import ValidationCallbacks

from experiments.shared.inherited_validation_client import (
    InheritedClientSettings,
    InheritedValidationClient,
)
from experiments.shared.validation_epoch_execution import ValidationProgressRelay


@pytest.mark.parametrize("stage", ["allocation", "verified"])
def test_budget_refusal_cancels_relay_without_masking_native_reason(stage):
    server, client_socket = socket.socketpair()
    client = InheritedValidationClient(
        InheritedClientSettings(
            channel_fd=client_socket.detach(),
            deadline_epoch=time.time() + 5,
            max_metadata_bytes=10000,
            max_state_bytes=10000,
        ),
        serialize_scope=lambda _: "scope",
        declare_rows=lambda _: 1,
    )
    relay = ValidationProgressRelay(
        server,
        sequence=0,
        expected_rows=1,
        deadline=time.monotonic() + 5,
        max_metadata_bytes=10000,
    )

    def reject():
        raise TrainingAllocationRejected("training allocation cannot fit validation")

    callbacks = ValidationCallbacks(
        check_allocation=reject if stage == "allocation" else None,
        verifier=SimpleNamespace(is_terminal=True, feed=lambda *a, **k: None),
        on_verified=reject if stage == "verified" else None,
    )
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(relay.feed, 15.0, elapsed_ms=15.0)
            try:
                with pytest.raises(
                    TrainingAllocationRejected, match="cannot fit validation"
                ):
                    client._receive(SimpleNamespace(expected_rows=1), callbacks)
            finally:
                client.close()
            with pytest.raises(
                RuntimeError,
                match="native training cancelled validation: training_allocation",
            ):
                pending.result(timeout=3)
        assert relay.rows == 0
    finally:
        client.close()
        server.close()
