"""Finite source transport refuses unrelated or missing package material."""

import pytest

from experiments.shared.native_objective_metadata import ObjectiveMetadataRequest
from experiments.shared.objective_code_package import ObjectiveCodePackage
from experiments.shared.objective_purpose_review import ObjectiveReviewMaterial
from experiments.shared.objective_source_check import inspect_objective_source


@pytest.mark.parametrize("name", ["../loss.py", "/loss.py", "a/../../loss.py"])
def test_package_cannot_write_outside_staging_root(name):
    with pytest.raises(ValueError):
        ObjectiveCodePackage(entrypoint=name, sources={name: "pass"})


def test_entry_source_must_match_package():
    package = ObjectiveCodePackage(entrypoint="loss.py", sources={"loss.py": "pass"})
    with pytest.raises(ValueError, match="entrypoint"):
        ObjectiveMetadataRequest(
            source="raise Exception()", loss_name="x", code_package=package
        )
    changed = package.model_copy(update={"sources": {"loss.py": "pass\n"}})
    assert changed.sha256 != package.sha256


@pytest.mark.parametrize("provided", [False, True])
def test_relative_helper_must_be_reviewed(provided):
    sources = {"loss.py": "from .helper import error"}
    if provided:
        sources["helper.py"] = "def error(p,t): return ((p-t)**2).mean()"
    material = ObjectiveReviewMaterial(
        sources=sources, effective_parameters={}, dependency_declaration="fixture"
    )
    result = inspect_objective_source(material, allowed_import_roots=frozenset())
    assert result.passed == provided


def test_dependency_effects_are_checked_even_when_entry_is_clean():
    material = ObjectiveReviewMaterial(
        sources={
            "loss.py": "from .helper import error",
            "helper.py": "import os\ndef error(p,t): return os.system('x')",
        },
        effective_parameters={},
        dependency_declaration="fixture",
    )
    result = inspect_objective_source(material, allowed_import_roots=frozenset())
    assert not result.passed
    assert all(item.file == "helper.py" for item in result.findings)
