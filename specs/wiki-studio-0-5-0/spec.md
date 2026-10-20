---
spec_mode: full
feature_id: wiki-studio-0-5-0
risk_category: feature
status: draft
date: 2026-10-20
---

# Spec: wiki-studio 0.5.0 — plain technical English for wiki pages

<!-- Project constitution: shared/skills/ — copilot-conventions, coding-standards, safety -->

Design references (read before building): `CLAUDE.md`; issue
[gosha70/wiki-studio#28](https://github.com/gosha70/wiki-studio/issues/28) (the origin);
the approved pitch `specs/pitches/28-plain-technical-english/pitch.md` (bet, cycle 01),
whose "Findings from the code" section cites every file and line this spec relies on;
in this repository `src/wiki_studio/schema/{ingest-rules,page-types,lint-rules,WIKI_MAINTAINER}.md`,
`prompt.py` (`_SCHEMA_NAMES`, `load_schema_files`), `health_lint.py`
(`_list_wiki_pages`, `_entity_mentions`, `_check_missing_cross_links`), `lint.py`,
`api.py` (`lint`, `LintResult`, `propose`, the three `write_patch_set_dir` call sites),
`ingestor_multi.py` (`write_patch_set_dir`), `promoter.py` (`_load_patch_from_dir`),
`yaml_lite.py`, `cli.py` (`_do_lint`, `_do_ingest`, `_do_propose`, query `--file-back`),
`docs/patch-set-format.md`, `tests/fixtures/wiki/glossary/index.md`.

## User Scenarios

### US1: The model is asked for plain, fact-preserving prose (Priority: HIGH)

**Given** a wiki that uses the packaged schema
**When** `ingest` (multi-page or legacy) or `query` composes its prompt
**Then** the prompt contains a "Writing rules" section with the issue's structure rules and the preserve list, and a wiki with its own `schema/ingest-rules.md` is told in the CHANGELOG to merge the section

### US2: A glossary entry can name the synonyms to avoid (Priority: HIGH)

**Given** a glossary page with `avoid: alignment check, origin check`, or a `glossary/index.md` entry whose first line is `Avoid: alignment check, origin check`
**When** the health lint or the prose lint reads the wiki
**Then** the terms are read in exactly one accepted form, every other form is reported as an `avoid-format` finding rather than ignored, a page that says only "alignment check" counts as mentioning the canonical page in the missing-cross-links check, and the accepted form survives memkernel's parse and render unchanged

### US3: `lint --prose` reports structural prose problems (Priority: HIGH)

**Given** a wiki whose pages contain long sentences, semicolons, filler phrases and over-long Summary or Key-ideas text
**When** the curator runs `wiki-studio lint --prose`
**Then** each problem is reported with file, line and check name, nothing inside code, tables, quotes or HTML comments is reported, and the exit code is 0

### US4: The term lock and the strict tier (Priority: HIGH)

**Given** glossary avoid terms and pages that use them
**When** the curator runs `wiki-studio lint --prose [--strict] [--paths …]`
**Then** each avoid term found on a non-glossary page is reported with file, line, found term and canonical term; `--strict` exits 1 when there are prose findings; `--paths` limits the pages scanned while the avoid map is still built from the whole glossary; `api.lint(prose=True)` returns the same findings

### US5: A rewrite never drops a fact unseen (Priority: HIGH)

**Given** a patch-set with an `update` edit whose new content lacks a `path:` citation, a backticked identifier or a number with a unit that the live page had
**When** `ingest`, `query --file-back` or `propose` writes the patch-set
**Then** `plan.json` records the removed items as `fact_warnings` on that edit, the CLI prints them to stderr (for `propose --promote`, before the apply step), promote ignores the key and never blocks on it, and the release is 0.5.0

## Requirements

- **FR-001**: `src/wiki_studio/schema/ingest-rules.md` MUST contain a `## Writing rules` section stating: one fact per sentence; at most 25 words per sentence in descriptive text and 20 in numbered steps; one instruction per step; active voice; no semicolons; one term per concept, the glossary term; the first sentence of `## Summary` states the main claim; and the preserve list — do not remove or rephrase identifiers, paths, numbers, `path:` citations, or the words "if", "unless" and "not verified"; split a long sentence, do not delete content from it. No prompt code changes.
- **FR-002**: The composed ingest-multi, legacy ingest and query prompts MUST each contain the `## Writing rules` heading (test). `page-types.md` (glossary and concept blocks) and `WIKI_MAINTAINER.md` (the "Keep prose tight" step) MUST reference the section, without using `` - `## …` `` bullet syntax in `page-types.md`.
- **FR-003**: `lint-rules.md` "What the linter does NOT check" MUST be updated: prose structure is checked by `lint --prose` (advisory); prose quality in the sense of clarity stays unchecked. The prose limits, the filler list and the scanner's known limits MUST be documented there.
- **FR-004**: A per-file glossary page MAY carry `avoid:` as one line of comma-separated terms, unquoted or wrapped in double quotes. Terms MUST NOT contain a comma, `"` or `\`. `glossary/index.md` entries MAY carry an `Avoid: …` line as the first non-blank line after `### <term>`, with the same syntax and splitter. `avoid:` on a page whose `page_type` is not `glossary` MUST be ignored. `yaml_lite` MUST NOT change.
- **FR-005**: Every other form MUST be reported as an `avoid-format` finding and contribute no terms: a block list or empty `avoid:`; a value starting with `[`; a single-quoted value; a term containing `"` or `\` (raw or escaped); an empty term after splitting; an index `Avoid:` line that is not the entry's first line or is followed by bullet items; one avoid term listed under two canonical terms. Findings MUST be reported by the `--health` tier (new `HealthFindingKind` `"avoid-format"`) and the `--prose` tier; when both tiers run in one call each malformed list MUST be reported once.
- **FR-006**: A whole-word matcher MUST be used for avoid terms and for slugs: case-insensitive; letters, digits, underscore and hyphen count as word characters on both sides; inner whitespace matches any whitespace run within one paragraph, never across a list item, a heading or a blank line. Tests MUST pin: no match for `pre-origin-gate`, `lint-rules`, `linter`, `origin checklist`, `origin check-in`; match for `lint.`, `(origin-gate)`, and a term wrapped across two lines of one paragraph; no match for "origin" ending one bullet and "check" starting the next.
- **FR-007**: `_entity_mentions` MUST accept optional aliases (canonical slug → avoid terms, from per-file glossary pages only) and count a whole-word alias hit as a mention of the canonical slug; slug matching MUST switch from substring to whole-word (CHANGELOG "Changed"). A page that uses only an avoid term MUST trigger the missing-cross-link finding for the canonical page. Index-entry terms feed the term lock only.
- **FR-008**: A decision record `docs/adr/0001-glossary-avoid-key.md` MUST state the optional key, its one accepted form and why it deviates from the issue's flow example, the memkernel round trip as observed (export never rewrites a glossary page; import drops `avoid:`; `parse_page`/`render_page` keeps a single-line scalar only within the accepted syntax), the requirement that memkernel keep unknown top-level scalar keys, and the memkernel follow-up. `page-types.md` MUST gain an "Optional keys" paragraph in the glossary block; the CHANGELOG MUST record the schema addition.
- **FR-009**: Round-trip compatibility MUST be tested in this repository: wiki-studio reads a raw value, then memkernel's parse rule (`_unquote`: strip one pair of matching outer `"` or `'`) and render rule (`_quote`: wrap in `"` when the value has any of `:#"'[]{}` or edge whitespace, escaping `\` and `"`) — both copied as test fixtures citing their memkernel source lines — then wiki-studio reads again. Accepted values `alignment check, origin check`, `it's, ok`, `"x: y, z"`, `"it's, ok"`, `build #2, origin check` and `"build #2"` MUST read back as the same terms. Unsupported values `the "old" gate`, `C:\cache`, `"the \"old\" gate"`, `"C:\\cache"`, `'it''s, ok'` and `'plain, term'` MUST produce an `avoid-format` finding on the first read and contribute no terms; nothing is asserted about them after memkernel.
- **FR-010**: A new module `src/wiki_studio/prose_lint.py` MUST provide a line-based scanner yielding `ProseSegment(path, line, kind, text)` with `kind` in `paragraph | bullet | numbered | heading`. It MUST skip frontmatter, fenced code (```` ``` ```` and `~~~`), table rows, blockquotes, HTML comments, index-entry `Avoid:` lines, and indented code blocks that follow a blank line outside a list; join wrapped lines into one paragraph; start a segment per list item; mask inline code as one token; replace `[text](target)` with `text`; treat a bare URL as one token. Sentences split at `[.!?]` followed by whitespace and then a capital letter, a backtick or end of text, with an abbreviation guard for "e.g.", "i.e.", "etc." and "vs."; a finding's line is its sentence's first line.
- **FR-011**: Prose checks MUST report `ProseFinding(path, line, check, message)`: (1) a sentence over 25 words, or over 20 in a numbered item; (2) a semicolon after masking; (3) a filler phrase from a fixed list including "it is important to note", "in order to", "ensure that"; (4) a `## Summary` of more than 4 sentences, or a `## Key ideas` bullet of more than 2 sentences; (5) the term lock of FR-013. Headings are exempt from checks 1–4. Limits and the filler list MUST be named constants in `src/wiki_studio/schema/__init__.py`. Pages come from the health lint's page list (excluding `schema/`, `scripts/`, `.audit/`); `log.md` is exempt.
- **FR-012**: `wiki-studio lint --prose` MUST print `prose: N finding(s) across M pages` and one `path:line [check] message` line per finding to stderr, like the health block; exit 0 by default and 1 under `--strict` with prose findings; `--paths` MUST limit the pages scanned; `--strict` and `--paths` help MUST read "with --health or --prose". No new exit code. `api.lint(..., prose: bool = False)` MUST return an optional `LintResult.prose: ProseLintResult | None = None`, added last with a default so positional construction keeps working; `passed` treats prose like health (fatal only under `strict`).
- **FR-013**: Check 5 (term lock) MUST, on every non-glossary page, report each avoid term found in prose segments including headings, with file, line, found term and the canonical term, using FR-006's matcher; masked inline code, fenced code and quotes are never matched. The avoid map is always built from the whole glossary, whatever `--paths` says.
- **FR-014**: A pure function `removed_facts(old: str, new: str) -> list[str]` MUST extract (a) frontmatter `sources[].path` values and `path:line` references in the body, (b) inline backticked identifiers, (c) numbers with a unit from a fixed list (ms, s, min, h, d, KB, MB, GB, %, words, lines, tokens), normalize (strip whitespace, ignore unit case, drop thousands commas, drop a trailing `()`), compare as sets over the whole page, and return the items in the old page and not the new. A citation moved between frontmatter and body or between sections, and a reflowed paragraph, MUST produce no item.
- **FR-015**: `write_patch_set_dir` MUST accept `wiki_dir: Path | None = None` and, for an `update` edit whose live target exists, write `edits[].fact_warnings: [...]` into `plan.json` only when the list is non-empty. The three call sites in `api.py` (ingest, propose, query file-back) MUST pass `paths.wiki_dir`. Promote MUST ignore the key. `docs/patch-set-format.md` MUST document the optional key.
- **FR-016**: `_do_ingest`, query `--file-back` and `_do_propose` MUST print `fact-check: <path>: N item(s) removed` and the items to stderr; `_do_propose` MUST print them after writing the patch-set and before its optional promote step. Warnings MUST NOT change any exit code or stop promote. CLI tests MUST cover `propose --from` with an `update` that drops a citation: without `--promote` (warning on stderr, exit 0, nothing applied) and with `--promote` (warning before the apply line, exit 0, update applied, `fact_warnings` kept in the archived `plan.json`).
- **FR-017**: The release MUST be 0.5.0: `pyproject.toml` and `src/wiki_studio/__init__.py` bumped together, the CLI contract version test updated, the README banner pinned to `v0.5.0`, CHANGELOG `[0.5.0]` with Added (writing rules, `avoid:`, `lint --prose`, fact warnings), Changed (whole-word slug matching) and the upgrade note for local `schema/ingest-rules.md` copies, and README `wiki-studio lint` documentation for `--prose`.

## Constraints

- **Standard library only.** No new runtime or dev dependency for these features (no Vale, proselint, pyyaml, NLP library); no full CommonMark parser.
- **No LLM calls** in any new check and no new prompt round trips.
- **Advisory first.** Prose, `avoid-format` and fact findings never block `promote`; the promote gate stays structural-only. `--strict` is the only way prose findings become fatal, and only for `lint`.
- **Shared schema.** `avoid:` is optional; existing pages stay valid; no existing frontmatter key, page type or directory changes. memkernel's and code-copilot-team's code and schema copies are not changed from this repository.
- **Contracts.** Exit codes 0 and 2..11 unchanged; the patch-set format only gains an optional key; `promoter.py` stays the single writer into the wiki (the single-writer test stays green); `api` changes are additive with defaults.
- **Out of scope.** The STE approved-word dictionary; auto-rewrite or `--fix`; visual or interactive artifacts; eval-set measurement of fact retention (issue follow-up); making index entries entities.
- **Circuit breaker (from the pitch).** If time runs short: drop prose checks 3–4 first, then the numbers-with-units extractor (FR-014 c). FR-014 (a) and (b) are never cut. If they cannot ship, FR-001/FR-002 (writing rules) are held back rather than shipped without the fact check.
- **Gate.** `poetry run ruff check src/ tests/ eval/ && poetry run ruff format --check src/ tests/ eval/ && poetry run mypy src/ && poetry run pytest -q -p no:cacheprovider --cov=wiki_studio --cov-fail-under=80` stays green; coverage does not fall below the current level (92%).
