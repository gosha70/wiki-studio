---
pitch_id: 28-plain-technical-english
title: "Plain technical English for wiki pages: writing rules, glossary term lock, lint --prose, fact preservation"
appetite: 2w
bet_status: shipped
cycle: "01"
circuit_breaker: "Core is S1-S4 plus S5's citation and identifier checks. If S3 is still uphill at day 5, drop prose checks 3-4. If S5 is not downhill by day 8, drop its numbers-with-units extractor. If S5's citation and identifier checks are not done by day 10, ship 0.5.0 without S1's writing rules and re-pitch A and D together. Never make prose findings block promote, add a dependency, or add an LLM call to stay on schedule."
shaped_by: "pitch-shaper (Claude Code) for gosha70"
shaped_date: 2026-10-20
---

<!-- Shape-Up pitch. Origin: https://github.com/gosha70/wiki-studio/issues/28 -->
<!-- The issue is the origin. This pitch shapes it; it does not replace it. -->

# Pitch: Plain technical English for wiki pages

## Problem

An LLM writes every wiki page, and people and agents read those pages for a
long time. No check looks at the prose. `lint-rules.md:68-78` lists prose
quality under "What the linter does NOT check". The only style guidance is
"Keep prose tight" (`WIKI_MAINTAINER.md:48`) and the Summary and Key-ideas
limits (`page-types.md:40-41`), and nothing enforces those limits.

Synonym drift has a cost you can measure. The missing-cross-links check finds
entities by slug text (`health_lint.py:185-200`). A page that says "alignment
check" for `origin-gate` does not count as a mention, so the check cannot
report the missing link. The origin is Karpathy's post of 2 Oct 2026, plus a
fact-check. The post makes two suggestions: constrained prose, and
throwaway visual artifacts. Issue #28 takes only the first: "One tip: ask
the model to write '80% of the way to' ASD-STE100 Simplified Technical
English." So does this pitch (see No-gos). The origin gives two findings that
shape this work:

- a style rule in a prompt is only a request, so a script must check it;
- simplification drops facts: about 47% of scored facts were lost under a
  strict STE prompt, against about 9% under a loose one.

How big is the gap today? A rough stdlib probe of the 23
code-copilot-team wiki pages found about 875 sentences. About 123 of them
are longer than 25 words, and the pages hold about 100 semicolons. A
first `lint --prose` run on a real wiki will report a few hundred findings.
This confirms the issue's "advisory first" constraint.

## Findings from the code

wiki-studio was read at main 8b5c8af and memkernel at its local checkout
4a9597d, on 2026-10-20. These facts drive the scopes and rabbit holes below.

1. **Prompts load three schema documents.** `prompt.py:25`
   (`_SCHEMA_NAMES = ingest-rules, page-types, citation-rules`) feeds
   ingest-multi (`prompt.py:161`), legacy ingest (`prompt.py:235`) and query
   (`querier.py:180`). `backends/copilot_cli.py:176` renders `ingest_rules` in
   full. A section in `ingest-rules.md` reaches all three prompts with no
   code change, as the issue says.
2. **A wiki's local schema copy wins.** `load_schema_files`
   (`prompt.py:36-46`) prefers `<wiki>/schema/<name>.md` over the packaged
   copy. code-copilot-team ships `knowledge/wiki/schema/ingest-rules.md` and
   `page-types.md`. So the writing rules reach that wiki only after it syncs
   its copy (resolved question 1).
3. **Only a single-line list survives both parsers.**
   - The issue's flow form, `avoid: [a, b]`, does not parse as a list.
     `yaml_lite` has no flow sequences (`yaml_lite.py:17-23`), so it reads
     the value as one string (`yaml_lite.py:116`).
   - A block list (`avoid:` followed by `  - term` lines) parses in
     `yaml_lite` but is lost in memkernel. memkernel's `_parse_frontmatter`
     (`memkernel/wiki/pages.py:52-88`) ignores every indented line outside
     `sources:`. After a parse and render it becomes `avoid: ""`.
   - A single-line comma-separated scalar, `avoid: alignment check, origin
     check`, survives both. `yaml_lite.py:116` reads it, and memkernel keeps
     it in `WikiPage.extra` (`pages.py:73, 109`) and writes it back
     (`pages.py:130-131`).
   - memkernel adds double quotes when a value contains `:#"'[]{}`
     (`pages.py:113-117`). `yaml_lite.unquote` removes them again
     (`yaml_lite.py:132-133`).
