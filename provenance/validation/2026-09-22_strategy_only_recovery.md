# Strategy-only preparation and recovery qualification

Scope: additive `O-StrategyOnly` preparation and optional baseline prompt
supplement. Dedicated Data Analysis and model advice remain disabled. The
frozen task package, fixed workflow, infra pin and baseline limits are unchanged.
The historical control uses older runtime versions; this work does not assert
code-identical comparison or schedule a replacement control.

## Local evidence

Exact checkout environment: `uv sync --group dev --frozen`, pinned infra
`c046744712fabfbd09c5c5a51a84fb30073d59e3`.

```bash
.venv/bin/python -m pytest -q \
  tests/experiments/test_orchestrator_strategy_only.py \
  tests/experiments/test_main_orchestrator_policy.py \
  tests/deployments/tidmad_coding_agent_baseline
```

Result: **109 passed**. Existing Python 3.14 TorchScript deprecation warnings
remain. Ruff checks/format and `git diff --check` passed for changed files.

The tests exercise all four native band bindings, attempted DA enablement on
the compact public adapter, legacy Full/NoPrior behavior, two actual subprocess
stdin deliveries, changed/missing/invalid advice refusal and unchanged baseline
prompt bytes. A `python -S` child verifies the deployment harness can still
import and deliver advice without site-packages, matching its bare-venv install.
Pin/environment checks are bypassed in the per-band unit preparation fixture;
that fixture is not a certificate of a deployed release.

A separate unmocked CLI preparation then passed for all four bands at candidate
`7329cbaa5f1a7590f580e6f952f2c5fe69ca8491`, using a clean source checkout at
the exact infra pin and this exp checkout's own frozen environment. All four
receipts resolve V3, no native analysis binding and empty model-advice routing.
This certifies preparation, not deployment of the systemd launch command.

## Real bounded recovery witness

The operator explicitly authorized sending controller V3 and synthetic drill
instructions to OpenAI. Two Codex 0.154.0 / gpt-5.6-sol medium invocations on an
idle reserved H100 completed in **34.92 s** and **35.28 s**, each below its
100-second cap. Production `_run_once` verified/appended the strategy locally;
SSH transported stdin to the remote research account. The deployed systemd
supervisor was not replaced or started by this drill.

The first session read the declaration and strategy and saved a short
continuation summary. The second fresh session read that summary, actually
reopened both files, computed the expected strategy hash, and recorded
`dedicated_data_analysis_enabled=false` and `model_advice_enabled=false`.
Transcript command-execution records, not only the final model answer, were
checked. Expected V3 SHA-256:
`9fdacff8154c82dc003474c49475c9d1f9c3dcf6d0cc67dfcf3f53a4c720e9f0`.

No training, inference, scoring or formal experiment clock ran. The synthetic
remote fixture was removed after local evidence collection. This witnesses
fresh-session recovery, not internal CLI compaction, permanent attention or
strategy quality.

## Deployment boundary

Read-only checks found obsolete Full input-only analysis views still readable
by the research account on all four reserved hosts. All 20 derived files were
removed after exact-path, band/count, idle-service, symlink and mount checks.
Public training and original private validation data were preserved; existing
private target reads remained denied. No other experiment hosts were changed.

Machine receipts and transcripts remain in the operator's local Nebius
inventory evidence directory, outside Git. Before formal launch, install the
reviewed release, assemble protected NoPrior bindings plus V3, confirm the
actual supervisor command passes `--prompt-supplement`, and check permissions
and recovery state on every host. This report does not mark formal launch ready.
