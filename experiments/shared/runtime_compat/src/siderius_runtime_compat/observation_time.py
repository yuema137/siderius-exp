"""Historical timestamp interpretation for explicitly selected paper profiles.

The original observation store discarded parsed UTC offsets by passing the
wall-clock tuple to mktime. Preserve that behavior here, including host-local
DST interpretation; corrected native behavior belongs to the framework.
"""

import time


def historical_timestamp_seconds(timestamp: str) -> float | None:
    """Return the original local-clock epoch, or None for unsupported input."""
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            return time.mktime(time.strptime(timestamp, fmt))
        except ValueError:
            continue
    return None


def historical_timestamp_order_key(timestamp: str) -> tuple[float, str]:
    """Retain original lexical ordering, including malformed timestamp strings."""
    return (0.0, timestamp)
