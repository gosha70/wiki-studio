---
page_type: decision
slug: mk-memkernel-0-3-plan-02
title: 'Documents reuse the canonical-plus-chunks pattern'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-3/plan.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Context

`code` memories already store a canonical record plus chunk records linked by `chunk_refs`, with `forget` cleaning both.

## Decision

`document` follows the same pattern through the document store, with a token-based splitter instead of the AST chunker and the canonical record's content replaced by a summary. Chunk records are tagged `document_chunk` and filtered out of top-level `recall` results.

## Consequences

no schema migration; `forget` works unchanged; `recall` must filter one more tag.
