"""Train measured SuperNEMO event and tracker baselines on a bounded scope."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from tasks.supernemo_signal_background.plugins.energy_matched_auc import (
    energy_matched_roc,
    weighted_roc,
)

PROCESSES = ("0nubb", "2nubb", "Bi214", "Tl208")
FILES = {
    "0nubb": "data_0nubb_merged.h5",
    "2nubb": "data_2nubb_merged.h5",
    "Bi214": "data_Bi214_merged.h5",
    "Tl208": "data_Tl208_merged.h5",
}
LABELS = {"0nubb": 1, "2nubb": 0, "Bi214": 0, "Tl208": 0}
SPLITS = {"train": 0, "validation": 1, "test": 2}
ENERGY_BIN_EDGES_KEV = np.arange(0.0, 3600.0 + 100.0, 100.0)
TRACKER_KEYS = ("tX", "tY", "tZ", "tR")


@dataclass(frozen=True, slots=True)
class Arrays:
    event_features: np.ndarray
    energy_sum: np.ndarray
    labels: np.ndarray
    hits: np.ndarray | None = None
    hit_mask: np.ndarray | None = None


def _bounded_indices(split_values: np.ndarray, split: str, limit: int) -> np.ndarray:
    available = np.flatnonzero(split_values == SPLITS[split])
    return available[: min(limit, available.size)]


def load_event_arrays(index_dir: Path, split: str, per_process: int) -> Arrays:
    features, energies, labels = [], [], []
    for process in PROCESSES:
        with np.load(index_dir / f"{process}_event_index.npz") as index:
            selected = _bounded_indices(index["splits"], split, per_process)
            features.append(index["event_features"][selected])
            energies.append(index["energy_sum"][selected])
            labels.append(np.full(selected.size, LABELS[process], dtype=np.float32))
    return Arrays(
        event_features=np.concatenate(features),
        energy_sum=np.concatenate(energies),
        labels=np.concatenate(labels),
    )


def load_tracker_arrays(
    data_dir: Path,
    index_dir: Path,
    split: str,
    per_process: int,
    max_hits: int,
) -> Arrays:
    event_parts, energy_parts, label_parts, hit_parts, mask_parts = [], [], [], [], []
    for process in PROCESSES:
        with np.load(index_dir / f"{process}_event_index.npz") as index:
            selected = _bounded_indices(index["splits"], split, per_process)
            starts = index["row_starts"][selected]
            counts = index["hit_counts"][selected]
            event_parts.append(index["event_features"][selected])
            energy_parts.append(index["energy_sum"][selected])
        padded = np.zeros((selected.size, max_hits, 5), dtype=np.float32)
        mask = np.zeros((selected.size, max_hits), dtype=bool)
        with h5py.File(data_dir / FILES[process], "r") as handle:
            columns = [
                np.asarray(handle[key], dtype=np.float32) for key in TRACKER_KEYS
            ]
        for event_index, (start, count) in enumerate(zip(starts, counts, strict=True)):
            kept = min(int(count), max_hits)
            values = np.column_stack(
                [column[int(start) : int(start) + kept] for column in columns]
            )
            tr_missing = ~np.isfinite(values[:, 3])
            values[:, 3] = np.nan_to_num(values[:, 3], nan=0.0)
            padded[event_index, :kept, :4] = values
            padded[event_index, :kept, 4] = tr_missing.astype(np.float32)
            mask[event_index, :kept] = True
        hit_parts.append(padded)
        mask_parts.append(mask)
        label_parts.append(np.full(selected.size, LABELS[process], dtype=np.float32))
    return Arrays(
        event_features=np.concatenate(event_parts),
        energy_sum=np.concatenate(energy_parts),
        labels=np.concatenate(label_parts),
        hits=np.concatenate(hit_parts),
        hit_mask=np.concatenate(mask_parts),
    )


def standardize(
    train: Arrays, validation: Arrays
) -> tuple[Arrays, Arrays, dict[str, list[float]]]:
    event_mean = train.event_features.mean(axis=0)
    event_std = np.maximum(train.event_features.std(axis=0), 1e-6)
    stats: dict[str, list[float]] = {
        "event_mean": event_mean.tolist(),
        "event_std": event_std.tolist(),
    }

    def transformed(
        source: Arrays, hit_mean: np.ndarray | None, hit_std: np.ndarray | None
    ) -> Arrays:
        hits = source.hits
        if hits is not None and hit_mean is not None and hit_std is not None:
            hits = hits.copy()
            hits[..., :4] = (hits[..., :4] - hit_mean) / hit_std
            hits[~source.hit_mask, :4] = 0.0
        return Arrays(
            event_features=(source.event_features - event_mean) / event_std,
            energy_sum=source.energy_sum,
            labels=source.labels,
            hits=hits,
            hit_mask=source.hit_mask,
        )

    hit_mean = hit_std = None
    if train.hits is not None and train.hit_mask is not None:
        active = train.hit_mask
        hit_mean = train.hits[..., :4][active].mean(axis=0)
        hit_std = np.maximum(train.hits[..., :4][active].std(axis=0), 1e-6)
        stats["hit_mean"] = hit_mean.tolist()
        stats["hit_std"] = hit_std.tolist()
    return (
        transformed(train, hit_mean, hit_std),
        transformed(validation, hit_mean, hit_std),
        stats,
    )


class Mlp(nn.Module):
    def __init__(self, width: int, depth: int) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        size = 5
        for _ in range(depth):
            layers.extend((nn.Linear(size, width), nn.GELU()))
            size = width
        layers.append(nn.Linear(size, 1))
        self.network = nn.Sequential(*layers)

    def forward(
        self, event: torch.Tensor, hits: torch.Tensor, mask: torch.Tensor
    ) -> torch.Tensor:
        del hits, mask
        return self.network(event).squeeze(-1)


class ResidualPointBlock(nn.Module):
    def __init__(self, width: int) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv1d(width, width, 1), nn.GELU(), nn.Conv1d(width, width, 1)
        )
        self.activation = nn.GELU()

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.activation(values + self.layers(values))


class TrackerNetwork(nn.Module):
    def __init__(self, width: int, depth: int, residual: bool) -> None:
        super().__init__()
        self.input = nn.Sequential(nn.Conv1d(5, width, 1), nn.GELU())
        blocks: list[nn.Module] = []
        for _ in range(depth):
            blocks.append(
                ResidualPointBlock(width)
                if residual
                else nn.Sequential(nn.Conv1d(width, width, 1), nn.GELU())
            )
        self.blocks = nn.Sequential(*blocks)
        self.head = nn.Sequential(
            nn.Linear(width + 5, width), nn.GELU(), nn.Linear(width, 1)
        )

    def forward(
        self, event: torch.Tensor, hits: torch.Tensor, mask: torch.Tensor
    ) -> torch.Tensor:
        values = self.blocks(self.input(hits.transpose(1, 2)))
        values = values.masked_fill(~mask[:, None, :], -torch.inf)
        pooled = values.amax(dim=2)
        return self.head(torch.cat((event, pooled), dim=1)).squeeze(-1)


def make_loader(arrays: Arrays, batch_size: int, shuffle: bool) -> DataLoader:
    count = arrays.labels.size
    hits = (
        arrays.hits if arrays.hits is not None else np.zeros((count, 1, 1), np.float32)
    )
    mask = arrays.hit_mask if arrays.hit_mask is not None else np.ones((count, 1), bool)
    dataset = TensorDataset(
        torch.from_numpy(arrays.event_features.astype(np.float32)),
        torch.from_numpy(hits),
        torch.from_numpy(mask),
        torch.from_numpy(arrays.labels),
    )
    return DataLoader(
        dataset, batch_size=batch_size, shuffle=shuffle, num_workers=0, pin_memory=True
    )


@torch.inference_mode()
def evaluate(
    model: nn.Module, loader: DataLoader, loss: nn.Module, device: torch.device
) -> tuple[float, np.ndarray]:
    model.eval()
    total_loss = 0.0
    scores = []
    for event, hits, mask, labels in loader:
        event, hits, mask, labels = (
            item.to(device, non_blocking=True) for item in (event, hits, mask, labels)
        )
        logits = model(event, hits, mask)
        total_loss += float(loss(logits, labels)) * labels.numel()
        scores.append(torch.sigmoid(logits).cpu().numpy())
    return total_loss / len(loader.dataset), np.concatenate(scores)


def plot_results(
    output_dir: Path, history: list[dict[str, float]], matched, ordinary
) -> None:
    epochs = [entry["epoch"] for entry in history]
    plt.figure(figsize=(6, 4))
    plt.plot(epochs, [entry["train_loss"] for entry in history], label="training")
    plt.plot(
        epochs, [entry["validation_loss"] for entry in history], label="validation"
    )
    plt.xlabel("Epoch")
    plt.ylabel("BCE loss")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "loss_curve.png", dpi=180)
    plt.close()
    plt.figure(figsize=(5, 5))
    plt.plot(
        matched.false_positive_rate,
        matched.true_positive_rate,
        label=f"Energy-matched AUC={matched.auc:.4f}",
    )
    plt.plot(
        ordinary[0], ordinary[1], label=f"Ordinary AUC={ordinary[3]:.4f}", alpha=0.8
    )
    plt.plot([0, 1], [0, 1], "--", color="grey")
    plt.xlabel("False-positive rate")
    plt.ylabel("True-positive rate")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "roc_curve.png", dpi=180)
    plt.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--index-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--architecture", choices=("mlp", "cnn", "resnet"), required=True
    )
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--depth", type=int, required=True)
    parser.add_argument("--train-per-process", type=int, required=True)
    parser.add_argument("--validation-per-process", type=int, required=True)
    parser.add_argument("--batch-size", type=int, required=True)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--max-hits", type=int, default=224)
    parser.add_argument("--seed", type=int, default=20260901)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda")
    load_started = time.perf_counter()
    loader = load_event_arrays if args.architecture == "mlp" else load_tracker_arrays
    if args.architecture == "mlp":
        train = loader(args.index_dir, "train", args.train_per_process)
        validation = loader(args.index_dir, "validation", args.validation_per_process)
    else:
        train = loader(
            args.data_dir,
            args.index_dir,
            "train",
            args.train_per_process,
            args.max_hits,
        )
        validation = loader(
            args.data_dir,
            args.index_dir,
            "validation",
            args.validation_per_process,
            args.max_hits,
        )
    train, validation, normalization = standardize(train, validation)
    data_seconds = time.perf_counter() - load_started
    train_loader = make_loader(train, args.batch_size, True)
    validation_loader = make_loader(validation, args.batch_size, False)
    model = (
        Mlp(args.width, args.depth)
        if args.architecture == "mlp"
        else TrackerNetwork(args.width, args.depth, args.architecture == "resnet")
    )
    model.to(device)
    parameters = sum(parameter.numel() for parameter in model.parameters())
    positives = float(train.labels.sum())
    negatives = float(train.labels.size - positives)
    loss = nn.BCEWithLogitsLoss(
        pos_weight=torch.tensor(negatives / positives, device=device)
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    history = []
    torch.cuda.reset_peak_memory_stats(device)
    train_started = time.perf_counter()
    for epoch in range(1, args.epochs + 1):
        model.train()
        total = 0.0
        for event, hits, mask, labels in train_loader:
            event, hits, mask, labels = (
                item.to(device, non_blocking=True)
                for item in (event, hits, mask, labels)
            )
            optimizer.zero_grad(set_to_none=True)
            batch_loss = loss(model(event, hits, mask), labels)
            batch_loss.backward()
            optimizer.step()
            total += float(batch_loss.detach()) * labels.numel()
        validation_loss, scores = evaluate(model, validation_loader, loss, device)
        history.append(
            {
                "epoch": epoch,
                "train_loss": total / len(train_loader.dataset),
                "validation_loss": validation_loss,
            }
        )
    torch.cuda.synchronize(device)
    train_seconds = time.perf_counter() - train_started
    matched = energy_matched_roc(
        validation.labels, scores, validation.energy_sum, ENERGY_BIN_EDGES_KEV
    )
    ordinary = weighted_roc(validation.labels, scores, np.ones(validation.labels.size))
    report = {
        "configuration": vars(args)
        | {
            "data_dir": str(args.data_dir),
            "index_dir": str(args.index_dir),
            "output_dir": str(args.output_dir),
        },
        "energy_bin_edges_kev": ENERGY_BIN_EDGES_KEV.tolist(),
        "parameters": parameters,
        "train_events": int(train.labels.size),
        "validation_events": int(validation.labels.size),
        "data_seconds": data_seconds,
        "training_seconds": train_seconds,
        "events_per_training_second": args.epochs * train.labels.size / train_seconds,
        "peak_vram_bytes": int(torch.cuda.max_memory_allocated(device)),
        "energy_matched_auc": matched.auc,
        "ordinary_auc": ordinary[3],
        "matching": {
            key: value
            for key, value in asdict(matched).items()
            if not isinstance(value, np.ndarray)
        },
        "normalization": normalization,
        "history": history,
    }
    (args.output_dir / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    np.savez_compressed(
        args.output_dir / "roc_data.npz",
        matched_fpr=matched.false_positive_rate,
        matched_tpr=matched.true_positive_rate,
        ordinary_fpr=ordinary[0],
        ordinary_tpr=ordinary[1],
    )
    plot_results(args.output_dir, history, matched, ordinary)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
