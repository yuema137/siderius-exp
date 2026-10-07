"""Capture bounded arithmetic/search cases using this interpreter's infra.

Run with the frozen reference checkout's own Python. No real data, GPU or API
is used. Probe observations are synthetic; the composers and search are real.
"""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import torch
from agent.skills.evaluate_vram_skill import batch_resolver, wrapper
from agent.skills.evaluate_vram_skill.structural_probe import (
    AutogradTapeReport,
    ForwardLayerReport,
    ProbeResult,
)

REFERENCE = "078b23ca7d88c2e498be37621e655b1eeb3c8c9e"


def probe(*, batch, params, outputs):
    return ProbeResult(
        mode="training",
        model_forward=ForwardLayerReport(
            module_name="Synthetic",
            layers=[],
            total_param_bytes=params,
            forward_output_bytes_sum=outputs * batch,
            forward_output_bytes_max=outputs * batch // 3,
        ),
        autograd_tape=AutogradTapeReport(
            unique_storage_count=2, total_saved_bytes=31 * batch
        ),
        input_bytes=4 * batch,
        output_bytes=8 * batch,
    )


def capture():
    root = Path(wrapper.__file__).resolve().parents[4]
    revision = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != REFERENCE:
        raise ValueError(f"Expected frozen reference {REFERENCE}, found {revision}")
    if subprocess.check_output(
        ["git", "-C", str(root), "diff", "HEAD", "--", "src"], text=True
    ):
        raise ValueError("Reference source checkout is modified")
    estimates = []
    for batch in (1, 3, 8):
        for params, outputs in ((0, 0), (64, 192), (8192, 2**30)):
            observed = probe(batch=batch, params=params, outputs=outputs)
            common = {
                "batch_size": batch,
                "leaf_parameter_bytes": params,
                "leaf_output_bytes_sum": observed.model_forward.forward_output_bytes_sum,
                "leaf_output_bytes_max": observed.model_forward.forward_output_bytes_max,
                "input_bytes": observed.input_bytes,
                "output_bytes": observed.output_bytes,
                "saved_tensor_bytes": observed.autograd_tape.total_saved_bytes,
            }
            for optimizer in (None, "sgd", "adam", "ADAMW"):
                train = {} if optimizer is None else {"optimizer": optimizer}
                total, breakdown = wrapper._compose_training_peak(
                    observed, str(train.get("optimizer") or "adam").lower()
                )
                estimates.append(
                    {
                        "observations": common
                        | {"phase": "training", "training_config": train},
                        "admission_bytes": total,
                        "diagnostic_bytes": total,
                        "breakdown": breakdown,
                    }
                )
            total, breakdown = wrapper._compose_inference_peak(observed)
            estimates.append(
                {
                    "observations": common
                    | {"phase": "inference", "training_config": {}},
                    "admission_bytes": batch_resolver._predict_inference_peak_bytes(
                        observed
                    ),
                    "diagnostic_bytes": total,
                    "breakdown": breakdown,
                }
            )
    searches = []
    for candidates in ((8, 4, 1), (7, 3)):
        for segmentation in (None, 100_000_000):
            for params, outputs in ((64, 192), (8192, 2**30)):
                threshold = batch_resolver._predict_inference_peak_bytes(
                    probe(batch=candidates[-1], params=params, outputs=outputs)
                )
                for cap in (threshold - 1, threshold, threshold + 1, threshold * 8):

                    def mocked_probe(*args, params=params, outputs=outputs, **kwargs):
                        sample = kwargs.get(
                            "input_sample", args[2] if len(args) > 2 else None
                        )
                        return probe(
                            batch=sample.shape[0], params=params, outputs=outputs
                        )

                    with patch.object(
                        batch_resolver,
                        "probe_activation_footprint",
                        side_effect=mocked_probe,
                    ):
                        try:
                            result = batch_resolver.resolve_inference_decision(
                                torch.nn.Linear(2, 2),
                                segmentation,
                                cap,
                                candidate_batches=candidates,
                                supplied_probe=torch.zeros(1, 2),
                            )
                            outcome = "accepted"
                        except batch_resolver.BatchSearchRefused as exc:
                            result = exc.decision
                            outcome = "refused"
                    searches.append(
                        {
                            "candidates": candidates,
                            "segmentation": segmentation,
                            "params": params,
                            "outputs": outputs,
                            "cap": cap,
                            "outcome": outcome,
                            "decision": result.model_dump(mode="json"),
                        }
                    )
    shared = torch.nn.Linear(2, 2)
    actual_decision = batch_resolver.resolve_inference_decision(
        torch.nn.Sequential(shared, shared, shared, shared),
        None,
        185 * 1024**2 + 256,
        candidate_batches=(7, 4, 1),
        supplied_probe=torch.zeros(1, 2),
    )
    return {
        "reference_revision": revision,
        "capture_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "api_calls": 0,
        "gpu_calls": 0,
        "scope": "Bounded synthetic estimates/search plus one actual CPU forward; no live GPU peak qualification",
        "estimates": estimates,
        "searches": searches,
        "actual_cpu_search": {
            "model": "one Linear(2, 2) object used four times in Sequential",
            "decision": actual_decision.model_dump(mode="json"),
            "scope": "Actual CPU forward observations and frozen resolver; no GPU measurement",
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(capture(), indent=2) + "\n")
