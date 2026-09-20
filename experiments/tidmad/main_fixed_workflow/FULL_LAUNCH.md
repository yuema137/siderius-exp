# Fixed Full launch preparation

Full prior V7 advice and analysis policies are frozen. Deployment qualification
remains separate; this release does not start or qualify a formal Full run.

Full uses the same `workflow.json`, band-data verifier, 24-hour unit clock and
supervisor as NoPrior. It enables advice and Data Analysis together, keeps
literature review on, and requires an explicit analysis policy digest and a
prepared composition. The composition must equal the frozen task with only its
analysis binding added. Task files are not rewritten.

Prepare the policy and composition outside both checkouts, data and the new
unit directory. The destination must not already exist:

```bash
.venv/bin/python -m experiments.tidmad.information_treatments.prepare_full \
  --band 0-3 --output-dir /operator-inputs/full-0-3
```

Repeat for `4-9`, `10-14`, `15-19` with separate destinations. This copies the
exact frozen band policy and creates a relocated task composition plus
`binding-receipt.json`. It performs no data reads, API calls, clock start or
model execution. Use the receipt's paths and policy SHA below. The same
`full_analysis_policy` / `resolve_prior` authorities are available to
orchestration preparation; a native orchestration launcher is not included in
this release. Access declarations AND the complete policy (including the
600-second resource envelope) must match V7. A new operator checksum alone
cannot authorize a changed policy.

Preview (no clock or run starts):

```bash
experiments/tidmad/main_fixed_workflow/launch.sh \
  --condition full --siderius-checkout /path/to/pinned/infra \
  --band 0-3 --data_dir /path/to/verified/band-data \
  --unit-dir /mounted-volume/new-full-unit --run_name full-band-0-3 \
  --analysis-policy /operator-inputs/full-0-3/analysis-policy.yaml \
  --analysis-policy-sha256 <reviewed-sha256> \
  --analysis-composition /operator-inputs/full-0-3/composition.yaml
```

Only a reviewed launch adds `--launch`. Full requires all three analysis flags;
NoPrior (the default condition) refuses them. The Full credential check includes
Data Analysis's configured provider; NoPrior continues to exclude it explicitly.

For reboot-safe deployment, install `systemd/tidmad-full@.service` after
replacing `@FULL_USER@`, `@FULL_GROUP@` and `@UNIT_MOUNT@`. Each instance uses
a mode-600 `/etc/tidmad-full/%i.env` containing `EXP_CHECKOUT`,
`SIDERIUS_CHECKOUT`, `BAND`, `DATA_DIR`, `UNIT_DIR`, `RUN_NAME`,
`ANALYSIS_POLICY`, `ANALYSIS_POLICY_SHA256`, `ANALYSIS_COMPOSITION`, and the
enabled providers' credentials. The template passes `--condition full` and all
three analysis bindings explicitly. Install the matching Full backup and disk
guard service/timer pairs with `/etc/tidmad-full/%i-backup.env`; low-space
handling stops the matching Full service, not a historical NoPrior instance.

The first launch receipt binds policy and composition hashes along with the
existing workflow, task, data, advice and revision identity. A restart reuses the
same deadline and refuses changed inputs or a change of condition. Shared GPU,
backup, storage and deployed service qualification remain separate requirements.
