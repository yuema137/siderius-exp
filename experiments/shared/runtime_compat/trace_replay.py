"""Drive numeric traces through a supplied verifier using a controlled clock."""

from contextlib import nullcontext
from unittest.mock import patch


def drive_trace(verifier, segments):
    """Return observed count; use the original interval API only when it exists."""
    now = 0.0
    observed = 0
    with patch("time.monotonic", side_effect=lambda: now):
        for segment in segments:
            now += segment["gap_before_seconds"]
            interval = (
                verifier.active_interval()
                if hasattr(verifier, "active_interval")
                else nullcontext()
            )
            with interval:
                for rate in segment["rates_ms"]:
                    if verifier.is_terminal:
                        break
                    now += rate / 1000.0
                    verifier.feed(rate, elapsed_ms=rate)
                    observed += 1
            if verifier.is_terminal:
                break
        verifier.finalize()
    return observed
