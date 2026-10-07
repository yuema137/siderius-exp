"""Opt-in paper storage presentation; persisted runtime evidence stays current."""

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .legacy_storage_4e46ced5 import classify_cache_state
from .static_preflight_v6 import historical_preflight_late_v6, historical_preflight_v6

_NEW_FIELDS = frozenset(
    {
        "expected_on_disk_bytes",
        "process_read_bytes_scope",
        "process_read_bytes_reason",
        "cache_state_unknown_reason",
    }
)


class _ScopedStorageEvidence(BaseModel):
    """The complete qualified setup-storage shape; partial/future shapes fail closed."""

    model_config = ConfigDict(extra="forbid", strict=True)

    dataset_root: str
    file_count: int = Field(ge=0)
    files_present: int = Field(ge=0)
    expected_raw_bytes: int = Field(ge=0)
    expected_on_disk_bytes: int = Field(ge=0)
    total_file_bytes: int = Field(ge=0)
    filesystem_type: str
    process_read_bytes_scope: Literal["complete", "incomplete", "unknown"]
    process_read_bytes_reason: str | None = Field(min_length=1)
    bytes_read_from_storage: int | None
    cache_state: Literal["cold_first_access", "warm_page_cache", "unknown"]
    cache_state_unknown_reason: str | None = Field(min_length=1)
    rss_bytes_before_setup: int | None = Field(ge=0)
    rss_bytes_after_setup: int | None = Field(ge=0)

    @model_validator(mode="after")
    def require_consistent_evidence(self):
        if self.expected_on_disk_bytes != self.expected_raw_bytes:
            raise ValueError(
                "Historical projection requires unchanged physical byte basis"
            )
        if self.files_present > self.file_count:
            raise ValueError("Storage files_present exceeds file_count")
        provenance, _ = _qualified_provenance()
        assessment = provenance.assess_cache_state(
            self.bytes_read_from_storage,
            self.expected_on_disk_bytes,
            process_read_bytes_scope=self.process_read_bytes_scope,
            process_read_bytes_reason=self.process_read_bytes_reason,
        )
        if (self.cache_state, self.cache_state_unknown_reason) != (
            assessment.state,
            assessment.unknown_reason,
        ):
            raise ValueError(
                "Current cache state or reason contradicts the qualified producer"
            )
        return self


def project_record(record: dict[str, Any]) -> dict[str, Any]:
    """Rebuild only the qualified old view from retained raw inputs, on a copy.

    Archived records without the new fields are already historical evidence.
    Never fabricate timings, physical bytes, counter deltas or memory values.
    """
    result = deepcopy(record)
    verification = result.get("runtime_verification")
    if verification is None:
        return result
    if not isinstance(verification, dict):
        raise TypeError("Storage projection requires a runtime_verification mapping")
    storage = verification.get("storage")
    if storage is None:
        return result
    if not isinstance(storage, dict):
        raise TypeError("Storage projection requires a storage mapping")
    if not _NEW_FIELDS.intersection(storage):
        return result
    evidence = _ScopedStorageEvidence.model_validate(storage)
    storage["cache_state"] = classify_cache_state(
        evidence.bytes_read_from_storage,
        evidence.expected_raw_bytes,
        filesystem_type=evidence.filesystem_type,
    )
    for key in _NEW_FIELDS:
        storage.pop(key)
    return result


def _qualified_provenance():
    """Use the current assessment authority only on the explicitly qualified source."""
    from core.runtime_control import provenance

    matrix = json.loads(
        (Path(__file__).parent / "fixtures/storage_reference_matrix.json").read_bytes()
    )
    source = Path(provenance.__file__).read_bytes()
    if hashlib.sha256(source).hexdigest() != matrix["current_provenance_sha256"]:
        raise ValueError(
            "Unqualified current storage provenance producer; select the paired #419 "
            "infra revision or qualify a new explicit profile"
        )
    return provenance, source


def _qualified_sources() -> dict[str, bytes]:
    root = Path(__file__).parent
    matrix_bytes = (root / "fixtures/storage_reference_matrix.json").read_bytes()
    matrix = json.loads(matrix_bytes)
    frozen = (root / "legacy_storage_4e46ced5.py").read_bytes()
    if hashlib.sha256(frozen).hexdigest() != matrix["frozen_module_sha256"]:
        raise ValueError("Frozen historical storage classifier changed")
    _, current_provenance = _qualified_provenance()
    return {
        "qualified_current_provenance.py": current_provenance,
        "storage_provenance_v7.py": Path(__file__).read_bytes(),
        "legacy_storage_4e46ced5.py": frozen,
        "storage_reference_matrix.json": matrix_bytes,
    }


def _provider(*, late: bool):
    from core.planner_strategy_identity import (
        PlannerStrategyIdentity,
        source_fingerprint,
    )

    original = historical_preflight_late_v6() if late else historical_preflight_v6()
    name = "legacy-9b78d505cb11-paper" + ("-late" if late else "") + "-storage-v7"

    def render(*, memory_history, **arguments):
        return original.user_renderer(
            memory_history=[project_record(record) for record in memory_history],
            **arguments,
        )

    return replace(
        original,
        identity=PlannerStrategyIdentity(
            name=name,
            version="7",
            content_sha256=source_fingerprint(
                _qualified_sources()
                | {"v6_identity.json": original.identity.model_dump_json().encode()}
            ),
        ),
        user_renderer=render,
    )


def historical_storage_v7():
    return _provider(late=False)


def historical_storage_late_v7():
    return _provider(late=True)
