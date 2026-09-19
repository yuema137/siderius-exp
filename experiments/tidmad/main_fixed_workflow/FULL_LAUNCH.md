# Fixed Full launch preparation

Implementation candidate: formal Full advice/policy and deployment qualification
are not frozen by this document. No formal Full run has been started.

Full uses the same `workflow.json`, band-data verifier, 24-hour unit clock and
supervisor as NoPrior. It enables advice and Data Analysis together, keeps
literature review on, and requires an explicit analysis policy digest and a
prepared composition. The composition must equal the frozen task with only its
analysis binding added. Task files are not rewritten.

Prepare the policy and composition outside both checkouts and outside the new
unit directory. Use the `information_treatments.prior_binding` helpers;
the orchestration deployment branch can reuse this authority. The policy must retain that band's declared
input-only assets/access/scope. Budget selection still requires the experiment's
review; this launcher does not choose a new budget.

Preview (no clock or run starts):

```bash
experiments/tidmad/main_fixed_workflow/launch.sh \
  --condition full --siderius-checkout /path/to/pinned/infra \
  --band 0-3 --data_dir /path/to/verified/band-data \
  --unit-dir /mounted-volume/new-full-unit --run_name full-band-0-3 \
  --analysis-policy /operator-inputs/analysis.yaml \
  --analysis-policy-sha256 <reviewed-sha256> \
  --analysis-composition /operator-inputs/composition.yaml
```

Only a reviewed launch adds `--launch`. Full requires all three analysis flags;
NoPrior (the default condition) refuses them. The Full credential check includes
Data Analysis's configured provider; NoPrior continues to exclude it explicitly.

The first launch receipt binds policy and composition hashes along with the
existing workflow, task, data, advice and revision identity. A restart reuses the
same deadline and refuses changed inputs or a change of condition. Shared GPU,
backup, storage and deployed service qualification remain separate requirements.
