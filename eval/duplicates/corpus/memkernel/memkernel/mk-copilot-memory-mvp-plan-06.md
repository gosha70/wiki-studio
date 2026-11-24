---
page_type: decision
slug: mk-copilot-memory-mvp-plan-06
title: 'Session scoping in tool contract'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/copilot-memory-mvp/plan.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Context

FR-009 requires `session_id` metadata, and episodic memories need session-scoped TTL. But the MCP tool parameters don't specify how `session_id` is supplied, and `recall` doesn't distinguish episodic from durable memories.

## Decision

`retain` accepts an optional `session_id` parameter (string). If omitted, defaults to `"default"`. `retain` also accepts a required `type` parameter (MemoryType enum: decision/convention/code/episode). `recall` accepts optional `type` and `session_id` filter parameters — when provided, results are filtered to matching metadata before ranking. Episodic memories (type=episode) are scoped to their session for TTL purposes but are searchable across sessions unless filtered.

## Consequences

Session scoping is opt-in via filter, not enforced by separate collections. This keeps the storage model simple (one collection per project) while allowing session-aware queries. TTL enforcement uses `type` + `timestamp` to identify expired records, not session boundaries. Copilots that want session-isolated recall pass `session_id` as a filter.
