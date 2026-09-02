# Cancer-gene MTG campaign

This experiment runs the single `mtg` NatureBench graph for 30 iterations with
one formal training round per iteration. Literature review is enabled and uses
the task-owned NatureBench root-paper configuration.

The complete graph remains visible in both regimes. Trial activates deterministic
25% of the task-owned training mask (about 929 supervised nodes) while retaining
the complete validation mask (414 nodes, including 64 positives) to keep AUPRC
feedback stable; Formal activates the complete masks
(3717 train and 414 validation nodes in the current release). The masks are
disjoint and the graph topology is unchanged.

The campaign uses 20 GiB Trial/Formal VRAM ceilings, measured admission, a
5-minute Trial budget, and a 15-minute Formal budget. The model may choose an
epoch count in the declared range [5, 50]. Batch size remains task-locked to 1
because MTG is a variable-size transductive graph. A versioned advice artifact
states these limits and the complete-graph memory semantics to the proposer and
tuner; its SHA-256 is pinned by the launcher.

```bash
bash experiments/cancer_gene_identification/launch.sh \
  --experiment mtg_campaign \
  --profile campaign \
  --siderius-checkout /path/to/pinned/SIDERIUS \
  --workspace /path/to/cancer-mtg-campaign-workspace \
  --data_dir /path/to/NatureBench/problem/data
```

Run with `--dry-run` first. The validation mean AUPRC is campaign evidence;
official NatureBench comparison still requires the declared refit and untouched
test evaluator.
