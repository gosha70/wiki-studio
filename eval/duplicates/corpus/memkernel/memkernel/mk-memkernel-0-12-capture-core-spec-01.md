---
page_type: decision
slug: mk-memkernel-0-12-capture-core-spec-01
title: 'Key'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-12-capture-core/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

(session, `tool_use_id`, extractor), with the extractor version as a tag. No version supersede; a
session is captured once, under the version installed then. (Amended by the owner, R2: the key named the record
UUID, which several results in one entry share.)
