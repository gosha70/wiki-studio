---
page_type: decision
slug: mk-copilot-memory-mvp-plan-04
title: 'Reference-based returns'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/copilot-memory-mvp/plan.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Context

MCP tool responses flow through the client's context window. Large responses waste tokens.

## Decision

`recall` returns `ArtifactRef` objects (ref_id, preview ~200 chars, score, token_count, type, timestamp). Full content requires a separate `get(ref_id)` call. The `type` and `timestamp` fields are required per FR-003 so clients can filter/sort without fetching full content.

## Consequences

Two-step retrieval flow. Clients must call `get` for full content. Reduces per-search token cost by 80-95%. ArtifactRef carries enough metadata for client-side filtering.
