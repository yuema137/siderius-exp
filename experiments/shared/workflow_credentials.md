# Workflow credential requirements

`required_workflow_api_keys(config, disabled_roles=...)` returns environment
variable names for providers in the validated `WorkflowLLMConfig`. It does not
read, print, transfer or validate credential values, or call a provider.

The default includes every configured role, including Data Analysis. Treatments
must pass disabled top-level roles explicitly; unknown names are refused to
avoid a misspelled exclusion. The NoPrior supervisor passes `data_analysis`.
A Full launcher must not inherit that exclusion. Nested proposer/tuner/review
provider routes contribute to the returned set.

This helper does not freeze an experiment, authorize a launch, or prove an
account can make API calls. The launcher still owns same-process name-only
presence checks, resource checks and immutable run receipts.
