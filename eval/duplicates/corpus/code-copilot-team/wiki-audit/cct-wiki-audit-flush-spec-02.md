---
page_type: decision
slug: cct-wiki-audit-flush-spec-02
title: '2 — Prefix-based pending detection'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-audit-flush/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Because
`ingest-log.md` is strictly append-only with a fixed preamble, "pending"
is unambiguous: the committed blob must be a byte prefix of the working
file; pending count = extra NDJSON lines after the preamble. This needs
no diff library and is robust to content (JSON with commas/newlines is
never an issue — we count physical lines after the preamble). If the
prefix check fails, the append-only contract was violated and the tool
**refuses** rather than guessing — it never edits the ledger.
