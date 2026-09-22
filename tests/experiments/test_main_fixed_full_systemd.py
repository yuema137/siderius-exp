"""Full systemd units bind the frozen analysis inputs and matching safeguards."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SYSTEMD = ROOT / "experiments/tidmad/main_fixed_workflow/systemd"


def test_full_service_passes_every_required_full_binding() -> None:
    text = (SYSTEMD / "tidmad-full@.service").read_text()
    assert "EnvironmentFile=/etc/tidmad-full/%i.env" in text
    for fragment in (
        "Environment=INFORMATION_CONDITION=full",
        "--condition ${INFORMATION_CONDITION}",
        "--analysis-policy ${ANALYSIS_POLICY}",
        "--analysis-policy-sha256 ${ANALYSIS_POLICY_SHA256}",
        "--analysis-composition ${ANALYSIS_COMPOSITION}",
        "--siderius-checkout ${SIDERIUS_CHECKOUT}",
        "--unit-dir ${UNIT_DIR}",
    ):
        assert fragment in text
    assert "RestartPreventExitStatus=2 3" in text
    assert "RequiresMountsFor=@UNIT_MOUNT@" in text


def test_full_backup_and_disk_guard_target_full_units() -> None:
    backup = (SYSTEMD / "tidmad-full-backup@.service").read_text()
    guard = (SYSTEMD / "tidmad-full-disk-guard@.service").read_text()
    backup_timer = (SYSTEMD / "tidmad-full-backup@.timer").read_text()
    guard_timer = (SYSTEMD / "tidmad-full-disk-guard@.timer").read_text()
    assert "EnvironmentFile=/etc/tidmad-full/%i.env" in backup
    assert "EnvironmentFile=/etc/tidmad-full/%i-backup.env" in backup
    assert "--instance %i" in backup
    assert "EnvironmentFile=/etc/tidmad-full/%i.env" in guard
    assert "--check-space-only" in guard and "--instance %i" in guard
    assert "Unit=tidmad-full-backup@%i.service" in backup_timer
    assert "Unit=tidmad-full-disk-guard@%i.service" in guard_timer
