"""Bounded counterfactual receipts for the H100 production-shell census."""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def posture_module():
    return importlib.import_module("tests.campaigns.tidmad_x9.test_h100_posture")


def test_production_shell_census_discovers_shell_only_export(
    posture_module, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    # Exercise the census' shell branch directly.  The token exists only in
    # this temporary shell reader, not in any Python source; a wrong
    # PRODUCTION_SH_ROOT would make this fail.
    launch = tmp_path / "scripts" / "launch"
    launch.mkdir(parents=True)
    (launch / "inert.sh").write_text(
        "#!/bin/sh\nvalue=${SIDERIUS_COUNTERFACTUAL_SHELL_ONLY}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(posture_module, "FRAMEWORK_ROOT", tmp_path)
    names = posture_module._production_string_constants()
    assert "SIDERIUS_COUNTERFACTUAL_SHELL_ONLY" in names


def test_unknown_export_is_refused_by_existing_census(posture_module) -> None:
    with pytest.raises(AssertionError, match="NO production module"):
        posture_module.test_every_exported_name_is_one_production_reads(
            {"exports": {"SIDERIUS_COUNTERFACTUAL_UNKNOWN": "1"}}
        )


def test_unknown_chain_flag_is_refused_by_existing_census(posture_module) -> None:
    with pytest.raises(AssertionError, match="no case label"):
        posture_module.test_every_chain_flag_is_accepted_by_the_chain_parser(
            {"args": ["--counterfactual_unknown_flag", "1"]}
        )
