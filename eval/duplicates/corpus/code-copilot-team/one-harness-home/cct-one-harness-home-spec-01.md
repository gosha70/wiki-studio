---
page_type: decision
slug: cct-one-harness-home-spec-01
title: 'Direction'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/one-harness-home/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Option A: `~/.cct/` wins for the user home.
Option B would retire `~/.cct/` but leave the per-project runtime
state at `.cct/`, so the names would still differ between project and
home. **Ruled 2026-11-15 by the owner: as recommended.**
