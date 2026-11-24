---
page_type: decision
slug: cct-wiki-audit-flush-spec-06
title: '6 — Detached HEAD / dirty tree tolerated'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-audit-flush/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

A pathspec commit works
on detached HEAD and does not require a clean tree (it ignores other
changes by construction). `audit-flush` proceeds and the commit lands
on the current HEAD; no special-casing, no refusal for unrelated dirty
state.
