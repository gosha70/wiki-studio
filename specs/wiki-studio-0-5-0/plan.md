---
spec_mode: full
feature_id: wiki-studio-0-5-0
risk_category: feature
justification: "Adds an optional key to the page schema shared with memkernel, a new lint tier with a CLI and API surface, and an optional patch-set key; a full spec pins the accepted syntax, the matcher and the contracts before an unattended build."
status: draft
date: 2026-10-20
collaboration_mode: single
origin:
  issue: 28
  urls:
    - https://github.com/gosha70/wiki-studio/issues/28
    - https://github.com/gosha70/wiki-studio/blob/pitch/28-plain-technical-english/specs/pitches/28-plain-technical-english/pitch.md
  origin_claim: |
    Issue #28 (opened by the owner from Karpathy's 2 Oct 2026 post; the issue
    takes only its tip to write "80% of the way to" ASD-STE100): the LLM writes
    every wiki page and no check covers the prose; synonym drift breaks the
    missing-cross-links check. Proposal: (A) a "Writing rules" section in
    ingest-rules.md, loaded by the existing prompts (no prompt code change),
    with a preserve list so rewrites keep facts; (B) an optional `avoid:` list on
    glossary entries, a deterministic term-lock check, and `_entity_mentions`
    counting avoid terms; (C) `lint --prose`, advisory, stdlib only, checks 1-5
    (sentence length, semicolons, filler, Summary/Key-ideas length, term lock),
    non-zero only with --strict, --paths scoping; (D) fact-preservation warnings
    in the patch-set preview for removed citations, identifiers and numbers on
    update, never a block. Constraints: no new runtime deps, shared schema
    (`avoid:` optional; record in CHANGELOG), advisory first, no new LLM calls.
    Out of scope: the STE dictionary. The approved pitch (bet, cycle 01) shapes
    it into five scopes and narrows `avoid:` to one memkernel-safe form.
---

# Plan: wiki-studio 0.5.0 — plain technical English for wiki pages (issue #28)

The approved pitch `specs/pitches/28-plain-technical-english/pitch.md` is the
shaping record: its "Findings from the code" cite the file and line behind
every decision below, and its rabbit holes and no-gos bind this build.

## Architecture decisions

- **ADR-1: Writing rules live in `ingest-rules.md`.** All three prompts already
  load it (`prompt.py` `_SCHEMA_NAMES`), so part A needs no prompt code. A
  separate `writing-rules.md` would need prompt code changes, which the issue
  rules out. Wikis with a local `schema/ingest-rules.md` (code-copilot-team)
  get an upgrade note; their sync is a follow-up issue.
