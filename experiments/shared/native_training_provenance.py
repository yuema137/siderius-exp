"""Retain public reconstruction inputs while the training child can read them."""

import hashlib
from pathlib import Path

from core.durable_io import publish_bytes_write_once, publish_json_atomically
from execute_tools.trained_model_artifact import TrainingArtifactCandidate


def publish_training_candidate_sources(sidecar: Path) -> None:
    """Run as the research training UID, inside its target-free namespace.

    Private capture paths are valid only inside this child. Copy their exact
    non-sensitive model/config/scope bytes before leaving that namespace, then
    rebind sidecar paths while preserving all observed hashes and identities.
    No checkpoint duplication or private coordinator filesystem access occurs.
    """
    if not sidecar.exists():
        return  # Tasks without historical-inference semantics have no sidecar.
    candidate = TrainingArtifactCandidate.model_validate_json(sidecar.read_bytes())
    root = sidecar.parent / "training_provenance"
    updates = {}
    for field, digest, expected_size, suffix in (
        (
            "model_config_path",
            candidate.model_config_sha256,
            candidate.model_config_byte_size,
            ".json",
        ),
        ("model_plugin_path", candidate.model_plugin_sha256, None, ".py"),
        ("training_scope_path", candidate.training_scope_sha256, None, ".scope.json"),
    ):
        path = getattr(candidate, field)
        if path is None:
            continue
        source = Path(path)
        if source.is_symlink() or not source.is_file():
            raise ValueError(
                f"training provenance source is not a regular file: {field}"
            )
        payload = source.read_bytes()
        if hashlib.sha256(payload).hexdigest() != digest or (
            expected_size is not None and len(payload) != expected_size
        ):
            raise ValueError(f"training provenance changed before publication: {field}")
        root.mkdir(exist_ok=True)
        destination = root / f"{digest}{suffix}"
        try:
            publish_bytes_write_once(str(destination), payload)
        except FileExistsError:
            if destination.is_symlink() or destination.read_bytes() != payload:
                raise ValueError(
                    "existing training provenance differs from its identity"
                ) from None
        updates[field] = str(destination.resolve())
    published = TrainingArtifactCandidate.model_validate(
        {**candidate.model_dump(), **updates}
    )
    publish_json_atomically(str(sidecar), published.model_dump(mode="json"))
