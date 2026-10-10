# Historical watchdog policy presentation

## Scope and ownership

Infra #683 separates declared watchdog ceilings from forecast-based tightening.
The native `budget-ceiling-v1` policy respects declared ceilings; explicit
`forecast-tightening-v1` retains the original deadline algorithm, including its
floor. Deadline policy belongs to execution, not the runtime-verifier plugin.

The eleven paper units already declare `--no-runtime_watchdog`. The archive
audit found 333 saved runtime policies with watchdog disabled, including all
eight TIDMAD units. Their 130 workspace locks do not record watchdog-specific
settings. Launch declarations and saved policy files establish the old setting;
missing lock fields alone do not establish compatibility. Original archives,
source bindings and scientific settings remain unchanged.

New frameworks serialize `watchdog.deadline_policy` even when watchdog is off.
The explicit v10 planner profiles remove this additive metadata from a copy of
the history used to render a historical prompt. Persisted records retain the
new evidence. V10 composes the existing v9 manual, v8 timing and earlier
historical representations; it does not replace their algorithms or defaults.

| Incoming watchdog evidence | Historical view |
| --- | --- |
| Original complete six-field shape | Unchanged |
| Disabled, either known deadline policy, no new budget field | Remove only `deadline_policy` |
| Enabled, explicit `forecast-tightening-v1`, no new budget field | Remove only `deadline_policy` |
| Enabled native policy | Refuse: its deadline semantics differ |
| New metadata with an unknown policy/field, partial shape, supplied budget field or invalid value | Refuse |

The optional `budget_seconds` field is omitted by the producer when absent.
A supplied field, including explicit null, is not the qualified producer shape.
Strict schema validation rejects coerced values in the new metadata shape.
Original six-field records pass through without retroactive validation; this
preserves evidence, not permission to execute an invalid configuration.
A numerical budget, timing,
forecast, score or validity result is never altered by the projection.

## Selection and new workspaces

Install the paired compatibility packages into the selected qualified framework's
own environment using the [installation instructions](usage.md#install-into-the-environment-that-will-run-infra).
Planner package 0.11.0 adds these explicit selectors; existing selectors and
installation defaults remain unchanged:

| Recorded lineage | Planner strategy |
| --- | --- |
| TESS, LIGO, TIDMAD NoPrior | `legacy-9b78d505cb11-paper-watchdog-v10` |
| Project8 dual, TIDMAD analysis-on | `legacy-9b78d505cb11-paper-late-watchdog-v10` |

Apply `paper-watchdog-v1.json` to a copied experiment and LLM configuration.
It extends `paper-epoch-caps-v1.json`, preserving eleven run/revision/launch
mappings, measured admission, verifier selections and all three explicit
100-epoch caps. Its common flags explicitly retain disabled watchdog. Recorded
run IDs identify evidence; choose a new execution ID and external workspace.
This overlay is not a complete launcher or permission to launch.

Keep old workspaces bound to their original framework and installed packages.
Do not change their locks or infer that an unchanged selector permits resume.
Source qualification changes inherited identities; v10 additionally owns its
projection source, inherited v9 identity and a separate qualification of the
actual imported deadline helper and policy alias. Session and tuner producer
sources remain bound by the existing runtime assembly. Unknown helper changes
refuse rather than trusting a policy name alone. The exp root installation pin is
unchanged, and installation alone does not qualify a new framework assembly.

## Offline verification

`capture_watchdog_history.py` calls the real `LLMBridge.plan` with each paper's
archived task inputs and registered, digest-checked first model. It appends
explicitly synthetic history for disabled native, disabled legacy and enabled
legacy watchdog. Each original reference receives its old six-field shape;
the candidate receives new metadata and selects v10. Complete system/user
messages must match and the supplied history must remain unchanged.

These are deterministic request-boundary comparisons, not recovered historical
conversations, model behavior tests or training replays. Network/provider/scoring
access is forbidden and no dataset is loaded. The historical enabled witness
checks the shared renderer branch; it does not imply any paper enabled watchdog.

Set `EXP_CHECKOUT`, `INFRA_CHECKOUT`, `REVISION`, `CASE`, `MODEL_PLUGIN` and
`PROFILE` to the selected verified sources, archived model and matching v10
selector, then capture into a fresh directory:

```sh
OUTPUT=$(mktemp -d)
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/planner_compat/capture_watchdog_history.py" \
  --case "$CASE" --model-plugin "$MODEL_PLUGIN" --revision "$REVISION" \
  --profile "$PROFILE" --output "$OUTPUT/candidate"
```

Run the same tool with the task's original framework environment and revision,
without `--profile`, into `$OUTPUT/reference`. Compare all `*-system.txt` and
`*-user.txt` bytes. Receipts bind the fixture, tool and framework identities.
Keep full request files outside the repository; qualification records contain
only compact results and source fingerprints.

## Executed qualification

The [compact receipt](qualifications/watchdog-policy/receipt.json) binds the
qualified framework and compatibility package versions. The separate
[archive audit](qualifications/watchdog-policy/archive-audit.json) records the
333 saved policies, 130 locks and eleven launch declarations without publishing
local archive paths or request text.

On final framework `597350da45b5559e7a32ed93be337cddc3d5a1f8`:

- 186 targeted offline tests passed, including 25 v10 cases. Those cases include
  23 actual session reconstructions checked against frozen component digests,
  admission decisions and historical policies.
- Twelve full planner requests matched fresh executions of the four original
  reference checkouts. All captures used isolated plugin/generated-model
  directories. LIGO's reference uses the existing frozen Formal appendix, which
  its original planning producer supplied before the bridge call.
- Four original paper startup message pairs matched through v10 with the current
  production manual. Source/child identity and unknown-assembly checks passed.

The 47 existing prompt boundaries matched freshly executed original references
at the preceding reviewed candidate `c6cfb842`. Twenty reflector requests also
matched preserved original-reference full bytes after verifying their fixture
and tool digests. The final change only makes a runtime-policy constructor
explicitly typed; its source is outside the rendering closure. All 162 rendering
source files and the installed prompt profile identity are unchanged. These
checks establish the same rendering source, not a claim that the earlier
captures executed at the final revision.

Historical v8 session-presentation checks belong to their older producer shape;
v8 intentionally does not remove the new watchdog metadata. V10's session and
request checks establish the new pairing. Original profiles and their fixtures
are retained. No LLM calls, GPU work, dataset downloads or training occurred.
