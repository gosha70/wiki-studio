---
page_type: decision
slug: mk-memkernel-0-14-capture-signals-spec-03
title: 'Record type for an owner answer: `episode`'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-14-capture-signals/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

(short-term, kept 30 days, `episode_ttl_days`). Not `decision`,
which is long-term by type and would enter long-term memory without the agent choosing; not `observation`, which
expires after 7 days (`observation_ttl_days`), so an answer nobody promoted within a week would be lost and the
first user scenario would fail.
