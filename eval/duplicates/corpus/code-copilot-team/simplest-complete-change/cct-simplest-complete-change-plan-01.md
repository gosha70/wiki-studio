---
page_type: decision
slug: cct-simplest-complete-change-plan-01
title: 'Native CCT Policy Without a Ponytail Dependency'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/simplest-complete-change/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

**Context**: Ponytail helped motivate the reuse-first ladder and can be installed alongside CCT. CCT must still provide its core policy consistently across supported harnesses without requiring another plugin, repository, release lifecycle or runtime component.
**Decision**: Implement the policy natively in CCT's shared instruction architecture. Ponytail is neither an installation nor a runtime dependency. CCT does not import Ponytail hooks, commands, personas or mutable upstream instruction files.
**Consequences**: CCT owns the wording, compatibility, tests, delivery and release lifecycle, and works when Ponytail is absent or changed. Users may install Ponytail independently; combined installs are not guaranteed compatible unless separately tested. Upstream ideas are re-expressed under CCT's requirements with licence and provenance reviewed; upstream changes do not flow into CCT automatically.
