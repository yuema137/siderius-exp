# PhyTS TESS information treatments

These small files say what information an experiment gives to its research
agent. They do not change the TESS task, data, metric or validity rules —
both treatments here select the same task package, `tasks/phyts_tess`, and
the same workflow parameters. **The information is the only variable.**

| treatment | used by | advice | Data Analysis | Literature Review |
|---|---|---|---|---|
| [`main-fixed-no-prior.yaml`](main-fixed-no-prior.yaml) | fixed workflow | disabled | disabled | disabled |
| [`main-fixed-full.yaml`](main-fixed-full.yaml) | fixed workflow | enabled, verified before launch | enabled | disabled |
| [`main-cli-no-advice.yaml`](main-cli-no-advice.yaml) | coding-agent baseline | disabled | `not_applicable` | `not_applicable` |

The CLI treatment says `not_applicable`, not `disabled`, and the distinction
is load-bearing: a general coding agent has no literature-review or
data-analysis MODULE to switch off. Claiming `disabled` would assert a
contrast against a capability the product does not have.

Select one with `--arm no-prior` or `--arm full` on the fixed-workflow
launcher. The launcher reads module settings and advice from that treatment
and verifies the selected files before starting. The
[technical treatment contract](../../shared/information_treatment.md) explains
how those declarations become execution settings.

Literature review is **disabled in both arms**, and what matters is that the
two agree: it is a second information channel, so a state that differed
between them would make the contrast a two-variable change rather than the
single "operator prior present or absent" comparison it is meant to be.

Disabling it is a choice of these frozen treatments. A different experiment
can enable Literature Review with an explicit configuration. Curated root
papers are optional: the framework also supports an empty root-paper list
with dynamic search. Such a change needs its own treatment and review; it is
not an edit to these recorded comparison arms.

## The advice artifact

[The advice file](../main_fixed_workflow/advice.json) carries per-node guidance under `interpret`, `analysis`, `propose`,
`implement` and `tune`.

The launcher checks the advice against the selected treatment and refuses
modified files. To use different advice, create and review a new treatment;
do not bypass the check to reuse an old experiment identity.

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
