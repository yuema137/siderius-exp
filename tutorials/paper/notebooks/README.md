# Notebook walkthroughs

**Browse first:** each notebook includes real training-sample pictures, a recorded
three-iteration result plot and exact scores. No setup is needed to view these
archived examples; your own results appear after you configure and run the demo.
See the [example gallery](../examples/README.md) for provenance and limitations.

Choose one task, follow its setup guide, and open the notebook copied into your
own external project. These are three-iteration workflow demos, not paper
artifact reproductions. Do not execute or edit these repository templates.

| Notebook | Task and data scope | Prepare your project |
|---|---|---|
| [01 TESS](01_tess_tutorial.ipynb) | Stellar rotation; released train/validation light curves and whole-star splits | [TESS setup](../README.md#1-install-in-the-two-exact-checkouts) |
| [02 TIDMAD](02_tidmad_tutorial.ipynb) | Denoising; one band, file-index validation and optional separate final test | [TIDMAD setup](../tidmad/README.md) |
| [03 Project8](03_project8_tutorial.ipynb) | Electron energy; time I/Q plus complex FFT channels, small event subset | [Project8/LIGO setup](../prepared/README.md) |
| [04 LIGO](04_ligo_tutorial.ipynb) | Chirp mass; two detector channels, small event subset | [Project8/LIGO setup](../prepared/README.md) |

Quick A saves your task/experiment bindings and prints the actual files and
parameters. Quick B invokes the saved script in your project's `scripts/`
directory. Quick C reads native results and writes plots into your project.
The task defines the data, model interface and scoring rules; the experiment
selects that task and supplies budgets, fractions, routing and output locations.

Run All requires prepared data, the selected kernel, exported provider keys and
supported NVIDIA hardware. It incurs API charges and GPU work. Set
`RUN_QUICK_DEMO=False` before Run All to practice editing without execution;
Quick A still saves configurations. Keep keys out of notebook cells and JSON.
Completed unchanged demos reuse recorded results. Choose a fresh `DEMO_NAME`
to run modified settings. See the setup guide for exact paths and commands.
