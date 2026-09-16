from pathlib import Path

from experiments.shared.information_treatment import (
    AdviceMode,
    ModuleState,
    resolve_information_treatment,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TREATMENTS = REPOSITORY_ROOT / "experiments/tidmad/information_treatments"


def _resolve(name: str, adapter: str):
    return resolve_information_treatment(
        TREATMENTS / name,
        repository_root=REPOSITORY_ROOT,
        adapter=adapter,
        required_modules=("literature_review",),
    )


def test_tidmad_advice_on_and_off_share_one_task_package():
    enabled = _resolve("prerelease-with-advice.yaml", "siderius")
    disabled = _resolve("prerelease-without-advice.yaml", "coding_agent")

    assert enabled.task_package_path == disabled.task_package_path
    assert enabled.task_package_path == REPOSITORY_ROOT / "tasks/tidmad"
    assert enabled.declaration.advice.mode is AdviceMode.ENABLED
    assert disabled.declaration.advice.mode is AdviceMode.DISABLED


def test_tidmad_advice_identity_and_module_treatment_are_explicit():
    enabled = _resolve("prerelease-with-advice.yaml", "siderius")
    disabled = _resolve("prerelease-without-advice.yaml", "coding_agent")

    assert enabled.advice_path == (
        REPOSITORY_ROOT / "experiments/tidmad/prerelease-tidmad-proof-of-function/advice.json"
    )
    assert enabled.module_states == {"literature_review": ModuleState.DISABLED}
    assert disabled.advice_path is None
    assert disabled.module_states == {"literature_review": ModuleState.NOT_APPLICABLE}