4. **There are two glossary-index layouts, and neither layout's entries
   are entities.**
   - The package fixture, `tests/fixtures/wiki/glossary/index.md:14-23`,
     follows `page-types.md:112-123`. Each `### <term>` entry is followed by
     its own `## Definition` and `## Where it appears` sections.
   - code-copilot-team's `knowledge/wiki/glossary/index.md` puts page-level
     H2s first, then entries, each closing with an italic
     `*Where it appears:*` line.
   - In both layouts, an entry runs from its `### <term>` heading to the
     next `###` heading or the end of the file.
   - Separately, `_check_missing_cross_links` takes entity slugs from file
     stems and skips `index` (`health_lint.py:216-223`). Index entries are
     therefore not entities today.
5. **`_entity_mentions` matches substrings.** It is a case-insensitive
   substring match (`slug.lower() in lower`, `health_lint.py:195-199`),
   although its docstring says whole-word (`health_lint.py:186-187`). If
   avoid terms went through it unchanged, "origin check" would match inside
   "origin checklist". New code for the term lock and avoid-term mentions
   therefore uses whole-word matching, and slug matching switches to the
   same rule (question 6, resolved).
6. **Lint already has the tier shape.** The structural tier always runs.
   `--health` is opt-in, and `--strict` makes it fatal (`cli.py:264-290`,
   `api.py:159-178`). `--paths` filters findings after the whole-wiki pass
   (`health_lint.py:454-456`). A fatal lint exits 1 (README.md:174). No new
   exit code is needed; 0 and 2..11 stay as they are (`errors.py`).
7. **`HealthFinding` has no line number** (`proposal.py:140-165`), and
   `HealthFindingKind` is a closed `Literal` (`proposal.py:131-136`). The
   term-lock criterion needs file and line, so prose findings need their own
   small dataclass.
8. **One function writes every patch-set preview.** `write_patch_set_dir`
   (`ingestor_multi.py:168-231`) serves ingest (`api.py:366`), propose
   (`api.py:441`) and query file-back (`api.py:622`). It takes no wiki path
   today, so it cannot read the old page.
9. **Promote ignores extra `plan.json` keys.** `_load_patch_from_dir`
   reads only `path`, `action`, `preview` and `rationale`
   (`promoter.py:79-116`). Curator-delta walks every file under `preview/`
   (`promoter.py:302-331`). The patch-set format is public and versioned
   with the package (`docs/patch-set-format.md:5-7`), and a minor version
   may add fields (`api.py:21-30`).
10. **The test backend never emits `update` edits** (`backends/test.py`).
    Fact-preservation tests must go through `api.propose` with an `update`
    edit, or call the diff function directly.
11. **Schema changes need a decision record.** `CLAUDE.md:51` requires a
    record in `docs/adr/` for frontmatter-key changes, and `docs/adr/` does
    not exist yet. `tests/test_schema.py:20` parses `` - `## X` `` bullets as
    required sections, so any edit to `page-types.md` must avoid that
    syntax.
12. **memkernel never rewrites `avoid:`.** memkernel's import and export
    paths (`memkernel/wiki/sync.py`) behave as follows:
    - The exporter has no glossary mapping (`sync.py:54-59`). It skips
      memories that were imported from the wiki (`sync.py:150`) and any
      target file that already exists (`sync.py:156-158`). So it never
      rewrites an existing glossary page.
    - The importer maps `glossary` to `FACT` (`sync.py:62-67`). It passes
      only title plus body, tags, source and importance to `retain`
      (`sync.py:404-415`), and never `page.extra`. So import drops `avoid:`.
    - From these files it is not known whether the Memory model could
      store frontmatter extras elsewhere.
    - The one rewrite path is a direct `parse_page` and `render_page` call
      on an existing page, which is public API (`memkernel/wiki/__init__.py:14`).
      A single-line scalar survives that path; a block list does not
      (finding 3).

## Appetite

**2w.** For an LLM executor the work is about 14.5-17.5 hours across five
scopes:

| Scope | Estimate |
|-------|----------|
| S1 | 1h |
| S2 | 3-4h |
| S3 | 5-7h |
| S4 | 2h |
| S5 | 3.5h |

With review rounds that is about 3 agent-days. Two weeks of wall-clock time
covers the per-phase review loop, roughly two rounds per scope, and the
owner's push, merge and tag gates.

The trim order below is the circuit breaker. It frees about 3h, for C's
checks 3-4 and D's units extractor, without dropping any part of the
issue. A 4-week appetite would invite the STE dictionary, prose auto-fixes
and blocking gates, and the issue rules all three out.

What is cut first, and why D stays:

- **Part D stays in 0.5.0.** The origin's evidence is that simplification
  drops facts, about 47% under a strict prompt and about 9% under a loose
  one. Part A asks the model for more aggressive rewrites. Shipping A
  without D ships the risk without the check.
- **The trim order is:**
  1. C's checks 3-4 (filler phrases, Summary and Key-ideas length);
  2. then D's numbers-with-units extractor, its noisiest part.
- **Kept in every case:** D's `path:` citations and backticked
  identifiers, and C's checks 1, 2 and 5.
