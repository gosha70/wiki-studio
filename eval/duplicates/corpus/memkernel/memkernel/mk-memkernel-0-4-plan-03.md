---
page_type: decision
slug: mk-memkernel-0-4-plan-03
title: 'Sourced code identity is (source, hash); chunk records are owner-specific; supersession is durable'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-4/plan.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Context

today `code` records and their chunks are deduplicated globally by content hash, so two paths with the same content share one record and an unchanged function is one chunk shared by old and new versions; and `_filter_live` only hides a superseded record when its successor is in the same result window.

## Decision

`find_by_hash` gains a `source` filter and sourced code dedups per path; chunk records get ids `<canonical>-chunk-<n>`, the `code_chunk` tag and `parent_ref`, and are written without dedup; the new canonical gets `supersedes=<old>` and every replaced canonical gets `superseded_by=<new>`, which `_filter_live`, `list_memories`, `consolidate` and `WikiExporter` honour independently of the fetched set; `revalidate()` writes review flags only, and unmarked 0.2/0.3 links are reported by health as `unmarked_supersessions`. Old canonicals stay (hidden); only their owned chunks are deleted.

## Consequences

provenance survives, recall stays clean for any query, flags and deletions can never touch another owner's chunks; the store holds one chunk record per owner (bounded by the number of live snapshots since replaced owners lose theirs). Legacy shared chunks are left as they are and documented.
