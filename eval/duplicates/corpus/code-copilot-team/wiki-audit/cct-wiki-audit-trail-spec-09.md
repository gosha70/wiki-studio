---
page_type: decision
slug: cct-wiki-audit-trail-spec-09
title: '9 — Patch-set-oriented record'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-audit-trail/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The default
`wiki ingest` path is multi-page: the gate returns a `WikiPatchSet`
(`edits`, `source_path`, `backend`, `rationale`) with **no scalar
`disposition`, no single `target_slug`, no single `page_type`** — one
ingest can touch many pages of several types, and a reject is simply an
empty `edits` list. A single-page-shaped record (the issue's literal
"target slug + page type") cannot represent a normal accepted multi-page
ingest unambiguously. Decision: the record is patch-set-oriented —
`disposition` is *derived* (`"accept"` iff `edits` non-empty, else
`"reject"`; the legacy single-source path uses
`IngestProposal.disposition` directly); `reason` is `patch.rationale`
(or `IngestProposal.reason`); the singular `target_slug`/`page_type`
fields are replaced by `proposal_dir` (basename, linking the line to the
archive `promote` will write), `target_paths` (sorted unique wiki-rel
paths over all edits), and `page_types` (sorted unique types). This
honors the issue's intent (which pages/types this decision concerned is
recorded) while fitting the actual multi-page contract, without
modifying the `WikiPatchSet` dataclass (that belongs to
`specs/wiki-ingest-pipeline/`; changing its shape here would be
cross-spec scope creep).
