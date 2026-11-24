---
page_type: decision
slug: mk-memkernel-0-7-governed-spec-05
title: '`page_id` on created pages'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-governed/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

The gated export passes `assign_page_ids=True` to `api.propose`, so every page
memkernel creates carries wiki-studio's stable `page_id`. The import keys pages by `page_key`, which is the
`page_id` when present.
**Amended during the build (2026-11-04; confirmed by the owner on 2026-11-04):** this spec said a later rename already kept the page's memory. Against the real wiki-studio it
did not: a renamed page keeps its content, so the import found no dedup hit at the new path and wrote a second
live memory. The import now also supersedes when the page's previous memory, found by `page_key`, is at another
path, so a rename leaves one live memory with its history. At the owner's request (2026-11-04) the import also
skips its "already current" early return when that memory's `source` is another path: a page moved with
identical bytes (wiki-studio's approval follows the `page_id` and the bytes, so the moved page is approved
without a new approval) gets its record at the new path, and the old path no longer finds it. A new page at the
old path therefore never takes the moved page's memory; wiki-studio itself refuses to approve one while the
moved page keeps the same slug. One more existing assertion changed with it (confirmed by the owner on 2026-11-04):
`test_a_rename_that_kept_its_page_id_is_not_a_deletion` asserted the memory stayed at the old path; it now asserts
the one live memory is at the new path and supersedes the old record, and still that nothing is withdrawn.
