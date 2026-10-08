# Choose a task and run a small demo

**New to SIDERIUS? Start with [TESS](paper/README.md).** Open its notebook to see
example data and a recorded result plot, then follow the setup guide. You do not
need to understand the full experiment directory before starting.

The repository has nine task families. A task package or experiment launcher
does not automatically include a beginner tutorial; the table below shows the
actual notebook coverage.

## Find your task

| Task | What the model does | Tutorial entry |
|---|---|---|
| TESS | Predict stellar rotation from a light curve | [Setup](paper/README.md) · [Notebook](paper/notebooks/01_tess_tutorial.ipynb) |
| TIDMAD | Recover a waveform from noisy detector data, using one band | [Setup](paper/tidmad/README.md) · [Notebook](paper/notebooks/02_tidmad_tutorial.ipynb) |
| Project8 | Predict electron energy from time and frequency views | [Setup](paper/prepared/README.md) · [Notebook](paper/notebooks/03_project8_tutorial.ipynb) |
| LIGO | Predict chirp mass from two detector channels | [Setup](paper/prepared/README.md) · [Notebook](paper/notebooks/04_ligo_tutorial.ipynb) |
| Oxford-IIIT Pet | Classify pet images by breed | [Setup](supplementary/pet/README.md) · [Notebook](supplementary/pet/pet_tutorial.ipynb) |
| MJD / Majorana | Classify detector waveforms | [Setup](supplementary/mjd/README.md) · [Notebook](supplementary/mjd/mjd_tutorial.ipynb) · [Recorded result](supplementary/mjd/example/README.md) |
| SuperNEMO | Classify signal and background events | [Setup](supplementary/supernemo/README.md) · [Notebook](supplementary/supernemo/supernemo_tutorial.ipynb) · [Recorded result](supplementary/supernemo/example/README.md) |
| Cancer | Rank candidate cancer genes using biological networks | Notebook not yet available; [task and experiment references](supplementary/README.md#tasks-awaiting-a-notebook) |
| DAVIS | Predict future video frames | Notebook not yet available; [task and experiment references](supplementary/README.md#tasks-awaiting-a-notebook) |

## Follow this sequence

1. **Browse the example.** Notebook pictures and plots show the data and a
   recorded run. Their provenance is documented; they are not your results.
2. **Use the task's setup link.** It gives the paired installations, data path or
   download procedure, required keys, supported hardware and project initializer.
3. **Open the copied notebook in your external project.** It explains the task
   package, saves experiment settings and shows the exact files to inspect.
4. **Preview the saved launch command.** Check data fractions, iterations,
   budgets, model routes and result locations. Fix missing prerequisites first.
5. **Run and plot.** Run All explicitly calls the saved shell script to request
   three iterations and plots the scores actually recorded. A run can stop
   early or have unscored attempts. It uses API credit and GPU time. A failed or
   invalid model remains a result to inspect; a high score is not the demo goal.

Keep the source repositories unchanged. Your editable notebook, task files,
experiment, LLM configuration, script and results belong in the separate project
created by the tutorial. Keep secrets external and export them before starting
Jupyter. Setting `RUN_QUICK_DEMO=False` skips the notebook's live-demo execution;
other preparation cells can still save files.

New projects use the [GPT-6 Luna test profile](shared/README.md). It is a starting
point for checking the process, not a whole-run spending cap. The recorded
galleries retain each recorded run's model and settings; inspect their provenance
rather than assuming every example used Luna. Choose research or custom model routing separately from run budgets.

## How the directories relate to the paper

- [Paper-task tutorials](paper/README.md) cover TESS, TIDMAD, Project8 and LIGO.
  They teach the workflow and editable parameters; they do not reproduce the
  paper's complete campaigns or coding-agent comparisons.
- [Supplementary tutorials](supplementary/README.md) cover tasks outside those
  four experiments. Pet, MJD and SuperNEMO have notebooks and recorded demos.
  The other task packages have
  separate references while their tutorials are developed.
- [Paper artifacts](../experiments/paper-artifacts.md) contain the route to frozen
  configurations, original source pairs, historical evidence and its limits.
- [Recorded example gallery](paper/examples/README.md) explains the four paper
  demos' figures; [Pet's example](supplementary/pet/example/README.md) has its own
  provenance.

Install from [yuema137/siderius-exp](https://github.com/yuema137/siderius-exp) and
[yuema137/SIDERIUS](https://github.com/yuema137/SIDERIUS), using the source pair
specified by your setup guide.
