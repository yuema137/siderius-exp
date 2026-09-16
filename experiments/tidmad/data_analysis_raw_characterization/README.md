# TIDMAD full-band raw-data characterization

This bounded experiment checks whether the generic Data Analysis Agent can
characterize real 10 MHz TIDMAD inputs across the complete high-frequency
validation band (files 15–19). It is a qualification smoke, **not** the matched
model-aware Data Analysis ON/OFF campaign or a benchmark run.

The [task composition](task_composition.yaml) reuses the static
[TIDMAD task package](../../../tasks/tidmad/README.md). Its
[analysis configuration](analysis_config.yaml) permits input-waveform data
only, samples at most ten windows with at least one per declared file, and
limits Data Analysis to 45 seconds. Targets, predictions, residuals and
historical model inference are unavailable in this experiment. It therefore
cannot establish model-aware analysis or an ON/OFF modeling effect.

Raw data, credentials and run workspaces remain outside both repositories.
The experiment needs an explicitly configured TIDMAD data root and a provider
credential before any effectful launch. No such launch is implied by these
configuration files.
