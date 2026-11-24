---
page_type: decision
slug: cct-wiki-audit-flush-spec-01
title: '1 — Verb, not a flag'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-audit-flush/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The issue offers `wiki audit-flush` *or*
`wiki ingest --commit-pending`. Decision: a dedicated **verb**. A flag
on `ingest` would re-enter the ingest argument surface, imply coupling
to an ingest run, and be undiscoverable for "I just want to flush." A
verb is one obvious surface, matches the issue title, and slots into
the existing dispatcher with no behavior change to other verbs.
