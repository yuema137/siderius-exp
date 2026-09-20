# PhyTS TESS information treatments

These small files say what information an experiment gives to its research
agent. They do not change the TESS task, data, metric or validity rules —
every treatment here selects the same task package, `tasks/phyts_tess`.

| treatment | advice | Data Analysis | state |
|---|---|---|---|
| [`main-fixed-no-prior.yaml`](main-fixed-no-prior.yaml) | disabled | disabled | available |
| `main-fixed-full.yaml` | enabled | enabled | **not written yet** |

## The no-prior arm

`main-fixed-no-prior.yaml` declares the absence explicitly rather than
leaving it implicit: `advice.mode: disabled` with null artifact, sha256 and
content type, and `modules.data_analysis.siderius: disabled`. The SIDERIUS
adapter renders that module state as `--no-data_analysis_enabled`; the flag
is derived from the treatment field rather than from a second experiment
switch, so the two can never disagree.

Literature review stays `enabled`. It is a different information channel from
human advice, and turning it off would make this arm a two-variable change
rather than the single "no operator prior" contrast it is meant to be.

## The full-prior arm is deliberately absent

Writing it needs one thing this repository does not yet hold: the frozen
advice artifact itself, whose content is per-node scientific guidance the
operator owns. Declaring an `enabled` treatment without it would not merely
be incomplete — the schema refuses an enabled advice block with a null
artifact or sha256, so a placeholder cannot be committed and later forgotten.

When that artifact exists, the arm is three things: the JSON beside the
experiment, its sha256 in a new `main-fixed-full.yaml`, and
`modules.data_analysis.siderius: enabled`. Nothing else changes; both arms
select the same composition and the same workflow parameters.
