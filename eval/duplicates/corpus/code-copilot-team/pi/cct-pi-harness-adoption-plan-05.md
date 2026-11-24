---
page_type: decision
slug: cct-pi-harness-adoption-plan-05
title: 'CCT-owned TOML config; Pi settings minimal'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-harness-adoption/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

policy lives in `~/.code-copilot-team/config.toml` and
trusted `.code-copilot-team/` project files (consistent with
`providers.toml`); `.pi/settings.json` carries only registration and
Pi-native options. Ordinary and protected-security precedence chains are
distinct; the security floor is monotonic (P7).
