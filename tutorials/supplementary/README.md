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

## SuperNEMO event tutorial

[SuperNEMO setup](supernemo/README.md) and its [notebook](supernemo/supernemo_tutorial.ipynb)
explain whole-event inputs, separate raw/prepared/project directories and the
saved-script workflow. The [recorded three-iteration demo](supernemo/example/README.md)
includes a real Train event, measured scores and provenance. Reserved test
events remain unused.

## Cancer graph tutorial

[Cancer setup](cancer/README.md) and its [notebook](cancer/cancer_tutorial.ipynb)
explain one complete CPDB graph, original label masks and editable active-label
fractions. The [recorded example](cancer/example/README.md) shows a real graph
preview and three completed iterations; original Test labels remain unused.

## DAVIS video tutorial

[DAVIS setup](davis/README.md) and its [notebook](davis/davis_tutorial.ipynb)
show eight context frames and four targets, original sequence splits and whole-clip
fraction controls. The [recorded three-iteration demo](davis/example/README.md)
keeps the first Health-invalid result as a hollow point, followed by two passing
results. The original
[task](../../tasks/davis_future_prediction/README.md) and
[qualification profile](../../experiments/davis_future_prediction/two_iteration_qualification/README.md)
remain separate references.

In particular, an older experiment profile called `demo` may run many iterations
and use historical settings. Follow its declared source pin and configuration;
do not treat its name as a short beginner exercise.

For the complete task-to-tutorial map, return to the [tutorial index](../README.md).
The [four paper-task demos](../paper/README.md) are a separate group with their
own setup instructions. New tutorial projects use the shared
[Luna test configuration](../shared/README.md); archived examples retain their
original provenance.
