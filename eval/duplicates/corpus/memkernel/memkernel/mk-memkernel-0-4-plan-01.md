---
page_type: decision
slug: mk-memkernel-0-4-plan-01
title: 'Revalidate by content hash, not by git'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-4/plan.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Context

issue #9 and the roadmap speak of git-diff-driven invalidation; `code` memories already store `content_hash` of the retained file text.

## Decision

compare the current file's hash with `content_hash`; no git dependency, works in any checkout or none.

## Consequences

a reformat counts as a change (acceptable: the snapshot is stale either way); 0.4 hashes whole files, per-chunk range invalidation is a named follow-up. `project_root` is a security boundary: sources are resolved with symlinks followed and `..` normalised and must lie under the resolved root; anything else is `unknown` and never read.
