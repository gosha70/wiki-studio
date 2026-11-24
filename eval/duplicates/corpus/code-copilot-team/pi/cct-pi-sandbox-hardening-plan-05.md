---
page_type: decision
slug: cct-pi-sandbox-hardening-plan-05
title: 'Trust asymmetry for scrub config'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-sandbox-hardening/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

(pre-commit review + phase-1 review,
2026-08-06) — loosening keys (`env_scrub=false`, `env_scrub_keep`) are
honored only from user-controlled scopes: global config, `CCT_CONFIG__*`
env, cli `--set`. BOTH in-repo layers (`config.toml`, `config.local.toml`)
are tighten-only, and a later user-controlled explicit boolean beats an
earlier repo enable (ordered walk). Tightening (`env_scrub_extra`) is
honored from any layer. The out-of-session CLI (`env scrub-list`) treats
project config as untrusted (existing model) and therefore never honors a
project-local opt-out — no FR-004a bypass, and launcher pass-through tests
target global config, not project config.
