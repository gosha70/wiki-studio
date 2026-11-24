---
page_type: decision
slug: mk-memkernel-0-4-plan-02
title: '`needs_review` is a flag, not a tier'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-4/plan.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Context

#3 proposed a `needs_review` state excluded from recall.

## Decision

additive metadata on the record; `_filter_live` drops flagged records unless asked for; `get` and `list_memories` still show them.

## Consequences

no schema change; old stores load with the default; the flag clears when the file matches again or when the memory is superseded.
