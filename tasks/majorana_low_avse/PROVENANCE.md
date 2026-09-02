# Provenance — Majorana Low-AvsE classification

- Dataset: *Majorana Demonstrator Data Release for AI/ML Applications*
- Zenodo record: 8257027
- DOI: `10.5281/zenodo.8257027`
- Root paper: arXiv `2308.10856`
- Release: Zenodo partial release, version 1.0; not the complete DataPlanet set
- Local authority during qualification: `/home/klz/Data/MAJORANA`

On 2026-09-02 all 25 local files were hashed and matched the MD5 values and
byte sizes returned by the official Zenodo API. The supervised package uses 16
Train files (1,040,000 unique events) and 6 Test files (390,000 unique events).
Their `id` sets have zero overlap. The three NPML files have no labels and are
excluded from supervised execution.

Observed `psd_label_low_avse` counts are 575,257/464,743 in Train and
215,707/174,293 in Test. Exact 25-keV within-bin balancing retains 789,750
Train and 296,998 Test events before experiment portions are applied.
