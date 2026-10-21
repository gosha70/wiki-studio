# Origin alignment check — wiki-studio-0-5-0

Gate: plan approval (Gate 1), after `plan.md` moved `status: draft` → `approved`, 2026-10-21 01:20 UTC (2026-10-20 21:20 −0400). Supersedes `origin-alignment-2026-10-20-2330.md`, which was stale against `plan.md`. Since that record, the only changes to the working artifacts are the plan status line (uncommitted) and 15bd910 (spec FR-006/FR-007 and tasks 8, 9, 12, 13). That commit spells out refinements that the owner-accepted pitch already required (review refinements to questions 5 and 6) and pins the memkernel citation to `4a9597d`. It does not change scope.

Origin: https://github.com/gosha70/wiki-studio/issues/28 (re-read this session via `gh issue view 28`, state OPEN), shaped by the approved pitch https://github.com/gosha70/wiki-studio/blob/pitch/28-plain-technical-english/specs/pitches/28-plain-technical-english/pitch.md (fetched this session; identical to the local `specs/pitches/28-plain-technical-english/pitch.md`, `bet_status: bet`, cycle 01).

Origin claim:
> Issue #28 (opened by the owner from Karpathy's 2 Oct 2026 post; the issue takes only its tip to write "80% of the way to" ASD-STE100): the LLM writes every wiki page and no check covers the prose; synonym drift breaks the missing-cross-links check. Proposal: (A) a "Writing rules" section in ingest-rules.md, loaded by the existing prompts (no prompt code change), with a preserve list so rewrites keep facts; (B) an optional `avoid:` list on glossary entries, a deterministic term-lock check, and `_entity_mentions` counting avoid terms; (C) `lint --prose`, advisory, stdlib only, checks 1-5 (sentence length, semicolons, filler, Summary/Key-ideas length, term lock), non-zero only with --strict, --paths scoping; (D) fact-preservation warnings in the patch-set preview for removed citations, identifiers and numbers on update, never a block. Constraints: no new runtime deps, shared schema (`avoid:` optional; record in CHANGELOG), advisory first, no new LLM calls. Out of scope: the STE dictionary. The approved pitch (bet, cycle 01) shapes it into five scopes and narrows `avoid:` to one memkernel-safe form.

Working claim:
> wiki-studio 0.5.0 (spec.md FR-001..FR-017, US1-US5) adds four parts. (A) A `## Writing rules` section in `ingest-rules.md` with the issue's structure rules and preserve list; the composed ingest-multi, legacy ingest and query prompts carry it with no prompt code change; `page-types.md`, `WIKI_MAINTAINER.md` and the `lint-rules.md` "does NOT check" list are updated. (B) An optional glossary `avoid:` key in one memkernel-safe form: a single-line comma-separated scalar, or the first `Avoid:` line of a `glossary/index.md` entry. Every other form is reported as an `avoid-format` finding. A whole-word matcher, which never crosses a blank line, list item or heading, is used for avoid terms and slugs. `_entity_mentions` counts per-file avoid terms and ignores index `Avoid:` lines. An ADR and an in-repo memkernel round-trip test back the key. (C) An advisory `lint --prose` tier (new `prose_lint.py`) with checks 1-5, exit 1 only under `--strict`, `--paths` scoping and `api.lint(prose=)`. (D) `removed_facts` diffs `update` edits for citations, identifiers and numbers with units. The results go into `plan.json` `edits[].fact_warnings` and are printed by ingest, query file-back and propose (before `--promote`), and they never block. Standard library only, no new LLM calls, no new exit codes, the promote gate unchanged; released as 0.5.0.

Acceptance criteria of #28, mapped:
  - Writing rules in `ingest-rules.md`, in the composed prompts (test) — FR-001, FR-002, US1.
  - `avoid:` parses on glossary pages and `glossary/index.md` entries; other pages ignore it — FR-004, FR-005, US2.
  - Term-lock finding names file, line, found and canonical term; none in code or quotes — FR-013, US4.
  - `_entity_mentions` counts avoid terms (synonym-only page test) — FR-007, US2.
  - `lint --prose` runs checks 1–5; exit 0 by default, non-zero with `--strict`; `--paths` scopes it — FR-010..FR-013, US3, US4.
  - Fact-preservation warnings for removed citations, identifiers and numbers — FR-014..FR-016, US5.
  - `lint-rules.md` "does NOT check" list updated — FR-003.
  - Docs and CHANGELOG updated; coverage at or above the gate — FR-008, FR-017, Constraints (Gate).

Mismatches (each a deliberate narrowing or addition recorded in the owner-approved pitch; none drops an issue requirement):
  - The issue's example `avoid: [alignment check, origin check]` (flow form) is not accepted. The one accepted form is a single-line comma-separated scalar: the flow form does not parse as a list in `yaml_lite`, and memkernel's parser loses a block list. The flow form is reported as an `avoid-format` finding, not ignored (pitch question 5, owner-accepted).
  - The issue says fact warnings appear "in the patch-set preview". They are recorded in `plan.json` (`edits[].fact_warnings`) and printed to stderr, not written as files under `preview/`, because promote's curator-delta reads every file under `preview/` (pitch question 3).
  - Beyond the issue: the decision record `docs/adr/0001-glossary-avoid-key.md` (the repository's CLAUDE.md requires one for a frontmatter-key change), and the switch of existing slug matching from substring to whole-word (pitch question 6, owner-accepted), recorded under CHANGELOG "Changed".
  - The circuit breaker can cut checks 3-4 and the units extractor under time pressure. It can also hold back part A if D's core slips. This is a contingency the owner accepted (pitch question 4), not a planned reduction; the full scope is planned.
  - The issue's follow-ups (eval-set measurement; code-copilot-team and memkernel adopting the rules) stay out of scope, as the issue says.

Verdict: aligned
Confidence: high
