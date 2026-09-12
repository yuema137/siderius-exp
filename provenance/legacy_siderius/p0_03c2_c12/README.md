# Preserved C12 historical driver

This directory is a non-live source-preservation archive for the fixed C12
driver retained before the infra03D cleanup. `runtime_campaign.py` is not a
supported generic campaign entry point, is not imported by production code,
and is intentionally outside live pytest collection.

The source is preserved byte-for-byte from the accepted infra checkout at
`8ce8366f5d9149cddb05e83eee5da41641789cc7`, where it was tracked as
`scripts/runtime_campaign.py`. No runtime outputs, data, caches, or secrets
are included.
