"""A probe cannot authorize reads outside captured research/public roots."""

import hashlib

import pytest
from core.local_code import CodePackageDeclaration

from experiments.shared.native_source_capture import (
    capture_selected_objective_package,
    capture_selected_source,
)


def test_capture_matches_selected_bytes_without_importing_them(tmp_path):
    path = tmp_path / "loss.py"
    source = "raise AssertionError('capture must not import')\n"
    path.write_text(source)
    digest = hashlib.sha256(source.encode()).hexdigest()
    assert (
        capture_selected_source(
            path, expected_sha256=digest, allowed_roots=(tmp_path,), source_cwd=tmp_path
        )
        == source
    )
    path.write_text("another revision")
    with pytest.raises(ValueError, match="changed"):
        capture_selected_source(
            path, expected_sha256=digest, allowed_roots=(tmp_path,), source_cwd=tmp_path
        )


def test_probe_path_and_symlink_do_not_grant_private_read(tmp_path):
    public = tmp_path / "public"
    public.mkdir()
    private = tmp_path / "private.py"
    private.write_text("private fixture")
    link = public / "alias.py"
    link.symlink_to(private)
    for path in (private, link):
        with pytest.raises((ValueError, PermissionError, OSError)):
            capture_selected_source(
                path,
                expected_sha256="a" * 64,
                allowed_roots=(public,),
                source_cwd=public,
            )


def test_declared_package_captures_helper_and_ignores_unrelated_files(tmp_path):
    (tmp_path / "loss.py").write_text("from .helper import error")
    (tmp_path / "helper.py").write_text("def error(p,t): return p-t")
    (tmp_path / "unrelated.py").write_text("raise AssertionError()")
    digest = hashlib.sha256((tmp_path / "loss.py").read_bytes()).hexdigest()
    package = capture_selected_objective_package(
        CodePackageDeclaration(root=".", files=("loss.py", "helper.py")),
        selected_path=tmp_path / "loss.py",
        selected_sha256=digest,
        allowed_roots=(tmp_path,),
        source_cwd=tmp_path,
    )
    assert set(package.sources) == {"loss.py", "helper.py"}
    assert package.entrypoint == "loss.py"
