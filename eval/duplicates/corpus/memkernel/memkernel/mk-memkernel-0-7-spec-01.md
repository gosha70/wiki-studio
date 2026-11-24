---
page_type: decision
slug: mk-memkernel-0-7-spec-01
title: 'How a memory is withdrawn'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

`supersede` needs a replacing record, but a deleted or
deprecated page has none. Three options:
**A, a new `withdrawn` marker (recommended).** Two new metadata keys, `withdrawn_reason` and `withdrawn_at`,
both absent by default.
Liveness becomes "no `superseded_by` and no `withdrawn_reason`". It is decided by **one** predicate that every
live-record path calls. Today 16 sites test `superseded_by` directly: `recall` and its window,
`list_memories`, `checkpoints_newest_first`, `consolidate`, health, revalidation, dedup in `chroma.py`, and
wiki export and import.
Records written by 0.1–0.6 load unchanged, because the key is absent and so live.
It says what happened: a withdrawn memory has no successor, and the marker carries why.
Cost: a core liveness change, touching every site once and moving it to the predicate.
**B, a tombstone record.** A new record ("page X withdrawn: deleted") supersedes the memory, so `supersede`
works unchanged.
But the tombstone is itself a live record. It would show up in `recall`, `list_memories`, `consolidate`,
export and health unless all of those learn to skip it, which is the same liveness change as A, plus an
embedding, a store record and a dedup case per withdrawal.
It also misstates history: "superseded by" a record that replaces nothing.
**C, a sentinel in `superseded_by`** (e.g. `withdrawn:deleted`). It needs no liveness change, but it
overloads a field every caller reads as a `ref_id`:
`get(superseded_by)` returns nothing;
health counts it as a dangling link;
`supersede`'s never-overwrite rule and the importer's `_is_this_pages` would both need special cases.

Rejected.

**The two markers together (confirmed):**
A withdrawn record **can** be superseded later. `supersede` sets `superseded_by` when it is empty and leaves
`withdrawn_reason` as it is, so the record keeps both: why it left, and what replaced it (D4's late link).
A superseded record is **not** withdrawn: `withdraw` on it returns `False` and changes nothing, because it is
already history and its successor says why.
Neither marker is ever cleared or overwritten.
