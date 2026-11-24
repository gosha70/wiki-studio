---
page_type: decision
slug: cct-wiki-studio-adoption-plan-08
title: 'The package swap is not a governance migration'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-studio-adoption/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Do not run `wiki-studio init` and do not add `.wiki-studio.json`, approvals or
findings. The legacy round trip already proves the five existing verbs work in
manifest-less mode. Governance changes require a separate origin and migration
decision.
