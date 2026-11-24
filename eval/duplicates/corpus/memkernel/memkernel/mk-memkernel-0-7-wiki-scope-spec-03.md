---
page_type: decision
slug: mk-memkernel-0-7-wiki-scope-spec-03
title: 'Dedup uses membership'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-wiki-scope/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

`retain` gains a keyword-only `dedup_owner: Callable[[Memory], bool] | None = None`. With `dedup_source=True`
and `dedup_owner`, a dedup hit is a live record with the same content hash, type and source **for which
`dedup_owner` is true**. The hit is selected among all such records, not just the first the store returns.
`dedup_owner` is a pure predicate over a record's tags, called once per matching record; it never raises (S1's
membership reads only `wiki-path:` and `wiki-id:`).
**Two or more hits** (for example two live records of this wiki with the same content, type and source, left
by an earlier defect): none is chosen and nothing is written. `retain` raises a new typed
`AmbiguousDedupError(ref_ids)` (a `ValueError` subclass in `core`); the import catches it and reports the page
under `ambiguous` with all the `ref_id`s. This is the backstop: the import's own check (S3) finds duplicates
before `retain` and before the early return for a current revision.
The import passes S1's membership predicate, never a single tag. So identical pages at the same path in two
wikis are two records; a moved wiki's frontmatter-only revision dedups into its own record by `wiki-id:`; and
a wiki later created at the old path never dedups into the moved wiki's record.
A legacy record is never a dedup hit. It joins a wiki only through S4's adoption.
**A retain without `dedup_owner` never dedups onto a wiki memory** (the owner's decision, 2026-11-03, on every
platform). A record carrying `wiki-path:` or `wiki-id:` is never a dedup hit for an ordinary `retain` (an
agent's, the MCP tool's, `promote`'s): when its content matches one, it gets its own record, and the wiki
memory's tags are never touched. Among several matches, the hit is the first record without identity tags.
So `retain` never raises for this, and only the import ever writes tags onto an identity-tagged record.
