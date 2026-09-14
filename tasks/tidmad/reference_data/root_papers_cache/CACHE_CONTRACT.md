# Literature cache contract

The literature-review node keys a cache entry by the sanitized `paper_id`.
For example, `arxiv:2406.04378` becomes
`arxiv_2406.04378.json`. Each entry is a validated `RetrievedPaper` record.
The cache is an optimization only: a miss resolves the configured root paper,
and a hit returns the stored record. There is no automatic invalidation when a
prompt or schema changes; remove the relevant ignored JSON file to force a
fresh resolution.

The cache is intentionally not committed. Its contents depend on the resolver
and are runtime evidence rather than task identity. The task composition and
literature configuration remain the authorities for what paper is required.
