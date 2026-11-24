---
page_type: decision
slug: cct-wiki-audit-trail-spec-04
title: '4 — Reject vs abandon'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-audit-trail/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

A reject is an *event* the gate produced — `wiki ingest`
writes a `disposition: "reject"` line, fully in scope. A true *abandon*
is the *absence* of an event: the process dies before `wiki ingest`
finishes (no line ever written) or a proposal is ingested but never
promoted. Capturing absence reliably requires long-lived machinery (a
sweep daemon or a mandatory teardown hook) well beyond #31's
"cheap-footprint" appetite, and #31's acceptance criteria only require a
line per `wiki ingest` *call* plus the accepted archive — not capturing
runs that never call ingest. So abandonment is **out of scope; no
`wiki abandon` command, no sweep**. Partial mitigation: an `accept`
ingest-log line with no matching `.audit/proposals/<name>/` archive is a
detectable "ingested but never promoted" signal — named here as the
hook point for a future cross-referential lint (the same deferred
semantic pass as Design Decision 3), explicitly a follow-up.
