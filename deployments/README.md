# Deployments

Deployment configuration is explicit and portable. Machine-specific values arrive through configuration or environment variables and are never hidden in task or framework code.

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
