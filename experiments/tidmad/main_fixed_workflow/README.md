# TIDMAD main fixed-workflow configuration

This is a partial, non-launchable starting point for the planned one-band,
24-hour main experiment. `workflow.json` pins the continuous-regression task,
the shared OpenAI agent configuration, and the exact 40,000-sample segment
length through SIDERIUS's existing workflow parameter-rule mechanism. It does
not choose Trial/Formal budgets, an iteration schedule, a workspace, or a band.

The future launcher will accept one treatment selector (`full` or `no-prior`).
Both treatments must use the same workflow and agent-parameter JSON. The
information-treatment manifest owns human advice and the dedicated data-analysis
state. `full` must refuse until the separately developed data-analysis component
is actually wired and validated; `no-prior` must pass explicit disabled states.
ML literature review stays enabled in both treatments. No run should be
started from this directory until those contracts and the launch gate are
completed and qualified.

The `main-fixed-no-prior.yaml` manifest already reserves an explicit
`data_analysis: disabled` state. The current SIDERIUS argument renderer refuses
that module because the runtime adapter is not landed yet. This is deliberate:
it prevents a nominal NoPrior launch from silently becoming an advice-only
ablation. The separately developed module can connect through this named
treatment state without changing the shared workflow JSON.
