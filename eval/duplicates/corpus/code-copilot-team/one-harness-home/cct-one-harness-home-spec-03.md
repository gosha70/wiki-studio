---
page_type: decision
slug: cct-one-harness-home-spec-03
title: 'Migration mechanics'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/one-harness-home/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Read fallback through 2.1.x; `cct home
migrate` as the only mover, never overwriting; doctor and setup
notices; fallback removed in the first 2.2 change. Alternative:
`setup.sh` moves files automatically. Recommended: the explicit
command; a move the user did not ask for is the issue's own
objection to symlinks in another form. **Ruled 2026-11-15 by the owner: as recommended.**
