# TIDMAD prerelease proof of function

This page documents a historical, dry-run-qualified regression witness. It is
not a current qualification route and does not authorize a campaign or a
provider-backed launch. For current bounded work, use
[`../two_iteration_qualification/`](../two_iteration_qualification/).

This is a bounded, dry-run-qualified continuous-waveform regression witness.
It does not authorize a campaign or a provider-backed launch.

The launcher pins the task composition, OpenAI Pro routing, ten iterations,
at most two completed rounds per iteration (with the final slot forced Formal
when reached), one epoch, the declared portions, the
full-clone Formal slot, measured admission, 30/120-minute time ceilings,
16/16-GiB VRAM ceilings, scope `15-19`, Health files `15,16,17,18,19`,
sequential order, fresh start, and retained denoised outputs. Supply explicit
`--siderius-checkout`, `--workspace`, and `--data_dir`; `--dry-run` is the only
safe execution mode for this prerelease proof.

The scientific contract is task-owned in
`tasks/tidmad/compositions/continuous_regression.yaml`. The output is
`[B,T]` float32 continuous waveform regression; classification logits and
argmax decoding are not valid alternatives. Health remains fail-closed: the
calibrated `amplitude_collapse` gate is the sole blocking gate, while the
other recording metrics are diagnostic.

No dataset, workspace, model, API credential, or result is stored here.

Advice provenance: `tasks/tidmad/reference_data/legacy_baseline_configs.json`
sha256 `2e15932ae8c87500b888f95efb4f356f16ed646a2f42b144fafd9610163728b0`;
`tasks/tidmad/reference_data/official_paper_result/fcnet.md` sha256
`74dff62030771e72b5bfe286cc8a5acd1616aed29311985ee43bf7adc9d62706`.
