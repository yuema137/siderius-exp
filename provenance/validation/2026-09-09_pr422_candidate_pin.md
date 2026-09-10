# PR #422 candidate-pin validation

## Scope and identities

This is a CPU-only external-consumer checkpoint, not a campaign or release
qualification. The experiment dependency advances from `e16ac4e8` to SIDERIUS
`655bcd258f6a54f5052b83bbb48a1dabd7845f0b`. `SIDERIUS_REVISION`, `pyproject.toml`,
and both framework references in `uv.lock` agree. No other locked dependency,
scientific task, campaign parameter, or runtime result changes in this update.

The checkout is `/home/yuema137/siderius-exp-current`, on the existing
`recovery/persist-demo-run-records` branch. Its own `.venv/bin/python` was used.
The installed distribution's `direct_url.json` commit and the interpreter prefix
were independently checked against the pin and this checkout's `.venv`.

## Environment

Run from the experiment repository root:

```bash
uv lock
env -u VIRTUAL_ENV uv sync --group dev --frozen
```

The original sync completed successfully while warning that an inherited foreign
`VIRTUAL_ENV` was ignored; no foreign environment was used. The command above
removes that irrelevant ambient setting explicitly. Runtime data and generated
test outputs remain in pytest temporary directories, outside the repository.

## Migration cohort

```bash
env -u PYTHONPATH -u VIRTUAL_ENV CUDA_VISIBLE_DEVICES='' \
  .venv/bin/python -m pytest --import-mode=importlib -p no:cacheprovider \
  tests/tasks/test_health_evidence_parity.py \
  tests/tasks/tidmad/test_d14_tidmad_parity.py \
  tests/tasks/tidmad/test_health_legacy_compatibility.py \
  tests/tasks/tidmad/test_deliverable_encoding_parity.py \
  tests/tasks/tidmad/test_validation_materialization_boundary.py \
  tests/tasks/tidmad/test_streamed_inference_persistence.py \
  tests/tasks/tidmad/test_historical_health_composition_parity.py \
  tests/tasks/tidmad/test_child_inference_deliverable_boundary.py \
  tests/tasks/tidmad/test_comparison_ordering_boundary.py -q --tb=short
```

Result: **40 passed in 4.33 seconds**. This includes the immutable D14 hashes,
historical Health policy/role oracles, full logical writer artifacts, validation
materialization failures, comparison ordering, and an actual CPU inference child
that persists two channels with independently checked complete values.

## Pin and external task contracts

`SIDERIUS_CHECKOUT` must identify a clean checkout at the exact pin. In this
validation it was `/tmp/SIDERIUS-pin-18557e60`; replace that location when
reproducing, not the revision. The startup test explicitly loads that checkout
in its child, and verifies source authority. The migration cohort above instead
uses the experiment environment's installed pinned distribution.

```bash
env -u PYTHONPATH -u VIRTUAL_ENV CUDA_VISIBLE_DEVICES='' \
  SIDERIUS_CHECKOUT=/tmp/SIDERIUS-pin-18557e60 \
  .venv/bin/python -m pytest --import-mode=importlib -p no:cacheprovider \
  tests/test_external_startup_preflight.py \
  tests/tasks/tidmad/test_tidmad_package_contract.py \
  tests/tasks/oxford_iiit_pet/test_package_contract.py \
  tests/tasks/davis_future_prediction/test_davis_package_contract.py \
  tests/tasks/cancer_gene_identification/test_cancer_package_contract.py \
  tests/tasks/supernemo_signal_background/test_package_contract.py \
  tests/tasks/majorana_low_avse/test_majorana_package_contract.py -q --tb=short
```

Result: **37 passed in 20.50 seconds**, with no GPU or LLM execution. An initial
combined invocation using pytest's default import mode refused collection because
Pets and SuperNEMO both have `test_package_contract.py` in non-package test
directories. Explicit `--import-mode=importlib` resolves the module-name collision
without skipping either module. Bare/default-import suite collection is not
certified by this result; preserve the explicit invocation above.

## Review and remaining boundaries

The dependency diff changes only the exact framework reference. The historical
goldens were not regenerated; test inputs/outputs, secrets, checkpoints, and raw
data are not committed. No scientific config changed and no task was launched.
Existing tracked framework/package and external-scope issues remain separate;
these focused passes do not replace final framework CI or release qualification.

## Final test-only candidate alignment

The final replay advances the exact pin from
`655bcd258f6a54f5052b83bbb48a1dabd7845f0b` to
`66d3edf2b2045eaf037fb5cc9ecb3dffee94523b`. Independent `git diff --name-only`
inspection confirms the intervening framework changes contain only three test
files and its separation ledger: no production source, package definition, or
scientific treatment changes. The tests repair stale Health fixture signatures
and isolate Quickstart manifest variants from inherited task registrations.

The same two exact command blocks above were rerun with the same checkout paths,
now at the new pin, after `env -u VIRTUAL_ENV uv lock` and
`env -u VIRTUAL_ENV uv sync --group dev --frozen`:

- Migration cohort: **40 passed in 4.24 seconds**.
- Pin and six external-task contracts: **37 passed in 20.56 seconds**.
- Installed `direct_url.json`, `SIDERIUS_REVISION`, `uv.lock`, and the own-venv
  interpreter prefix agree; only the framework revision changed in the lock.

No GPU/LLM workload was launched. No historical oracle, experiment configuration,
raw data, or runtime output changed. Final framework CI remains a separate
acceptance gate; this record certifies the synchronized external-consumer pair.

## Framework PR closure and final complete CI

SIDERIUS [PR #422](https://github.com/Galileo-Sandbox/SIDERIUS/pull/422) merged
as `2091acdfcb24eb9c8d3953ee7ba1e3ba99926aa0`, preserving its commit history.
The experiment pin remains `66d3edf2b2045eaf037fb5cc9ecb3dffee94523b`:
`git merge-base --is-ancestor` succeeds and `git diff` from that pin to the
merge is empty. This is the qualified code now on framework master, not an
outdated implementation; no dependency or environment change is needed merely
to replace the exact tested ancestor with a merge commit containing the same tree.

The final [complete CI run](https://github.com/Galileo-Sandbox/SIDERIUS/actions/runs/34436551662)
finished **SUCCESS**. The primary implementing agent verified the actual CI merge
commit `2682a254` has the same tree as the candidate, with all 697 selected files
accounted for:

| Suite | Passed | Skipped | Failed | Errors |
| --- | ---: | ---: | ---: | ---: |
| Bulk | 11,573 | 21 | 0 | 0 |
| Sensitive | 184 | 0 | 0 | 0 |
| Total | 11,757 | 21 | 0 | 0 |

This completes the PR's framework CI gate in addition to the external 40 + 37
checks above. It is not a release or authorization to launch a scientific
campaign. Framework issues
[#423](https://github.com/Galileo-Sandbox/SIDERIUS/issues/423) and
[#424](https://github.com/Galileo-Sandbox/SIDERIUS/issues/424), and experiment issues
[#30](https://github.com/Galileo-Sandbox/siderius-exp/issues/30) and
[#31](https://github.com/Galileo-Sandbox/siderius-exp/issues/31) remain open;
this closure does not claim those deferred boundaries are fixed.

This final update changes only this validation record. The pin, lock, scientific
configuration, datasets, workspaces, and all runtime artifacts remain unchanged.
