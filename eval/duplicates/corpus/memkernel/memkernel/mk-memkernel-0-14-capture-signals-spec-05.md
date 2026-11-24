---
page_type: decision
slug: mk-memkernel-0-14-capture-signals-spec-05
title: 'Caps'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-14-capture-signals/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

owner answers 30 per session, keeping the **last** 30; failed-then-fixed and session outcome as in S2
(5 per session, the first N); the run cap of 20 shared. The owner's choice of 30 and "keep the last", from the
per-session table (2026-11-18); a cap of 5 would keep 34% of the answers.
