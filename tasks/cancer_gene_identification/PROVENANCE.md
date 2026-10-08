# PROVENANCE — NatureBench cancer-gene identification

## Dataset

The executable benchmark package is NatureBench case
`s41551-024-01312-5`, distributed by FrontisAI on Hugging Face:

<https://huggingface.co/datasets/FrontisAI/NatureBench/tree/main/tasks/s41551-024-01312-5>

NatureBench attributes the reformatted data to the TREE study and Zenodo DOI
`10.5281/zenodo.11648891`. The originating code is:

<https://github.com/Blair1213/TREE>

No dataset bytes or hidden test labels are committed in this pack.

## Comparator

AI-Build-AI's released implementation and predictions are at:

<https://github.com/aibuildai/AI-Build-AI/tree/main/tasks/cancer-gene-identification>

Its README and blog report mean AUPRC `0.774`. The eight exact values in its
committed `predictions/score.json` have arithmetic mean
`0.7725415502369475`; this pack treats the latter as the reproducible artifact
target and preserves the former only as the published claim.

## Declarations and code

The task composition points to declarations and plugins co-located under this
pack. Graph packing preserves complete-network transduction and reads adjacency
matrices blockwise before emitting sparse edge records. The metric arithmetic
implements average precision and ROC AUC without importing a second benchmark
package; targeted tie-handling tests pin the threshold semantics.

The local synthetic fixtures in
`tests/tasks/cancer_gene_identification/test_cancer_package_contract.py` are
generated at test time and are not scientific evidence. The later
[CPDB tutorial receipt](../../tutorials/supplementary/cancer/example/provenance.json)
records a real-data, three-iteration GPU workflow at its exact source pair.
See [STATUS.md](STATUS.md) for the CPDB-only scope and the separate historical
multi-network qualification; neither establishes the full comparator result.
