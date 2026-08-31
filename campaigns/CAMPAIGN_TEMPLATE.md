# Campaign Name

## Status and authorization

- Status: `planned | qualified | active | stopped | complete | invalidated`
- Launch authorization: `not authorized | authorized`
- Stage-transition authorization: describe each explicit boundary.

File presence is not authorization.

## Selected task and workflow

- Task package: `tasks/<task>/`
- Run-unit workflow: describe or link the workflow selected by each run unit.
- Frozen experiment treatment: link the experiment or frozen treatment input.

Trial and Formal remain workflow concepts. Do not redefine them here.

## Campaign topology

Describe only the required arms, bands, stages, repetitions, and cross-run
dependencies. Leave undecided values marked `TBD` rather than supplying defaults.

## Selection protocol

Declare how valid run results are compared and selected across campaign units.

## Deployment request

Reference a deployment profile. Do not embed hostnames, credentials, or
machine-specific paths in scientific task or treatment files.

## State and provenance

Declare campaign-owned workspace, state, results, and provenance locations.
Every run must record exact SIDERIUS and siderius-exp revisions.
