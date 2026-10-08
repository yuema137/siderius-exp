# v1.0.0 metadata and installation qualification

The consumer version advances from `0.0.0` to `1.0.0` and pins framework
`52373be9a52bead36fd1f15d706385967e0a129d`, whose package version is now
`1.0.0`. This prepares release metadata for final review. It does not create a
tag, release or public synchronization.

The framework commit changes only its `pyproject.toml` and generated `uv.lock`
version entries. Parsed TOML comparison confirms no other metadata or dependency
changes. Its complete `src` and `configs` Git trees equal the qualified
`b13b9263` trees. The consumer's parsed metadata and lock differ only in its
version, the framework version and the exact framework pin. The existing README
framework-source link follows that pin.

[receipt.json](receipt.json) verifies all four canonical source sets directly:
18 runtime members, 78 preflight members, 158 rendering members and 10 planner
members. Their membership, source bytes and assembly identities equal the
[previous qualification](../2026-10-08_standalone_inference_release/report.md).
Installed framework bytes match those sources. The four compatibility packages
retain their versions and all 51 installed source files; their parent/child
identities in both checkout-owned environments exactly match the earlier
receipt. No qualification row or historical receipt was changed.

The consumer's own environment was synchronized with
`uv sync --group dev --frozen`, followed by normal installation of the selected
compatibility packages. Installed framework metadata reports `1.0.0` and the
exact new Git SHA. The existing dependency-pin test passes. The consumer remains
a virtual uv project (`tool.uv.package=false`); its version is recorded in
`pyproject.toml` and the lock, with no installed consumer distribution claimed.

The earlier 47-request/94-body comparisons, 44 routes and 36+143 tests remain
applicable within their recorded scopes because their source assemblies and
scientific inputs are unchanged. Those corpora were not rerun for metadata.
No API, GPU or training campaign ran. Resumed model-preparation accounting
remains deferred under infra issue #673.

Dependency fetching used the approved command-scoped rewrite from the declared
public URL to the development repository. Public-host availability and the
operator's final release gates remain separate checks.
