---
page_type: decision
slug: mk-copilot-memory-mvp-plan-05
title: 'Deduplication semantics — content hash vs ref_id identity'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/copilot-memory-mvp/plan.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Context

FR-010 requires dedup by content hash. But each Memory has a unique ref_id, and `forget(ref_id)` deletes one memory. If two `retain` calls send identical content, what happens? Options: (a) return the existing ref_id (idempotent), (b) create a second metadata-only record sharing content, (c) reject the duplicate.

## Decision

**Content+type-scoped dedup within a project, with metadata refresh.** The dedup key is `(content_hash, type)`. When `retain` is called with content whose SHA-256 hash and `type` already match an existing record in the same project's collection, the system returns the existing `ref_id` and **updates mutable metadata** (`session_id`, `timestamp`, `checkpoint`) to the new values. The content and `ref_id` stay the same — no re-embedding occurs. Same content with a **different `type`** creates a separate memory with its own `ref_id` — a decision and an episode with identical text are semantically different records.

## Consequences

`retain` is idempotent for content+type (no duplicate storage or embedding cost) but keeps provenance fresh — the same decision retained in a later session will appear under that session's `session_id` filter and carry the latest timestamp. Checkpoints with unchanged content still update their recency and `checkpoint` flag. `forget(ref_id)` is safe — it deletes exactly one record since there are no aliases or shared content references. Cross-project dedup is not performed (project isolation takes priority). The BM25 side index mirrors this: one entry per ref_id, content unchanged on metadata refresh (no BM25 re-index needed).
