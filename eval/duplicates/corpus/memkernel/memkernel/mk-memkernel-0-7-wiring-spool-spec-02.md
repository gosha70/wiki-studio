---
page_type: decision
slug: mk-memkernel-0-7-wiring-spool-spec-02
title: 'Spool pruning'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-wiring-spool/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

At each `startup` drain:
A session with no `ended` line whose newest line is older than `SPOOL_UNENDED_MAX_AGE` (a named constant, 7
days) is removed. The current session is never removed.
Such a session gets no "ended without a saved checkpoint" line, because its window never closed.
If any were removed, the block says so once: "N earlier session(s) recorded no end (crashed, or session-end.py
is not registered under SessionEnd)."
The spool then holds at most the current session, sessions under 7 days old without an end, and ended sessions
not yet drained.
