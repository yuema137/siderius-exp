# Historical planner compatibility

This optional package recreates selected historical planner inputs so they can
be compared with archived evidence. It does not replay an entire scientific
experiment or promise the same future LLM response. Installing it registers an
installation default; explicit strategy selection still takes precedence.

Start with the [paper artifact reference](../../paper-artifacts.md) to identify
the experiment and source pair. The repository installation pin and each
adapter's qualified framework assemblies are separate constraints; installing
this package does not update or qualify the framework.

| Need | Reference |
| --- | --- |
| Installation and selection | [Installation and selection](usage.md#install-into-the-environment-that-will-run-infra) |
| Actual task startup evidence | [Actual task startup evidence](paper-startup-parity.md) |
| Retain paper epoch caps on the updated framework | [Explicit epoch caps and v9 manual profiles](epoch-manual-compatibility.md) |
| Preserve paper history after the watchdog deadline change | [Watchdog history setup](watchdog-policy-compatibility.md) |
| Latest storage-view contract | [Latest storage-view contract](storage-provenance-compatibility.md) |
| Present explicitly selected historical timing decisions | [Historical timing setup](../runtime_compat/README.md) |
| New-workspace migration requirements | [New-workspace migration requirements](migration.md) |

Use a new external workspace for a changed profile. Preserve historical source,
configuration and evidence. The [shared support index](../README.md) distinguishes
planner, prompt and resource compatibility.

<details>
<summary>Links retained from the earlier detailed README</summary>

<a id="install-into-the-environment-that-will-run-infra"></a>
[Install into the environment that will run infra](usage.md#install-into-the-environment-that-will-run-infra)

<a id="select-a-strategy-for-a-new-experiment"></a>
[Select a strategy for a new experiment](usage.md#select-a-strategy-for-a-new-experiment)

<a id="keep-old-results-intact"></a>
[Keep old results intact](usage.md#keep-old-results-intact)

<a id="check-the-installed-package-without-an-api-call"></a>
[Check the installed package without an API call](usage.md#check-the-installed-package-without-an-api-call)

<a id="correct-new-runs-or-inspect-historical-prompts-369"></a>
[Correct new runs or inspect historical prompts (#369)](usage.md#correct-new-runs-or-inspect-historical-prompts-369)

<a id="match-the-papers-actual-planner-startup"></a>
[Match the paper's actual planner startup](usage.md#match-the-papers-actual-planner-startup)

<a id="historical-runtime-refusal-wording-v5"></a>
[Historical runtime-refusal wording (v5)](usage.md#historical-runtime-refusal-wording-v5)

<a id="passing-static-preflight-evidence-v6"></a>
[Passing static-preflight evidence (v6)](usage.md#passing-static-preflight-evidence-v6)

<a id="scoped-storage-evidence-v7"></a>
[Scoped storage evidence (v7)](usage.md#scoped-storage-evidence-v7)

</details>
