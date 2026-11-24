---
page_type: decision
slug: cct-pi-project-config-spec-01
title: 'Location'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-project-config/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`.cct.toml` at the repo root, not `.cct/config.toml`:
`.cct/` stays runtime state and needs no gitignore carve-out.
**Ruled 2026-11-18 by the owner.**
