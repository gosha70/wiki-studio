---
page_type: decision
slug: cct-wiki-studio-adoption-plan-05
title: 'Delete both duplicate engines'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-studio-adoption/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Delete `scripts/wiki_ingest/` and `knowledge/wiki/scripts/lint-wiki.sh`.
Retarget every production caller to the package launcher. A guard catches a
restored engine tree/import. A CCT-only policy discovered during reconciliation
is expressed as schema data or a thin assertion, never by keeping a second
structural linter.
