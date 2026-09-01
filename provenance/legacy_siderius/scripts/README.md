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

`vram_preflight_validation.py` preserves the V19 candidate-scale validation
matrix, including its three named model families, fixed 12-GiB envelope, and
historical machine output location. The complete pre-split test module is
archived beside it so the task-specific candidate assertions remain
recoverable while the generic isolated-probe tests continue in SIDERIUS. Their
pre-move SHA-256 identities are
`6431bc53edc78be405cae327258e2cb6aa34a1a739f2c7a65590bda62ae8080e` and
`d37193a1e73f780041bd817962da6b799ec6f36b781471ee08b4d98db3e5a49d`.

`runtime_bootstrap.py` preserves the C10 task-aware environment launcher
that selected a fixed nano model, 40,000-sample segmentation, TIDMAD
measurement capability, and legacy calibration registry behavior. Its two
pre-split framework test modules are archived with it; the generic bootstrap
core and its task-neutral tests remain in SIDERIUS. The three pre-move
SHA-256 identities are
`e4f61bc516f7f5ba454c47c6c9d02493f3cfa279747e7c4c57fa67d5a28dc538`,
`c4ae7420edbe95a7cf80c7659d76ae423763bf6f47f2a76ca65a8830734323b4`,
and
`a38cae98eb029d6173448009f0271ead8804c116167425fbaed4a589db7e2941`.

`build_diagnostic_summary.py` and the round-7 `agent_012` Health
reproducer preserve the pre-V17 TIDMAD diagnostic review path. They encode a
ten-round completion rule, TIDMAD score/vector fields, recovered HDF5
artifacts, the PUNet launch decision, and a historical scientific collapse
fingerprint. Their pre-move SHA-256 identities are
`66cf0385178ff7f47279723dad6de154f02c0d859497e42b5d2c2d511d7d0529` and
`65249c823b5bb4ea31057395a2dd571af274848e86355ca1bf796ad82bb5d75d`.
