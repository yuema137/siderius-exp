# Provenance — SuperNEMO signal-background classification

## Source

- Zenodo record: <https://zenodo.org/records/20698789>
- DOI: <https://doi.org/10.5281/zenodo.20698789>
- Title: *SuperNEMO Dataset for 0vbb AI Summer School - UC Irvine, USA
  (20-21 June 2026)*
- Creator: Miroslav Macko, on behalf of the SuperNEMO Collaboration
- License: CC BY 4.0

## Data artifacts

| File | Bytes | Zenodo MD5 | Process | Events |
|---|---:|---|---|---:|
| `data_0nubb_merged.h5` | 4,573,397,944 | `8109782ce2a90b5246a8fca9ed097bf8` | signal | 1,987,942 |
| `data_2nubb_merged.h5` | 7,121,195,308 | `f15e7cba4e0562d3e2644d1e571c180a` | background | 3,284,115 |
| `data_Bi214_merged.h5` | 5,847,162,948 | `2e93e8b928ce5a074ee62d4754c564de` | background | 2,634,001 |
| `data_Tl208_merged.h5` | 5,514,190,096 | `3a67f2d346f01d886e3c6707ef226658` | background | 2,549,142 |

The four files were downloaded to TestPod permanent storage on 2026-09-02.
Each download command verified the corresponding Zenodo MD5 before exiting.
Dataset bytes are not tracked by Git.

## Identity and leakage boundary

`ev_no` is local to a process file. The task therefore treats
`(process, ev_no)` as the event identity. The executable profiler verifies
strictly increasing event IDs within each process, consistent event-level
features across every adjacent hit pair, and pairwise-empty train,
validation, and test identity intersections.

