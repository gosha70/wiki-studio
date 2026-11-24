---
page_type: decision
slug: cct-wiki-audit-trail-spec-02
title: '2 — Curator-edit delta capture'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-audit-trail/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

There is no "accept-then-edit" command;
edits happen as in-place hand-edits of
`doc_internal/proposals/<dir>/preview/` between ingest and promote. So
"the LLM proposal" = the proposal directory as written by `wiki ingest`;
"post-edit" = the same directory at `wiki promote` time. To capture the
delta without bloating the tracked tree, `wiki ingest` writes an
immutable `.ingest-snapshot/` (a copy of `plan.json` + `preview/`)
*inside the gitignored proposal directory*. At promote, the archiver
diffs live content vs `.ingest-snapshot/`; if they differ it writes
`curator-delta.md` (a `diff -U3` unified diff) into the tracked archive;
if they are identical it writes nothing. Storage is paid only when an
edit actually happened, and the full original snapshot stays local
(gitignored) — only the small diff is committed. This honors the issue's
"cheap commit footprint" appetite.
