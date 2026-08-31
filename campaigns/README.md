# Campaigns

Campaigns compose one or more experiments into multi-stage or multi-arm work.
They own cross-run authorization, stage transitions, arm or band topology,
campaign-wide frozen treatment, and result-selection protocols. Each campaign
unit still selects a workflow; campaign status does not redefine that
workflow's Trial/Formal semantics.

The presence of a campaign does not authorize execution. Each campaign records its own operator authorization boundaries.
