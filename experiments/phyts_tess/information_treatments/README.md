# PhyTS TESS information treatments

These small files say what information an experiment gives to its research
agent. They do not change the TESS task, data, metric or validity rules —
both treatments here select the same task package, `tasks/phyts_tess`, and
the same workflow parameters. **The information is the only variable.**

| treatment | used by | advice | Data Analysis | Literature Review |
|---|---|---|---|---|
| [`main-fixed-no-prior.yaml`](main-fixed-no-prior.yaml) | fixed workflow | disabled | disabled | enabled |
| [`main-fixed-full.yaml`](main-fixed-full.yaml) | fixed workflow | enabled, sha-pinned | enabled | enabled |
| [`main-cli-no-advice.yaml`](main-cli-no-advice.yaml) | coding-agent baseline | disabled | `not_applicable` | `not_applicable` |

The CLI treatment says `not_applicable`, not `disabled`, and the distinction
is load-bearing: a general coding agent has no literature-review or
data-analysis MODULE to switch off. Claiming `disabled` would assert a
contrast against a capability the product does not have.

Select one with `--arm no-prior` or `--arm full` on the fixed-workflow
launcher. The adapter derives every flag from the declaration — module state
becomes `--data_analysis_enabled` / `--no-data_analysis_enabled`, and an
enabled advice block becomes `--advice` plus `--advice_sha256` — so the two
can never disagree with each other.

Literature review stays **enabled in both arms**. It is a different
information channel from human advice, and turning it off in one arm would
make the contrast a two-variable change rather than the single "operator
prior present or absent" comparison it is meant to be.

## The advice artifact

[`../main_fixed_workflow/advice.json`](../main_fixed_workflow/advice.json),
sha256 `b4ec769dce62ca2c2f22a705f0dffd212827d7fd97258f1fdb90f23960780a08`,
carrying per-node guidance under `interpret`, `analysis`, `propose`,
`implement` and `tune`.

The digest is declared in the treatment and re-certified from the same bytes
at load, so an edited advice file refuses the launch instead of quietly
running a different treatment under an unchanged identity.

**It is a DRAFT awaiting operator review.** Every claim in it is either
transcribed from the PhyTS benchmark paper or measured from the released
data; the artifact's own `_meta` key records which, line by line. `_meta` is
inert by contract — a leading underscore is the framework's explicit way to
say "this is not advice" — so the agents never read it.

The substantive prior it carries: state-space models outperform
convolutional and zero-shot foundation-model approaches on this task;
capacity is not the lever, since all three published baselines peak near 300k
parameters and the best one degrades at 700k; the signal is periodic rather
than positional; and the target is a global property of the whole sequence,
which is why whole-window summaries beat last-token representations.
