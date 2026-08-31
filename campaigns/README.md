# Campaigns

Campaigns compose one or more experiments into multi-stage or multi-arm work.
They own cross-run authorization, stage transitions, arm or band topology,
campaign-wide frozen treatment, and result-selection protocols. A single
workflow treatment belongs under `experiments/`, not here.

The presence of a campaign does not authorize execution. Each campaign records its own operator authorization boundaries.
