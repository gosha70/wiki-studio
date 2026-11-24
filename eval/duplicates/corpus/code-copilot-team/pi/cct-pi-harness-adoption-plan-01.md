---
page_type: decision
slug: cct-pi-harness-adoption-plan-01
title: 'Advisory package / enforced runtime split'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-harness-adoption/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Context

Registering the runtime in Pi's package manifest would load
enforcement in bare `pi`, breaking the "bare pi stays plain" guarantee.

## Decision

Native manifest exposes only `pi.skills`/`pi.prompts`/
`pi.themes`; runtime lives outside auto-discovered paths and is loaded
explicitly by `pi-code --extension <managed>/runtime/index.ts` with
`CCT_RUNTIME=1` as defense-in-depth (refuse enforcement init without it,
except test/SDK bootstrap).

## Consequences

two documented install modes (FR-002a); tests must prove
bare `pi` executes no runtime init code.
