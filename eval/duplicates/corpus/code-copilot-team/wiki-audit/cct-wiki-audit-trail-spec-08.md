---
page_type: decision
slug: cct-wiki-audit-trail-spec-08
title: '8 — Audit append happens at the CLI layer, after materialization'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-audit-trail/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The natural-looking hook — "call `append_ingest_log` inside the
ingestor right after the gate" — cannot satisfy this spec's own
`proposal_hash` contract: the proposal directory (`plan.json` +
`preview/`) is written by `write_patch_set_dir` / `_write_proposal_file`
in `__main__.py` *after* the ingestor returns, and `--dry-run` body
stripping also happens in `__main__.py`. Hashing the materialized
payload therefore requires the append to run *after* materialization.
Decision: `append_ingest_log` is called from the `__main__.py` ingest
handlers (`_do_ingest`, `_do_ingest_multi`) after the proposal directory
exists and after any dry-run stripping, still fail-closed (a failed
append exits non-zero before the run is treated as audited). The
ingestor modules are not touched for the log. `--check` returns before
materialization and therefore never logs — consistent with its
"zero side effects" contract. A `build_log_record` helper in `audit.py`
derives the record from either a `WikiPatchSet` (multi-page) or an
`IngestProposal` (legacy) so both paths converge on one record shape.
