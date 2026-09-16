# TIDMAD information treatments

These small files say what information an experiment gives to its research
agent. They do not change the TIDMAD task, data, metric, or validity rules.

Both treatments use the same task package in `tasks/tidmad`:

- `prerelease-with-advice.yaml` includes the reviewed prerelease advice file.
- `prerelease-without-advice.yaml` explicitly includes no human advice.

The launch adapter resolves one of these files before doing any work. When
advice is enabled, its checksum is checked before launch. When it is disabled,
the absence is recorded instead of being left implicit.

Module states are also explicit. For example, literature review can be turned
off in a SIDERIUS workflow while being `not_applicable` to a coding-agent
product that has no matching workflow module.
