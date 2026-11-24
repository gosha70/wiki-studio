---
page_type: decision
slug: mk-memkernel-0-7-wiki-scope-spec-07
title: 'When a wiki''s identity changes'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-wiki-scope/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

**A manifest is added.** The wiki now has an id, and its earlier memories are path-only, so none belongs to
it (S1). If live path-only memories carry this wiki's path, or the path-hash ledger file exists, the import
stops with `import_error` before any write, unless the call passes `adopt_manifest=True`: the owner's assertion
that this directory is the same wiki it was before the manifest. This is a wiki-wide assertion, because the
ledger is wiki-wide; `adopt_pages` doesn't imply it. With `adopt_manifest=True`:
the ledger is migrated first (below); if migration fails, the import stops with `import_error` and nothing
is written;
every live path-only memory at this path gains this wiki's `wiki-id:` (S5).
**A conflicting identity at this path.** A live memory carries this wiki's `wiki-path:` and a `wiki-id:` that
isn't this wiki's id (or any `wiki-id:`, when this wiki has no manifest). That memory's wiki was last imported
from this path, so either its manifest was removed or replaced, or another directory now stands there. These
can't be told apart, so the import stops with `import_error` naming the ids, before any write. The report
gives a remedy for each cause:
**the manifest was removed:** restore it;
**the manifest was replaced** (a re-`init`): restore the earlier one;
**the wiki moved and another directory now stands here,** or a move's retag stopped halfway: import the
moved wiki from its new location first, which retags its memories away from this path;
**the earlier wiki is gone for good:** `forget` its memories.

This check covers only memories carrying a `wiki-id:`. A wiki reusing a moved wiki's old path is kept off the
moved wiki's memories by membership (S1), which needs their `wiki-id:` to match; once the move's retag is done,
no memory carries the old path and the check has nothing to fire on.
**A wiki with a manifest moves.** Its memories still belong to it by `wiki-id:`. Before any page write, the
import sets **every** live memory carrying its `wiki-id:` to the new `wiki-path:`, replacing the old one (S5),
so the old path is free for another wiki. The retag is one pass over the store's live memories (`list_all`
has no paging), per record and idempotent, not atomic; it touches only tags, never the ledger. Only an import
of **this** wiki (the same `wiki_id`) sets its memories' path; another wiki's import never retags them, it
stops at the conflict check instead. Memories carrying this wiki's own `wiki-id:` are never a conflict for it,
at any path: its import runs the retag first, before the conflict check and any page write. So a retag that
stops halfway is finished by this wiki's next import,
from whichever directory it is imported: the condition (a memory of this id at another path) persists. Importing from the old directory after a move needs that
directory to still hold the same manifest, which is the copied-wiki case below, not a recovery path.
**A wiki without a manifest moves.** It is a new wiki at the new path, as the ledger already treats it. Its
old memories are path-only at the old path, so a manifestless wiki later placed there continues them (S1); no
check can tell the two apart. This is the one
case US1 excludes; a manifest avoids it.
**The governed ledger** (the ungoverned import has none). Its key is the `wiki_id` when the wiki has a
manifest, else the path hash. A migration happens only on manifest added with `adopt_manifest=True`, before any
memory write, holding both files' locks while it moves the ledger. The locks are always taken in the same order
(the path-hash file's, then the `wiki_id` file's), so two imports never deadlock. The whole run is serialized by
the store's `wiki-import` lock (S8), so the two ledger locks are not held beyond the migration (confirmed by the
owner, 2026-11-03, from the build of #89). The states:
only the path-hash file exists: it is renamed to the `wiki_id` file;
both files exist (for example add, remove, re-add): the import stops with `import_error` naming both files,
nothing written. The owner deletes the stale one; memkernel doesn't guess which ledger is authoritative;
the rename fails: `import_error`, nothing written, both files as they were;
only the `wiki_id` file exists while path-only memories remain at this path (a crash after the rename,
before the retag finished): the migration is complete. The import still requires `adopt_manifest=True`,
because path-only memories remain; with it, it continues the retag (step 2 above), which is idempotent.

This is fatal, unlike the existing non-fatal `ledger_error` for a corrupt file (#78), because an import
under the wrong ledger could withdraw the wrong memories.
**Not handled:** a copied wiki directory (two directories, one `wiki_id`) is one wiki; each import retags its
memories to the directory imported last. Stated in the README.
