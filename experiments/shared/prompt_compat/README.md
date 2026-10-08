# Historical prompt compatibility

This optional package assembles selected historical messages for paper-era
experiments. It changes rendering only when a task selects a profile, and
refuses an unqualified framework assembly. Offline message equality is narrower
than a complete run replay or recovery of a paper model.

Start with the [paper artifact reference](../../paper-artifacts.md) to identify
the experiment and source pair. The repository installation pin and each
adapter's qualified framework assemblies are separate constraints; installing
this package does not update or qualify the framework.

| Need | Reference |
| --- | --- |
| Installation and selection | [Installation and selection](usage.md#1-install-into-the-infra-environment) |
| Coverage and missing evidence | [Coverage and missing evidence](parity-report.md) |
| Recovered formal evidence | [Recovered formal evidence](formal-evidence-parity.md) |
| Routing qualification | [Routing qualification](proposer-routing-audit.md) |
| Development renderer qualification | [Offline comparisons and release limits](release-renderer-qualification.md) |

Use a new external workspace for a changed profile. Preserve historical source,
configuration and evidence. The [shared support index](../README.md) distinguishes
planner, prompt and resource compatibility.

<details>
<summary>Links retained from the earlier detailed README</summary>

<a id="1-install-into-the-infra-environment"></a>
[1. Install into the infra environment](usage.md#1-install-into-the-infra-environment)

<a id="2-configure-copies-in-a-new-workspace"></a>
[2. Configure copies in a new workspace](usage.md#2-configure-copies-in-a-new-workspace)

<a id="3-inspect-the-offline-comparisons"></a>
[3. Inspect the offline comparisons](usage.md#3-inspect-the-offline-comparisons)

<a id="4-replay-the-archived-failure-when-available"></a>
[4. Replay the archived failure, when available](usage.md#4-replay-the-archived-failure-when-available)

<a id="runtime-feedback-candidate-qualification"></a>
[Runtime-feedback candidate qualification](usage.md#runtime-feedback-candidate-qualification)

<a id="recover-formal-evidence-for-an-old-interpretation-cache"></a>
[Recover formal evidence for an old interpretation cache](usage.md#recover-formal-evidence-for-an-old-interpretation-cache)

<a id="proposer-model-selection-after-the-routing-fix"></a>
[Proposer model selection after the routing fix](usage.md#proposer-model-selection-after-the-routing-fix)

<a id="static-preflight-evidence"></a>
[Static preflight evidence](usage.md#static-preflight-evidence)

</details>
