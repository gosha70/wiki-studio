---
page_type: decision
slug: mk-memkernel-0-10-recall-log-spec-08
title: 'What the report says about each repeat'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-10-recall-log/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

One of four outcomes:
**Shown:** memkernel returned the memory to that session before the error happened again.
**Missed:** the memory was in the store the session used, but memkernel did not return it before the error.
**Other store:** the memory was in a store the session never used.
**Unknown:** no log for that session, so it cannot be told.
