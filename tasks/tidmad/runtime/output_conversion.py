"""Task-owned conversion from a continuous prediction to ABRA storage bytes.

Both SIDERIUS composed inference and the coding-agent evaluator call this
function. The conversion intentionally preserves the existing composed
regression behavior: subtract the declared ADC offset, then cast to the
declared storage dtype. Changing range handling or rounding is a separate
scientific-treatment decision, not a caller-specific implementation detail.
"""

from __future__ import annotations

import numpy as np


def regression_to_storage(
    prediction: np.ndarray, *, value_offset: int, storage_dtype: str | np.dtype
) -> np.ndarray:
    """Convert finite offset-domain predictions using the existing ABRA codec."""

    values = np.asarray(prediction)
    if not np.issubdtype(values.dtype, np.floating):
        raise TypeError("continuous regression prediction must be floating point")
    if not np.isfinite(values).all():
        raise ValueError("continuous regression prediction contains non-finite values")
    return (values - value_offset).astype(np.dtype(storage_dtype))
