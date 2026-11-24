---
page_type: decision
slug: mk-memkernel-0-7-governed-spec-06
title: 'The gate checklist items only the bridge can tick'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-governed/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

**Receipts:** consumed since 0.6 (`proposal`, `submission_digest`, `archived_dir`); nothing to build.
**The lock file:** the README tells a project whose wiki is in git to ignore `.*.wiki-studio.lock` beside the
wiki directory; memkernel creates no lock file of its own there.
**`hash_recipe`:** memkernel reads no ingest log, so there is no consumer; the README and #48 say so.
