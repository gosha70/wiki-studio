---
page_type: decision
slug: mk-memkernel-0-4-plan-04
title: 'Health is read-only and split into quick and full'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-4/plan.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Context

near-duplicate detection re-embeds and queries each long-term memory; the status resource and `consolidate` must stay cheap; the pass must be complete within its candidate set.

## Decision

`health(full=False)` for the summary paths (status, consolidate, session start); `health()` for the admin endpoint and curators. `VectorStorePort.list_all` gains `include_content=False` so the quick report, `stale_sources` and `expired_present` read ids and metadata only. Near-duplicates query each candidate with `top_k = health_duplicate_limit`, filter neighbours on the long-term type values (never the `tier` key, which pre-0.2 records lack) and keep only neighbours inside the candidate set, so every qualifying pair in the set is found. `stale_sources` covers `code` memories only: a `document` source is a name, not a path.

## Consequences

the hooks cost O(n) metadata reads, not O(n) embeddings or O(n) document loads; the full pass is O(n) queries bounded by the limit; a fix mode is a later feature.
