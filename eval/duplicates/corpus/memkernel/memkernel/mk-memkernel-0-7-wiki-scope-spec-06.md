---
page_type: decision
slug: mk-memkernel-0-7-wiki-scope-spec-06
title: '`MemoryService.set_wiki_identity`, not a general retag'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-wiki-scope/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

A new `MemoryService.set_wiki_identity(ref_id, *, wiki_path, wiki_id=None) -> bool` changes only an existing
record's identity tags, nothing else: it replaces any `wiki-path:` with `wiki_path`, and adds `wiki-id:` when
`wiki_id` is given and the record has none. It returns False when nothing changed.
It refuses, with `ValueError`: an unknown record; another project's; a record that isn't a wiki memory (no
`wiki` tag); and a `wiki_id` that differs from one the record already carries. So it can neither move a memory
to another wiki nor touch any other tag. No MCP tool or CLI calls it; only the wiki import does.
The import calls it **before** `_retain_page`'s early return for a revision that is already current, so an
adopted, governed 0.6 record with the same `page_sha:` gains its tags without a new record.
