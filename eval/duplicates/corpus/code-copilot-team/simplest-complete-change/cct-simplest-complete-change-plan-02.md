---
page_type: decision
slug: cct-simplest-complete-change-plan-02
title: 'Single Home for the Reuse Ladder (`copilot-conventions`) vs Config Boundary'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/simplest-complete-change/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

**Context**: Both `copilot-conventions` and `coding-standards` are always-loaded rules. Putting the reuse ladder in both would bloat prompt context and create maintenance drift.
**Decision**: Place the ordered reuse ladder in `shared/skills/copilot-conventions/SKILL.md` under `Target Alignment and Complexity Control`. Keep `shared/skills/coding-standards/SKILL.md` focused strictly on clarifying the boundary between externalized configuration defaults (schema, fallback, and operator defaults) and genuinely non-configurable named constants.
**Consequences**: Zero duplication between always-loaded skills; clear separation of concerns.
