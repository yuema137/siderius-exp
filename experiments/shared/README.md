# Shared experiment support

These helpers let experiments reuse launch, credential, export and compatibility
behavior without moving scientific meaning into the framework. Start with your
[experiment](../README.md); use this directory when that experiment links a
shared responsibility.

| Need | Owner |
| --- | --- |
| Understand treatment inputs | [Information treatment](information_treatment.md) |
| Bind launch credentials | [Workflow credentials](workflow_credentials.md) |
| Export or restore a selected model | [Scripted export](scripted_model_export.md), [native restore](native_model_restore.md) |
| Understand scripted execution | [Implementation contract](scripted_implementation.md) |
| Check validation admission | [Validation admission](validation_admission.md) |
| Compare historical planner inputs | [Planner compatibility](planner_compat/README.md) |
| Compare other historical agent messages | [Prompt compatibility](prompt_compat/README.md) |
| Select historical resource formulas | [Preflight compatibility](preflight_compat/README.md) |

Compatibility checks have their own framework-version requirements. They do not
change the repository dependency pin or reconstruct a complete paper result.
Use the [paper artifact reference](../paper-artifacts.md) for that evidence map.
