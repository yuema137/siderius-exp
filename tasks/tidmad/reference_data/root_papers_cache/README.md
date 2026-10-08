# Literature paper cache

This tracked directory documents the legacy cache location. The native fixed
workflow stores extracted root-paper records in the run workspace instead:

```text
<workspace>/cache/literature/root_papers/
```

Use the `workspace` selected by your saved experiment. Inspect entries there
when checking what a literature review reused. To request a fresh resolution,
remove the relevant entry from that workspace cache before the next review;
the tracked task directory is not the active cache. For example, the root paper
`arxiv:2406.04378` uses `arxiv_2406.04378.json`.

The [pinned native caller](https://github.com/yuema137/SIDERIUS/blob/52373be9a52bead36fd1f15d706385967e0a129d/src/workflows/model_exploration.py#L2826-L2833)
supplies this workspace path to the literature-review node. Cache entries are
runtime evidence, not task-authoring inputs. Keep raw papers, credentials and
generated results outside the repositories.

For the exact cache key, file format and refresh behavior, see
[the cache contract](CACHE_CONTRACT.md). For the human task overview, return
to the [TIDMAD task page](../../README.md).
