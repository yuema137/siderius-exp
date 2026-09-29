"""The `nop_004` run record must stay reproducible, or fail loudly.

Two cases, each naming a defect nothing else would catch:

* ``test_the_recorded_treatment_still_resolves_to_the_same_manifest`` — the
  record pins the treatment it ran under. Editing
  ``main-fixed-no-prior.yaml`` afterwards leaves the record describing a
  treatment this tree no longer contains, and nothing else would notice:
  the record is static data, the treatment still resolves, and every other
  test still passes. The reproduction recipe would then be quietly wrong.

* ``test_the_results_table_matches_the_extracted_record`` — the markdown
  table is hand-written while ``results.json`` is extracted from the unit's
  own persisted records. A transcription slip in the table is invisible to
  reading and would be published as a result.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from experiments.shared.information_treatment import resolve_information_treatment

EXP_ROOT = Path(__file__).resolve().parents[2]
RECORD_DIR = (
    EXP_ROOT / "experiments" / "phyts_tess" / "main_fixed_workflow" / "runs" / "nop_004"
)
RESULTS = RECORD_DIR / "results.json"
REPORT = RECORD_DIR / "RESULTS.md"
TREATMENT = (
    EXP_ROOT
    / "experiments"
    / "phyts_tess"
    / "information_treatments"
    / "main-fixed-no-prior.yaml"
)


def _record() -> dict:
    return json.loads(RESULTS.read_text(encoding="utf-8"))


def test_the_recorded_treatment_still_resolves_to_the_same_manifest():
    """Recomputed through the same authority the supervisor used, not a copy."""
    recorded = _record()["treatment"]
    observed = resolve_information_treatment(
        TREATMENT,
        repository_root=EXP_ROOT,
        adapter="siderius",
        required_modules=("literature_review", "data_analysis"),
    ).receipt()

    assert observed["treatment_id"] == recorded["treatment_id"]
    assert observed["manifest_sha256"] == recorded["manifest_sha256"], (
        "nop_004 ran under treatment manifest "
        f"{recorded['manifest_sha256']}, but main-fixed-no-prior.yaml now hashes "
        f"to {observed['manifest_sha256']}. The run record describes a treatment "
        "this tree no longer contains. If the revision was deliberate, say so in "
        "RESULTS.md and re-pin; do not relax this check."
    )


#: Every R-squared the report prints in its results table, as
#: ``iteration -> (trial, formal)``. Parsed from the markdown rather than
#: restated, so the comparison is against what a reader actually sees.
_ROW = re.compile(
    r"^\|\s*\**(\d+)\**\s*\|[^|]+\|\s*\**\*?(−?[\d.]+)\*?\**\s*\|\s*\**(−?[\d.]+)\**\s*\|$"
)


def _table_rows() -> dict[int, tuple[float, float]]:
    rows: dict[int, tuple[float, float]] = {}
    for line in REPORT.read_text(encoding="utf-8").splitlines():
        match = _ROW.match(line.strip())
        if not match:
            continue
        iteration = int(match.group(1))
        trial = float(match.group(2).replace("−", "-"))
        formal = float(match.group(3).replace("−", "-"))
        rows[iteration] = (trial, formal)
    return rows


def test_the_results_table_matches_the_extracted_record():
    """The published table against the machine-extracted truth."""
    table = _table_rows()
    assert len(table) == 16, (
        f"expected 16 complete iterations in the report table, parsed {len(table)}"
    )

    for entry in _record()["iterations"]:
        iteration = entry["iteration"]
        if iteration not in table:
            continue
        rounds = {r["is_trial"]: r["r2"] for r in entry["rounds"]}
        printed_trial, printed_formal = table[iteration]
        assert round(rounds[True], 4) == printed_trial, (
            f"iteration {iteration} trial: table says {printed_trial}, "
            f"record says {rounds[True]:.4f}"
        )
        assert round(rounds[False], 4) == printed_formal, (
            f"iteration {iteration} formal: table says {printed_formal}, "
            f"record says {rounds[False]:.4f}"
        )
