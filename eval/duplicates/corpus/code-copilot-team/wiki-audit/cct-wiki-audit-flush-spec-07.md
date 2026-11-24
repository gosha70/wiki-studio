---
page_type: decision
slug: cct-wiki-audit-flush-spec-07
title: '7 — Fail-closed on a malformed working log'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-audit-flush/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The pathspec commit
captures the *entire* file's bytes, so if the working `ingest-log.md`
has a torn final line (a crashed mid-append) or any non-v1 / non-JSON
record, committing would persist an invalid tracked ledger. So before
counting or committing, `detect_pending` runs the existing `audit_lint`
v1 validation over the working log (and checks it ends with a newline);
any failure sets `malformed=True` and `flush` **refuses**
(`AuditFlushError`, exit 11) and commits nothing. The malformed tail is
left in the working tree to be completed/repaired by the next correct
append — `audit-flush` never edits or truncates the ledger to "fix" it.
Rationale: an audit trail that commits known-invalid bytes is worse
than one that loudly refuses.
