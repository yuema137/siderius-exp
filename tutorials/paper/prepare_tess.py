"""Download two pinned public TESS splits and call the task's staging authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from tasks.phyts_tess.tools.stage_data import main as stage
from tutorials.paper.runner import ROOT, disjoint


class TessSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset: str
    revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    files: dict[str, str]


def download_file(url: str, destination: Path, sha256: str) -> None:
    """Verify downloaded bytes before publishing; do not replace existing inputs."""
    temporary = destination.with_suffix(destination.suffix + ".partial")
    try:
        with (
            urllib.request.urlopen(url, timeout=60) as source,
            temporary.open("xb") as target,
        ):
            shutil.copyfileobj(source, target)
        with temporary.open("rb") as stream:
            observed = hashlib.file_digest(stream, "sha256").hexdigest()
        if observed != sha256:
            raise ValueError(f"download checksum mismatch: {destination.name}")
        temporary.rename(destination)
    finally:
        temporary.unlink(missing_ok=True)


def prepare(raw: Path, data: Path) -> None:
    """Prepare a new external data root with no test split or scientific re-splitting."""
    raw, data = raw.resolve(), data.resolve()
    if not disjoint(raw, ROOT) or not disjoint(data, ROOT) or not disjoint(raw, data):
        raise ValueError(
            "raw/data directories must be separate and outside the exp checkout"
        )
    if raw.exists() or data.exists():
        raise ValueError(
            "raw and data destinations must be new; existing files are never replaced"
        )
    source = TessSource.model_validate_json(
        (Path(__file__).parent / "configs/tess_source.json").read_text()
    )
    raw.mkdir(parents=True)
    for relative, digest in source.files.items():
        url = f"https://huggingface.co/datasets/{source.dataset}/resolve/{source.revision}/{relative}"
        download_file(url, raw / Path(relative).name, digest)
    stage(["--source", str(raw), "--data_dir", str(data)])
    # Keep source provenance next to raw input, not in the exact two-file run view.
    (raw / "download_receipt.json").write_text(
        json.dumps(source.model_dump(), indent=2)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--data-dir", required=True, type=Path)
    args = parser.parse_args()
    prepare(args.raw_dir, args.data_dir)


if __name__ == "__main__":
    main()
