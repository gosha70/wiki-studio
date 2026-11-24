---
page_type: decision
slug: cct-one-harness-home-spec-05
title: 'Per-project convention'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/one-harness-home/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Keep `.code-copilot-team/config.toml`
as the committed per-project Pi configuration, out of this feature.
Option A moves it to `.cct/config.toml`, but `.cct/` is the untracked
runtime-state directory (review artifacts, ledgers, memory); a
committed config inside it needs every project to carve a gitignore
exception, and `pi-code init`'s manifest records the path and hash.
If you want the project side renamed too, it is a separate issue
with its own fallback and manifest rule. **Ruled 2026-11-15 by the
owner: rename the project side too, as a separate issue and PR after
this one.** This feature ships the user home; the project-side issue
carries its own fallback, manifest rule and gitignore guidance.
