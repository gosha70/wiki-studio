---
page_type: decision
slug: cct-wiki-studio-adoption-plan-03
title: 'The launcher chooses the bytes'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-studio-adoption/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`scripts/wiki` executes the repository venv's interpreter after checking
distribution metadata for exactly 0.9.0. It never uses an arbitrary PATH binary
or system interpreter. The same resolver is shared with doctor so “healthy”
means the bytes the next command will actually run. Runtime never auto-installs;
missing/mismatch stops before side effects and names the setup command.

`scripts/wiki-ingest` delegates to that launcher and adds only
`ingest --legacy-single-source`.
