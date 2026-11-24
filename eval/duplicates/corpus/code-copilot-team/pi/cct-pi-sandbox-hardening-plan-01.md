---
page_type: decision
slug: cct-pi-sandbox-hardening-plan-01
title: 'Default ON'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-sandbox-hardening/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`security.env_scrub` defaults true; opt-out honored from
trusted scopes per decision 5. Subagent spawning is itself opt-in
(`agents.subagents_enabled`) and the keep-list keeps children functional.
