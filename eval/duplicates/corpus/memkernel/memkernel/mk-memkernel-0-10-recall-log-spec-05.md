---
page_type: decision
slug: mk-memkernel-0-10-recall-log-spec-05
title: 'Size limit'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-10-recall-log/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

Both limits are settings: a maximum size per file (default 5 MB)
and a maximum number of files (default 10), so at most 50 MB by default.
