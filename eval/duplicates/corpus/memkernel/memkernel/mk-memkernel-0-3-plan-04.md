---
page_type: decision
slug: mk-memkernel-0-3-plan-04
title: '`MemoryLifecycle` returns text, performs no I/O beyond the service'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-3/plan.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Context

haa and the Claude Code hooks both need the session protocol; haa injects text into its message list, hooks print to stdout.

## Decision

each lifecycle method returns a markdown string and takes only what the service provides; printing and stdin parsing stay in the hook scripts.

## Consequences

identical behaviour across harnesses; easy to unit test.
