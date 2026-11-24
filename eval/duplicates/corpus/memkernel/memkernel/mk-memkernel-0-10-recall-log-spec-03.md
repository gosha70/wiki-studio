---
page_type: decision
slug: mk-memkernel-0-10-recall-log-spec-03
title: 'A normal session start shows memories without `recall`, so logging only `recall` calls would report them as missed.'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-10-recall-log/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

A normal session start shows memories without `recall`, so
logging only `recall` calls would report them as missed. Each hook block that shows memories writes one record
listing the `ref_id`s it injected.
