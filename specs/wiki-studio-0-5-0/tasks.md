# Tasks: wiki-studio 0.5.0 — plain technical English for wiki pages (#28)

<!-- One `## US<n>:` group = one auto-build phase, in pitch order (S1..S5 -> US1..US5). [US#]/FR tags trace to spec.md. -->
<!-- Read first: CLAUDE.md, spec.md, plan.md, and specs/pitches/28-plain-technical-english/pitch.md ("Findings from the code" has the file:line for every decision). -->
<!-- Run per phase: poetry run ruff check src/ tests/ eval/ && poetry run ruff format --check src/ tests/ eval/ && poetry run mypy src/ && poetry run pytest -q -p no:cacheprovider --cov=wiki_studio --cov-fail-under=80 -->
<!-- Every new source file starts with the two-line EGOGE / Apache-2.0 header. Standard library only. Do not edit tests/fixtures/wiki/ (copy it into the test instead). -->

## US1: Writing rules in the schema (pitch S1, part A)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 1 | | Add a `## Writing rules` section with the FR-001 rules and preserve list (one fact per sentence; 25 words, 20 in numbered steps; one instruction per step; active voice; no semicolons; the glossary term; first Summary sentence states the main claim; preserve identifiers, paths, numbers, `path:` citations, "if", "unless", "not verified"; split, do not delete) | `src/wiki_studio/schema/ingest-rules.md` | build | [ ] |
| 2 | [P] | Reference the section from the glossary and concept blocks of `page-types.md` (plain sentence, no `` - `## …` `` bullets: `tests/test_schema.py` parses those as required sections) and from the "Keep prose tight" step of `WIKI_MAINTAINER.md` (FR-002) | `src/wiki_studio/schema/page-types.md`, `src/wiki_studio/schema/WIKI_MAINTAINER.md` | build | [ ] |
| 3 | [P] | Update "What the linter does NOT check": prose structure is checked by `lint --prose` (advisory); clarity/helpfulness stays unchecked (FR-003; limits and known scanner limits are added in US3) | `src/wiki_studio/schema/lint-rules.md` | build | [ ] |
| 4 | | Tests: the composed ingest-multi, legacy ingest and query prompts each contain `## Writing rules`; `test_schema.py` still green (FR-002) | `tests/test_prompt.py` | build | [ ] |
| 5 | | CHANGELOG `[Unreleased]`: Added (writing rules) and the upgrade note for wikis with a local `schema/ingest-rules.md` | `CHANGELOG.md` | build | [ ] |

**Checkpoint US1** — verify before continuing:
- [ ] `grep -n "## Writing rules" src/wiki_studio/schema/ingest-rules.md` matches
- [ ] Prompt tests green for all three prompts; `tests/test_schema.py` green
- [ ] Full gate green

---

## US2: Glossary `avoid` terms, format findings, whole-word matching (pitch S2, part B data)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 6 | | Create `prose_lint.py` with `AvoidEntry(canonical, page, anchor, terms)`, `FormatProblem(path, line, message)` and `load_avoid_map(wiki_dir) -> tuple[dict[str, AvoidEntry], list[FormatProblem]]`: read `avoid:` from per-file `page_type: glossary` frontmatter via `yaml_lite`, and the first non-blank `Avoid:` line after each `### <term>` in `glossary/index.md` (both layouts: fixture `## Definition` sections and code-copilot-team `*Where it appears:*` lines); split on commas, strip, one optional pair of outer double quotes (FR-004) | `src/wiki_studio/prose_lint.py` | build | [ ] |
| 7 | | Report every refused form as a `FormatProblem` and contribute no terms: block list / empty value, leading `[`, single-quoted value, `"` or `\` in a term (raw or escaped), empty term, misplaced or bulleted index `Avoid:` line, one term under two canonicals; ignore `avoid:` on non-glossary pages (FR-005) | `src/wiki_studio/prose_lint.py` | build | [ ] |
| 8 | | Whole-word matcher `find_term(text, term)` / `contains_term`: case-insensitive; `[A-Za-z0-9_-]` are word chars on both sides; a space inside a term matches whitespace with at most one line break (never a blank line), so the rule holds on a whole page body as well as on one paragraph (FR-006) | `src/wiki_studio/prose_lint.py` | build | [ ] |
| 9 | | `_entity_mentions(text, candidates, aliases=None)`: slug matching switches to the whole-word matcher; alias hits (canonical slug → terms from per-file glossary pages) count as the canonical slug; `_check_missing_cross_links` passes the aliases and strips index-entry `Avoid:` lines from `glossary/index.md` before counting; add `"avoid-format"` to `HealthFindingKind` and report `load_avoid_map` problems in the `--health` tier (FR-005, FR-007) | `src/wiki_studio/health_lint.py`, `src/wiki_studio/proposal.py` | build | [ ] |
| 10 | [P] | Decision record (FR-008): the optional key, its one form and why it deviates from the issue's flow example; memkernel round trip as observed (export never rewrites a glossary page; import drops `avoid:`; parse/render keeps a single-line scalar only within the accepted syntax; Memory model unknown); the requirement that memkernel keep unknown top-level scalar keys; the follow-up for memkernel | `docs/adr/0001-glossary-avoid-key.md` | build | [ ] |
| 11 | [P] | "Optional keys" paragraph in the glossary block of `page-types.md` (no `` - `## …` `` bullets); CHANGELOG schema entry and "Changed: whole-word slug matching" | `src/wiki_studio/schema/page-types.md`, `CHANGELOG.md` | build | [ ] |
| 12 | | Tests: both forms parse (frontmatter; index entry on a copy of `tests/fixtures/wiki/glossary/index.md` with an `Avoid:` line, and on a code-copilot-team-layout sample); each refused form yields exactly one problem; non-glossary `avoid:` ignored; matcher cases of FR-006 (no match: `pre-origin-gate`, `lint-rules`, `linter`, `origin checklist`, `origin check-in`, bullet-boundary split; match: `lint.`, `(origin-gate)`, wrapped term in one paragraph; no match across a blank line in a raw body); a synonym-only page triggers the missing-cross-link finding; `Avoid: lint check` in a `glossary/index.md` entry is not a mention of the `lint` page; existing health tests updated only where whole-word slugs change a substring-only result, each changed assertion named in the phase commit message with the substring match it relied on (FR-004..FR-007) | `tests/test_avoid_terms.py`, `tests/test_health_lint*.py` as needed | build | [ ] |
| 13 | | Round-trip test (FR-009): copy memkernel's `_unquote` and `_quote` as test fixtures citing `gosha70/memkernel src/memkernel/wiki/pages.py` at main `4a9597d` (`_unquote` lines 45-49, `_quote` lines 113-117; verified 2026-10-20); accepted values `alignment check, origin check`, `it's, ok`, `"x: y, z"`, `"it's, ok"`, `build #2, origin check`, `"build #2"` read back as the same terms after read → parse → render → read; unsupported `the "old" gate`, `C:\cache`, `"the \"old\" gate"`, `"C:\\cache"`, `'it''s, ok'`, `'plain, term'` yield a problem on the first read and no terms, with no assertion after memkernel | `tests/test_avoid_roundtrip.py` | build | [ ] |

**Checkpoint US2** — verify before continuing:
- [ ] `load_avoid_map` on the fixture copy returns the index entry's terms and no problems
- [ ] Synonym-only page test and all FR-006 matcher cases green
- [ ] `docs/adr/0001-glossary-avoid-key.md` exists; `tests/test_schema.py` green
- [ ] Full gate green

---

## US3: Prose scanner and `lint --prose` checks 1–4 (pitch S3, part C)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 14 | | Named constants: `PROSE_MAX_WORDS = 25`, `PROSE_MAX_WORDS_NUMBERED = 20`, `SUMMARY_MAX_SENTENCES = 4`, `KEY_IDEA_MAX_SENTENCES = 2`, `FILLER_PHRASES` (at least "it is important to note", "in order to", "ensure that"), `PROSE_ABBREVIATIONS` ("e.g.", "i.e.", "etc.", "vs.") (FR-011) | `src/wiki_studio/schema/__init__.py` | build | [ ] |
| 15 | | Scanner `scan_page(path, text) -> list[ProseSegment]` per FR-010: skip frontmatter, ```` ``` ````/`~~~` fences, `|` rows, `>` lines, HTML comments, index-entry `Avoid:` lines, indented code after a blank line outside a list; join wrapped lines; one segment per list item (`bullet`/`numbered`); `heading` segments; mask inline code, `[text](target)` → `text`, bare URL one token; track the starting line | `src/wiki_studio/prose_lint.py` | build | [ ] |
| 16 | | Sentence splitter with the abbreviation guard; a finding's line is its sentence's first line (FR-010) | `src/wiki_studio/prose_lint.py` | build | [ ] |
| 17 | | `ProseFinding(path, line, check, message)`, `ProseLintResult(findings, pages_checked)`, and `run_prose_lint(wiki_dir, *, paths=None)` running checks 1–4 over pages from the health lint's page list, `log.md` exempt, headings exempt from 1–4 (FR-011) | `src/wiki_studio/prose_lint.py` | build | [ ] |
| 18 | [P] | Document the limits, the filler list and the scanner's known limits in `lint-rules.md` (FR-003, FR-011) | `src/wiki_studio/schema/lint-rules.md` | build | [ ] |
| 19 | | Tests: each skip rule; wrapped paragraph joined; list numbering (20-word limit); abbreviation not a boundary; each of checks 1–4 positive and negative; line numbers; `log.md` exempt | `tests/test_prose_lint.py` | build | [ ] |

**Checkpoint US3** — verify before continuing:
- [ ] `run_prose_lint` on `tests/fixtures/wiki` completes; no finding inside code, tables, quotes or comments
- [ ] Full gate green

---

## US4: Term lock, API and CLI tier (pitch S4, parts B+C, check 5)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 20 | | Check 5 (FR-013): on non-glossary pages, every prose segment including headings, report each avoid term with file, line, found term, canonical term via the US2 matcher; avoid map always from the whole glossary; `avoid-format` problems reported in this tier too, and only once per call when `--health` also runs (FR-005) | `src/wiki_studio/prose_lint.py` | build | [ ] |
| 21 | | `api.lint(..., prose: bool = False)`; `LintResult.prose: ProseLintResult | None = None` added last; `passed` treats prose like health (fatal only under `strict`) (FR-012) | `src/wiki_studio/api.py` | build | [ ] |
| 22 | | CLI `--prose`; `--strict`/`--paths` help "with --health or --prose"; `_do_lint` prints `prose: N finding(s) across M pages` and `path:line [check] message` lines to stderr like the health block; exit 0, or 1 under `--strict` with findings (FR-012) | `src/wiki_studio/cli.py` | build | [ ] |
| 23 | [P] | README `wiki-studio lint` flag table: `--prose` row; mention advisory default and `--strict` | `README.md` | build | [ ] |
| 24 | | Tests (CLI in-process via `wiki_studio.cli.main(argv)`): advisory exit 0; `--strict` exit 1; `--paths` scoping with the avoid map still whole-glossary; no term-lock finding inside inline code, fences or quotes; finding names file, line, found and canonical term; `--prose --health` together reports a malformed list once; `api.lint(prose=True)` result; positional `LintResult` construction still works; CLI contract tests green | `tests/test_prose_cli.py`, `tests/test_api.py` | build | [ ] |

**Checkpoint US4** — verify before continuing:
- [ ] `poetry run wiki-studio lint --prose` exits 0 on the fixture wiki; `--strict` exits 1 when a finding is planted
- [ ] Full gate green

---

## US5: Fact preservation on update, release 0.5.0 (pitch S5, part D)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 25 | | `removed_facts(old, new) -> list[str]` with extractors (a) `sources[].path` and `path:line`, (b) backticked identifiers, (c) numbers with units from a fixed list; normalize; whole-page set difference (FR-014). Extractor (c) is the first cut under the circuit breaker; (a) and (b) are never cut | `src/wiki_studio/fact_diff.py` | build | [ ] |
| 26 | | `write_patch_set_dir(..., wiki_dir: Path | None = None)`: for `update` edits whose live target exists, add `fact_warnings` to that edit in `plan.json` only when non-empty; pass `paths.wiki_dir` from the three `api.py` call sites (ingest, propose, query file-back); confirm promote ignores the key (FR-015) | `src/wiki_studio/ingestor_multi.py`, `src/wiki_studio/api.py` | build | [ ] |
| 27 | | stderr output `fact-check: <path>: N item(s) removed` plus the items in `_do_ingest`, query `--file-back` and `_do_propose` (after writing, before the optional promote); never changes an exit code (FR-016) | `src/wiki_studio/cli.py` | build | [ ] |
| 28 | [P] | Document `edits[].fact_warnings` in the `plan.json` key table (optional, advisory, ignored by promote) | `docs/patch-set-format.md` | build | [ ] |
| 29 | | Tests: `api.propose` with an `update` that drops a citation, an identifier and a number → all three in `fact_warnings`; a moved citation and a reflowed paragraph → no key; `create` edits → no key; CLI `propose --from` update without `--promote` (warning on stderr, exit 0, nothing applied) and with `--promote` (warning before the apply line, exit 0, applied, key kept in the archived `plan.json`) (FR-014..FR-016) | `tests/test_fact_diff.py`, `tests/test_agent_verbs.py` or a new CLI test file | build | [ ] |
| 30 | | Release 0.5.0 (FR-017): `pyproject.toml` + `src/wiki_studio/__init__.py`; `tests/test_cli_contract.py` version; README banner pinned to `v0.5.0` and `--version` example; CHANGELOG `[Unreleased]` → `[0.5.0] — <date>` with Added, Changed (whole-word slug matching), the upgrade note, and "Closes #28" context; SECURITY supported versions 0.5.x | `pyproject.toml`, `src/wiki_studio/__init__.py`, `tests/test_cli_contract.py`, `README.md`, `CHANGELOG.md`, `SECURITY.md` | build | [ ] |

**Checkpoint US5** — verify before continuing:
- [ ] `poetry run wiki-studio --version` prints 0.5.0; `poetry build` succeeds
- [ ] The propose `--promote` CLI test shows the warning before the apply line
- [ ] Full gate green

---

## Final Verification

- [ ] Type checker: 0 errors; linter and formatter: 0 errors
- [ ] Full suite green with coverage at or above 92 percent
- [ ] No runtime or new dev dependency in `pyproject.toml`
- [ ] Single-writer test (`tests/test_e2e.py::TestE2ESingleWriterInvariant`), CLI contract tests, `tests/test_schema.py` and both evaluation runs' determinism tests green
- [ ] Exit codes unchanged (0, 2..11); `promote` never blocked by prose, `avoid-format` or fact findings
- [ ] Every issue #28 acceptance criterion maps to a passing test (plan.md, Success criteria)
