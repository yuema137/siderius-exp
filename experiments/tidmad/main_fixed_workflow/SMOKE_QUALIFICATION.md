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
2. Split functional qualification into bounded witnesses (normally seconds to
   minutes, with a 10–15 minute outer limit per batch):
   - run native training, inference, scoring and persistence on explicitly
     labelled small diagnostic fixtures, without modifying frozen task files;
   - replay copies of actual valid Formal artifacts through the native next
     iteration runner in a fresh process, including plugin/state restoration,
     and verify the restored summaries reach the next agent's input boundary.
     Record any relocation of fixture manifest paths and preserve original
     output bytes and hashes. A boundary probe is evidence of dispatch, not
     evidence of a live model response;
   - check all deployed bands' frozen scopes and treatment using preflight.
   Model convergence and scientific score quality are not functional gates.
   No-records/timeout cannot substitute for a required success-path witness.
   Diagnostic scopes/budgets and fixtures must never seed formal fresh starts.
3. Provoke a deterministic contract refusal. Preserve its failed manifest and
   halt marker; verify no next candidate starts. The supervisor must return
   permanent exit 3; the actual service must end with no automatic restart.
   A subsequent start preserves halt and deadline. Check an ordinary recoverable
   child failure separately; do not disable all retries to hide the defect.
4. Inspect NRestarts, last completed iteration/attempt, score timestamp, stage and
   repeated errors. Active service, GPU use or a changing log alone is insufficient.
5. For Full, require a successful generated-analysis program as well as reference
   skills. A previous Full deployment lacked `bubblewrap`: reference skills
   succeeded, but every generated program was refused before materialization.
   Under the execution UID and service restrictions, run the native readiness
   check documented in [Full launch](FULL_LAUNCH.md), then from the exact infra
   checkout run `REQUIRE_ANALYSIS_SANDBOX=1 .venv/bin/python -m pytest -q
   tests/unit/agent/data_analysis/test_analysis_code_sandbox.py`.
   Record successful authorized-input and artifact witnesses, plus refusal
   cases. These synthetic checks require no training or model calls. Missing
   dependencies, blocked namespaces, failures or skips do not qualify the host.
   Recheck each deployed host; one host's result cannot qualify another.

Local service-boundary check, from this checkout's own frozen environment:

```bash
RUN_SYSTEMD_HALT_TEST=1 .venv/bin/python -m pytest -q tests/experiments/test_main_fixed_halt_systemd.py
```

This creates and cleans a unique transient user service without model calls/data.
It tests actual supervisor and restart properties, not real-task lifecycle or
installed-host qualification. Historical manifests/halt markers must not be
deleted to make a stopped run appear resumable. Deployment and a fresh run require
separate recorded authorization; this document starts neither.
