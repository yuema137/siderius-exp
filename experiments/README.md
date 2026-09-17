# Experiments

Start here when you have selected a task and need one concrete, bounded
treatment. An experiment is a reproducibility identity, not a campaign
authorization. Open the task-specific qualification page before preparing a
workspace; use `--dry-run` where the launcher supports it.

| Task family | Bounded qualification | Notes |
|---|---|---|
| TIDMAD | [`two_iteration_qualification/`](tidmad/two_iteration_qualification/) | engineering qualification; not Gold |
| TIDMAD coding-agent baseline | [`coding_agent_baseline/`](tidmad/coding_agent_baseline/) | four independent no-advice Codex band units; launch record, not final results |
| TIDMAD raw Data Analysis | [`data_analysis_raw_characterization/`](tidmad/data_analysis_raw_characterization/) | full high-frequency band, raw-data smoke only; not the matched ON/OFF treatment |
| TIDMAD Data Analysis pair | [`data_analysis_pair/`](tidmad/data_analysis_pair/) | bounded local ON/OFF qualification; Literature Review runs first |
| Oxford-IIIT Pet | [`two_iteration_qualification/`](oxford_iiit_pet/two_iteration_qualification/) | consumer-pair qualification |
| DAVIS | [`two_iteration_qualification/`](davis_future_prediction/two_iteration_qualification/) | consumer-pair qualification |
| Cancer MTG | [`p0_final_pair_qualification/`](cancer_gene_identification/p0_final_pair_qualification/) | consumer-pair qualification |

Archived experiments are retained as dated evidence and are not current launch
routes. Campaign coordination belongs under [`campaigns/`](../campaigns/README.md).

Each experiment directory selects one static task package and one workflow,
then owns one concrete treatment: parameter values, advice, literature-review
state, iteration and epoch counts, data exposure, output locks, resource
budgets, and result receipts.

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

Final consumer-pair qualification wrappers live under each task's
`p0_final_pair_qualification/` directory and support exact-checkout,
fresh-workspace and `--dry-run` validation.
