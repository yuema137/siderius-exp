# Legacy SIDERIUS test archive

This directory preserves historical real-task tests removed from the SIDERIUS
framework repository during framework/experiment separation.

These files are provenance, not the current `siderius-exp` test suite. They
may depend on historical repository layouts, machine paths, task defaults,
seeds, APIs, or resource treatments. Reproduction requires the recorded
historical SIDERIUS revision and an explicit compatibility review. Current
task qualification lives under `tests/` and uses external task packages
against an exact pinned framework revision.

`test_c2_prephase_validation.py` and `test_c2_documentation_sync.py` preserve
the complete pre-split C2 harness and Gate-documentation oracles. Their
pre-move SHA-256 identities are
`143f5d1bd101f53c7cd612f0a8c5c4d79fa979b2524ea90812de1192cf82c0c1` and
`23058b02c45c7d6194a44dc79cbc32d3edc9622cad15755ff82b999e2b3f6b31`.
They are provenance-only; current generic stability tests remain in SIDERIUS.
