"""Information-preserving, input-only frequency view of the prepared Project8 I/Q events."""

from __future__ import annotations

import numpy as np

CHANNEL_NAMES = ("time_I", "time_Q", "fft_real", "fft_imag")
TRANSFORM_ID = "project8-full-complex-fft-ortho-v1"


def dual_representation(time_iq: np.ndarray) -> np.ndarray:
    """Return [N, 4, L]; the first pair indexes time, the second frequency.

    The input is already centered and scaled by the frozen time-domain
    preparation. A full complex FFT preserves both quadratures, negative
    frequencies and phase. Orthonormal scaling preserves total squared norm;
    there is no second normalization, magnitude conversion, crop or fftshift.
    """
    if time_iq.dtype != np.float32 or time_iq.ndim != 3:
        raise ValueError("expected float32 [N, 2, L] prepared inputs")
    if time_iq.shape[1] != 2 or min(time_iq.shape[0], time_iq.shape[2]) < 1:
        raise ValueError("expected nonempty events with exactly two I/Q channels")
    if not np.isfinite(time_iq).all():
        raise ValueError("time-domain inputs contain nonfinite values")
    # Use float64 for the deterministic transform, then store float32 like the
    # time view. No targets or population statistics enter this function.
    signal = time_iq[:, 0].astype(np.float64) + 1j * time_iq[:, 1]
    spectrum = np.fft.fft(signal, axis=-1, norm="ortho")
    result = np.empty((len(time_iq), 4, time_iq.shape[-1]), dtype=np.float32)
    result[:, :2] = time_iq
    result[:, 2] = spectrum.real
    result[:, 3] = spectrum.imag
    if not np.isfinite(result).all():
        raise ValueError("frequency-domain inputs overflowed float32")
    return result
