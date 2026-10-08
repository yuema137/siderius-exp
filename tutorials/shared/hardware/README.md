# Check your hardware before running a tutorial

You can read the notebooks and plot existing results on a CPU machine. Running
the training demos requires a supported GPU. Do not start a paid run just to
discover whether your machine has enough room: save your experiment settings,
then run the hardware check below.

## 1. Choose a GPU and review the saved budget

Use Linux and the paired, frozen Python environments from your tutorial's setup
guide. The supported tutorial route currently uses an NVIDIA GPU with working
CUDA kernels and driver memory accounting. Other NVIDIA models can use the same
route if those checks pass; they have not all been tested. On a machine with
several GPUs, select one before starting Jupyter or the script:

```bash
export CUDA_VISIBLE_DEVICES=0  # Replace 0 with the GPU you intend to use.
```

AMD/ROCm compatibility is experimental and untested. Required driver/process
accounting is not implemented for that tutorial route, so it currently refuses
to launch. Intel GPU and CPU training are unsupported. CPU data inspection still
needs enough host memory and disk space for the selected dataset.

Your saved experiment JSON owns the VRAM allowances: `vram_gib`, or the explicit
`trial_vram_gib` and `formal_vram_gib` overrides. These are GiB, not decimal GB.
Trial and Formal run sequentially: the check uses the **larger** allowance,
rather than adding them together. It also counts memory already occupied on
the selected device and respects declared deployment limits.

For example, a card with 12 GiB total and 5 GiB already occupied cannot provide
an 8 GiB allowance. An idle card with exactly 8 GiB also fails the tutorial's
requirement that the allowance be below physical capacity. Free memory in RAM
does not substitute for GPU VRAM. Do not simply lower the allowance to bypass
the error: the generated model must still fit and pass native measurement.

## 2. Check the experiment you actually intend to run

After initializing your external project and saving the selected experiment,
run this from the exp checkout. Replace the paths with your own:

```bash
export EXP_CHECKOUT="/absolute/path/siderius-exp"
export EXPERIMENT="/absolute/path/my-project/experiments/my-demo.json"
cd "$EXP_CHECKOUT"
"$EXP_CHECKOUT/.venv/bin/python" -m tutorials.shared.hardware \
  --experiment "$EXPERIMENT"
```

For the four paper-task notebooks, **Quick A must first save its JSON**. Check
that Quick A file, not the initial example if you have since changed settings.
For Pet, MJD and SuperNEMO, initialization already creates the default JSON.
After saving a variant, use the new JSON path printed by the notebook.

This command needs no API key, makes no LLM call, starts no training and creates
no run workspace. It checks the source/environment pair and the saved hardware
fields, queries the selected GPU and runs a tiny CUDA kernel. It reports memory
and storage observations so you can inspect the machine you will actually use.
It does **not** validate every task setting, download data or replace the saved
script's configuration and data checks.

If it fails, fix the reported cause before launching: select a supported device,
repair its driver/environment, free occupied VRAM or use a larger GPU. Do not
disable monitoring or change a deployment quota just to make the check pass.
Rerun the check after changing your GPU or saved resource settings.

The same GPU check also runs at a fresh tutorial launch, before provider calls.
A passing snapshot does not reserve memory: another process can start afterward.
It also does not measure a model that has not been generated yet. Native model
measurement, admission and runtime monitoring remain necessary.

## 3. Allow for data, RAM and saved results

The following budgets describe the shipped short demo, not a measured universal
minimum. Your saved JSON wins after edits. The recorded examples establish their
specific hardware/configuration; they do not qualify every generated model on
every GPU.

| Tutorial | Initial short-demo VRAM allowance | Data and host-memory considerations |
|---|---:|---|
| [TESS](../../paper/README.md) | 8 GiB | Keep room for the selected source/staged arrays and run outputs. Changing the waveform population changes data memory; no universal host-RAM minimum has been established. |
| [TIDMAD](../../paper/README.md) | 8 GiB | Reuse the required original files; choosing a small fraction does not shrink them. Decoding selected waveform segments also uses host RAM. Follow the one-band setup and inspect its selected files before downloading. |
| [Project8](../../paper/prepared/README.md) | 8 GiB | The two complete source files total about 9.83 GB. The preparation helper can use selected row ranges and reports actual transfers; allow additional space for staged time/frequency arrays and outputs. |
| [LIGO](../../paper/prepared/README.md) | 8 GiB | The source manifest lists about 2.36 GB across 60 files; selected-row preparation can transfer less. Keep additional room for staged arrays and outputs. |
| [Pet](../../supplementary/pet/README.md) | 8 GiB | Account for downloaded archives, extracted images, manifests and checkpoints. Fewer training images do not remove the original dataset or extraction space. |
| [MJD](../../supplementary/mjd/README.md) | 10 GiB | The 22 original supervised files total about 43.5 GB; reuse them in place. Runtime-selected waveforms and generated models need additional RAM/storage. |
| [SuperNEMO](../../supplementary/supernemo/README.md) | 10 GiB | Raw files total about 23.1 GB. One-time index preparation produced about 204 MiB and peaked at 8.7 GiB host RAM in the recorded run; an 8 GiB host is unsuitable for that demonstrated preparation. Leave headroom for the OS and other programs. |

The current MJD and SuperNEMO examples completed on an RTX 5090; their example
receipts record the exact run. The earlier tutorials likewise link their own
recorded evidence. A VRAM allowance is a chosen limit, not an observed peak or a
guaranteed minimum GPU requirement.

Disk space must cover what you actually retain: original files, any archive and
extracted copy, prepared data, checkpoints, predictions and logs. Multiple saved
runs accumulate outputs. Reading free disk space does not predict how large an
arbitrary generated model or future run will become. Similarly, available host
RAM is an observation; absent a task-specific bound, it is not a memory-fit
guarantee. Check the data-preparation instructions before attempting large
preparation on a small host. No general CPU-core or host-RAM minimum has been
qualified for all tutorials.

After hardware checks pass, return to your notebook's saved-file review and
launch the exact script it names. For implementation details, see the
[GPU check contract](../gpu-runtime.md).
