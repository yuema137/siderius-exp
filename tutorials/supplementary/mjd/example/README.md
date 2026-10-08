# Recorded MJD demo

This three-iteration demo used real Majorana Low-AvsE data and GPT-6 Luna on an
RTX 5090. It demonstrates the complete notebook → saved script → recorded score
workflow. It is a supplementary example, not a paper artifact or a promised score.
The [provenance receipt](provenance.json) records the executed source revisions,
settings, task identity and hashes of the native score records.

## See the input

![One official Train waveform before and after task normalization](waveform.png)

This CPU-only preview shows one actual Train waveform and the model input after
the task's baseline normalization. It is not a generated prediction or evidence
of training quality. The preview's sampling seed selected 7,834 balanced training
examples and 2,846 balanced evaluation examples at the configured one-percent
fractions. Counts are illustrative; attempts can use different sampling seeds.
All 22 official supervised files were verified before launch.

## See the recorded result

![Measured Formal energy-matched AUC versus iteration](score-versus-iteration.png)

| Iteration | Trial AUC | Formal AUC | Recorded execution |
|---|---:|---:|---|
| 1 | 0.7704 | 0.8591 | Successful |
| 2 | 0.6213 | 0.7830 | Successful |
| 3 | 0.7467 | 0.8185 | Successful |

The plot uses Formal records only. MJD explicitly declares **no Health checks**;
filled markers and CSV `validity=pass` mean successful scored execution, not
Health PASS. Failed scored Formal attempts would appear hollow. The line tracks
the best raw score; it need not rise every iteration. Official Test supplies
feedback during search and is not an untouched final test.

The [CSV](score-versus-iteration.csv) preserves the recorded values and refers to
native source files relative to the external project. The [SVG](score-versus-iteration.svg)
is also available. This gallery is never substituted for a user's own results.

## What this run establishes

All three iterations completed with diagnostic result authority. The successful
notebook command took about 13.7 minutes. The validation campaign used 33 API
requests, accounted at about $0.05, with no unknown-cost requests. Its cumulative
command time was about 15.4 minutes, including API waits, an initial failed
attempt and the cached rerun; this is a conservative upper bound, not measured
GPU utilization or a public notebook spending limit.

The initial attempt stopped before API calls or training because its tutorial
fraction was below the native CLI minimum. The tutorial now checks the same
minimum when saving settings. The completed run used that corrected source;
no framework acceptance rule or scientific split changed. Repeating Run All reused the saved result without new API requests and left
the completion receipt unchanged.
This establishes one completed source/data/hardware sequence, not every possible
generated model or device.

Follow the [tutorial setup](../README.md) to create your own external project.
Initialization clears these archived notebook outputs so your copy displays
only what you inspect and run locally. Dataset identity and scientific meaning
remain owned by the [task package](../../../../tasks/majorana_low_avse/README.md).
