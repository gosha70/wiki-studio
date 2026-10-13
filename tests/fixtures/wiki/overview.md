---
page_type: overview
slug: overview
title: About This Wiki
status: stable
last_reviewed: 2026-10-12
sources:
  - path: README.md
    sha: 77d3811c1afe59832e9faa935deff81cb4b10b92
---

# About This Wiki

## Summary

This is the fixture wiki for the wikiforge test suite. It has exactly one page of every page type and three draft pages compiled by memkernel, so the structural linter, the query path and the memkernel schema contract are exercised together.

## Key ideas

- Every page type lives in the directory the schema assigns to it.
- `index.md` reaches every page; `log.md` records every edit.
- Draft pages from memkernel carry `memkernel_ref` and `memory_type` and cite a `memkernel://` source.

## Where this shows up

- `tests/fixtures/wiki/` in the wikiforge repository.
- `tests/test_fixture_wiki.py` asserts zero lint violations.

## Related

- [Spec-Driven Development](concepts/spec-driven-development.md)
- [Glossary](glossary/index.md)
