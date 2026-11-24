---
page_type: decision
slug: mk-memkernel-0-10-recall-log-spec-02
title: 'Where to log'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-10-recall-log/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

Recalls made by the MCP tool, and what the hook blocks show (A1), through one small
`recall_log` module; `MemoryService.recall` keeps its signature. Recalls by other Python callers are not logged.
