"""Measure bounded training-step time and peak VRAM for baseline model shapes."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
from torch import nn

from tasks.supernemo_signal_background.tools.run_baseline import Mlp, TrackerNetwork


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--architecture", choices=("mlp", "cnn", "resnet"), required=True
    )
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--depth", type=int, required=True)
    parser.add_argument("--batch-size", type=int, required=True)
    parser.add_argument("--max-hits", type=int, default=224)
    parser.add_argument("--warmup-steps", type=int, default=2)
    parser.add_argument("--measured-steps", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    device = torch.device("cuda")
    torch.manual_seed(20260901)
    model: nn.Module
    if args.architecture == "mlp":
        model = Mlp(args.width, args.depth)
        hits = torch.zeros((args.batch_size, 1, 1), device=device)
        mask = torch.ones((args.batch_size, 1), dtype=torch.bool, device=device)
    else:
        model = TrackerNetwork(
            args.width, args.depth, residual=args.architecture == "resnet"
        )
        hits = torch.randn(
            (args.batch_size, args.max_hits, 5), dtype=torch.float32, device=device
        )
        mask = torch.ones(
            (args.batch_size, args.max_hits), dtype=torch.bool, device=device
        )
    model.to(device)
    event = torch.randn((args.batch_size, 5), dtype=torch.float32, device=device)
    labels = torch.randint(0, 2, (args.batch_size,), device=device).float()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    loss = nn.BCEWithLogitsLoss()

    def step() -> None:
        optimizer.zero_grad(set_to_none=True)
        value = loss(model(event, hits, mask), labels)
        value.backward()
        optimizer.step()

    for _ in range(args.warmup_steps):
        step()
    torch.cuda.synchronize(device)
    torch.cuda.reset_peak_memory_stats(device)
    started = time.perf_counter()
    for _ in range(args.measured_steps):
        step()
    torch.cuda.synchronize(device)
    elapsed = time.perf_counter() - started
    report = {
        "architecture": args.architecture,
        "width": args.width,
        "depth": args.depth,
        "batch_size": args.batch_size,
        "max_hits": args.max_hits,
        "parameters": sum(parameter.numel() for parameter in model.parameters()),
        "measured_steps": args.measured_steps,
        "seconds_per_step": elapsed / args.measured_steps,
        "events_per_second": args.batch_size * args.measured_steps / elapsed,
        "peak_allocated_bytes": int(torch.cuda.max_memory_allocated(device)),
        "peak_reserved_bytes": int(torch.cuda.max_memory_reserved(device)),
        "device": torch.cuda.get_device_name(device),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
