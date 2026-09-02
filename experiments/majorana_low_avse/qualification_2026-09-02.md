# Majorana qualification record — 2026-09-02

The task package passed exact-pin composition, split, model-forward, launcher,
energy-balance, metric, and dataset-integrity checks. A real qualification was
started at SIDERIUS `7568fc54b6bcc00ce6ee5c1e88f3219550a688cb` and
siderius-exp `11d51dd33a245c9a2a56e4ddf52fa2a49b5b5cf2` after all 22 supervised
files passed the task-owned size and MD5 gate.

The run was stopped during iteration 1 literature review when the concurrent
SuperNEMO external witness proved generic SIDERIUS issue #420. The shared
measured-admission timer excluded task-owned DataLoader latency, so continuing
Majorana against that framework revision could not establish valid resource
qualification. The workspace is retained as non-authoritative evidence; the
next run must use a fresh identity and the repaired exact SIDERIUS revision.
