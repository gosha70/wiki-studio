---
page_type: decision
slug: cct-wiki-studio-adoption-plan-13
title: 'A pin bump is a reviewed CCT feature-maintenance change'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-studio-adoption/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The CCT maintainer proposing a bump owns an atomic update to the version/hash,
publishing provenance, schema classification/delta/fingerprint, doctor and
catalogue statements, and full contract evidence. This cost is deliberate: it
is what prevents upstream behavior changing without a CCT commit. The update
procedure is documented beside the lock.
