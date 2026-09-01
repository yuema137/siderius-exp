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

`finalize_recovered_diagnostic_round.py` preserves the one-off recovery of
a TIDMAD diagnostic round after an NVRM Xid 8 incident. It encodes ten-round
completion, eighteen reused outputs, regeneration of files 8 and 9, WaveNet
record paths, and the historical Health/scoring treatment. Its pre-move
SHA-256 identity is
`01a2777a4e7b56d805da9e4cb7fc01ad9c48dd79e943d10a5ad459efff2a914f`.

`pregate_runtime_control_validation.py` preserves the pre-Gate real-GPU
runtime-control validation driver. It fixes a WaveNet architecture, focal
loss, TIDMAD scopes and sample sets, the V18 480,000-step incident geometry,
and historical H100 watchdog/budget scenarios. The generic runtime-control
mechanisms and their task-neutral tests remain in SIDERIUS. Its pre-move
SHA-256 identity is
`9d3413b9c4477ee9414a8a283120a32fd9ae8b714033549a5a4bc509fdf79acb`.

`investigate_6_3556_mechanism.py` preserves the one-off scorer diagnostic for
the historical 6.3556 phantom. It fixes TIDMAD's 10-Msample segment geometry,
10-MHz sampling frequency, twenty-file/two-hundred-segment workload, int8-to-
millivolt conversion, and the investigated `noise <= 1e-10` threshold. Its
pre-move SHA-256 identity is
`97e3813d37486fcddc9b7ce9870afceede553c7f56c194431e26873cd6a9b409`.

`render_proposer_prompts_for_audit.py` preserves the historical Checkpoint-P
human prompt audit. Its synthetic evidence fixes PUNet/WaveNet, TIDMAD score
and band semantics, a FreLE literature finding, a legacy RTX 3090 context,
and the P-a through P-e commit ladder. Current generic proposer contracts and
prompt tests remain in SIDERIUS. Its pre-move SHA-256 identity is
`687564e8b9bd7086c258d241c5e68c15b78580af7cd2928d42e9175f4ea352c2`.

`c2_prephase_validation.py` preserves the V20 PR-C2 Gate-2 Lite GPU harness.
It owns the dated case matrix, immutable attempt artifacts, bounded Formal
comparison arms, TIDMAD SampleSet construction, and Gate-specific environment
and peak-stability interpretation. The generic measurement, admission,
environment-stability, and formal-stability components remain in SIDERIUS.
Its pre-move SHA-256 identity is
`e5be6df8ce89975f71435d648bfceee9ec3e64a4695317ddde1e03dbc535ea82`.
