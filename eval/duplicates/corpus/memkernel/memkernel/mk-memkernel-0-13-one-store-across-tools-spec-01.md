---
page_type: decision
slug: mk-memkernel-0-13-one-store-across-tools-spec-01
title: 'Several stdio servers: support them'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-13-one-store-across-tools/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

(the #139 fix is on `main`), and document the shared HTTP server as the alternative
for a long-running setup: both setups are supported. Stdio-per-tool is what every tool's MCP config does by default,
and the #139 fix makes it correct.
