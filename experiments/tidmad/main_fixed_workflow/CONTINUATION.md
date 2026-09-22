# Reviewed continuation after infrastructure failure

Ordinary restarts preserve the original 24-hour UTC clock and halt marker.
An operator-authorized outage exclusion uses the separate `continuation` entry
point. This is a continuation of the original experiment, not a fresh run.

## Preparation

1. Stop the failed unit and its backup/disk-guard timers. Collect the complete
   unit, operator inputs, source revisions, and service failure evidence into
   external diagnosis storage. Verify independent remote/local SHA-256 lists.
2. Preserve the original `launch.json` and all committed iterations, plugins,
   generated library, calibration, and research history. Upgrade reviewed
   source revisions at the same checkout paths with their own frozen virtualenvs.
   Task bytes, advice, commands, data, and scientific settings must remain equal.
3. Qualify native restoration of every completed iteration with the new code.
   Record restored candidates, scores, history, and source versions. Only after
   verified collection and explicit recovery review, remove the uncommitted
   failed tail and its halt/stop markers. Never remove a committed iteration or
   change `run_invariants_lock.json` to make a mismatch pass.
4. Write an external recovery evidence file identifying the verified archive,
   failure, failed paths removed, restored state, and new source revisions.
   The launcher records this file's hash; it does not audit its claims for you.

## Preview and launch

From the selected experiment checkout, using its own environment:

```bash
.venv/bin/python -m experiments.tidmad.main_fixed_workflow.continuation \
  --siderius-checkout /explicit/infra-checkout \
  --unit-dir /persistent-volume/existing-unit \
  --stopped-epoch FAILED_CHAIN_EXIT_EPOCH \
  --recovery-evidence /external/recovery-evidence.json
```

The stop epoch must match a failed `chain_exit` in the original events. Review
the preview, then add `--launch` to the service command. Preserve the existing
service user, provider environment, process-group termination, restart policy,
and backup destinations. The entry point uses the original supervisor lock.

The first actual launch creates `continuation.json` atomically. Its deadline is
`continuation_start + 86400 - (failure_stop - original_start)`. Downtime before
that launch is excluded; subsequent service restarts reuse this exact deadline.
Neither the original clock nor previous results are rewritten. A halt, changed
scientific input, changed recovery evidence, or changed revision after this
continuation starts refuses another launch. Multiple separately reviewed outage
exclusions are not implemented by this entry point.

Restore the existing backup/disk-guard timers and confirm the new clock, native
resume index, restored history, and first live workflow progress. Archive the
original and continuation receipts together when collecting the final unit.
