"""Frozen paper-reference cache classifier, used only for historical rendering.

The function body is verbatim from the five qualified framework references;
see fixtures/storage_reference_matrix.json. Do not use for runtime evidence.
"""

from typing import Literal

CacheState = Literal[
    "cold_first_access", "warm_page_cache", "already_materialized", "unknown"
]
COLD_READ_FRACTION = 0.5


def classify_cache_state(
    bytes_read: int | None,
    expected_bytes: int | None,
    *,
    cold_read_fraction: float = COLD_READ_FRACTION,
    filesystem_type: str | None = None,
) -> CacheState:
    """Classify the cache state of a completed setup read (§2.2).

    The classification is measured, not assumed: ``bytes_read`` is the
    storage-layer read counter delta across the setup window and
    ``expected_bytes`` the on-disk size of what was read. A warm-cache
    measurement must never be presented as a cold-start prediction, so
    any missing counter yields ``"unknown"``.

    Args:
        bytes_read:         Storage-layer bytes read during setup
                            (``read_process_read_bytes`` delta), or
                            ``None`` when the counter was unavailable.
        expected_bytes:     On-disk bytes of the files the setup read,
                            or ``None`` when unknown.
        cold_read_fraction: Fraction of ``expected_bytes`` above which
                            the access counts as cold.
    """
    normalized_fs = (filesystem_type or "").lower()
    if normalized_fs == "virtiofs" or "fuse" in normalized_fs:
        # /proc/self/io observes reads performed by this process. FUSE and
        # virtiofs may perform the backing read in another process, so a zero
        # delta is not evidence of a warm cache.
        return "unknown"
    if bytes_read is None or expected_bytes is None:
        return "unknown"
    if expected_bytes <= 0:
        return "unknown"
    return (
        "cold_first_access"
        if bytes_read >= cold_read_fraction * expected_bytes
        else "warm_page_cache"
    )
