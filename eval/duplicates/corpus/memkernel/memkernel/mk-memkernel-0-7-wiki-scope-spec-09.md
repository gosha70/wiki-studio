---
page_type: decision
slug: mk-memkernel-0-7-wiki-scope-spec-09
title: 'Concurrency for wiki identity'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-wiki-scope/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

The store locks and the single
tag writer are their own prerequisite spec, `specs/memkernel-0-7-store-locks/` (the owner's "split S8",
2026-11-03): store-keyed lock identity, `VectorStorePort.exclusive(name)`,
`VectorStorePort.merge_tags(ref_id, add, remove)`, `update_metadata` refusing `tags`, and `LockReentryError`. This
spec uses them:
**One import at a time per store.** Every import, governed and ungoverned, holds
`exclusive("wiki-import")` for its whole run (unlocked where there is no lock; see below). Different wikis' ledger locks don't serialize each
other, and the ungoverned import has no ledger, so only this lock makes S3's and S4's checks and their writes
one step. Two wikis adopting the same `ref_id` run one after the other: the second sees the record already
owned and reports `candidate changed`. Lock order, always: the import lock, then the path-hash ledger, then the
`wiki_id` ledger.
**Identity tags are reserved.** Serialization stops lost updates, not wrong ones, so `wiki-path:` and `wiki-id:`
can be set only by the identity operations:
`MemoryService.retain` and the MCP `retain` tool refuse, with `ValueError`, any tag in `tags` that starts with
`wiki-path:` or `wiki-id:`. The import passes a new record's identity through a separate keyword,
`retain(..., wiki_identity=(path, id))`, which applies only when a new record is written; a dedup hit
keeps its identity tags as they are;
so a dedup refresh never adds or re-adds an identity tag, in either order with a move's retag;
`set_wiki_identity` changes identity tags through `merge_tags` and rejects a conflicting `wiki-id:`, as S5
says.
**`promote` never creates a wiki candidate.** Promoting a wiki memory drops every wiki-import tag from the copy:
`wiki`, `page:`, `page_type:`, `page_key:`, `page_sha:`, `wiki-path:` and `wiki-id:`. The importer's candidates
are wiki-tagged live memories (`sync.py:384`), so the copy is an ordinary memory, linked by `promoted_from`.
**Without a lock (Windows and other non-POSIX platforms): the owner's decision of 2026-11-03.** "On Windows,
let adoption run unlocked with one warning (the race needs my own contradictory assertion), documented." With
the earlier decision that ordinary imports degrade like #69, nothing in the wiki import refuses without the lock:
every import holds `exclusive("wiki-import")`, and `set_wiki_identity` writes through
`merge_tags`; without a lock both run unlocked and the store-locks spec logs one warning.
What unlocked races between two imports can do:
same wiki, two ledger saves: the last save wins and entries are lost, so fewer deletions are provable; the
next run records every page again. Repaired.
same wiki, two ledger migrations (`adopt_manifest`): one rename fails (`import_error`), the other completes.
Repaired.
same wiki, a move's retag run twice: idempotent. Repaired.
same wiki, one page imported twice, or one predecessor superseded twice: two owned records with correct
identity tags; S3 reports `duplicate records` until the owner `forget`s one. Not repaired; accepted.
two wikis adopting the same unowned record at once (`adopt_legacy`, `adopt_pages` or `adopt_manifest` in
both): the later tag write wins, so a record can end tagged for one wiki while the other supersedes it.
Identity can be permanently wrong, but only after the owner asserts the same record for two wikis, which is
already wrong with a lock. Accepted and documented.

`retain(wiki_identity=...)` writes a new record, which no other writer can touch before it exists. The README
lists these races under Windows; the CHANGELOG says the import runs unlocked there, as 0.6 did. A later
Windows-tested lock can close them.
**Not changed:** the ledger stays under `MEMKERNEL_STATE_DIR`. Two processes that share a store but not a state
directory keep separate ledgers, so each can prove fewer deletions; the import lock still serializes them. The
README says: give processes that share a store the same `MEMKERNEL_STATE_DIR`.
