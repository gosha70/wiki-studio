---
page_type: decision
slug: cct-plugin-generate-from-sources-plan-04
title: 'commands and agents that need templates or a helper script'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/plugin-generate-from-sources/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Recommended: ship `templates/sdd/` and `review-decide.sh` inside the
plugin and rewrite the paths (FR-1, FR-2), so every command works for a
plugin-only user exactly as far as it works for a `setup.sh` user. The
alternative, packaging only the self-contained components, drops five
commands and leaves eight agents pointing at paths that do not exist.
