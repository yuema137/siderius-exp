# TIDMAD waveform denoising

TIDMAD asks a model to recover an injected signal from noisy SQUID detector
waveforms. In the current continuous-regression task, the model receives a
waveform window and returns one denoised value at every time step. Historical
classification compositions remain separately identified in the
[technical contract](task-contract.md#1-composition-files-what-siderius-loads).

This package defines the data, model input/output, score and Health checks.
An [experiment](../../experiments/README.md) chooses research iterations,
training budgets, provider models and hardware. Changing the scientific task
creates a new task identity; changing a budget does not redefine the waveform.

## Choose your route

| Goal | Start here |
| --- | --- |
| Learn with one band and an editable project | [One-band tutorial](../../tutorials/paper/tidmad/README.md) |
| Run the current fixed workflow | [Experiment guide](../../experiments/tidmad/main_fixed_workflow/README.md) |
| Prepare the external HDF5 data | [Data guide](data/README.md) |
| Inspect previous qualification and source evidence | [Status](STATUS.md) and [provenance](PROVENANCE.md) |
| Locate paper settings and their limits | [Paper artifact reference](../../experiments/paper-artifacts.md) |

The tutorial is a small process demonstration. It is not a complete paper
reproduction. The old `examples/tidmad` projection is historical; new runs
select this task explicitly.

## Understand the data before changing it

The dataset contains 20 training/validation file pairs. A band selects file
indices `0-3`, `4-9`, `10-14` or `15-19`. Each file contains 200 long waveform
segments; the model processes shorter windows within those segments. Raw HDF5
files stay in an external data directory supplied through `--data_dir`.

The paper-style fixed workflow uses a declared parent of 20 segments per file.
Formal uses that entire parent; `formal_portion=0.1` describes its fraction of
the original 200, rather than selecting another tenth. Its model window is
40,000 samples. Exact encoding, scope limits, scoring and Health rules belong
to the [task contract](task-contract.md#the-data-contract-in-one-minute).

<a id="which-file-owns-which-decision"></a>

## Change the right owner

For a different existing band, keep the task package and change the experiment's
band/data-root inputs. For a different split, score, output meaning or Health
rule, create and qualify a new task variant. Preserve old inputs and evidence.
The [ownership map](task-contract.md#which-file-owns-which-decision) identifies
the declaration and implementation that must change together.

<a id="5-reference-data-and-tools"></a>

The [reference data and tools](task-contract.md#5-reference-data-and-tools)
record normalization anchors, raw/ground-truth rulers and paper-model results.
They do not replace the external raw data or qualify a changed task.

Current task documentation is included in the coding-agent bundle's visible
task view. Documentation changes therefore change that view's hash even when
scientific configuration is unchanged. Use the recorded exp checkout or archived
bundle for a historical view; see the
[bundle provenance boundary](../../experiments/paper-artifacts.md#task-documentation-and-bundle-identity).
