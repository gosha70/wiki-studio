---
page_type: decision
slug: cct-pi-project-config-spec-05
title: 'Companion files'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-project-config/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The personal override is `.cct.local.toml` and the
manifest is `.cct-init.json`, both at the repo root beside
`.cct.toml`; `init` adds `.cct.local.toml` to the ignore lines beside
`.cct/`, since a personal file must not be committed. The migrate
command is `pi-code migrate`, beside `init` and `sync`, which own the
same files. **Approved 2026-11-18 by the owner with the bundle.**
