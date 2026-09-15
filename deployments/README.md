# Deployments

Deployment configuration is explicit and portable. Machine-specific values arrive through configuration or environment variables and are never hidden in task or framework code.

## Available packages

- [TIDMAD coding-agent baseline](tidmad_coding_agent_baseline/README.md):
  prepares isolated Codex and Claude Code product baselines from the existing
  TIDMAD task package. It does not define a new task or add a workflow to the
  agents.

## Planned campaign topology

This table records resource ownership intent only. It is not an executable
scheduler configuration and does not authorize a workload.

| Deployment pool | Capacity intent | Campaign use |
|---|---|---|
| TIDMAD campaign pool | four H100 GPUs | TIDMAD campaign |
| Contrast-task campaign pool | one test H100 GPU | Oxford-IIIT Pet, DAVIS future prediction, and Cancer Gene Identification campaigns |

Concurrency, scheduling order, GPU memory limits, time budgets, iteration
counts, and campaign treatments remain TBD. Those values must be reviewed and
frozen in the appropriate deployment or campaign package before launch.
