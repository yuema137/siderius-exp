# Legacy SIDERIUS script archive

This directory preserves historical task or Gate scripts removed from the
SIDERIUS framework repository during framework/experiment separation.

The scripts are provenance-only. They are not supported launchers, current
experiment workflows, or current Gold treatment. Reproducing a historical
run requires an explicit compatibility review against the recorded SIDERIUS
revision and the corresponding archived inputs.

`v18_wave_summary.py` and its original unit test preserve the V18 split-wave
operator checkpoint exactly as it existed in SIDERIUS. The script encodes the
V18 run-name grammar, TIDMAD indexed deliverables, per-scope Health review, and
wave-approval semantics, so it is experiment provenance rather than a generic
framework reporting utility. Their pre-move SHA-256 identities are
`b4a2b2d14b82e8948b938208f3529dcd2fb50e980b9b08d0bdaca5fdf5ee6558` and
`63d5645a89d246b61caeaf85b5f3c6b1eca9b6bc52fad5bff88b718167851852`.
