# Project8: explicit time and frequency representations

This is a new task contract for a fresh run. The original
[`regression.yaml`](compositions/regression.yaml) remains the historical
**time-domain-only input contract**. The new composition is
[`dual_representation.yaml`](compositions/dual_representation.yaml).

## What the agent receives

The English [`task_config.yaml`](declared/dual_representation/task_config.yaml)
is loaded through the composition, including both `task_description` and the
forward contract. It requires **both representations to contribute to the
prediction**, with architecture and fusion chosen by the agent. Merely accepting
four channels and dropping one pair is noncompliant. The source must identify
where each view is consumed. This is a task requirement; a tensor shape check
alone does not prove model compliance. Inspect generated code and perform an
input-sensitivity check during qualification, with saturated/dead models treated
as inconclusive rather than proof of compliance.

| Channels | Meaning | Last axis |
|---|---|---|
| 0, 1 | Existing centered, per-event scaled noisy I/Q | Time sample |
| 2, 3 | Real/imaginary parts of the full orthonormal FFT of channels 0 + i1 | Unshifted signed frequency bin |

Shape: float32 `[B,4,24576]`; output: float32 `[B,1]` in eV. This is two
representations, each stored as two real components, not two scalar channels.
The FFT uses only permitted noisy inputs. It preserves phase and both frequency
signs, with float32 storage rounding. There is no extra observation, label,
spectral crop, magnitude-only conversion, `fftshift`, or normalization fitted
across events. The time and frequency axes must not be interpreted as aligned
physical positions. In particular, original physical I/Q amplitudes were already
removed by the historical per-channel scaling.

## Scientific context and sources

The task text supplies physical context and input semantics without specifying
a model, baseline score, student solution, or locally observed result.

| Source | Use in the task | Boundary |
|---|---|---|
| Owner-provided PhyTS manuscript, Sections 3.4/5 and Appendix A/Table 7 | Data construction, cavity noise, sample rate/length, I/Q, target and auxiliary truth fields | No distribution of the manuscript; no claim that its S4D used FFT inputs |
| [Project 8 overview, Section 3](https://arxiv.org/abs/1703.02037) | Ideal energy-frequency relation and physical definitions | Its numerical apparatus settings do not define the PhyTS simulation |
| [Locust simulation paper](https://arxiv.org/abs/1907.11124) | Distinguish particle dynamics from simulated RF readout | No extra simulator truth becomes a feature |
| [Project 8 event reconstruction paper](https://arxiv.org/abs/2402.13256) | Corroborates relevance of start frequency and time-frequency structure | Its Phase II spectrogram pipeline, cuts and detector settings are not imported |

The new view is not asserted to reproduce the public PhyTS FFT/crop recipe or
the paper's preprocessing. A Fourier representation can change learning
behavior without adding information. It does not guarantee better performance
or establish direct comparability with a published test score.

## Preparation and identity

From this checkout's own frozen environment:

```bash
.venv/bin/python -m tasks.phyts_project8.tools.build_dual_representation \
  --source /data/project8-time \
  --declaration tasks/phyts_project8/declared/prepared.json \
  --output /data/project8-dual-v1
```

The source manifest and every source array are checked before transformation.
Output is a new directory; overwriting existing data is refused. Targets, row
order and the frozen 500-of-5000 validation-loss snapshot are preserved.
Pin the resulting manifest in `declared/dual_representation/prepared.json`.
Deployment must retain the evaluator access boundary; the offline builder is
an operator tool with access to both splits, not an agent data-access tool.
A new composition identity and empty workspace are required. This change does
not relabel earlier scores or alter the old task.
