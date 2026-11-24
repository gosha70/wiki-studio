---
page_type: decision
slug: cct-wiki-audit-trail-spec-01
title: '1 — Audit path layout'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-audit-trail/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Keep the leading-dot `.audit/` exactly as issue #31 suggests: it signals
"tooling, not content," consistent with how `schema/` and `scripts/` are
already treated by the linter. The cost is a hard prerequisite — the
structural linter and lint schema MUST exempt `knowledge/wiki/.audit/`
before anything writes there, or every `wiki promote`'s
`_validate_staged_tree` fails (the linter's `find` currently has no
dotdir exclusion). The accepted-proposal archive is a **directory**
`knowledge/wiki/.audit/proposals/<date>-<slug>/`, not the single `.md`
the issue floats: a `WikiPatchSet` is inherently multi-file
(`plan.json` + N preview pages); collapsing to one `.md` is lossy.
Stored: `plan.json` verbatim (machine truth) and `proposal.md` (the
auditor-readable render) — both, because they serve different readers at
negligible cost (text only). The `<date>-<slug>` is reused verbatim from
`proposals_dir.name` (today's deterministic ingest naming — no new slug
rule); same-name collisions get a deterministic `-2`/`-3` suffix. The
narrowed invariant (per user decision): `wiki promote` remains the only
writer to the canonical content tree; `wiki ingest`'s single exception
is append-only to `ingest-log.md`. This is enforced by a test, not just
convention (see Requirement 7).
