---
page_type: decision
slug: cct-pi-project-config-spec-02
title: 'Gitignore'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-project-config/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

No exception is needed; `init` only makes sure
`.cct/` is ignored, and `doctor` warns if `git check-ignore .cct.toml`
reports the configuration as ignored. **Ruled 2026-11-18 by the
owner.**
