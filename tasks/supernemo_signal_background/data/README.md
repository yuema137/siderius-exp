# SuperNEMO data

Download the four HDF5 files from the [official release](https://zenodo.org/records/20698789)
into your own data directory outside the source repositories. The
[source manifest](../declared/source_files.json) lists the required filenames,
sizes and verification details. Keep the completed download for later runs.

The model consumes events, while the raw files contain detector-hit rows.
Execution therefore also needs event indexes. The
[tutorial preparation guide](../../../tutorials/supplementary/supernemo/README.md#2-download-raw-data-and-prepare-event-indexes)
shows how to generate those indexes in a separate directory, using symbolic
links to the raw files rather than copying them. Point the tutorial's
`data_dir` at that prepared directory.

The existing indexer preserves the task's event-level train/validation/test
membership. Search uses train and validation; a fraction changes selection
within those partitions, not membership. This tutorial does not run the reserved
final test.

Generated indexes, reports, checkpoints, predictions and workspaces remain
external. Only small, explicitly identified example plots and provenance belong
in the repository. Historical machine paths in older receipts describe those
past runs, not a required location on your machine.
