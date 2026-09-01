"""Campaign-owned CLI wiring for durable wave summaries."""

from __future__ import annotations

import json

from campaigns.tidmad_gold.scripts.record_wave_summary import main


def test_cli_writes_matching_canonical_and_derived_records(tmp_path, capsys):
    """A moved CLI must still reach the campaign-owned persistence authority."""
    canonical = tmp_path / "queue" / "wave_state.jsonl"
    derived_dir = tmp_path / "summaries"

    result = main(
        [
            "--canonical",
            str(canonical),
            "--derived-dir",
            str(derived_dir),
            "--campaign-id",
            "qualification",
            "--wave",
            "2",
            "--band",
            "4-9",
            "--band-tag",
            "04_09",
            "--start",
            "2026-09-01T00:00:00Z",
            "--end",
            "2026-09-01T01:00:00Z",
            "--disposition",
            "complete",
            "--chain",
            "chain_arch:arch:111:0",
            "--chain",
            "chain_loss:loss:222:0",
        ]
    )

    assert result == 0
    canonical_record = json.loads(canonical.read_text().strip())
    derived_record = json.loads((derived_dir / "wave_2_04_09.json").read_text())
    assert canonical_record == derived_record
    assert canonical_record["record_id"] == "qualification:2:04_09:1"
    assert "qualification:2:04_09:1 wave_2_04_09.json" in capsys.readouterr().out
