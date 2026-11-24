---
page_type: decision
slug: cct-wiki-audit-trail-spec-05
title: '5 — Atomicity boundary'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-audit-trail/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The accepted-proposal archive is staged into the *same*
temporary tree `_commit_stage_to_wiki` atomically applies. Because
`.audit/` is under `knowledge/wiki/`, this makes the archive atomic with
the wiki content write for free — same plan-then-apply-with-rollback,
same all-or-nothing guarantee — without inventing a second commit. A new
`_stage_audit_archive` step runs between the `_apply_edit` loop and
`_validate_staged_tree`; `_commit_stage_to_wiki`'s planned-write set is
extended to carry `.audit/**/plan.json` and `.audit/ingest-log.md` (it
currently `rglob`s `*.md` only). On validation failure the whole promote
aborts in the temp dir — wiki and `.audit/` both untouched, no archive
for a non-accepted proposal (correct). The **ingest-log** append is
deliberately *not* in the promote atomic unit: it is a standalone
fail-closed write by `wiki ingest`, because it must record rejects (and
dry-runs) that never reach promote. This asymmetry is intentional:
ingest-log answers "what did we evaluate?"; the archive answers "what
landed?".
