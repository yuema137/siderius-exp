# Orchestration smoke: what one short run must show before `onp_001`

The operator authorized the smoke on 2026-09-21 with the fixed workflow's
budgets: six hours of wall clock and 8 GiB VRAM. Nothing in this sheet
extends either. The smoke runs under a separate unit id (`onp_smoke_001`),
in cleared state, and its artifacts are collected before any formal unit
starts.

## Why reading cannot settle it

The shared native machinery was built around TIDMAD's geometry. Whether it
transfers to `[B, 1, 1024] float32 → [B, 1] float32` — through capture,
admission, the bubblewrap namespace, per-epoch validation served from the
evaluator's targets, export, and `tess-score` — is a claim only execution
answers. Three defects were found by reading alone after the authorization
probe had already passed (the wrong entrypoint, empty namespaces, NaN
validation targets); the smoke exists for the ones reading cannot find.

## Required evidence, in order

1. **Preflight, operator side, no clock.** `verify_launcher_policy --installed`,
   `verify_evaluator_policy --installed`, `probe_authorization.sh` (PASS is
   the named refusal), and `probe_namespace.py` for all three namespaces
   with CUDA visible. Any failure blocks the smoke.
2. **One protected training call** with a tiny model and a short explicit
   epoch budget, launched by the caller's own bound tuner process, not by
   hand: capture accepts the framework's argv, admission accepts the
   composition and scope, per-epoch validation returns **finite** losses,
   and the training result lands under `/home/tess-caller/work/onp_smoke_001`
   readable by the caller.
3. **One export and one `tess-score` invocation** from the same process:
   a receipt under `/var/lib/tess-evaluations` that `read_tess_evaluation`
   accepts for the exact candidate bytes, with `evaluated_rows == 442`, a
   finite R-squared, and the task's Health gate persisted. Do not narrow the
   evaluated split to manufacture a pass.
4. **Two iterations of the caller's loop**, so the second candidate sees the
   first's receipt, and one deliberate transport failure (a candidate id
   reused) to show the diagnostic lands and the retained candidate survives.
5. **The clock.** The unit is launched through `supervisor.py`; the launch
   record is write-once; the process group is gone after the deadline or
   after a clean exit, and no GPU process remains.

Framework or setup failures block `onp_001`. Model quality, the agent's
strategy and unobserved hypothetical edge cases do not.

## The driver

Steps 2–4 are one process: `smoke_tuner.py` in the published runtime is
`SUBMISSION.md`'s binding made executable — composition, complete
evaluator and protected validation launcher bound around one native
tuner run of two rounds (trial, then complete-split formal) with a
two-epoch budget and every other bound as declared. Launched by the
caller account inside the supervisor's clock:

```bash
sudo -u tess-caller env OPENAI_API_KEY="$OPENAI_API_KEY" <framework-python> \
    -m experiments.phyts_tess.main_orchestrator.supervisor \
    --unit_dir /home/tess-caller/units/onp_smoke_001 --launch -- \
    <framework-python> <runtime>/experiments/phyts_tess/main_orchestrator/smoke_tuner.py \
        --workspace /home/tess-caller/workspace/onp_smoke_001 --run-id onp_smoke_001 \
        --storage-root /home/tess-caller/work \
        --composition <deployment>/bundle/caller/composition.yaml \
        --data-dir <rundata> --unit-dir .
```

`--unit-dir .` works because the supervisor writes `launch.json` before it
spawns the caller and spawns it with the unit directory as its cwd.

It writes `run/smoke-summary.json` in the workspace with every receipt.

## What to record

The smoke unit's `launch.json`, every `evaluation_diagnostics/*.json`, the
receipts, the coordinator's `/var/lib/tess-native/evaluator/candidates/<id>/`
listing (operator-side), and the actual replay time of step 2 — never a
padded schedule. Record the outer controller's product and version.
