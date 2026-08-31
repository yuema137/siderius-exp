# Campaigns

Campaigns compose one or more experiments into multi-stage or multi-arm work.
They own cross-run authorization, stage transitions, arm or band topology,
campaign-wide frozen treatment, and result-selection protocols. Each campaign
unit still selects a workflow; campaign status does not redefine that
workflow's Trial/Formal semantics.

The presence of a campaign does not authorize execution. Each campaign records its own operator authorization boundaries.

## Campaign package contract

Each campaign package must identify:

- the task or tasks it coordinates;
- the workflow selected by each run unit;
- the experiment treatment or other frozen run inputs used by each unit;
- the arm, band, stage, or repetition topology;
- the authorization boundary for launch and stage transitions;
- the cross-run result-selection protocol;
- the deployment profile it requests; and
- the campaign-owned state, results, and provenance locations.

A campaign selects workflows; it does not redefine Trial or Formal. Hardware
assignment is deployment policy and must not be hidden in task declarations or
scientific treatment files.

## Current campaign packages

| Campaign | Status | Planned deployment intent |
|---|---|---|
| [`tidmad_gold`](tidmad_gold/) | existing; stopped | four-H100 campaign pool |
| [`oxford_iiit_pet`](oxford_iiit_pet/) | planned; not launchable | shared contrast-task H100 pool |
| [`davis_future_prediction`](davis_future_prediction/) | planned; not launchable | shared contrast-task H100 pool |
| [`cancer_gene_identification`](cancer_gene_identification/) | planned; not launchable | shared contrast-task H100 pool |

Deployment intent records ownership only. It does not freeze concurrency,
budgets, iteration counts, treatment values, or scheduling order.

Use [`CAMPAIGN_TEMPLATE.md`](CAMPAIGN_TEMPLATE.md) when creating a campaign.
