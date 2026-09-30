"""The task data path an external caller may hold: no evaluated targets.

`PhytsTessTaskDataPath` reads the committed identity manifest, and that
manifest carries the validation ``frot`` values. Handing it to an external
caller would hand over the answers, so this variant reads the **agent view**
instead — the one `tasks/phyts_tess/tools/build_views.py` already produces and
re-verifies by re-reading the bytes it wrote.

Everything that defines the task is inherited rather than restated: the
sequence length, the normalization order, the star-grouped sampling and the
deliverable naming all come from the pack. Only the row SOURCE changes, so
there is no second place for the preprocessing to drift.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import ClassVar

# `deliverable_name` is imported for RE-EXPORT, and `__all__` below is what
# declares that. The framework looks for it in the MODULE beside the
# task_data_path implementation and refuses to fall back to an indexed
# template when it finds none. The evaluator reads the same artifacts the
# caller writes, so defining a second naming rule here would be a second way
# for the two sides to disagree about which file is which.
from tasks.phyts_tess.runtime.tess_data_path import (
    PhytsTessTaskDataPath,
    TessRow,
    TessScope,
    TessSplit,
    ValidationScopeError,
    deliverable_name,
)

__all__ = [
    "EVALUATED_TRUTH_IS_EVALUATOR_OWNED",
    "PUBLIC_TESS_TASK_ID",
    "PublicTessScope",
    "PublicTessTaskDataPath",
    "deliverable_name",
]

#: A distinct identity from the pack's `phyts_tess_rotation`. Same id with
#: different content is exactly what the framework's registration rule
#: refuses, and it is right to.
PUBLIC_TESS_TASK_ID = "phyts_tess_rotation_public"

#: Refusal text, named so a test can assert the reason rather than the type.
EVALUATED_TRUTH_IS_EVALUATOR_OWNED = (
    "evaluated-split truth is owned by the evaluator process; a public scope "
    "carries identities only"
)

#: Where `build_views.py` writes each manifest inside the agent view.
_TRAIN_MANIFEST = Path("manifests") / "train.csv"
_PREDICT_MANIFEST = Path("manifests") / "predict.csv"


class PublicTessScope(TessScope):
    """A scope whose evaluated rows have identities and no targets.

    ``truth()`` refuses rather than returning an empty mapping. An empty
    mapping would let a caller "score" every prediction as missing and get a
    number back; a refusal cannot be mistaken for a result.
    """

    def truth(self) -> dict[str, float]:
        raise ValidationScopeError(EVALUATED_TRUTH_IS_EVALUATOR_OWNED)


class PublicTessTaskDataPath(PhytsTessTaskDataPath):
    """The pack's data path, sourced from the answer-free agent view.

    Training rows keep their targets — that is supervision, not an answer.
    Evaluated rows lose theirs, and the scope built from them refuses to
    produce truth at all.

    It declares its OWN id. Reusing the pack's would give the framework two
    implementations under one identity, and its registration rule — same id
    plus different content refuses — exists precisely to catch that. The
    public path is a different implementation and says so.
    """

    task_data_path_id: ClassVar[str] = PUBLIC_TESS_TASK_ID

    def __init__(self, agent_view: str, sequence_length: int | None = None) -> None:
        root = Path(agent_view)
        train = root / _TRAIN_MANIFEST
        predict = root / _PREDICT_MANIFEST
        for manifest in (train, predict):
            if not manifest.is_file():
                raise ValidationScopeError(
                    f"agent view is incomplete: {manifest} is missing. Build it with "
                    "tasks/phyts_tess/tools/build_views.py rather than by hand."
                )
        # The base class wants one manifest path; the training one is the only
        # source it may ever read directly, and `_rows` overrides the rest.
        if sequence_length is None:
            super().__init__(manifest_path=str(train))
        else:
            super().__init__(manifest_path=str(train), sequence_length=sequence_length)
        self._agent_view = root
        self._train_manifest = train
        self._predict_manifest = predict
        self._public_catalog: dict[TessSplit, tuple[TessRow, ...]] = {}

    # ------------------------------------------------------------------ rows

    def _rows(self, split: TessSplit) -> tuple[TessRow, ...]:
        """One split's population, read from the agent view.

        Sorted by ``(gaia_id, sector)`` exactly as the pack does, because the
        framework hashes the serialized scope to verify transport and a
        different order is a different payload.
        """
        cached = self._public_catalog.get(split)
        if cached is not None:
            return cached

        manifest = self._train_manifest if split == "train" else self._predict_manifest
        with manifest.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            columns = set(reader.fieldnames or ())
            if split != "train" and "frot" in columns:
                raise ValidationScopeError(
                    f"{manifest} carries a target column for the evaluated split. "
                    "This view is not answer-free and must not be published."
                )
            records = [
                TessRow(
                    gaia_id=int(entry["gaia_id"]),
                    sector=int(entry["sector"]),
                    # Evaluated rows have no target here. NaN rather than 0.0:
                    # a zero is a plausible rotation frequency and would be
                    # scored as though it were measured, while arithmetic on a
                    # NaN cannot quietly produce a believable number.
                    frot=float(entry["frot"]) if split == "train" else math.nan,
                )
                for entry in reader
                if entry.get("split", split) == split
            ]
        if not records:
            raise ValidationScopeError(f"{manifest} declares no {split!r} rows")
        rows = tuple(sorted(records, key=lambda row: (row.gaia_id, row.sector)))
        self._public_catalog[split] = rows
        return rows

    # ----------------------------------------------------------------- scope

    def build_eval_scope(self, request: object) -> PublicTessScope:
        """The evaluated scope, rebuilt as the refusing variant."""
        scope = super().build_eval_scope(request)  # type: ignore[arg-type]
        return PublicTessScope(
            split=scope.split,
            rows=scope.rows,
            sequence_length=scope.sequence_length,
        )
