---
page_type: decision
slug: mk-memkernel-0-7-store-locks-spec-03
title: 'Tags have one writer'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-store-locks/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

`update_metadata` sends only the caller's keys; Chroma merges the rest (`plan.md`). That merge is an assumption
about chromadb (`>=1.0,<2`), not something memkernel can enforce; a test pins it, so a chromadb change that
breaks it fails CI before any release. With it, no `update_metadata` call can write `tags`, so `merge_tags`'s
lock needs no coordination with them. If a chromadb release stopped merging keys, an unlocked
`update_metadata` could write back a stale `tags` value between `merge_tags`'s read and write; the pinning
test fails on that release, before memkernel could ship with it.
`update_metadata` refuses a `tags` key with `ValueError`, in the port contract and the adapter.
A new port method, `VectorStorePort.merge_tags(ref_id, add, remove) -> bool`, reads the
record's tags and writes the result inside the store's lock `tags` (L1), so a tag added meanwhile is never
lost. It returns False when nothing changed.
Both current `tags` writers move to it: `_refresh_existing` (the dedup tag merge) and the code-chunk sync. No
other `update_metadata` call in `src/` passes `tags`; tests that do move with them.
