---
page_type: decision
slug: mk-memkernel-0-7-store-locks-spec-02
title: 'A named exclusive lock on the store'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-store-locks/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

A new port method, `VectorStorePort.exclusive(name)`,
is a context manager holding the store's lock `name` (L1) until it exits. `name` is one of the module's
constants (`wiki-import`, `tags`); any other value raises `ValueError`. It blocks until acquired, with no timeout,
deliberately: `flock` is released when the holder exits or dies, and a hung holder is a defect to fix, not one to
time out around. #80's wiki
import holds `exclusive("wiki-import")` for its whole run: it takes the lock where one exists, and never
refuses without one (L4).
**Not re-entrant.** A thread holds each store lock at most once. Taking a lock name the same thread already
holds, for the same store, raises a new `LockReentryError` (a `RuntimeError` subclass in `core/models.py`)
before acquiring anything, so a nested take fails loudly instead of deadlocking (a second `flock` on a new file
handle blocks against the first, even in one process). A per-thread registry of held (store key, name) pairs
tracks this; another thread of the same process waits for the lock instead (the owner's decision,
2026-11-03). It applies with and without `fcntl`. `merge_tags` takes
`tags` itself, so a caller holding `exclusive("tags")` can't call it: the error says so.
**Long waits are logged.** A take that waits longer than `LOCK_WAIT_LOG_SECONDS` (a named constant, 10 seconds)
logs one info line naming the lock and the store, then keeps waiting.
