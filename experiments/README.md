# Experiments

For a first hands-on run, start with the [tutorial index](../tutorials/README.md).
This directory includes reusable treatments, qualification scripts and historical
records with different source pins. A directory or a profile named `demo` is not
by itself a ready-to-run beginner tutorial; follow the selected entry's guide.

Start here when you have selected a task and need one concrete treatment.
For a first run, choose one of the [five notebook demos](../tutorials/README.md):
the four paper-task demos or supplementary Pet. They are simplified examples,
not one-click paper reproductions. The table below also includes research
launchers, which need their declared data, environments and budgets.

An experiment is a reproducibility identity, not a campaign authorization.
An available launcher does not mean that every profile has completed a real run
on the current repository pair. Read its evidence and use `--dry-run` where
supported before preparing an effectful launch.

| Task family | Bounded qualification | Notes |
|---|---|---|
| TIDMAD | [`two_iteration_qualification/`](tidmad/two_iteration_qualification/) | engineering qualification; not Gold |
| TIDMAD coding-agent baseline | [`coding_agent_baseline/`](tidmad/coding_agent_baseline/) | four independent no-advice Codex band units; launch record, not final results |
| TIDMAD raw Data Analysis | [`data_analysis_raw_characterization/`](tidmad/data_analysis_raw_characterization/) | full high-frequency band, raw-data smoke only; not the matched ON/OFF treatment |
| TIDMAD Data Analysis pair | [`data_analysis_pair/`](tidmad/data_analysis_pair/) | bounded local ON/OFF qualification; Literature Review runs first |
| Oxford-IIIT Pet | [tutorial template](oxford_iiit_pet/tutorial_demo/README.md), [`two_iteration_qualification/`](oxford_iiit_pet/two_iteration_qualification/) | start with the [Pet tutorial](../tutorials/supplementary/pet/README.md) |
| DAVIS | [`two_iteration_qualification/`](davis_future_prediction/two_iteration_qualification/) | consumer-pair qualification |
| Cancer MTG | [`mtg_size_qualification/`](cancer_gene_identification/mtg_size_qualification/) | launcher available; no uninterrupted complete discovery-chain qualification is claimed |
| Majorana Low-AvsE (MJD) | [profiles and qualification](majorana_low_avse/README.md) | research launcher; supplementary notebook planned |
| SuperNEMO | [profiles and qualification](supernemo_signal_background/README.md) | research launcher; supplementary notebook planned |
| PhyTS TESS | [`main_fixed_workflow/`](phyts_tess/main_fixed_workflow/) | historical NoPrior execution recorded; current-pair qualification is separate |
| PhyTS LIGO | [`main_fixed_workflow/`](phyts_ligo/main_fixed_workflow/) | NoPrior; archived launch/startup evidence is indexed separately |
| PhyTS Project 8 | [`main_fixed_workflow/`](phyts_project8/main_fixed_workflow/) and [dual representation](phyts_project8/main_fixed_workflow_dual_representation/README.md) | distinct input contracts; keep their evidence separate |

For the paper's recorded source/configuration pairs and their limits, use the
[paper artifact reference](paper-artifacts.md). Compatibility adapters and shared
launch responsibilities are grouped under [shared support](shared/README.md).

Archived experiments are retained as dated evidence and are not current launch
routes. The [P0 final-pair wrappers](p0_final_pair_qualification/README.md)
intentionally require their separate historical infra revision. They do not
qualify the current release. Cancer, MJD and SuperNEMO supplementary notebooks
remain planned. Coding-agent and orchestration preparation directories may also
require deployment work; their own pages state whether they are launchable.
Campaign coordination belongs under [`campaigns/`](../campaigns/README.md).

Each experiment directory selects one static task package and one workflow,
then owns one concrete treatment: parameter values, advice, literature-review
state, iteration and epoch counts, data exposure, output locks, resource
budgets, and result receipts.

### TIDMAD: which file should I open?

The TIDMAD fixed workflow has more than one layer. Use these files in order:

1. [`tasks/tidmad/README.md`](../tasks/tidmad/README.md) explains the scientific
   data contract, the 20 training/validation file pairs and 200 segments per
   file, channels, model I/O,
   score, Health, and task-owned reference rulers.
2. [`tidmad/main_fixed_workflow/README.md`](tidmad/main_fixed_workflow/README.md)
   explains the fixed workflow files, treatments, preflight, launch command,
   band isolation, budgets, and backup services.
3. [`tidmad/information_treatments/README.md`](tidmad/information_treatments/README.md)
   explains which advice and agent modules each treatment enables.
4. [`../tasks/tidmad/data/README.md`](../tasks/tidmad/data/README.md) explains
   how to stage the external HDF5 root and verify the anchor file.

If you only want a different existing band, change the experiment's `--band`
and external `--data_dir`. If you want a different training parent, score,
model I/O contract, or Health rule, start a new task/experiment identity and
update the owning task files described in the TIDMAD README.

The workflow owns the execution procedure, including Trial/Formal roles and
their progression. The experiment may set approved values for that workflow;
it does not redefine what Trial or Formal means.

For a fixed workflow, keep shared launch parameters in one experiment JSON
and per-agent model settings in one referenced JSON. Select the information
treatment separately: one advice JSON may give different named guidance to
different agents, while the advice-off arm receives no advice file. The
TIDMAD prerelease launcher demonstrates this split; its advice switch is not
the later `Full`/`NoPrior` comparison, which also requires a real data-analysis
agent.

Experiment records identify the exact SIDERIUS revision, this repository
revision, resolved task identity, configuration and plugin hashes, dataset
identity, executable argv, and runtime budgets. Changing any treatment value
creates a new experiment identity; it does not modify the task package.
Historical locked launchers retain their own `SIDERIUS_REVISION` beside the
experiment. The repository-root revision names the current development pair;
updating it must not silently retarget an archived experiment.

Historical P0 consumer-pair wrappers live under each task's
`p0_final_pair_qualification/` directory. Use the revision required by their
[shared historical pin](p0_final_pair_qualification/SIDERIUS_REVISION), a fresh
workspace and `--dry-run`; do not substitute the repository-root release pin.
