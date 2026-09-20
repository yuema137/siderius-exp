"""Launch code is captured bytes, never live research paths or executed imports."""

import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from core.local_code import CodePackageDeclaration, capture_package

from experiments.shared.validation_code_snapshot import stage_validation_code


def test_parallel_staging_keeps_original_code_and_relative_package_identity(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "plugin.py").write_text(
        "from .helper import value\nraise AssertionError('must not import')\n"
    )
    (source / "helper.py").write_text("value = 2\n")
    package = capture_package(
        CodePackageDeclaration(root=".", files=("plugin.py", "helper.py")), source
    )
    # Research source may change after capture; it must not change staged bytes.
    (source / "helper.py").write_text("value = 999\n")
    parent = tmp_path / "protected"
    parent.mkdir(mode=0o700)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: stage_validation_code(
                    package, parent=parent, owner_uid=os.getuid()
                ),
                range(2),
            )
        )
    assert results[0].root != results[1].root
    for result in results:
        assert result.identity == package.identity
        assert (result.root / "helper.py").read_text() == "value = 2\n"
        assert result.root.stat().st_mode & 0o777 == 0o555
        assert (result.root / "plugin.py").stat().st_mode & 0o222 == 0


def test_inconsistent_capture_is_removed_instead_of_published(tmp_path):
    (tmp_path / "source.py").write_text("value=1\n")
    package = capture_package(
        CodePackageDeclaration(root=".", files=("source.py",)), tmp_path
    )
    package.members[0].__dict__["source"] = b"value=999\n"
    parent = tmp_path / "protected"
    parent.mkdir(mode=0o700)
    with pytest.raises(ValueError, match="differs from captured"):
        stage_validation_code(package, parent=parent, owner_uid=os.getuid())
    assert list(parent.iterdir()) == []


@pytest.mark.parametrize("fault", [None, "constructor", "path", "bytes"])
def test_discovery_is_bound_to_captured_member_without_importing_or_opening_probe_path(
    tmp_path, monkeypatch, fault
):
    import hashlib
    from pathlib import Path

    from experiments.shared.native_model_discovery import NativeModelSelection
    from experiments.shared.validation_code_snapshot import bind_discovered_model_source

    source = "raise AssertionError('coordinator must not import')\n"
    (tmp_path / "model.py").write_text(source)
    captured = capture_package(
        CodePackageDeclaration(root=".", files=("model.py",)), tmp_path
    )
    parent = tmp_path / "protected"
    parent.mkdir(mode=0o700)
    staged = stage_validation_code(captured, parent=parent, owner_uid=os.getuid())
    selected = NativeModelSelection(
        model_type="fixture",
        constructor_sha256="c" * 64 if fault == "constructor" else "a" * 64,
        source_sha256="d" * 64
        if fault == "bytes"
        else hashlib.sha256(source.encode()).hexdigest(),
        plugin_path=tmp_path / "private.py"
        if fault == "path"
        else staged.root / "model.py",
    )
    monkeypatch.setattr(
        Path, "open", lambda *a, **k: pytest.fail("opened a probe-selected path")
    )
    if fault:
        with pytest.raises(ValueError, match="differs"):
            bind_discovered_model_source(
                selected,
                package=staged,
                constructor_sha256="a" * 64,
                builtin_source_sha256="b" * 64,
            )
    else:
        bound = bind_discovered_model_source(
            selected,
            package=staged,
            constructor_sha256="a" * 64,
            builtin_source_sha256="b" * 64,
        )
        assert bound.plugin_package.root == staged.root
        assert bound.plugin_package.identity.member == "model.py"
        assert bound.plugin_package.identity.package == staged.identity
