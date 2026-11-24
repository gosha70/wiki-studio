---
page_type: decision
slug: cct-api-probe-dsn-constraints-plan-02
title: 'extract the sqlite path rule into db.py and use it from both `connect()` and the validator.'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/api-probe-dsn-constraints/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

extract the sqlite path rule into db.py and use it
from both `connect()` and the validator. *(Recommend — the alternative is
two parsers of a non-obvious rule, which is the exact defect class flagged
and fixed twice in this series.)*
