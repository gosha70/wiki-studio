---
page_type: decision
slug: mk-memkernel-0-7-spec-05
title: 'Deprecation'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

A page's memory is withdrawn with reason `deprecated` **once the deprecated
revision is approved**: `review_state` reports it `approved`, and its text has `status: deprecated`. Until then
the page is `stale`, and its last approved memory stays live (memkernel-0-6 FR-013). A
deprecated page that comes back to `stable` and is approved again gets a **new** memory: withdrawn records are
never dedup hits, just like superseded ones.
