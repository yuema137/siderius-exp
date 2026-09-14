# Literature paper cache

This folder is a machine-local cache used when the TIDMAD literature review
reads a root paper. It is not a task-authoring surface and it is not needed to
understand or run the task with a prepared literature configuration.

Cache files are ignored by Git. They may be created in a workspace during a
run and can be removed when a fresh paper resolution is required. Raw papers,
credentials, and generated results must stay outside the repository.

For the exact cache key, file format, and refresh behavior, see
[`CACHE_CONTRACT.md`](CACHE_CONTRACT.md). For the human task overview, return
to the [TIDMAD task page](../../README.md).
