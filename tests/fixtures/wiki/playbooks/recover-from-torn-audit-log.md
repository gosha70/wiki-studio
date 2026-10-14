---
page_type: playbook
slug: recover-from-torn-audit-log
title: Recover From a Torn Audit Log
status: stable
last_reviewed: 2026-10-12
sources:
  - path: README.md
    sha: 77d3811c1afe59832e9faa935deff81cb4b10b92
---

# Recover From a Torn Audit Log

## Symptom

`wiki-studio audit-flush` exits 11 and reports the working ingest log as malformed.

## Recovery steps

1. Run `wiki-studio lint --strict` to see which record fails validation.
2. Do not truncate the file; the next correct ingest appends a well-formed line.
3. Re-run `wiki-studio audit-flush --dry-run` to confirm the pending count.

## Verification

`wiki-studio audit-flush --dry-run` prints the pending count and a blob SHA.

## Prevention

Only `wiki-studio ingest` writes the ingest log; never edit it by hand.

## Related

- [Empty Index Commit After Git Lock Bypass](../incidents/empty-index-commit-after-git-lock-bypass.md)
