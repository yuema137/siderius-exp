# Supplementary tasks and tutorials

These tasks are outside the paper's four experiments. **To follow a complete
notebook walkthrough today, start with [Oxford-IIIT Pet](pet/README.md).** It
shows images, creates an external editable project, explains the saved task and
experiment, launches a three-iteration search and plots the recorded scores.

[Open the Pet notebook](pet/pet_tutorial.ipynb) to browse the example before
setup. The [setup guide](pet/README.md) explains data reuse/download, keys,
parameter changes, preview and execution. These are process demos, not paper
artifacts or promises of a particular score.

## MJD waveform tutorial

[MJD setup](mjd/README.md) and its [notebook](mjd/mjd_tutorial.ipynb) now provide
the external-project and saved-script walkthrough. CPU previews use local official
data; the [recorded three-iteration demo](mjd/example/README.md) includes actual
waveforms, scores and provenance. Official Test feeds search evaluation, not a
blind final test.

## Tasks awaiting a notebook

SuperNEMO, Cancer and DAVIS already have task packages and experiment code.
Their notebook-plus-script tutorials are **not yet available**. The references
below are for inspecting existing work; they are not interchangeable with the
Pet walkthrough or evidence of a newly qualified three-iteration demo.

| Task | Existing references |
|---|---|
| SuperNEMO event classification | [Task](../../tasks/supernemo_signal_background/README.md) · [Experiment profiles](../../experiments/supernemo_signal_background/README.md) |
| Cancer-gene identification | [Task and current entrypoints](../../tasks/cancer_gene_identification/README.md) · [Two-network qualification reference](../../experiments/cancer_gene_identification/two_network_qualification/README.md) |
| DAVIS future-frame prediction | [Task](../../tasks/davis_future_prediction/README.md) · [Bounded qualification reference](../../experiments/davis_future_prediction/two_iteration_qualification/README.md) |

In particular, an older experiment profile called `demo` may run many iterations
and use historical settings. Follow its declared source pin and configuration;
do not treat its name as a short beginner exercise.

For the complete task-to-tutorial map, return to the [tutorial index](../README.md).
The [four paper-task demos](../paper/README.md) are a separate group with their
own setup instructions. New tutorial projects use the shared
[Luna test configuration](../shared/README.md); archived examples retain their
original provenance.
