"""Stage already captured native Python code under a protected launch directory.

Uses the framework's finite package capture and identity contract. Never import
candidate code here. The operator supplies a protected parent, captures source
before review, and binds both training and validation to the returned package.
"""

import os
import shutil
import stat
import tempfile
from pathlib import Path

from core.local_code import CapturedCodePackage, CodePackageDeclaration, capture_package

from experiments.shared.epoch_model_worker import EpochModelSource
from experiments.shared.native_loss_discovery import NativeLossSelection
from experiments.shared.native_model_discovery import NativeModelSelection
from experiments.shared.objective_code_package import ObjectiveCodePackage


def stage_validation_code(
    package: CapturedCodePackage, *, parent: Path, owner_uid: int
) -> CapturedCodePackage:
    """Copy captured bytes once; do not reopen mutable research source paths.

    Each invocation gets its own directory, so parallel jobs cannot overwrite
    each other's capture. Sources are readable but not writable by worker UIDs;
    the enclosing operator parent remains private. The launcher mounts only the
    selected staged directory read-only into the training/validation workers.
    This creates code identity, not evidence that any model was trained.
    """
    info = parent.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != owner_uid
        or info.st_mode & 0o022
        or os.geteuid() != owner_uid
    ):
        raise PermissionError("code snapshot parent must be operator-owned")
    declaration = CodePackageDeclaration(
        root=".", files=tuple(member.pin.member for member in package.members)
    )
    root = Path(tempfile.mkdtemp(prefix="native-code-", dir=parent))
    try:
        for member in package.members:
            target = root / member.pin.member
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(member.source)
            target.chmod(0o444)
        captured = capture_package(declaration, root)
        if captured.identity != package.identity:
            raise ValueError("staged code differs from captured native source")
        # Traverse while directories are still owner-writable for failure cleanup.
        directories = [path for path in root.rglob("*") if path.is_dir()]
        for directory in directories:
            directory.chmod(0o555)
        root.chmod(0o555)
        return captured
    except BaseException:
        for directory in [root, *root.rglob("*")]:
            if directory.is_dir():
                directory.chmod(0o700)
        shutil.rmtree(root)
        raise


def bind_discovered_model_source(
    selection: NativeModelSelection,
    *,
    package: CapturedCodePackage | None,
    constructor_sha256: str,
    builtin_source_sha256: str,
) -> EpochModelSource:
    """Match isolated discovery to operator-pinned bytes, without candidate import.

    Never open a path merely because the probe returned it. Plugin selection
    must name a member of this already-staged capture. Builtin identity comes
    from the operator's installed framework source, not from the probe itself.
    """
    from core.local_code import MemberIdentity

    from experiments.shared.epoch_model_worker import StagedModelPackage

    if selection.constructor_sha256 != constructor_sha256:
        raise ValueError("discovered constructor differs from installed runtime")
    if selection.plugin_path is None:
        if selection.source_sha256 != builtin_source_sha256:
            raise ValueError("discovered builtin differs from installed runtime")
        return EpochModelSource(
            model_type=selection.model_type,
            constructor_sha256=constructor_sha256,
            source_sha256=builtin_source_sha256,
        )
    if package is None:
        raise ValueError("discovered plugin has no operator code capture")
    member = next(
        (
            item
            for item in package.members
            if package.root / item.pin.member == selection.plugin_path
        ),
        None,
    )
    if member is None or member.pin.content_sha256 != selection.source_sha256:
        raise ValueError("discovered plugin differs from operator code capture")
    return EpochModelSource(
        model_type=selection.model_type,
        constructor_sha256=constructor_sha256,
        source_sha256=member.pin.content_sha256,
        plugin_package=StagedModelPackage(
            root=package.root,
            identity=MemberIdentity(package=package.identity, member=member.pin.member),
        ),
    )


def bind_discovered_loss_package(
    selection: NativeLossSelection, *, package: CapturedCodePackage, loss_name: str
) -> ObjectiveCodePackage:
    """Bind observed native selection to captured bytes without path reads/imports."""
    if selection.loss_name != loss_name:
        raise ValueError("native loss selection differs from requested configuration")
    member = next(
        (
            item
            for item in package.members
            if package.root / item.pin.member == selection.plugin_path
        ),
        None,
    )
    if member is None or member.pin.content_sha256 != selection.source_sha256:
        raise ValueError("native loss selection differs from captured package")
    return ObjectiveCodePackage(
        entrypoint=member.pin.member,
        sources={item.pin.member: item.source.decode() for item in package.members},
    )
