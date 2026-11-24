---
page_type: decision
slug: cct-api-probe-dsn-constraints-plan-01
title: 'add `scheme_not_allowed`, `host_not_allowed`, `sqlite_file_missing` to the #100 closed set rather than folding them into `bad_dsn`.'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/api-probe-dsn-constraints/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

add `scheme_not_allowed`, `host_not_allowed`,
`sqlite_file_missing` to the #100 closed set rather than folding them into
`bad_dsn`. *(Recommend — the set is meant to grow deliberately, and each
needs a different operator action: fix the scheme, use the configured
host, or save-then-ingest to create the file.)*
