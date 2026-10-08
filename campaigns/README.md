# Campaigns

A campaign coordinates several experiment runs, such as different bands or
conditions. An experiment defines one run; a campaign defines how runs are
organized and compared. **Looking for a small runnable demo? Start with the
[tutorials](../tutorials/README.md).**

## Find a campaign

| Campaign | Current state | Planned deployment intent |
|---|---|---|
| [TIDMAD Gold](tidmad_gold/README.md) | stopped; not authorized | four-H100 campaign pool |
| [Oxford-IIIT Pet](oxford_iiit_pet/README.md) | planned; not launchable | shared contrast-task H100 pool |
| [DAVIS](davis_future_prediction/README.md) | planned; not launchable | shared contrast-task H100 pool |
| [Cancer](cancer_gene_identification/README.md) | planned; not launchable | shared contrast-task H100 pool |

A script or recorded workspace does not authorize a new launch. Check the
selected campaign's authorization for both launching and moving between stages.
Deployment intent identifies the requested hardware pool; it does not set a
schedule, concurrency, budgets, iteration counts or scientific treatment.

## Define a campaign

Use the [campaign template](CAMPAIGN_TEMPLATE.md) for the required task,
workflow, treatment, topology, selection, authorization and provenance fields.
Each run still follows its selected workflow's Trial/Formal rules. Hardware
assignment belongs to deployment configuration, not scientific task declarations.

## Retired campaigns

[TIDMAD X9](tidmad_x9/README.md) is retired. Its execution scripts and dedicated
tests were removed; the notice links to historical source. Use the tutorials
above for current workflow demos.
