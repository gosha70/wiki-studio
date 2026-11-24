---
page_type: decision
slug: cct-api-probe-dsn-constraints-plan-03
title: 'a missing sqlite file is REJECTED with "database file does not exist yet — save the configuration and run ingest to create it", not created.'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/api-probe-dsn-constraints/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

a missing sqlite file is REJECTED with
"database file does not exist yet — save the configuration and run ingest
to create it", not created. *(Recommend — for a brand-new store there is
nothing to test; probing would only prove the server can write a file,
which is precisely the primitive being removed. The message keeps the
test-before-save workflow honest rather than blocking it.)*
