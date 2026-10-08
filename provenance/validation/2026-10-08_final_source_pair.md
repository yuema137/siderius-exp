# Final release source-pair qualification

## Exact pair and installation

- Infra: `faff23aad38a2892160f64a4f3cefe1c9d6c3632`.
- Exp source used by the checks: `390dcd75f18510c267f589636ce5c5313fca51dc`.
- Evidence: [portable receipt](2026-10-08_final_source_pair.json).

SIDERIUS_REVISION, pyproject.toml and uv.lock agree. Normal VCS installation
records the declared public URL and exact commit in direct_url.json; it is not
an editable/local-path dependency. Before public synchronization, a process-only
Git URL rewrite supplied the identical local Git object to uv. Frozen offline
sync and lock verification then passed. No persistent Git configuration, manual
cache injection, network download or unrelated dependency upgrade was used.
The only other lock delta is the declared preflight package 0.1.0 to 0.2.0.
This is internal source qualification, not proof that the commit is already
fetchable from the public mirror. Public installation requires a separate
post-synchronization check.

## Checked behavior

| Check | Result | Boundary |
| --- | --- | --- |
| Historical rendering | 47 matching requests; four matching proposer routes | Recovered request inputs, not full historical conversations |
| Historical static estimation | 104 guarded CPU tests, including 45 arithmetic and 32 batch decisions | Historical static_only; protected GPU policy unselected |
| Tutorial source checks | 112 tests passed | CPU fixtures and command generation; no real launch |
| TESS and TIDMAD external projects | Initialization and saved-script previews passed | No dataset arrays read or HDF5 hashes checked |
| Project8 and LIGO external projects | Preparation and saved-script previews passed | Existing source data; 512 training and 1000 validation rows per task |
| Pet external project | Initialization and saved-script preview passed | 814 declared image paths present; pixels not decoded |

Project8 preparation produces the selected time/frequency representation;
LIGO preparation uses its existing declared representation. Data and generated
projects remain outside the repositories. No existing run workspace was reused.
API, GPU, training and download counts are zero. The saved previews display
commands and check their declared prerequisites; they do not establish model
execution, authentication, driver readiness or a score.

The [rendering report](../../experiments/shared/prompt_compat/qualifications/final-pair/report.md)
and [static-estimation report](../../experiments/shared/preflight_compat/qualifications/final-pair/report.md)
record their own identities and precise exclusions. Scientific task packages,
paper configurations, frozen fixtures and archived records were not rewritten.
Tutorials remain small learning demos, not one-command reproduction of paper
artifacts. Real onboarding and final public-source installation are separate
release checks.
