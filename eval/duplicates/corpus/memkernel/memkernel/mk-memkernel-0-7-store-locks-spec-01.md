---
page_type: decision
slug: mk-memkernel-0-7-store-locks-spec-01
title: 'Lock identity is the store''s own, never a setting'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-store-locks/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

**Persistent client,** configured or injected: the client's own `get_settings().persist_directory`, resolved to
a real absolute path, plus its `tenant`, `database` and the collection name. Lock files sit in that directory,
beside `.memkernel-open.lock`, named `.memkernel-<name>-<key>.lock`, where `<key>` is a short sha256 of tenant,
database and collection.
**An injected persistent client** whose directory differs from a `chroma_persist_path` that was explicitly
set (by `MEMKERNEL_CHROMA_PERSIST_PATH` or as a setting), and is non-empty, is refused with `ValueError` when
the adapter is built, so settings and store can't disagree. With the default or an empty `chroma_persist_path`,
an injected persistent client is allowed, and its locks key off its own directory (the owner's decision,
2026-11-03, so `build_service(chroma_client=...)` with default settings keeps working).
`realpath` resolves symlinks, not case: on a case-insensitive file system, two spellings of one directory
give two keys. memkernel opens the store from one configured path, so this needs two processes configured
with differently cased paths; the README says to use one spelling.
**In-memory client:** separately constructed `EphemeralClient`s in one process share one data set, so the lock
is process-wide, keyed by tenant, database and collection, never by the client object. A test pins that two
separately constructed `EphemeralClient`s see each other's records, so a chromadb change that breaks it fails
CI.
`MEMKERNEL_STATE_DIR` plays no part.
