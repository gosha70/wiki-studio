---
page_type: decision
slug: mk-memkernel-0-7-spec-03
title: 'How deletion is detected'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

wiki-studio provides no signal. **Only a memory that
this wiki's ledger recorded as imported (an `applied` import entry naming its `ref_id`) may be withdrawn as
deleted. A legacy memory, imported before the ledger existed or by the ungoverned import, never is**, even when
its page is gone. The ledger is the only proof that the memory came from this wiki. Such a memory counts as
deleted when, in a **complete** governed listing (`api.review_state` with `pages=None`, which returned without
error):
its `page_key:` tag matches no listed page;
its `source` path matches no listed page;
and the file at that `source` is absent from the wiki directory.

All three must hold, so a rename that kept its `page_id` is matched by key and is not a deletion. A rename that
lost its `page_id` withdraws the old memory, and the new path is imported once approved, as wiki-studio treats it
too. A listing error withdraws nothing.