- **A ships only with D's core.** If D's core slips, A is held back
  (circuit breaker).

## Solution shape

Three layers, all standard library, with no new LLM calls:

1. **Ask (A).** Add a "Writing rules" section to `ingest-rules.md`.
   `page-types.md` and `WIKI_MAINTAINER.md` reference it. The existing
   prompts carry it unchanged.
2. **Check (B + C).** Add a new module `prose_lint.py`. A small markdown
   scanner turns each page into prose segments with line numbers. Five
   checks run over those segments. One of them is the term lock, fed by
   `avoid` terms read from glossary pages in one accepted form. Any other
   form is reported as a finding, never silently ignored. The same `avoid`
   map also feeds `_entity_mentions`, using whole-word matching.
3. **Show (D).** When a patch-set holds an `update` edit,
   `write_patch_set_dir` diffs the old live page against the new content. It
   records the citations, identifiers and numbers that disappeared as an
   optional `fact_warnings` list on that edit in `plan.json`. The CLI prints
   a one-line count per edit to stderr. Promote ignores the key and never
   blocks on it.

Target release: **0.5.0**. It is a minor release, and every change is
additive:

- the `prose=` keyword on `api.lint`;
- an optional `LintResult.prose` field with a default;
- a new `avoid-format` `HealthFindingKind`;
- an optional `plan.json` key;
- an optional frontmatter key.

Bump `pyproject.toml` and `src/wiki_studio/__init__.py` together.

## Scopes

Build order: S1 and S2 can start at once. S3 is independent. S4 joins S2
and S3. S5 is independent of all the others.

### S1: Writing rules in the schema (part A), ~1h

- Add a `## Writing rules` section to `src/wiki_studio/schema/ingest-rules.md`
  with the issue's rules: one fact per sentence; at most 25 words, or 20 in
  numbered steps; one instruction per step; active voice; no semicolons; the
  glossary term; the first Summary sentence states the main claim. Include
  the preserve list: identifiers, paths, numbers, `path:` citations, and the
  words "if", "unless" and "not verified". Split a long sentence; do not cut
  content from it.
