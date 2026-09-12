"""Bounded counterfactual receipts for the H100 production-shell census."""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def posture_module():
    return importlib.import_module("tests.campaigns.tidmad_x9.test_h100_posture")


def test_production_shell_census_discovers_chain_flag(posture_module) -> None:
    # This is a shell-only discovery: the flag is read from _chain_common's
    # case parser, not invented by the Python posture census.
    accepted = posture_module._chain_parser_flags()
    assert "--data_scope" in accepted


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
