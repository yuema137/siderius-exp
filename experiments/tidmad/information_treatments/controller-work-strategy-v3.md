# Controller work strategy advice V3

**Audience:** the external coding agent in the strategy-advice-on condition.
This advice concerns how to organize research. It grants no additional data
access, tool capability, compute, evaluation permission or time. Follow the
current task package, treatment declaration and resource limits.

## Organize independent work when useful

Choose the order and granularity of work from the current evidence. Use serial
execution when one step depends on another. When useful, independent agents or
tool calls may investigate separate questions, implement separate candidates,
or review permitted evidence concurrently. Give each concurrent effort its own
working directory and outputs; coordinate changes to shared state explicitly.

Use observed resource consumption to decide how much concurrency is worthwhile.
Account for shared compute, memory, provider limits and remaining wall time.
Avoid duplicating work that is unlikely to add information. Parallel execution
is an option, not a required pattern or a goal by itself.

## Adapt exploration to evidence and measured cost

Use inexpensive checks to resolve uncertainty before committing substantial
resources. Decide what to expand, stop, retry or replace using completed
results, validity checks, failure evidence and measured execution cost.
Distinguish a transient service failure from an unsupported capability when
deciding whether to retry an available tool.

Keep candidate configurations, outputs and provenance separate so comparisons
remain interpretable. Reassess the plan when new evidence arrives; avoid
following an unchanged schedule after its assumptions no longer hold.

## Reserve time to finish

Track remaining wall time and allow for integration, required evaluation and
submission. Use completed valid evidence when selecting the final deliverable.
Do not spend the entire budget on unfinished exploration or assume that
background work will complete after the deadline.
