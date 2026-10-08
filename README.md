# siderius-exp

Learn how to use [SIDERIUS](https://github.com/yuema137/SIDERIUS) on a scientific
dataset: define the problem, choose an experiment, run it, and inspect the results.
This repository contains task packages, tutorials and recorded experiments;
SIDERIUS provides the execution framework.

## Start with a tutorial

**For a first try, start with [TESS](tutorials/paper/README.md).** It predicts
stellar rotation from brightness measurements and has a small downloadable
dataset. Browse the notebook's data pictures and recorded result plot first;
then follow its setup guide to run your own copy.

The [tutorial index](tutorials/README.md) lists every task and shows which ones
already have a notebook. The other available walkthroughs cover TIDMAD, Project8,
LIGO and Pet image classification. MJD, SuperNEMO, Cancer and DAVIS have task and
experiment code, but their beginner notebooks are not yet available.

We recommend working with your coding agent. Open this repository and say:

```text
Help me run the small TESS tutorial in a new project at /absolute/path/my-tess-demo, starting with environment and data setup.
```

Your agent should follow the selected tutorial, prepare the files, explain the
choices and show the saved launch command. You supply provider credentials and
approve paid execution. You can also follow the same guide yourself.

## What you will do

1. **Choose a task and inspect its example.** See the data format and what the
   model predicts before installing anything.
2. **Install the paired environments.** Follow that tutorial's setup guide for
   the exp and infra installations and required keys.
3. **Follow its project and data steps in order.** Use a fresh project path
   outside both repositories; do not create it manually before initialization.
   Reuse existing data or download it once as instructed. Depending on the task,
   task files are copied during initialization or created during data preparation.
   Edit only the files saved in your external project.
4. **Preview, then run the saved script.** Inspect the saved files, effective
   parameters and output path before spending API or GPU time. Notebook Run All
   can invoke that same script; it does not contain a second training engine.
5. **Read the score-versus-iteration plot.** Change settings in your project and
   use a new run directory for the next experiment.

Use the [Luna test configuration](tutorials/shared/README.md) for a first process
check. For research, start from the paper's LLM routing or choose your own models.
Model selection does not set a dollar limit; data, training and API budgets are
separate. Keep keys, datasets, generated models and results outside the repos.

## Which files own your choices?

| You want to change | Edit in your external project |
|---|---|
| The prediction problem: inputs, labels, data splits, metric or scientific checks | The **task package** |
| How the search runs: iterations, Trial/Formal data fractions, time/VRAM budgets or LLM routing | The **experiment** and its linked configuration files |
| Which saved experiment to launch | The generated **shell script** or its documented arguments |

For example, a new train/validation split changes the task definition. Keeping
that split and increasing the iteration count changes the experiment. Each
tutorial shows its actual file layout and the parameters its launcher supports.

## Paper and historical experiments

[Beyond a Better Score: Long-Horizon Agentic ML Development and Evaluation Protocol for Physics Time Series](https://zenodo.org/records/23071121)
introduces SIDERIUS and studies agent-driven model development on TIDMAD, TESS,
Project8 and LIGO, including scientific validity and compute budgets.

**Tutorials are simplified process demos, not one-click reproductions of paper
artifacts or scores.** Their pictures include recorded examples with their own
provenance. A new LLM-driven run can produce different models and results.
For historical reproduction settings and available evidence, use the
[paper artifact reference](experiments/paper-artifacts.md).

## Explore beyond the walkthroughs

| Directory | When you need it |
|---|---|
| [Tasks](tasks/README.md) | Understand or extend a task's data, model and scoring contracts |
| [Experiments](experiments/README.md) | Inspect a particular workflow treatment, launcher or recorded run |
| [Campaigns](campaigns/README.md) | Coordinate several experiments; not needed for a first tutorial |
| [Deployments](deployments/README.md) | Configure a particular execution environment |
| [Contributor rules](CLAUDE.md) | Change repository code or run development checks |

<a id="framework-revision"></a>
The exact framework dependency is recorded in [SIDERIUS_REVISION](SIDERIUS_REVISION)
and the frozen dependency files. Follow the selected tutorial's installation
instructions; do not substitute another checkout's virtualenv or source path.
Some historical launchers have their own older pins, documented by their owners.

<a id="running-the-live-tests"></a>
Developer tests and scientific runs are separate. For contribution validation,
follow [the contributor rules](CLAUDE.md#validation-and-independent-review) and
the selected experiment's technical contract.

## License

Original software and documentation use the [MIT License](LICENSE). Third-party
code, datasets and data-derived examples retain their own terms; see [NOTICE](NOTICE)
and each task's provenance. The project license does not grant additional rights
to external data, paper content or dependencies.
