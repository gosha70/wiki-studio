---
page_type: decision
slug: mk-memkernel-0-8-untrusted-memory-spec-04
title: 'Budget and truncation'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-8-untrusted-memory/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

The tags and the notice count against `TOTAL_BUDGET` (9,000), and the section
shares stay as they are. A share measures its lines as injected, tags included, so tag overhead never pushes a
section past its share. Truncation stays balanced:
`_fit` and `_truncate` cut the stored text before it is wrapped, so a cut never falls inside a tag. A truncated
checkpoint says so inside its element, as today, with the `get(ref_id)` pointer outside it;
`_cap`, the last guard, never leaves a `<stored-memory>` open. It cuts before the first element it cannot keep
whole, then adds its existing "truncated" line. It never closes a partial quote, because that would present a
cut quote as complete.

A test fills every section, with stored text that itself contains the tag, and checks three things: the block is
under 9,000 characters, every element is balanced, and no stored `</stored-memory>` survives unescaped. The
balance check is a scan, not an XML parser, because the block is markdown: it finds every `<stored-memory` and
`</stored-memory>` in order and requires strict open-then-close pairs, never nested, with exactly the elements
memkernel wrote.
