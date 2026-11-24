---
page_type: decision
slug: mk-memkernel-0-7-wiki-scope-spec-08
title: 'The ledger''s rebuild follows the scope'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-wiki-scope/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

A corrupt ledger is rebuilt (#78) only from memories that
belong to this wiki (S1), never from legacy or other wikis' memories.