- **ADR-2: One accepted `avoid` form.** A single-line comma-separated scalar,
  unquoted or double-quoted, in frontmatter and as the first `Avoid:` line of
  an index entry. It is the only form that survives both `yaml_lite` and
  memkernel's parser and renderer. Flow lists, block lists, single-quoted
  values and terms with `"` or `\` are refused as `avoid-format` findings,
  never silently changed. `yaml_lite` is not extended (its header forbids it).
  Recorded as `docs/adr/0001-glossary-avoid-key.md`, the repository's first ADR.
- **ADR-3: Prose checks get their own module and dataclasses.** `HealthFinding`
  has no line number and `HealthFindingKind` is closed, so `prose_lint.py`
  defines `ProseSegment`, `ProseFinding`, `ProseLintResult`. The avoid reader
  (`load_avoid_map`) lives there too; `health_lint` imports it, and only the
  `avoid-format` kind is added to `HealthFindingKind`.
- **ADR-4: One whole-word matcher for slugs and avoid terms.** Hyphen,
  underscore, letters and digits are word characters on both sides; whitespace
  inside a term matches only within one paragraph. Switching existing slug
  matching to it is a recorded behaviour change: it only removes advisory
  findings (fewer false missing-cross-link warnings).
- **ADR-5: `lint --prose` is a third tier shaped like `--health`.** Advisory,
  fatal only under `--strict` (exit 1, already used), `--paths` filters scanned
  pages. `LintResult.prose` is added last with a default.
- **ADR-6: Fact warnings are an optional `plan.json` key plus stderr.** Written
  by `write_patch_set_dir`, the one function behind ingest, propose and query
  file-back; never under `preview/` (curator-delta reads every file there);
  promote ignores the key. `propose` prints them before `--promote` applies the
  update, because that is the path the memkernel arm's agent uses.

## Phases (one auto-build phase per pitch scope, in pitch order)

| Phase | Pitch scope | What | Main files |
|---|---|---|---|
| US1 | S1 | Writing rules section and references; lint-rules "does NOT check" update; prompt tests | `schema/ingest-rules.md`, `schema/page-types.md`, `schema/WIKI_MAINTAINER.md`, `schema/lint-rules.md`, `tests/test_prompt.py` |
| US2 | S2 | `avoid` reader and format findings, whole-word matcher, `_entity_mentions` aliases and whole-word slugs, ADR, memkernel round-trip test | `prose_lint.py` (reader, matcher), `health_lint.py`, `proposal.py` (`HealthFindingKind`), `docs/adr/0001-glossary-avoid-key.md`, `schema/page-types.md`, tests |
| US3 | S3 | Prose scanner and checks 1–4; constants in `schema/__init__.py` | `prose_lint.py`, `schema/__init__.py`, `schema/lint-rules.md`, tests |
| US4 | S4 | Term lock (check 5), `api.lint(prose=)`, `LintResult.prose`, CLI `--prose`, README | `prose_lint.py`, `api.py`, `cli.py`, `README.md`, tests |
| US5 | S5 | `removed_facts`, `fact_warnings` in `plan.json`, stderr output (ingest, query file-back, propose before promote), patch-set format doc; release 0.5.0 | `fact_diff.py` or `prose_lint.py`, `ingestor_multi.py`, `api.py`, `cli.py`, `docs/patch-set-format.md`, version files, CHANGELOG, README banner, tests |

US1 and US2 are independent; US3 is independent; US4 needs US2 and US3; US5 is
independent of the others and carries the release bump, so it goes last.

## Unattended run

`specs/wiki-studio-0-5-0/automation.json`: profile `pr`, one branch
`feature/wiki-studio-0-5-0` off `main`, five phases with no milestone pause,
DeepSeek gating review (max 3 rounds per phase), `pr.closes: [28]`, caps sized
for five phases. The driver reads this bundle from `main`, so PR #29 (pitch +
this bundle) is merged after this plan is approved and before the run.

## Test strategy

- Every FR maps to at least one unit or CLI test (CLI in-process through
  `wiki_studio.cli.main(argv)`); fixtures are new files under `tests/`, and the
  shared `tests/fixtures/wiki/` stays unchanged (index layouts are tested on
  copies).
- Regression: the single-writer test, the CLI contract tests, `test_schema.py`
  and both evaluation runs' determinism tests stay green.
- Coverage stays at or above the current 92%.

## Risks

- Sentence splitting and skip rules in markdown are approximate; findings are
  advisory and known limits are documented (pitch rabbit holes).
- Fact-diff false positives (reflow, `foo()` vs `foo`, numbers spelled out);
  normalized whole-page sets and advisory output contain them.
- Whole-word slug matching changes advisory health results for wikis that run
  `--health --strict` in CI; recorded under "Changed".
- A first `lint --prose` on a real wiki reports hundreds of findings; that is
  why the tier is advisory.

## Success criteria (issue #28 acceptance)

1. Writing rules section in `ingest-rules.md`, in all three composed prompts (test).
2. `avoid:` parses on glossary pages and `glossary/index.md` entries; other pages ignore it; other forms are findings.
3. Term-lock finding names file, line, found term and canonical term; none inside code or quotes.
4. `_entity_mentions` counts avoid terms (synonym-only page test).
5. `lint --prose` runs checks 1–5; exit 0 by default, 1 with `--strict`; `--paths` scopes it.
6. Fact-preservation warnings in `plan.json` and on stderr for removed citations, identifiers and numbers, including `propose --promote`.
7. `lint-rules.md` "does NOT check" updated; docs, ADR and CHANGELOG updated; coverage at or above the gate; version 0.5.0.
