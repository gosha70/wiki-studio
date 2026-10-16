# Run 2 — one-time ingest record

Produced by `eval/navigation/run2_protocol.py` under the protocol of
`specs/wiki-studio-0-3-0/` (US5). Facts are in `manifest.json`; add observations below, never edits.

## Observations

- **Probe pass rule changed one minute before the recorded probe.** Commit 81c920b
  (11:55:41 local) failed the probe on any `pytest` process anywhere on the machine;
  commit 61b3d9b (11:56:46 local) narrowed that to a pytest whose parent chain reaches
  the probe's own `claude` call, after a scratch probe had tripped on an unrelated
  pytest. The recorded probe (15:57:55 UTC, 11:57:55 local) ran under the narrowed
  rule and saw two unrelated pytest processes, both from memkernel's virtual
  environment (`pytest_unrelated` in the manifest); under the earlier rule it would
  have failed. The byte comparison of the fixture, the decisive check, was unchanged
  by the rule change and passed. Recorded here by the build on the reviewer's request.
