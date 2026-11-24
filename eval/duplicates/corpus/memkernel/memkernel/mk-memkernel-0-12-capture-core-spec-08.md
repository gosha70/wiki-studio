---
page_type: decision
slug: mk-memkernel-0-12-capture-core-spec-08
title: 'Yield'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-12-capture-core/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

S2 ships as the pipeline's first slice: the spool, the reader, the key, redaction, the startup run
and the #120 hookup, with failed-then-fixed commands as its one extractor. That extractor captures rarely: 1 pair
in 289 failures across 65 transcripts (the yield fact above). S3 adds the extractors with real yield. The README
says both (FR-012).
