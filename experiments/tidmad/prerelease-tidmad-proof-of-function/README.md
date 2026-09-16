# TIDMAD prerelease proof of function

This is the locked bounded experiment for a fresh TIDMAD continuous-waveform
proof-of-function run. It is not the Gold campaign and old workspaces are not
valid qualification evidence. Run it only with explicit operator authorization
and the external API/data preparation described by the framework operating
guide.

The launcher pins the task composition, OpenAI Pro routing, ten iterations,
at most two completed rounds per iteration (with the final slot forced Formal
when reached), one epoch, the declared portions, the
full-clone Formal slot, measured admission, 30/120-minute time ceilings,
16/16-GiB VRAM ceilings, scope `15-19`, Health files `15,16,17,18,19`,
sequential order, fresh start, and retained denoised outputs. Supply explicit
`--siderius-checkout`, `--workspace`, and `--data_dir`; use `--dry-run` to
inspect the frozen launch before an authorized effectful run.

The experiment's optional information is declared once in
[`../information_treatments/prerelease-with-advice.yaml`](../information_treatments/prerelease-with-advice.yaml).
The launcher validates that declaration and the advice checksum before it calls
SIDERIUS. It does not keep a second copy of the advice path, digest, or
literature-review setting.

The default is the reviewed advice-on treatment. To reproduce the otherwise
identical explicit advice-off treatment, add `--advice-treatment off`; the
launcher selects the repository-owned off manifest and a separate run name.
It does not accept an arbitrary advice path. Use a fresh workspace for each
treatment.

The advice presents the strongest committed reference as the roughly
300M-parameter FCNet, encourages active exploration across roughly 10M--500M
parameters, and asks the agent to use the available VRAM and time envelopes
productively. Those are search instructions, not a hard parameter-count gate
or a substitute for the task metric.

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
