---
page_type: decision
slug: cct-wiki-audit-trail-spec-07
title: '7 — Backfill'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-audit-trail/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Issue #31 puts
historical backfill out of scope; confirmed. Verified:
`doc_internal/proposals/.applied/` is **empty** (created 2026-05-06,
never populated), so there is literally nothing to migrate even if we
wanted to. No one-shot migration script. Existing/future
`doc_internal/proposals/.applied/<name>/` stays exactly where it is as a
gitignored *local cache* and is never swept into `.audit/`. Pre-feature
proposals are simply not represented in the audit trail; the trail
starts the day the feature lands.
