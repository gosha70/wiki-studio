---
page_type: decision
slug: mk-memkernel-0-7-wiki-scope-spec-01
title: 'Terms'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-wiki-scope/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

A memory's **identity tags** are `wiki-path:` and `wiki-id:`. A **legacy** memory carries neither
(0.6 memories carry the generic `wiki` tag, which says nothing about which wiki). A **path-only** memory carries a
`wiki-path:` and no `wiki-id:`.
