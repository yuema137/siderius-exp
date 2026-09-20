"""Capture source selected by a target-free native probe within readable roots.

Probe results are untrusted locators. Reuse native input's descriptor-based
bounded read; never import source in the private coordinator. Package callers
supply the declared dependency set, not a guessed recursive directory scan.
"""

import hashlib
from collections.abc import Sequence
from pathlib import Path

from core.local_code import CodePackageDeclaration

from experiments.shared.native_training_inputs import _read_allowed_input
from experiments.shared.objective_code_package import ObjectiveCodePackage


def capture_selected_source(
    path: Path,
    *,
    expected_sha256: str,
    allowed_roots: Sequence[Path],
    source_cwd: Path,
    max_bytes: int = 1048576,
) -> str:
    roots = tuple(root.resolve(strict=True) for root in allowed_roots)
    absolute = path if path.is_absolute() else source_cwd / path
    payload = _read_allowed_input(absolute, roots, max_bytes=max_bytes)
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ValueError("native-selected source changed before capture")
    return payload.decode("utf-8")


def capture_selected_objective_package(
    declaration: CodePackageDeclaration,
    *,
    selected_path: Path,
    selected_sha256: str,
    allowed_roots: Sequence[Path],
    source_cwd: Path,
) -> ObjectiveCodePackage:
    """Read only explicitly declared members from authorized source roots."""
    roots = tuple(root.resolve(strict=True) for root in allowed_roots)
    root = Path(declaration.root)
    root = root if root.is_absolute() else source_cwd / root
    selected = (
        selected_path if selected_path.is_absolute() else source_cwd / selected_path
    )
    names = {root / name: name for name in declaration.files}
    if selected not in names:
        raise ValueError("native-selected loss is absent from declared package")
    sources = {}
    remaining = 1048576
    for name in declaration.files:
        payload = _read_allowed_input(root / name, roots, max_bytes=remaining)
        remaining -= len(payload)
        sources[name] = payload.decode("utf-8")
    entrypoint = names[selected]
    if hashlib.sha256(sources[entrypoint].encode()).hexdigest() != selected_sha256:
        raise ValueError("native-selected loss changed before package capture")
    return ObjectiveCodePackage(entrypoint=entrypoint, sources=sources)


def capture_native_code_transport(
    manifest: Path,
    *,
    manifest_sha256: str,
    allowed_roots: Sequence[Path],
    source_cwd: Path,
):
    """Capture an inherited finite package with the framework's transport schema.

    Validate every member through bounded descriptor reads rather than letting
    an untrusted transport direct privileged path reads. No source executes.
    """
    from core.local_code import CapturedCodePackage
    from core.local_code.capture import CapturedMember
    from core.local_code.transport import CodeTransport

    transport = CodeTransport.model_validate_json(
        capture_selected_source(
            manifest,
            expected_sha256=manifest_sha256,
            allowed_roots=allowed_roots,
            source_cwd=source_cwd,
        )
    )
    roots = tuple(root.resolve(strict=True) for root in allowed_roots)
    members = []
    remaining = 4194304
    for pin in transport.identity.members:
        payload = _read_allowed_input(
            transport.root / pin.member, roots, max_bytes=remaining
        )
        remaining -= len(payload)
        if hashlib.sha256(payload).hexdigest() != pin.content_sha256:
            raise ValueError("native package member changed since parent binding")
        members.append(CapturedMember(pin=pin, source=payload))
    return CapturedCodePackage(
        root=transport.root, locator_root=transport.locator_root, members=tuple(members)
    )
