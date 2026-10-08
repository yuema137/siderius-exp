# Gold Stage 1 workflow

This campaign directory owns the production Gold Stage 1 treatment. It is
intentionally separate from bounded qualification. The stopped v0.1.4 campaign used the
calibrated Health policy in `health_checks.yaml`, whose only blocking check is
`amplitude_collapse`.

The [August 2026 dry-run witness](../../../../provenance/validation/2026-08-30_tidmad_gold_external_dry_run.md)
confirmed that Stage 1 selected the requested framework checkout and campaign
files, and that unauthorized Stage 2 was refused. It did not run training or
qualify an H100 workload.

Gold remains stopped and unauthorized. Before any new launch, qualify deployment
preflight, runtime-profile binding, persistent storage, dataset availability,
the four-H100 topology and the final source revision, then obtain campaign
authorization. The dry-run record alone is not permission to start.