- Reference the section from the glossary and concept blocks of
  `page-types.md` and from step 6 of `WIKI_MAINTAINER.md` ("Keep prose
  tight", line 48). Do not use `` - `## ...` `` bullet syntax in
  `page-types.md` (finding 11).
- Update the "does NOT check" list in `lint-rules.md:68-78`: prose
  *structure* is now checked by `lint --prose` (advisory). Prose *quality*,
  in the sense of clarity and helpfulness, stays unchecked.
- Tests: the composed ingest-multi, legacy ingest and query prompts each
  contain the section heading (extend `tests/test_prompt.py`).
- CHANGELOG `[Unreleased]` gets an upgrade note: wikis with a local
  `schema/ingest-rules.md` must merge the section (finding 2).

### S2: Glossary `avoid` terms, format findings, whole-word mentions (part B data), ~3-4h

**One accepted form.** This deviates from the issue's flow-style example,
for the reasons in finding 3.

- *Per-file glossary page (frontmatter):* `avoid: alignment check, origin
  check`. It is one line of comma-separated terms. A term cannot contain a
  comma, a double quote (`"`) or a backslash (`\`). The value is either
  unquoted or wrapped in **double** quotes; memkernel wraps values that
  contain `:`, `#`, `'`, brackets or braces in double quotes, and those
  survive (finding 3). A **single-quoted** value (`'...'`) is refused as an
  `avoid-format` finding: `yaml_lite` decodes YAML's doubled apostrophe
  (`'it''s, ok'` reads as `it's, ok`) but memkernel's reader only strips
  the outer quotes and its renderer then double-quotes the result, so the
  value reads back as `it''s, ok`. Rejecting the single-quoted form is
  simpler than matching the two decoders, and an apostrophe needs no
  quoting (`avoid: it's, ok` reads the same in both). `"` and `\` are
  refused because memkernel's renderer escapes them (`\"`, `\\`) and
  neither memkernel's reader nor `yaml_lite` decodes the escapes, so the
  term would come back changed: `the "old" gate` returns as
  `the \"old\" gate`, and `C:\cache` as `C:\\cache`. A value that contains
  either character, escaped or not, is an `avoid-format` finding naming the
  character; it is never silently altered or dropped.
- *`glossary/index.md` entry:* the first non-blank line after
  `### <term>` reads `Avoid: alignment check, origin check`. It uses the
  same syntax and the same splitter, and comes before `## Definition` in
  the fixture layout or before the definition paragraph in the
  code-copilot-team layout.
- *Why the first line and not an `## Avoid` section:*
  - Position alone scopes the line to one entry in both layouts
    (finding 4).
  - An `## Avoid` H2 would read as a page-level section in the
    code-copilot-team layout.
  - It would also add an H2 that the glossary's required-section list
    (`page-types.md:115-118`) does not name.
  - A section invites a bullet list, which is the form that memkernel
    loses.

**Every other form is a finding, never ignored.** These are reported as
`avoid-format`:

- an `avoid:` block list, or an empty `avoid:`;
- a value that starts with `[` (the flow form);
- an `Avoid:` line in an index entry that is not the entry's first line,
  or that is followed by bullet items;
- an empty term after splitting (`a,,b`);
- one avoid term listed under two canonical terms.

**Where format findings are reported.** The tiers that read the avoid
map report them: `--prose` (S4) and `--health` (as the new
`HealthFindingKind` `"avoid-format"`). Both are advisory and become fatal
under `--strict`. The structural lint and the promote gate do not change
(question 7, resolved). `avoid:` on a page that is not a glossary page is
ignored, as the issue's acceptance criterion says.

**Reader.** `load_avoid_map(wiki_dir) -> tuple[dict[canonical,
AvoidEntry], list[FormatProblem]]` lives in `prose_lint.py`, and
`health_lint` imports it. An `AvoidEntry` holds the canonical term, the
target page (and anchor, for index entries) and the avoid terms.

**Whole-word matching.** Add a helper that matches a term case-insensitively.
It requires a boundary, on both sides, of anything that is not a letter,
digit, underscore or hyphen, so "origin checklist", "origin check-in" and
"pre-origin check" do not match "origin check". Inner whitespace matches `\s+`, so a term split across a wrapped
line still matches, but only within one paragraph: never across a list
item, a heading or a blank line.

- `_entity_mentions` (`health_lint.py:185`) takes an optional
  `aliases: dict[str, list[str]] | None`. A whole-word avoid-term hit counts
  as a mention of its canonical slug.
- Aliases come from per-file glossary pages only, because index entries are
  not entities (finding 4). Widening the entity set is out of scope.
- Slug matching switches to the same whole-word rule in this scope
  (question 6, resolved), recorded under CHANGELOG "Changed".

**Decision record.** `docs/adr/0001-glossary-avoid-key.md`, required by
CLAUDE.md:51, is the first ADR in the repo. It states:

- the optional key, its one accepted form, and why it deviates from the
  issue's flow-style example (finding 3);
- the memkernel round trip as determined from the code (finding 12):
  - export never rewrites a glossary page;
  - import drops `avoid:`, because `extra` is not passed to `retain`;
  - a direct `parse_page` and `render_page` call keeps a single-line
    scalar **only if it contains no `"` and no `\`**. memkernel's `_quote`
    escapes those two characters and its `_unquote` does not decode them
    (nor does `yaml_lite`), so a term with either one changes on every
    round trip. Likewise a single-quoted value: `yaml_lite` decodes `''`
    to `'`, memkernel's `_unquote` does not, so `'it''s, ok'` reads back as
    `it''s, ok`. The accepted syntax therefore excludes `"` and `\` inside
    terms and single-quoted values (S2), and only for that narrowed syntax
    does the ADR claim the round trip holds;
  - whether the Memory model can keep frontmatter extras is not
    determined.
- the **requirement**: any memkernel path that parses and re-renders an
  existing wiki page must keep unknown top-level scalar keys unchanged. For
  values in the accepted syntax it does today; values with `"` or `\`, and
  single-quoted values, it does not (above), which is why they are refused
  here. Compatibility is established in this repo by a test of the
  complete sequence: wiki-studio reads the raw value, then memkernel's
  **parse** rule (`_unquote`: strip one pair of matching outer `"` or `'`,
  nothing else) and its **render** rule (`_quote`: wrap in `"` when the
  value has `:#"'[]{}` or edge whitespace, escaping `\` and `"`), both
  copied as fixtures with their source lines cited, and wiki-studio reads
  again. Accepted values must read back as the same terms. Unsupported
  values must produce an `avoid-format` finding on the first read and
  contribute no terms; nothing is guaranteed about what memkernel turns
  them into (it can strip the very syntax that was refused, e.g.
  `'plain, term'` re-renders as the valid `plain, term`). The
  memkernel-side test remains a follow-up, not the evidence.
- the **follow-up for memkernel's own issue**: add that round-trip test
  for `avoid:`, and decide whether imported glossary memories should carry
  the avoid terms. This is not assumed done in this cycle.

**Docs.** Add an "Optional keys" paragraph to the glossary block in
`page-types.md`, and a CHANGELOG entry under the schema.

**Tests.**

- Both forms parse.
- The index parser runs on a copy of
  `tests/fixtures/wiki/glossary/index.md` with an `Avoid:` line added, and
  on a code-copilot-team-layout sample. The shared fixture stays as it is,
  so `test_fixture_wiki.py` is unaffected.
- Each refused form yields one `avoid-format` finding.
- Round trip, read → memkernel parse → memkernel render → read: the
  accepted values `alignment check, origin check`, `it's, ok`,
  `"x: y, z"` and `"it's, ok"` come back as the same terms.
- Unsupported values, on their first read only: `the "old" gate` and
  `C:\cache`, raw and memkernel-escaped (`"the \"old\" gate"`,
  `"C:\\cache"`), and the single-quoted `'it''s, ok'` and `'plain, term'`,
  each yield an `avoid-format` finding and contribute no term. No
  assertion is made about them after a pass through memkernel.
- A non-glossary page's `avoid:` is ignored.
- A page that uses only synonyms triggers the missing-cross-link finding
  (issue acceptance criterion).
- "origin checklist" does not count as a mention.

### S3: Prose scanner and `lint --prose` checks 1-4 (part C), ~5-7h

- Add `src/wiki_studio/prose_lint.py` with a line-based scanner. It yields
  `ProseSegment(path, line, kind, text)`, where `kind` is `paragraph`,
  `bullet`, `numbered` or `heading`. Rules:
  - Skip frontmatter, fenced code (```` ``` ```` and `~~~`), table rows
    (`|`), blockquotes (`>`), HTML comments and index-entry `Avoid:` lines.
  - Join wrapped lines into one paragraph; real pages wrap at about 70
    columns.
  - Each list item starts a new segment.
  - Mask inline code as one token, replace `[text](target)` with `text`,
    and treat a bare URL as one token.
- Sentence splitting uses a regex boundary (`[.!?]` followed by space and
  then a capital, a backtick or the end of the text). A short abbreviation
  guard covers "e.g.", "i.e.", "etc." and "vs.". A finding's line is the
  line where its sentence starts.
- Checks:
  1. More than 25 words, or more than 20 in a numbered item.
  2. A semicolon after masking.
  3. A filler phrase from a fixed list.
  4. A `## Summary` of more than 4 sentences, or a `## Key ideas` bullet of
     more than 2.
- Headings are skipped by checks 1-4.
- Limits and the filler list are named constants in
  `src/wiki_studio/schema/__init__.py`, which is where the repo keeps
  `REQUIRED_KEYS` (line 93). Document them in `lint-rules.md`.
- Add `ProseFinding(path, line, check, message)` and a
  `ProseLintResult(findings, pages_checked)`.
- Pages come from `_list_wiki_pages` (`health_lint.py:60`), which excludes
  `schema/`, `scripts/` and `.audit/`. `log.md` is exempt because it is
  append-only history.
- Tests: fixture snippets for each skip rule, wrapped paragraphs, list
  numbering, an abbreviation, and each check.

### S4: CLI/API tier and the term-lock check (parts B+C, check 5), ~2h

- Check 5: for each prose segment on a non-glossary page, including
  headings, report each avoid term with its file, line, found term and
  canonical term. It uses S2's whole-word matcher. Masked inline code is
  never matched, and the scanner already drops fenced code and quotes. S2's
  `avoid-format` problems are reported in this tier too.
- `api.lint(..., prose: bool = False)` and an optional
  `LintResult.prose: ProseLintResult | None = None`, added at the end with a
  default so positional construction (`api.py:652`) keeps working.
  `passed` treats prose like health: fatal only under `strict`.
- `cli.py`: add a `--prose` flag. Widen the `--strict` and `--paths` help to
  "with --health or --prose". `_do_lint` prints `prose: N finding(s) across M
  pages` and one `path:line [check] message` line per finding to stderr,
  matching the health block (`cli.py:478-489`).
- `--paths` limits which pages are scanned, while the avoid map is still
  built from the whole glossary. Exit codes: 0 by default, 1 under
  `--strict` with findings. No new exit code.
- README `wiki-studio lint` table row. Tests: CLI in-process via
  `wiki_studio.cli.main(argv)`. Cover advisory exit 0, strict exit 1,
  `--paths` scoping, no findings inside code or quotes, and `--prose` with
  `--health` together.

### S5: Fact preservation on update (part D), ~3.5h (citations and identifiers ~2.5h incl. propose output, units ~1h)

- Add a pure function `removed_facts(old: str, new: str) -> list[str]`,
  with the extractors in `prose_lint.py` or a small `fact_diff.py`. It
  extracts three kinds of item:
  1. frontmatter `sources[].path` values, plus `path:line` references in
     the body;
  2. inline backticked identifiers;
  3. numbers with a unit from a fixed list: ms, s, min, h, d, KB, MB, GB,
     %, words, lines, tokens, and so on.
- Extractors 1 and 2 are core. Extractor 3 is the first part cut under the
  circuit breaker.
- Normalize before comparing: strip whitespace, ignore unit case, drop
  thousands commas, drop a trailing `()`. Compare as sets over the whole
  page, so a fact that moves between frontmatter and body, or between
  sections, is not reported.
- `write_patch_set_dir(patch, output_dir, *, wiki_dir: Path | None = None)`:
  for an `update` edit whose live target exists, write
  `edits[].fact_warnings: [..]` into `plan.json` only when the list is not
  empty. The three call sites (`api.py:366, 441, 622`) pass
  `paths.wiki_dir`. Promote ignores the key (finding 9). This optional key
  is allowed in a minor version (`docs/patch-set-format.md:5-7`,
  `api.py:21-30`).
- Show the warnings: `_do_ingest`, query `--file-back` and `_do_propose`
  print `fact-check: <path>: N item(s) removed` (and the items) to stderr.
  `_do_propose` prints them right after writing the patch-set and
  **before** its optional promote step, because `propose --from …
  --promote` is the path the memkernel arm's agent uses and applies the
  update at once; without this the warnings would never be seen there.
  Warnings stay advisory: they never change an exit code or stop promote. Document the optional
  key in the `plan.json` key table of `docs/patch-set-format.md`.
- Tests: `api.propose` with an `update` edit that drops a citation, an
  identifier and a number. Also cover a moved citation and a reflowed
  paragraph, which must produce no warning. The test backend has no update
  path (finding 10).
- CLI tests for `propose --from` with an `update` that drops a citation:
  proposal only (warning on stderr, exit 0, nothing applied) and with
  `--promote` (warning on stderr before the apply line, exit 0, update
  applied, `fact_warnings` kept in the archived `plan.json`).

## Decisions taken in shaping (accepted by the owner, 2026-10-20)

- Part A goes in `ingest-rules.md`, as the issue says, not in a new
  `writing-rules.md`. A new file would need prompt code changes, against
  the issue's "no prompt code changes". The local-override gap (finding 2)
  is handled by an upgrade note instead.
- `avoid:` has one accepted form, a single-line comma-separated scalar, in
  frontmatter and in index entries. The flow and block forms are reported
  as `avoid-format` findings. `yaml_lite` is not changed.
- Index entries carry an `Avoid:` line as the first line after
  `### <term>`, and feed the term lock only. Only per-file glossary pages
  feed `_entity_mentions`.
- Avoid-term and slug matching are both whole-word, with hyphens part of a
  word (question 6, resolved).
- The ADR is written (CLAUDE.md:51), even though the issue names only the
  CHANGELOG. It states the memkernel round trip as a requirement and a
  follow-up, not an assumption.
- Fact warnings go in `plan.json` and on stderr, not in a file under
  `preview/`.
- Limits and lists are named constants, not parsed back out of the
  markdown schema.

## Rabbit holes

- **Sentence splitting in markdown.** Abbreviations, `0.4.1`, `lint.py.`,
  "Fig. 3", ellipses and lines that wrap mid-sentence can each eat a day.
  *Workaround:* use a regex boundary plus a short abbreviation guard, and
  accept some error. The findings are advisory. Never add an NLP library,
  and never try a full CommonMark parser.
- **Skipping code, quotes and tables.** Nested lists, indented code inside
  list items, HTML blocks and `|` inside inline code can each be handled
  one more way. *Workaround:* handle fences, `|` rows, `>` lines, HTML
  comments and inline code, and nothing else. Indented code blocks
  (4-space indent outside a list) are skipped only when they follow a blank
  line. Record other cases as known limits in `lint-rules.md`.
- **The `glossary/index.md` `avoid` format.** It is tempting to give index
  entries their own frontmatter, an `## Avoid` section with bullets, or to
  make them first-class entities in the cross-link check. *Workaround:*
  use one `Avoid:` line in the first position, with the same syntax as the
  frontmatter key, and limit index entries to the term lock (finding 4).
- **Supporting more than one list form.** Accepting flow or block lists
  "to be helpful" means growing `yaml_lite`, which its header forbids. It
  also means writing a form that memkernel loses (finding 3).
  *Workaround:* accept exactly one form and report every other form as a
  finding.
- **The shared-schema ADR.** It could grow into a general "schema
  evolution policy" or a memkernel change. *Workaround:* write a one-page
  ADR for one optional key only. State memkernel's behaviour as observed,
  and put the round-trip test and any import change into memkernel's
  follow-up issue. memkernel's code is not touched from this repo.
- **False positives in the fact diff.** Reflowed paragraphs, renamed
  headings, numbers spelled out ("twenty"), `foo()` against `foo`, and
  code spans moved into fenced blocks will all look like losses.
  *Workaround:* compare normalized sets over the whole page, and accept the
  rest because the warning is advisory. The units extractor is the
  noisiest part and is cut first. Do not recompute at promote time after
  curator edits. Do not add severity levels or a suppression syntax.

## No-gos

- No visual or interactive artifacts (the post's second suggestion:
  diagrams, interactive pages, animations). Out of scope for this pitch;
  a separate issue if wanted. Nothing here blocks diagrams later: the prose
  scanner skips fenced code (S3), so a Mermaid diagram in a fenced block is
  never checked as prose.
- No STE approved-word dictionary or vocabulary check. It is copyrighted,
  and strict vocabulary causes the most fact loss.
- No LLM calls in any new check, and no new prompt round trips. The cost
  stays the same.
- No new runtime dependencies (no Vale, proselint, pyyaml or NLP library).
- No blocking promote on prose, fact or `avoid-format` findings. The
  promote lint gate (`promoter.py:205-221`) stays structural-only.
- No auto-rewrite or `--fix` mode for prose.
- No new exit codes, and no change to existing frontmatter keys, page
  types or directories.
- No eval-set measurement of fact retention in this cycle. That is the
  issue's own follow-up.
- No changes to code-copilot-team's or memkernel's code or schema copies
  from this repo. Those are their own follow-up issues.

## Circuit breaker

Core is S1-S4 plus S5's citation and identifier extractors. The trigger and
actions, in order:

1. If S3 is still uphill at the end of day 5, drop prose checks 3-4 (filler
   and Summary/Key-ideas length). Record them as a follow-up and finish S4.
2. If S5 is not downhill by day 8, drop its numbers-with-units extractor.
   Ship `path:` citations and backticked identifiers, and record units as a
   follow-up.
3. If S5's citation and identifier extractors are still not done by day
   10, ship 0.5.0 with S2-S4 (term lock and `lint --prose`). Hold back S1's
   writing rules and re-pitch A and D together. Rules that ask for
   aggressive rewrites do not ship without the check that shows dropped
   facts.
4. Never, to save time: make prose findings fatal by default or part of the
   promote gate, add a dependency or an LLM call, or ship the `avoid:` key
   without its ADR and CHANGELOG entry.

"Exhausted" means two working weeks have passed, or the review loop is
stuck in a third round on the same scope.

## Questions for the owner

### Resolved in review (2026-10-20)

1. **The writing rules will not reach wikis with a local
   `schema/ingest-rules.md`, code-copilot-team included** (finding 2).
   *Resolved:*
   - Keep the section in `ingest-rules.md`, as the issue says.
   - Add a CHANGELOG upgrade note.
   - Fold the code-copilot-team schema sync into its follow-up issue.
   - Why not a separate `writing-rules.md`: it would need prompt code
     changes, which the issue rules out.
2. **Write an ADR for `avoid:`?** *Resolved:* yes, as
   `docs/adr/0001-glossary-avoid-key.md`, plus the CHANGELOG entry. It
   now includes the memkernel round-trip requirement and follow-up (S2).
3. **Where should fact-preservation warnings live?** *Resolved:* an
   optional `edits[].fact_warnings` key in `plan.json`, plus one stderr
   line per edit. An optional key is allowed in a minor version, because
   the format is public and versioned with the package
   (`docs/patch-set-format.md:5-7`) and a minor version may add fields
   (`api.py:21-30`). Document it in the key table of
   `docs/patch-set-format.md`.

### Resolved by the owner (2026-10-20)

The owner accepted the recommendations for questions 4-7, with the review refinements below. No questions remain open.

4. **What is the trim order under pressure?** *Resolved (owner accepted the recommendation, 2026-10-20):*
   1. Cut C's checks 3-4 first.
   2. Then cut D's numbers-with-units extractor.
   3. Keep D's `path:` citations and backticked identifiers, and C's
      checks 1, 2 and 5, in 0.5.0.
   4. If D's core still slips, hold back A rather than ship it alone.

   The reason: part A asks for more aggressive rewrites, and the origin's
   evidence is that rewrites drop facts. The appetite still holds, with
   about 3 agent-days of work in 2 weeks.
5. **What is the `avoid` format?** This deviates from the issue's flow
   example. *Resolved (owner accepted the recommendation, 2026-10-20):*
   - frontmatter: `avoid: alignment check, origin check`, one line,
     comma-separated;
   - `glossary/index.md`: `Avoid: alignment check, origin check` as the
     first line after `### <term>`;
   - any other form is an `avoid-format` finding.

   The reason: a block list is lost in memkernel's parser, and the flow
   form does not parse as a list in `yaml_lite` (finding 3). The first-line
   position works in both index layouts (finding 4). The parser is tested
   on a copy of `tests/fixtures/wiki/glossary/index.md` and on a
   code-copilot-team-layout sample. The cost is that a term cannot contain
   a comma.

   *Review refinement (for the spec):* an index entry's `Avoid:` line is
   body text, so the prose checks (S3) and the cross-link mention count
   (S2) must skip it; otherwise the glossary reports and counts its own
   avoid terms. Test both.
6. **Should `_entity_mentions` also switch slug matching from substring
   to whole-word?** *Resolved (owner accepted the recommendation, 2026-10-20):* yes, in the same release, recorded under
   CHANGELOG "Changed" as a behaviour change.
   - Today a slug such as `lint` counts inside "linter" and "health-lint".
     That over-counts mentions and causes false missing-cross-link
     warnings.
   - The docstring already promises whole-word matching
     (`health_lint.py:186-187`).
   - One function with two matching rules would make alias counts and slug
     counts disagree.
   - The change only removes advisory findings. It can change results only
     for users who run `--health --strict` in CI.
   - Cost: about 30 minutes, inside S2.

   *Review refinement (for the spec):* define "word" for hyphenated
   identifiers. A plain `\b` boundary treats `-` as a break, so
   `origin-gate` would still match inside `pre-origin-gate` and `lint`
   inside `lint-rules`. The matcher counts letters, digits and hyphens as
   word characters on **both** sides, for slugs and avoid terms alike. The
   spec pins each case with a test (`pre-origin-gate`, `lint-rules`,
   `linter`, `origin checklist`, `origin check-in` do not match; `lint.`,
   `(origin-gate)`, a term wrapped across lines do). "Wrapped across lines"
   means a line break inside one paragraph counts as a space; matching
   never joins text across a list item, a heading or a blank line. One test:
   "origin" ending one bullet and "check" starting the next is not a use of
   the term.
7. **Should `avoid-format` findings be advisory or blocking?**
   *Resolved (owner accepted the recommendation, 2026-10-20):* advisory, in the two tiers that read the avoid map
   (`--prose` and `--health`), and fatal under `--strict`. This keeps the
   structural lint and the promote gate unchanged in this release, and it
   reports a malformed value exactly where it would otherwise be ignored.
   The alternative is to make it a structural rule, which would block
   promote. That costs nothing on existing wikis, which have no `avoid:`
   yet, but it changes the gate.

   *Review refinement (for the spec):* when `--prose` and `--health` run
   together, each malformed avoid list is reported once, not once per tier.

## Bet log

| Date | bet_status | Note |
|------|------------|------|
| 2026-10-20 | shaping | Pitch drafted from issue #28. Code read at main 8b5c8af. |
| 2026-10-20 | shaping → shaped | 5 scopes, 2w appetite, D trim-able after C3-4. 5 open questions for the owner. |
| 2026-10-20 | shaped | Revised after independent review. One `avoid:` form that survives memkernel, all other forms reported. Index format matched to the real layouts. Whole-word matching for new code. memkernel round trip stated in the ADR. D kept, with only its units extractor trim-able. Questions 1-3 resolved; 4-7 open. |
| 2026-10-20 | shaped | Second review: recommendations 4-7 accepted by the reviewer with three spec refinements (skip index `Avoid:` lines in prose and mention counts; hyphen counts as a word character on both sides; one report per malformed list across tiers). Scope and estimate unchanged; owner's answers pending. |
| 2026-10-20 | shaped | Owner accepted recommendations 4-7 with the review refinements (including the line-wrap rule). No open questions; next is the 0.5.0 spec and plan. |
| 2026-10-20 | shaped | Review of 816e952 (two P2): S5 now prints fact warnings from `propose` before `--promote`, with CLI tests for both paths (+~0.5h); `avoid` terms may not contain `"` or `\\` (memkernel escapes them and no reader decodes), refused as `avoid-format`; ADR compatibility claim narrowed and tested in this repo with memkernel's quoting rule. Appetite unchanged. |
| 2026-10-20 | shaped | Review of e2375c0 (one P2): single-quoted `avoid` values refused (`yaml_lite` decodes `''`, memkernel's reader does not, so `'it''s, ok'` read back as `it''s, ok`); the compatibility test now runs the full read → memkernel parse → render → read sequence with both memkernel rules copied as fixtures. Appetite unchanged. |
| 2026-10-20 | shaped | Review of c945ea1 (one P2): test contract split. Accepted values must survive the full round trip; unsupported values must be refused on the first read with no terms; no guarantee about unsupported values after memkernel, which can strip the refused syntax. |
| 2026-10-20 | shaped | External review against the whole post: the visual-artifacts half is out of scope by the origin (issue #28 takes only the STE tip). Recorded as a no-go, with the scope boundary stated in the Problem section and the fenced-code skip noted. No scope change. |
| 2026-10-20 | shaped → bet | Owner approved the pitch. Cycle 01 (wiki-studio's first); target release 0.5.0. Next: spec and plan in `specs/`. |
| 2026-10-30 | shipped | Shipped in 0.5.0 on 2026-10-20 (closes #28): writing rules in the prompts, the glossary `avoid:` key, `lint --prose` and the fact-preservation warnings. The pitch file was never updated after the bet; status corrected during the cooldown after cycle 03. |
