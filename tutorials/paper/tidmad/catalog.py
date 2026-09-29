"""Inspect channel 2 to propose a frequency catalog; never infer it from filenames."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

import h5py
import numpy as np

from experiments.tidmad.main_fixed_workflow.band_inputs import verify_band_inputs
from tasks.tidmad.runtime.frequency_split import FrequencyCatalog, FrequencyRow
from tutorials.paper.runner import ROOT


def identify_frequency(samples: np.ndarray, sampling_hz: float = 10_000_000) -> int:
    """Require a stable dominant tone in ten subwindows, then label its 1 Hz bin.

    This is an inspection aid for the released injected sinusoid, not a general
    multi-tone detector. Ambiguous/changing segments stop preparation for review.
    """
    if (
        samples.ndim != 1
        or len(samples) != 10_000_000
        or not np.isfinite(samples).all()
    ):
        raise ValueError("expected one complete, finite, one-second PSD segment")

    def peak(part):
        power = np.abs(np.fft.rfft(part.astype(np.float64) - part.mean())) ** 2
        power[0] = 0
        index = int(power.argmax())
        if not power[index] > 0 or power[index] / power.sum() < 0.8:
            raise ValueError("no unambiguous dominant injected tone; inspect channel 2")
        return index * sampling_hz / len(part)

    frequency = peak(samples)
    if any(abs(peak(part) - frequency) > 10 for part in np.array_split(samples, 10)):
        raise ValueError(
            "injected frequency changes inside this segment; do not guess a split"
        )
    return round(frequency)


def build_catalog(data: Path) -> FrequencyCatalog:
    evidence = verify_band_inputs(ROOT, data, "0-3")
    reference = (
        ROOT / "tasks/tidmad/reference_data/tidmad_signal_frequencies.txt"
    ).read_text()
    match = re.search(r"freq\s*\[([^\]]+)\]", reference, re.DOTALL)
    if match is None:
        raise ValueError("nominal injected-frequency reference is missing")
    nominal = np.unique(np.fromstring(match.group(1), sep=" ").astype(int))
    rows = []
    for family in ("training", "validation"):
        for index in range(4):
            name = f"abra_{family}_{index:04d}.h5"
            print(f"Inspecting {name}", flush=True)
            with h5py.File(data / name, "r") as stream:
                channel = stream["timeseries/channel0002"]
                hz = float(
                    channel.attrs.get(
                        "sampling_frequency",
                        stream["timeseries/channel0001"].attrs["sampling_frequency"],
                    )
                )
                if hz != 10_000_000:
                    raise ValueError("expected the released 10 MHz source")
                for segment in range(200):
                    samples = channel["timeseries"][
                        segment * 10_000_000 : (segment + 1) * 10_000_000
                    ]
                    try:
                        frequency = identify_frequency(samples, hz)
                    except ValueError as exc:
                        raise ValueError(f"{name}, segment {segment}: {exc}") from exc
                    nearest = int(nominal[np.argmin(np.abs(nominal - frequency))])
                    if abs(nearest - frequency) > 10:
                        raise ValueError(
                            f"{name}, segment {segment}: observed {frequency} Hz is not within 10 Hz of a declared nominal tone"
                        )
                    rows.append(
                        FrequencyRow(
                            family=family,
                            file=index,
                            segment=segment,
                            frequency_hz=nearest,
                            observed_peak_hz=frequency,
                        )
                    )
    # Detect a data change during scanning as well as before it.
    for name, digest in evidence["file_sha256"].items():
        with (data / name).open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                raise ValueError("source changed during catalog inspection")
    return FrequencyCatalog(source_sha256=evidence["file_sha256"], rows=tuple(rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve().is_relative_to(ROOT):
        raise ValueError("choose a fresh external catalog path")
    catalog = build_catalog(args.data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write(catalog.model_dump_json(indent=2))
    print(
        "Catalog proposed. Review channel-2 frequency assignments before using a scientific holdout."
    )


if __name__ == "__main__":
    main()
