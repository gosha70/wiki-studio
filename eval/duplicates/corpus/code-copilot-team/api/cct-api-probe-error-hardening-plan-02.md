---
page_type: decision
slug: cct-api-probe-error-hardening-plan-02
title: 'classify on lowercase substring matching of `str(exc)`; the matched text is NEVER returned.'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/api-probe-error-hardening/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

classify on lowercase substring matching of
`str(exc)`; the matched text is NEVER returned. Type-based signals take
precedence over substrings. *(Recommend — it is the only portable way to
distinguish auth-vs-unreachable across sqlite3/psycopg without importing
psycopg at module level.)*
