"""Bounded external declarations and custom-loss semantic witnesses."""

from __future__ import annotations

import hashlib
from pathlib import Path

import torch
import yaml
from agent.schemas.custom_loss_contract import (
    custom_loss_snapshot_from_forward_contract,
    validate_synthetic_loss_pair,
)
from agent.schemas.task_config import ForwardContract
from pytest import approx

from tasks.cancer_gene_identification.plugins._cancer_gene_task import (
    CancerGeneTaskDataPath,
)
from tasks.cancer_gene_identification.plugins.cancer_gene_masked_bce import (
    PLUGIN_CAPABILITY_CONTRACT as CANCER_CONTRACT,
)
from tasks.cancer_gene_identification.plugins.cancer_gene_masked_bce import (
    CancerGeneMaskedBce,
    CancerGeneMaskedBceConfig,
)
from tasks.davis_future_prediction.plugins.davis_exact_l1_loss import (
    PLUGIN_CAPABILITY_CONTRACT as DAVIS_CONTRACT,
)
from tasks.davis_future_prediction.plugins.davis_exact_l1_loss import (
    PluginLoss,
    PluginLossConfig,
)
from tasks.davis_future_prediction.runtime.davis_data_path import DavisTaskDataPath

ROOT = Path(__file__).resolve().parents[2]


def _config(name: str) -> dict:
    return yaml.safe_load(
        (ROOT / "tasks" / name / "declared" / "task_config.yaml").read_text()
    )


def test_all_task_probe_applicability_is_explicit() -> None:
    expected = {
        "tidmad": "temporal",
        "oxford_iiit_pet": "not_applicable",
        "davis_future_prediction": "not_applicable",
        "cancer_gene_identification": "not_applicable",
        "supernemo_signal_background": "not_applicable",
        "majorana_low_avse": "not_applicable",
    }
    assert {
        name: _config(name)["forward_contract"]["segmentation_applicability"]
        for name in expected
    } == expected


def test_davis_provider_matches_and_invokes_exact_l1() -> None:
    prediction, target = DavisTaskDataPath.custom_loss_validation_pair()
    assert DavisTaskDataPath.custom_loss_validation_pair()[0].equal(prediction)
    assert prediction.shape == target.shape == (1, 3, 4, 128, 224)
    assert prediction.dtype == target.dtype == torch.float32
    prediction = prediction.requires_grad_()
    loss = PluginLoss(PluginLossConfig())(prediction, target)
    assert loss.item() == approx(0.5, abs=1e-6)
    loss.backward()
    assert torch.isfinite(prediction.grad).all()


def test_cancer_provider_preserves_labeled_mask_and_invokes_bce() -> None:
    prediction, target = CancerGeneTaskDataPath.custom_loss_validation_pair()
    assert CancerGeneTaskDataPath.custom_loss_validation_pair()[0].equal(prediction)
    assert prediction.shape == target.shape == (1, 2, 3)
    assert prediction.dtype == target.dtype == torch.float32
    assert torch.equal(
        (target[..., 0] > 0.5) & (target[..., 1] > 0.5) & (target[..., 2] >= 0),
        torch.tensor([[True, False]]),
    )
    prediction = prediction.requires_grad_()
    loss = CancerGeneMaskedBce(CancerGeneMaskedBceConfig())(prediction, target)
    assert torch.isfinite(loss)
    loss.backward()
    assert torch.isfinite(prediction.grad).all()


def test_tidmad_scientific_assets_remain_byte_pinned() -> None:
    expected = {
        "tasks/tidmad/reference_data/segment_anchors.json": "0c44b6084dc8afc4dc2fa34f5253bc8d780b4e8ae086945e7051d8bf7928ba90",
        "campaigns/tidmad_gold/fcnet_band_references.json": "f15ed7a5995dc86678a991ac26b76212361038d58d2cea96205a216f74f6d5a5",
        "campaigns/tidmad_gold/gold_advice_v6_regression.json": "e621e1a5aa7ee87eab6978cb125a6e1b4aa944669a4761cccac908175ad23eae",
    }
    assert {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for path in expected
    } == expected


def test_custom_loss_contracts_and_pairs_match_infra_authority() -> None:
    for name, plugin_contract, provider in (
        ("davis_future_prediction", DAVIS_CONTRACT, DavisTaskDataPath),
        ("cancer_gene_identification", CANCER_CONTRACT, CancerGeneTaskDataPath),
    ):
        forward_contract = ForwardContract.model_validate(
            _config(name)["forward_contract"]
        )
        expected = custom_loss_snapshot_from_forward_contract(forward_contract)
        assert expected is not None
        assert plugin_contract == expected.model_dump(mode="json")
        validate_synthetic_loss_pair(
            provider.custom_loss_validation_pair(),
            forward_contract.model_io.output,
            forward_contract.supervision_target,
            applicability=forward_contract.custom_loss_applicability,
        )
