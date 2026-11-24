---
page_type: decision
slug: cct-llm-catalog-spec-09
title: 'Session keys'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/llm-catalog/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The launcher generates the session id and
passes `--session-id` for Claude Code and Pi; stamps start as
`attempted`; bare `--continue` and the interactive picker stay
native. Project-latest restoration was withdrawn: the harness's
"most recent" and CCT's "most recent stamp" are different sets.
Recommended. **Ruled 2026-11-10 by the owner: accepted as recommended.**
