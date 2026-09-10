# Legacy SIDERIUS advice archive

This directory preserves historical run and Gate advice removed from the
SIDERIUS framework repository during the framework/experiment separation.
Paths below this directory mirror their original SIDERIUS paths so historical
design records can identify the exact artifact without turning it into a
current default.

These files are provenance-only:

- no active experiment or campaign launcher selects them;
- they are not current Gold treatment;
- they must not be copied into a SIDERIUS installation;
- reproducing a historical run requires explicitly selecting the corresponding
  archived artifact and recording its content hash.

The migration compared every copied file byte-for-byte with its original
source before deleting the framework copy. Files that still had a live
framework test consumer were deliberately excluded from this batch and remain
in the source repository until that test responsibility is migrated or
replaced.
