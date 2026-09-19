# Qualification before a new fixed-workflow launch

A completed Trial does not qualify the workflow lifecycle. Record exact infra/exp
SHAs, lock, commands, artifacts and boundaries reached. Timeout means incomplete.

## Why the previous smoke missed the failure

The v4 qualification completed Trial with collapse rejection. The diagnostic
three-minute Formal budget expired without completing Formal. It therefore never
proved a valid scored output could be committed and consumed by the next process.
Built-in scoreability fixtures missed external executable contracts restored as
data-only declarations. The shell halt test also omitted the outer supervisor and
systemd restart policy. These missing gates should have blocked workflow
qualification. This is a test-selection and launch-readiness failure.

## Required gates

1. Persist a scored output with a synthetic external scoreability plugin; load it
   in a fresh process through the native workflow loader and reconcile the full
   declaration. Changed aggregation, transform, references and contract parameters
   must still refuse. Restored declarations must remain non-executable.
2. In an isolated real-task qualification unit, complete one valid Formal result
   and demonstrate the next iteration consumes it and reaches its next agent
   stage. A no-records iteration does not exercise this route. If the bounded
   budget expires first, mark this gate pending and explicitly revise the setup.
3. Provoke a deterministic contract refusal. Preserve its failed manifest and
   halt marker; verify no next candidate starts. The supervisor must return
   permanent exit 3; the actual service must end with no automatic restart.
   A subsequent start preserves halt and deadline. Check an ordinary recoverable
   child failure separately; do not disable all retries to hide the defect.
4. Inspect NRestarts, last completed iteration/attempt, score timestamp, stage and
   repeated errors. Active service, GPU use or a changing log alone is insufficient.

Local service-boundary check, from this checkout's own frozen environment:

```bash
RUN_SYSTEMD_HALT_TEST=1 .venv/bin/python -m pytest -q tests/experiments/test_main_fixed_halt_systemd.py
```

This creates and cleans a unique transient user service without model calls/data.
It tests actual supervisor and restart properties, not real-task lifecycle or
installed-host qualification. Historical manifests/halt markers must not be
deleted to make a stopped run appear resumable. Deployment and a fresh run require
separate recorded authorization; this document starts neither.
