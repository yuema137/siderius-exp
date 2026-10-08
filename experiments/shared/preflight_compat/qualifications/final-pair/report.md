# Final-pair historical static qualification

## Result

Preflight compatibility 0.2.0 qualifies assembly
`59107d905aa655d0eb1013979405075ac3006b0f1883eb842983a9c85f7b380c`
at infra `faff23aad38a2892160f64a4f3cefe1c9d6c3632` for historical
`static_only` with `gpu_execution_policy` unselected.

[Source review](source-review.json) records the estimator closure changing
from 58 to 77 members: 19 added members and 22 changed existing members.
Static arithmetic and batch-search owners remain byte-identical; newly measured
and protected paths are outside this qualification.

[Receipt](receipt.json) records normal installations into both candidate
checkout environments, identical parent/child identities and unknown-assembly
refusals. The focused guarded CPU cohort passed 104 tests, including all 45
frozen arithmetic cases and 32 batch decisions, historical/combined projections,
configuration and installation checks. The guard forbids optimizer updates;
the existing tiny CPU observation check is not a training run. No API or GPU
calls were made. Exp package source was
`390dcd75f18510c267f589636ce5c5313fca51dc`; subsequent receipt/docs changes do
not alter it.

## Limits

`drop_last=False` producer geometry intentionally follows corrected current
code. The earlier paper audit joined 25 of 26 Project8 False configurations;
one lacks geometry evidence. This qualification does not invent that missing
case or promise universal historical producer/training parity. Historical
static presentation combined with the new protected GPU policy is not qualified.
Current tutorials use native estimation; installing this package does not select
historical estimation implicitly.

Frozen reference fixtures and prior evidence remain unchanged. Existing
unknown-source, modified-source and unsupported-evidence refusals remain in
place. Re-run the existing tests and [installation procedure](../../README.md)
in the exact selected checkout environments. Use a new workspace when adopting
the changed compatibility identity; do not rewrite archived locks.
