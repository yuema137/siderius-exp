# Campaigns

Start here when work spans multiple runs, arms, bands, or stages. A campaign
page tells you whether execution is authorized; an experiment page tells you
what one run means. The presence of scripts, ledgers, or a workspace never
authorizes a launch.

| Campaign | Current state | Entry point |
|---|---|---|
| TIDMAD Gold | stopped; not authorized | [`tidmad_gold/README.md`](tidmad_gold/README.md) |
| Oxford-IIIT Pet | planned; not launchable | [`oxford_iiit_pet/README.md`](oxford_iiit_pet/README.md) |
| DAVIS | planned; not launchable | [`davis_future_prediction/README.md`](davis_future_prediction/README.md) |
| Cancer | planned; not launchable | [`cancer_gene_identification/README.md`](cancer_gene_identification/README.md) |

Campaigns compose one or more experiments into multi-stage or multi-arm work.
They own cross-run authorization, stage transitions, arm or band topology,
campaign-wide frozen treatment, and result-selection protocols. Each campaign
unit still selects a workflow; campaign status does not redefine that
workflow's Trial/Formal semantics.

The presence of a campaign does not authorize execution. Each campaign records its own operator authorization boundaries.

## Retired campaigns

[TIDMAD X9](tidmad_x9/README.md) is retired. Its execution scripts and dedicated
tests have been removed; the linked notice explains the boundary and where to
inspect historical source. Use the [paper tutorials](../tutorials/paper/README.md)
for current workflow demos.

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
