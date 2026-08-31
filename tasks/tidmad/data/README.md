# `data/` — TIDMAD data root (nothing is stored here)

No dataset lives in this directory, and nothing in this pack downloads one
(roadmap §22.23.10). The TIDMAD HDF5 files are acquired from the official
distribution named in `../PROVENANCE.md` into a **machine-local**, read-only
directory. Every experiment or campaign names that directory explicitly:

```bash
--data_dir /path/to/TIDMAD
```

The campaign preflight and chain launcher validate the directory before any
run spends compute. Which files exist and how they are named is projected
read-only in `../resolved/identity.json`.

That is what the qualification experiment launcher requires, and it is why the
command published in `../README.md` reproduces on any machine: the caller
selects its own data root instead of depending on framework state.

Prepared/derived data, caches and run artifacts belong to the workspace
(`--workspace`, default `./siderius_workspace`, gitignored) — never to the
tracked example tree.
