# Certified native model restoration

`restore_native_model(root, reference, approved_plugin)` is a context manager
for an isolated research process. The reference must be a validated native
`TrainedModelArtifactRef`, and the caller must choose the permitted plugin file.
It verifies the descriptor and executable identity, constructor implementation,
source, configuration and checkpoint bytes before registering model code. It
uses SIDERIUS's existing constructor and strict weights-only loading; config is
validated by the plugin's declared schema.

The temporary snapshot remains present until the context exits, so scripted
export can inspect its source. The resulting model is a disposable CPU eval
instance. Registry modifications are process-local; use a fresh research worker
for each request. Packaged plugins requiring a bound code package and custom
prediction/metadata adapters are explicitly unsupported by this adapter.

The function creates no sandbox. Do not call it in a privileged data/evaluator
process. Certification establishes which code is being executed, not that the
code is safe, the model is useful, or the task's access policy permits a caller
to receive it. Those decisions belong to the deployment boundary. This module
neither changes source/weights nor supplies missing authority from filenames.
