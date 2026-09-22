"""Verify an optional operator-owned instruction artifact before each invocation."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class PromptSupplement:
    """A short immutable advice artifact, relative to its protected manifest."""

    artifact: str
    sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.artifact, str) or not self.artifact:
            raise ValueError("supplement artifact must be a nonempty string")
        if Path(self.artifact).is_absolute() or ".." in Path(self.artifact).parts:
            raise ValueError("supplement artifact must be relative to its manifest")
        if not isinstance(self.sha256, str) or not re.fullmatch(
            r"[0-9a-f]{64}", self.sha256
        ):
            raise ValueError(
                "supplement SHA-256 must contain 64 lowercase hexadecimal characters"
            )

    @classmethod
    def from_json(cls, data: bytes) -> PromptSupplement:
        payload = json.loads(data)
        if not isinstance(payload, dict) or set(payload) != {"artifact", "sha256"}:
            raise ValueError("supplement manifest requires exactly artifact and sha256")
        return cls(artifact=payload["artifact"], sha256=payload["sha256"])

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2) + "\n"


def append_verified_supplement(prompt: bytes, manifest: Path | None) -> bytes:
    """Keep baseline bytes unchanged unless an explicit supplement is selected.

    The operator must protect the manifest and artifact from the research UID.
    This verifies delivery on process entry, not model compliance or automatic
    reinjection during a CLI's internal context compaction.
    """
    if manifest is None:
        return prompt
    manifest = manifest.absolute()
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError("prompt supplement manifest must be a regular file")
    declaration = PromptSupplement.from_json(manifest.read_bytes())
    artifact = manifest.parent / declaration.artifact
    if (
        artifact.is_symlink()
        or not artifact.resolve().is_relative_to(manifest.parent.resolve())
        or not artifact.is_file()
    ):
        raise ValueError("prompt supplement artifact must be a confined regular file")
    if not 0 < artifact.stat().st_size <= 65536:
        raise ValueError("prompt supplement must contain 1 to 65536 bytes")
    content = artifact.read_bytes()
    if hashlib.sha256(content).hexdigest() != declaration.sha256:
        raise ValueError("prompt supplement checksum mismatch")
    text = content.decode("utf-8")
    if not text.strip():
        raise ValueError("prompt supplement is empty")
    header = (
        "\n\n# Operator-declared controller advice\n"
        f"Source: {artifact.resolve()}\nSHA-256: {declaration.sha256}\n"
        "The verified text below is supplied at every new outer invocation. "
        "Keep its absolute path in continuation summaries. After context recovery, "
        "reopen the run declaration and this advice before continuing. "
        "It grants no additional capabilities, data access or budget.\n\n"
    )
    return prompt + header.encode("utf-8") + content
