---
page_type: decision
slug: mk-memkernel-0-7-spec-02
title: 'Where the sync state lives'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

Every page needs a state (pending, applied or failed) with a retry path,
including a page whose first import failed, which has no memory to carry a tag. Two options:
**Tags on the page's memory** (`sync:failed`, …). These need no new storage, but they can't represent a page
with no memory. Tags also merge on dedup, keep no attempt count or last error, and a withdrawn memory would
carry state the store treats as history. Rejected.
**A ledger in memkernel's state directory (confirmed).** One JSON file per project **and** wiki:
**Location:** outside Chroma's directory, in a memkernel state directory: a new setting
`MEMKERNEL_STATE_DIR`, default `.memkernel/state`, resolved exactly like `MEMKERNEL_CHROMA_PERSIST_PATH`: a
relative path against the working directory of the process (the MCP server, a hook, a library caller), so
the README's advice to set an absolute persist path applies to it too. It gets a row in the README configuration table, and the README tells users to keep it out of
git (`.memkernel/state/`, like `.memkernel/wiki-proposals/`).
**File:** `<state dir>/wiki-sync/<project_id>/<wiki key>.json`. One project may import several wikis, and two
projects may share a store.
**Wiki key:** the wiki manifest's `wiki_id` when there is one. It is stable, because it travels with the wiki
through moves and renames of its directory. Otherwise the key is the sha256 of the wiki directory's path
**relative to the project root** (POSIX form, normalised), so a project moved or cloned elsewhere keeps its
ledger. Moving the wiki inside the project without a manifest gives it a new key, and a new, empty ledger.
One entry per page key: `path`, `state` (`pending` / `applied` / `failed`), `action` (`import`, `withdraw`,
`supersede`), the revision sha256, the memory `ref_id`, `attempts`, `last_error` and `updated_at`.
**Writing:** written whole to a temporary file and moved into place with `os.replace`.
**Lock:** a POSIX `fcntl` lock on the ledger's own lock file is held **for the whole import run**, so two
imports of one wiki never interleave; the second waits. Without `fcntl`, no lock, as in #69.
With an in-memory store (empty `chroma_persist_path`) the ledger is in memory too, for the process's life.
It is memkernel's bookkeeping, not the wiki's, so it never goes into the wiki or wiki-studio's audit trail.
