---
page_type: decision
slug: cct-wiki-audit-flush-spec-05
title: '5 — Independent of promote; still git-free elsewhere'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-audit-flush/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

This is the
sole pipeline command that runs git, by design and in one place
(`audit_flush.py`). `ingest`/`promote`/`lint` remain git-free. No hook,
no scheduler, no auto-invoke — the boundary the pipeline maintains is
preserved; `audit-flush` is the explicit, user-driven exception.
