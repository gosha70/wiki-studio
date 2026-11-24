---
page_type: decision
slug: mk-memkernel-0-7-spec-04
title: 'Supersession'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

For a page in state `superseded`, the importer reads `superseded_by` from the
page's frontmatter. **What it names:** a wiki-relative page path, as wiki-studio's schema and lint define it. Lint
requires the target to exist, not to be the page itself, and not to be superseded in turn. The importer resolves
the path to that page's key through the same complete listing.
if the successor page has a live memory from this store (by key or path), the old memory is **superseded** by
it, through the existing `supersede`;
otherwise the old memory is **withdrawn** with reason `superseded`, and the ledger keeps it `pending` until the
successor's memory exists. Once it does, the importer adds the `superseded_by` link. The withdrawn marker stays
as history; `superseded_by` is set because it was empty, and nothing is overwritten.
**An unknown successor** (a path the listing does not contain, not yet approved, or not imported) **stays
`pending` and is reported** under `pending`, with the successor path and why. It is retried at every import
and is never resolved by guessing.
