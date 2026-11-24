---
page_type: decision
slug: mk-memkernel-0-7-wiki-scope-spec-05
title: 'Legacy memories are adopted only on the owner''s word'
status: stable
last_reviewed: 2026-11-23
sources:
  - path: specs/memkernel-0-7-wiki-scope/spec.md
    sha: 8279d7631851584a939a03d6243df57a4cc25c31
---

## Decision

No evidence in a 0.6 store proves which wiki a legacy memory came from: not a matching `page_sha:` (two wikis
may hold identical pages) and not the absence of other wikis (they may not be imported yet). So memkernel never
adopts on its own.
**By default**, a page with no owned candidate (S3) and any legacy live candidate gets **nothing written**: no import, no
supersession, no withdrawal. It is reported under a new `ambiguous` key (`{"path", "ref_ids", "reason"}`)
with the remedy: import again with `adopt_legacy=True` (or name the page in `adopt_pages`) if these are this
wiki's memories, or `forget` the ones that are not.
**`adopt_legacy=True`** (`wiki_import(adopt_legacy=true)`, `WikiImporter.import_pages(..., adopt_legacy=True)`;
the owner's decision of 2026-11-03, the upgrade path): the owner's wiki-wide assertion that this wiki's legacy
records are its own. It applies only where a page has no owned candidate and **exactly one** legacy candidate:
that record is adopted (S5) and a new revision supersedes it, as today. A page with two or more legacy
candidates stays `ambiguous` (`several legacy candidates`), nothing written. The risk is the owner's: if
another wiki's sole legacy record sits at one of this wiki's page keys or paths, it is adopted, so the README
tells a project with several wikis to use `adopt_pages` instead. Per call, never a setting.
**`adopt_pages`** (selective cases; `wiki_import(adopt_pages=[...])`, `WikiImporter.import_pages(..., adopt_pages=...)`): a
list of `{"path", "ref_id"}` entries, copied from the `ambiguous` report. Each entry is the owner's assertion
that **this record** is this page's. It is adopted only if, at import time, the page still has no owned
candidate and its **sole** legacy candidate is exactly that `ref_id`; it then gains this wiki's tags (S5), and a
new revision supersedes it, as today. If the candidate was removed or replaced, or another appeared, nothing is
written and the page is reported with `candidate changed`, so a record the owner never saw is never adopted.
Two or more legacy candidates stay `ambiguous`. Pages not named are untouched, so the owner confirms each
record. With `adopt_legacy=True` in the same call, a page named in `adopt_pages` follows `adopt_pages`'s rule.
**A named record now another wiki's** (confirmed by the owner, 2026-11-03, from the build of #89): when an
`adopt_pages` entry names a record that is still at the page but now carries another wiki's identity (another
wiki adopted it first, SC-8), the page is reported `candidate changed` and nothing is written for it. A named
record that is gone is `not ambiguous`.
**The `reason` values,** one per cause, so a caller can tell "adopt me" from a defect. A page carries exactly
one: S3's order checks owned candidates first and consults legacy ones only when there is no owned candidate,
so `duplicate records` and the legacy reasons never apply to one page together.
`legacy owner unproven`: one legacy candidate, no `adopt_legacy` and page not named in `adopt_pages` (remedy:
`adopt_legacy=True`, name it, or `forget`);
`several legacy candidates`: two or more, named or not (remedy: `forget` the ones that aren't this page's);
`duplicate records`: two or more of this wiki's records match the page (S3) or dedup it (S2). `ref_ids`
lists the records found; in both cases they are this page's records (dedup is scoped by the page's
source), so the remedy is the same: `forget` all but one;
`candidate changed`: an `adopt_pages` entry whose `ref_id` is no longer the page's sole legacy candidate
(remedy: review the new report entry and name its record);
`not ambiguous`: an `adopt_pages` entry for a page with an owned candidate, or no legacy candidate (nothing
to do).
`adopt_legacy` and `adopt_pages` are per call, not settings, so they are never on by accident.
**Rejected:** adopting on a matching `page_sha:` or on "no other wiki known" (the first draft): neither proves
ownership, so either could make one wiki supersede another's record, which US1 forbids.
