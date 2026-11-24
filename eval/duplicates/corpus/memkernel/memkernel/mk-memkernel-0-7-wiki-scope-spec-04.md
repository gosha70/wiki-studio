---
page_type: decision
slug: mk-memkernel-0-7-wiki-scope-spec-04
title: 'A page''s previous memory, its corrections, its deprecation and supersession are this wiki''s only'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-wiki-scope/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

`_previous` (import, D4, D5) and `_is_this_pages` (`corrects` ownership) consider only memories that belong to
this wiki (S1), plus legacy candidates under S4.
**Resolution order for a page,** run before `_retain_page`'s early return and before `retain`, and by every
caller of `_previous`: the import, D4's predecessor and successor lookups, and D5's deprecated page:
**Owned candidates** (this wiki's live memories), with today's lookup: by page key, else by path.
**An interrupted supersession is completed first.** `retain` writes the replacement before it marks the
predecessor (`services.py:623-626`), so a failure in between leaves two live records. The replacement
carries `supersedes=<predecessor>`, which is the durable recovery data: when one candidate's `supersedes`
names another live candidate of the same lookup, the import calls `MemoryService.supersede(predecessor,
replacement)` (idempotent, never overwrites a marker) and keeps the replacement as the only candidate.
If the step that matches still finds **two or more**, the page is `ambiguous` (`duplicate records`):
**no store write and no ledger mark** for that page, in the import, D4 and D5 alike. If it finds one, that
is the previous memory.
**Only when no owned candidate exists,** legacy candidates are consulted (S4). A legacy record at the same
key or path as an owned record is ignored, left as it is, and never blocks the page.
A memory of another wiki is never a candidate, and never "this page's" correction.
