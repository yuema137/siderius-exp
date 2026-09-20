# PhyTS TESS — main fixed workflow

One bounded treatment of [`tasks/phyts_tess`](../../../tasks/phyts_tess/):
the SIDERIUS reference workflow, one trial round and one formal round per
iteration, under a six-hour wall-clock budget on a single RTX 5090.

Two arms, differing **only** in what the agent is told:
`--arm no-prior` and `--arm full`. Both select the same composition and the
same workflow parameters — see
[`../information_treatments/`](../information_treatments/README.md).

## Preview the exact command

```bash
bash experiments/phyts_tess/main_fixed_workflow/launch.sh \
    --siderius-checkout /path/to/SIDERIUS \
    --data_dir /path/to/run-data \
    --unit_dir /path/to/unit \
    --run_name tess_nop_001 \
    --arm no-prior
```

Without `--launch` this prints the argv and exits. It starts no clock, spends
no budget and needs no provider key. Add `--launch` to start or resume.

Stage the data root first — [`tasks/phyts_tess/data/README.md`](../../../tasks/phyts_tess/data/README.md).
The unit directory must be **outside** both checkouts and outside the data
root; the supervisor refuses otherwise, because a unit writing into a
checkout would change the revision it claims to be running.

## The treatment

| knob | value | why |
|---|---|---|
| `--num_iterations` | 100 | deliberately unreachable; the wall clock is the real stop |
| `--max_rounds` | 2 | with `force_formal_round` and the trial pin below, exactly one trial then one formal |
| `--plan_overrides` | `{"is_trial": true}` | pins round 1 as a trial so the planner cannot make both rounds formal |
| `--trial_time_budget_minutes` | 5 | |
| `--formal_time_budget_minutes` | 15 | |
| `--trial_vram_budget_gb` | 8 | the card has ~31.8 GiB; 8 is the budget, not the capacity |
| `--formal_vram_budget_gb` | 8 | |
| `--formal_portion` | 1.0 | the whole training pool, no operator restriction |
| `--formal_eval_portion` | 1.0 | formal evaluation is always the full validation split |
| `--formal_training_scope_source` | `agent` | the agent owns the formal training portion |
| trial portions | **not passed** | omitted means agent-controlled; typing them would freeze them |

**Formal evaluation is operator-owned no matter what.** The framework flag's
own help says so, so the agent cannot shrink the formal evaluation set even
in principle. `--formal_eval_portion 1.0` states the intent as well as
relying on that.

## The six-hour clock

Written **once**, at first launch, into `<unit_dir>/launch.json`, and then
immutable. A restart — crash, operator resume, reboot — continues against the
same deadline. A unit that restarted three times must not quietly receive
three budgets, or no two units are comparable.

At the deadline the chain's **process group** is SIGKILLed, so a hung child
cannot outlive the budget. The stop is recorded as `deadline_stop` in
`<unit_dir>/events.jsonl` and is not a failure.

A permanent framework halt writes `workspace/.chain_halted`. That marker
survives restarts and is never erased here: erasing it would silently convert
a refusal into a retry budget.

## Checked before the clock starts

Provider key **presence** by name — values are never read or logged — and
exactly one GPU whose name contains `RTX 5090`. Both run before the clock is
created, so a missing key costs zero minutes. Key presence is not usable
provider access; a key can be present and still be rejected by the provider.

Which keys are required is derived from the **selected arm's own module
states**, not from a constant. A hardcoded exclusion would keep excluding
Data Analysis after an arm enabled it, and the run would then start without
the key it needs and fail after the clock had already begun.

Selecting an arm also certifies its treatment manifest and, on the full arm,
re-computes the advice digest from the same bytes it parses. An edited advice
file refuses the launch rather than running a different treatment under an
unchanged identity.

## Unit layout

```
<unit_dir>/
├── launch.json      write-once clock and preflight receipt
├── events.jsonl     append-only transitions
├── logs/chain.log   the chain's combined output
├── workspace/       the run workspace, including generated_library
└── calibration/     unit-local timing evidence, reused across resumes
```

`SIDERIUS_CALIBRATION_DIR` is bound here so a fresh unit cannot inherit
host-wide timing evidence from an unrelated run, while a resume continues
its own.

## Not yet done

No run has been executed. The preview path has been exercised; `--launch`
has not. Read [`../../../tasks/phyts_tess/STATUS.md`](../../../tasks/phyts_tess/STATUS.md)
for what the task package itself has and has not verified.
