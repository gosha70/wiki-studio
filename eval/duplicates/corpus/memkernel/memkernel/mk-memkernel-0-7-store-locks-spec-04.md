---
page_type: decision
slug: mk-memkernel-0-7-store-locks-spec-04
title: 'Platforms'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-store-locks/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

The locks use `fcntl.flock` and are verified on POSIX only. Where `fcntl` is unavailable
(Windows and any other non-POSIX platform), like #69's store-open lock:
`exclusive` and `merge_tags` run unlocked, and the first such call per process and lock name logs one warning;
the re-entry check (L2) still applies;
the README describes the locks and that they are POSIX-only, and what runs unlocked elsewhere. No caller needs
to refuse without a lock (the owner's decision, 2026-11-03), so there is no `required` flag and no error for
a missing lock; a later caller that needs one can add it.

The existing store-open and ledger locks keep their behavior; this spec doesn't change them.
