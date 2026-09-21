# Controller work strategy advice V2

**Audience:** the O-Full outer coding agent only. Read this alongside the
separately declared Full V8 model research advice. It is a reference and a
resource-planning aid, not a required architecture, training recipe, schedule,
or additional data, compute, or evaluation permission.

## Concrete scientific reference

The published TIDMAD FCNet is the reference to beat. It is a band-specific,
fully connected waveform denoising autoencoder: a 40,000-sample input is
compressed through widths 4,000, 400, and 40, then reconstructed through
400 and 4,000 back to 40,000 samples. The reference implementation uses ReLU
between its linear layers and has 323,280,840 trainable parameters. It trains
against continuous clean-waveform targets with SmoothL1 loss and Adam. Four
separate checkpoints serve files 0–3, 4–9, 10–14, and 15–19. Within each
band, the published training loop visits files in sequence while shuffling
samples within each file. These properties are reference points for new model
ideas, not requirements to copy its code, exact widths, optimizer, or training
schedule.

Aim to exceed FCNet with a valid, scientifically supported candidate. Use its
architecture, capacity, learned compression/reconstruction, band scope, and
file-order behavior as concrete comparison points when choosing experiments.
A recognizably related candidate or a well-motivated alternative is allowed.
Evaluate actual training extent, score, Health, and measured cost;
do not attribute a gap to architecture or capacity before considering
optimization, data coverage, loss, output behavior, and ordering. The shared
Full V8 advice explains when the existing sequential-order capability may be
worth testing. Do not import results or histories from another experimental
arm unless the current task explicitly supplies them.

## Adaptive use of the toolkit

Use the available wall time, compute, memory, and agent capacity to improve the
best valid scientific result. Choose the work pattern adaptively rather than
following a fixed schedule. When useful and safe, independent sub-agents may
propose hypotheses, perform authorized analysis, implement and test separate
candidates, or review evidence concurrently. Avoid GPU oversubscription,
duplicated low-information work, and concurrent writes to shared candidate
state; preserve each candidate's configuration, evidence, and provenance.

Combine inexpensive probes that reduce uncertainty with larger experiments
that can realize promising ideas. Use measured cost, score, Health, and
scientific evidence to decide what to expand, stop, or replace. Reserve time
for integration, complete-band evaluation, and submission of the strongest
valid candidate. Parallelism and experiment scale are tools to use when they
improve the chance of exceeding the FCNet reference, not targets in themselves.
