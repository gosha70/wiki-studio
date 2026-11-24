---
page_type: decision
slug: mk-memkernel-0-10-recall-log-spec-07
title: 'What counts as a stored error, and as a repeat'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-10-recall-log/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

**Stored error:** text a memory quotes in backticks that contains an error word (`Error`, `Exception`,
`Traceback`, `FAILED`, `fatal`). Example: a memory saying ``npm test fails with `Error: Cannot find module 'x'` ``
stores the error `Error: Cannot find module 'x'`. Each such span is its own stored error; matching is
case-sensitive.
**Repeat:** a later session whose own `Bash` output contains that exact text.
