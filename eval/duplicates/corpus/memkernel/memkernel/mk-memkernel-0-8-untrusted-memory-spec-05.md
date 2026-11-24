---
page_type: decision
slug: mk-memkernel-0-8-untrusted-memory-spec-05
title: 'Where it applies'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-8-untrusted-memory/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

Everything memkernel injects from the store:
the session-start block, with the full and the `compact` sources;
`on_post_compact()`, which harnesses inject.

The session-end status injects no stored text, so it is unchanged.

MCP tool results (`recall`, `get`) are unchanged: they are data the agent asked for, and #85 rules out changes to
MCP tools and ports. The minimal 0.5 CLAUDE.md block and the frozen arms are untouched.
