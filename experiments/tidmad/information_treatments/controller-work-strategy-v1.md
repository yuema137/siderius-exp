# Controller work strategy advice V1

**Audience:** orchestration and general coding agents. Apply this advice on top
of the separately declared model research advice. Do not provide it to the fixed
workflow, whose outer execution strategy is already controlled by the workflow.
This advice grants no additional data access, compute or evaluation authority.

Use the available wall time, compute, memory and agent capacity to maximize the
best valid scientific score, with the strongest available baseline as the main
performance reference. Choose the work pattern adaptively rather than following
a fixed schedule.

When useful and safe, run independent work in parallel. Sub-agents may propose
different model hypotheses, perform separate authorized data analyses, implement
and test separate candidates, and review results concurrently. Avoid
oversubscribing the GPU, duplicating low-information work, or allowing concurrent
jobs to overwrite shared state; preserve each candidate's configuration, evidence
and provenance.

Combine inexpensive probes and small experiments that reduce uncertainty with
fewer larger experiments that can realize the most promising ideas. Use measured
cost, score, Health and scientific evidence to decide what to expand, stop or
replace. Reserve enough time for integration, full evaluation and submission of
the strongest valid candidate. Parallelism and experiment scale are tools, not
targets; use them only when they improve the chance of exceeding the baseline.
