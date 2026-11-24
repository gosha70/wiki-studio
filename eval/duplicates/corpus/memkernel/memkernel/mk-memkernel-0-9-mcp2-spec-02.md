---
page_type: decision
slug: mk-memkernel-0-9-mcp2-spec-02
title: 'Transport tests: both'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-9-mcp2/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

(a) A test launcher that calls `create_server()` with the tests' `MockEmbedding`
and the real `server.run(transport)` in a subprocess, for stdio and for Streamable HTTP: fast, runs in CI.
(b) One `slow` test that starts the real `memkernel` command (real model) over stdio and does a roundtrip: covers
the entry point; CI does not run it.
