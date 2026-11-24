---
page_type: decision
slug: cct-pi-sandbox-hardening-plan-02
title: 'Keep-list defaults'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-sandbox-hardening/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`,
`PI_API_KEY` (plus the OS/CCT baselines); anything else via
`security.env_scrub_keep`.
