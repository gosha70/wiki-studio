---
page_type: decision
slug: cct-simplest-complete-change-plan-03
title: 'Selective Decision Memory via Existing MemKernel Interfaces'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/simplest-complete-change/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

**Context**: Recording every trivial implementation choice creates noise, whereas losing high-impact architectural reuse decisions causes future sessions to re-litigate rejected designs.
**Decision**: The decision-record contract already exists on master (#445: `decision`, `requirement`, `chosen`, `rejected`, `evidence`, `revisit-when`; recall before building, check evidence before reuse, ask on conflict). Implementation verifies it against FR-005 and adds only the "selective, high-value" qualification, with no new fields and no MemKernel API change.
**Consequences**: High signal-to-noise ratio in memory without any MemKernel schema or API changes.
