---
page_type: decision
slug: mk-memkernel-0-7-hooks-spec-02
title: '"The latest checkpoint" for agents'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-hooks/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

`recall` gains `order: "relevance" | "newest"` (default `"relevance"`, today's behaviour). `order="newest"` is
accepted **only with `checkpoint_only=true`**: it returns live checkpoints newest first through
`MemoryService.checkpoints_newest_first()`, cut to `top_k`. With `checkpoint_only=false` it is refused with a
clear error. It is a parameter, not a tool, so the count stays 9.
**Alternative:** an MCP resource `memory://checkpoint/latest`. Agents call tools more readily than they read
resources, so this is not recommended.
