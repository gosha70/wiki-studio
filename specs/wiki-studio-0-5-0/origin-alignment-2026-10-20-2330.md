# Origin alignment check — wiki-studio-0-5-0

Gate: spec, plan and tasks drafted (Gate 1, before plan approval), 2026-10-20 23:30 local.

Origin: https://github.com/gosha70/wiki-studio/issues/28 (opened by the owner from Karpathy's 2 Oct 2026 post, taking only its "80% of the way to ASD-STE100" tip), shaped into the approved pitch `specs/pitches/28-plain-technical-english/pitch.md` (bet, cycle 01; owner approved 2026-10-20 with recommendations 4-7 accepted).

Working claim:
> wiki-studio 0.5.0 adds (A) a "Writing rules" section with a preserve list to `ingest-rules.md`, carried by the existing ingest and query prompts with no prompt code change; (B) an optional glossary `avoid:` key in one memkernel-safe form, every other form reported as an `avoid-format` finding, a whole-word matcher used for avoid terms and slugs, and `_entity_mentions` counting avoid terms; (C) an advisory `lint --prose` tier with checks 1–5 (sentence length, semicolons, filler, Summary/Key-ideas length, term lock), exit 1 only under `--strict`, `--paths` scoping, `api.lint(prose=)`; (D) `fact_warnings` for citations, identifiers and numbers removed by an `update`, recorded in `plan.json` and printed by ingest, query file-back and propose (before `--promote`), never blocking. Standard library only, no new LLM calls, no new exit codes, the promote gate unchanged; released as 0.5.0 in one unattended run and one PR that closes #28.

Acceptance criteria of #28, mapped:
  - Writing rules in `ingest-rules.md`, in the composed prompts (test) — FR-001, FR-002, US1.
  - `avoid:` parses on glossary pages and `glossary/index.md` entries; other pages ignore it — FR-004, FR-005, US2.
  - Term-lock finding names file, line, found and canonical term; none in code or quotes — FR-013, US4.
  - `_entity_mentions` counts avoid terms (synonym-only page test) — FR-007, US2.
  - `lint --prose` runs checks 1–5; exit 0 by default, non-zero with `--strict`; `--paths` scopes it — FR-010..FR-013, US3, US4.
  - Fact-preservation warnings for removed citations, identifiers and numbers — FR-014..FR-016, US5.
  - `lint-rules.md` "does NOT check" list updated — FR-003, US1/US3.
  - Docs and CHANGELOG updated; coverage at or above the gate — FR-008, FR-017, Final Verification.

Mismatches (each a deliberate narrowing or addition recorded in the owner-approved pitch, none dropping an issue requirement):
  - The issue's example `avoid: [alignment check, origin check]` (flow form) is not accepted; the one accepted form is a single-line comma-separated scalar, because the flow form does not parse as a list in `yaml_lite` and a block list is lost by memkernel's parser. The flow form is reported as an `avoid-format` finding, not ignored.
  - The issue says fact warnings appear "in the patch-set preview"; they are recorded in `plan.json` (`edits[].fact_warnings`) and printed to stderr, not as files under `preview/`, because promote's curator-delta reads every file under `preview/`.
  - Beyond the issue: a decision record `docs/adr/0001-glossary-avoid-key.md` (required by the repository's CLAUDE.md for a frontmatter-key change), and existing slug matching switched from substring to whole-word (owner-accepted question 6), recorded under CHANGELOG "Changed".
  - The issue's follow-ups (eval-set measurement; code-copilot-team and memkernel adopting the rules) stay out of scope, as the issue says.

Verdict: aligned
Confidence: high
