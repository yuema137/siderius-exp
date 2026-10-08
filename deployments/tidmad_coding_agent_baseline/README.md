# TIDMAD coding-agent baseline

Use this deployment to give a coding agent one TIDMAD waveform band and a
24-hour search budget. The evaluator keeps validation data private and scores
submitted models. The task's scientific rules come from the
[TIDMAD package](../../tasks/tidmad/README.md).

The main experiment runs each band independently. The older four-band package
is a diagnostic pilot; its storage and submission rules differ. The
[recorded September 2026 units](../../experiments/tidmad/coding_agent_baseline/)
retain their own source revisions and archive hashes.

<a id="before-renting-gpus"></a>

## Prepare one band

Start from clean, frozen exp and pinned framework checkouts. Before provisioning
an H100, choose the band and review the [main task](task-main-band.md) and
[information treatment](../../experiments/tidmad/information_treatments/main-cli-no-advice.yaml).
Build the package from the exp root:

```bash
.venv/bin/python -m \
  deployments.tidmad_coding_agent_baseline.tools.build_bundle \
  --task-md deployments/tidmad_coding_agent_baseline/task-main-band.md \
  --information-treatment \
    experiments/tidmad/information_treatments/main-cli-no-advice.yaml \
  --siderius-checkout /path/to/exact-pinned-SIDERIUS \
  --band 4-9 \
  --output /safe/bundles/tidmad-band-4-9.tar.gz
```

Replace `4-9` with the selected band. Conditions compared within that band must
receive identical archive bytes. Keep data, credentials and run outputs outside
the source repositories. Building an archive does not start or qualify a run.

## Install, check, then start

Follow the [operator procedure](operations.md#install-one-vm) to install the
private evaluator and stage verified data. Complete the
[H100 drill](operations.md#required-h100-drill) before scheduling the clock.
That procedure covers separate credentials, restart/reboot checks, cleanup and
the common start time. A passing local test does not replace the live drill.

## Submit a candidate

Inside the prepared agent machine, score a candidate for its allowed band:

```bash
tidmad-score candidate \
  --band 4-9 \
  --candidate-id my-candidate-001 \
  --candidate-source /work/agent/candidates/my-candidate-001
```

The evaluator retains eligible complete-band candidates. At the deadline it
selects the best retained candidate for that unit; a missing candidate remains
a partial submission. The [candidate contract](operations.md#scoring-and-submission)
lists required files and explains inference isolation and final collection.

## Find the next owner

| Need | Read |
| --- | --- |
| Visibility, VM resources and retained artifacts | [Deployment contract](operations.md#what-the-agent-can-see) |
| Exact install, service and recovery steps | [Operator procedure](operations.md#install-one-vm) |
| Scientific task and data meaning | [TIDMAD task](../../tasks/tidmad/README.md) |
| Past runs and their immutable inputs | [Experiment records](../../experiments/tidmad/coding_agent_baseline/README.md) |
