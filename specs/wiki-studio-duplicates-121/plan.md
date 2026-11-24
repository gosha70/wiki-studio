---
spec_mode: full
feature_id: wiki-studio-duplicates-121
risk_category: feature
justification: "A measurement whose value rests on a corpus extracted verbatim from two other repositories at pinned commits by a rule fixed before any page is read, labels made by a session with no candidate code and reviewed by the owner, and a bar frozen before any candidate runs; then, only with a winner, a new on-by-default kind in findings, the read surface every host and the nightly pass use, with a body-line convention that needs an ADR, a WikiPaths switch read from the environment, packaged schema text and the knowledge contract. A full spec pins the extraction rule to the character, the scorer's input rules, the bar, the per-phase truth rule, the main-session script runs between phases and the cut path before two unattended runs."
status: draft
date: 2026-11-23
collaboration_mode: single
origin:
  issue: 121
  urls:
    - https://github.com/gosha70/wiki-studio/blob/main/specs/pitches/121-near-duplicate-finding/pitch.md
    - https://github.com/gosha70/wiki-studio/issues/121
    - https://github.com/gosha70/wiki-studio/pull/132
    - https://github.com/gosha70/wiki-studio/pull/134
    - https://github.com/gosha70/wiki-studio/issues/54
    - https://github.com/gosha70/wiki-studio/blob/main/eval/patterns/report.md
    - https://github.com/gosha70/wiki-studio/blob/main/eval/patterns/issues/duplicate-title-summary-finding.md
  origin_claim: |
    Issue 121 (filed by the owner on 2026-11-22, no comments on 2026-11-23),
    drafted by the issue 54 study (eval/patterns/issues/duplicate-title-summary-finding.md)
    and shaped by the bet pitch specs/pitches/121-near-duplicate-finding/pitch.md
    (cycle 10, building; reviewer-approved in PR #132; bet and cycle start
    PR #134). Problem, as the pitch states it: two decision pages can record
    the same decision in different words and nothing tells a curator; the
    issue 54 study's signal (b), Jaccard of the title and Y-statement tokens
    at 0.25, found 2 of 3 true pairs with 1 false candidate, verdict "fail",
    on too few pairs to estimate anything. Issue 121 asks for an
    investigation before any code: re-run (b) on a larger corpus labelled
    independently with the labels frozen first, settle how a decision page
    and its incident record are labelled, and only then decide whether a
    model-free findings kind is worth its false alarms. The owner's preferred
    shape for the kind (issue 121, 2026-11-19): on by default, silence one
    pair with a body line in the conflict callout's form, an optional switch
    per wiki, every finding ends with the exact line to silence it, findings
    only. Owner decisions (2026-11-23): D1 4w, the full project, S4-S6 only
    with a winner; D2 (against the default) the corpus is code-copilot-team's
    routing and pi spec decisions at fd05256 and memkernel's spec decisions
    at 8279d76, about 215 pages, extracted verbatim, everything the issue 54
    corpus was drawn from or overlaps excluded, a fixed extension order;
    D3 one labelling session with no candidate code, grouping by question,
    the owner reviews every true and companion label plus 20 seeded false
    pairs (routing 8, pi 1, memkernel 11); D4 at least 8 true pairs else not
    testable, find at least three quarters rounded up, false not outnumbering
    true, candidates B0 and B1 at 0.25, fewest false wins, a tie to B0; D5 a
    companion disposition counted false, supersedes counted true, the issue
    54 label frozen; D6 same page type only; D7 findings only, not lint
    --health; D8 WIKI_STUDIO_DUPLICATE_CHECK=off read into WikiPaths; D9
    every pair scored, a cross pair unrelated unless listed from one summary
    pass with one line per group and one per ungrouped page; D10 (against
    the reviewer's recommendation) every content page type compared with its
    own type, and the report, contract and documents say only decision pages
    were measured. Settled S-1 to S-9: the related line is a body line with
    ADR-0006; model-free; additive within findings_version 1; no double
    report with conflicts; a finding never blocks; every finding ends with
    the related line; the issue 54 study stays frozen; 0.11.0 is tagged and
    released before S4 touches src/; script runs are main-session steps and
    the evidence PR is opened by hand. The owner's release rule (2026-11-23):
    no release step in any build run; the owner alone decides when a version
    is released.
---

# Plan: a near-duplicate finding from titles and summaries (issue 121)

The bet pitch `specs/pitches/121-near-duplicate-finding/pitch.md` is the
shaping record (reviewer-approved in PR #132; owner decisions D1-D10 on
23 November 2026; bet and cycle 10 start PR #134, which may not be merged yet:
the pitch file in the working tree is the source). Its "Findings from the code"
were re-checked on the branch `specs/bet-121-cycle-10` at 7d3234c (main at
b18d852, 0.11.0 merged and untagged, plus the two pitch commits) and hold, with
the current line numbers in the spec's design references. Findings 7-13 rest on
the code-copilot-team and memkernel checkouts, which this writing session did
not re-count; the extraction run re-counts them by rule (FR-011 reports any
difference). Issue 121's body was not re-fetched (no shell in the writing
session); its words are taken from the pitch and from the text it was filed
from, `eval/patterns/issues/duplicate-title-summary-finding.md`, and the
origin-alignment record at approval reads the issue itself. Facts found while
re-checking that shape the spec:

1. **Lint's required keys.** `REQUIRED_KEYS` (`schema/__init__.py` 115) is
   `page_type`, `slug`, `title`, `status`, `last_reviewed`; lint (342-373)
   also requires the slug to equal the file stem, `page_type` to match its
   directory and `sources:` for a decision page, and checks no sections. The
   pitch's page frontmatter lists four of these; FR-006 adds `status` and
   `last_reviewed`, and FR-012's temporary wiki puts each page under
   `decisions/<slug>.md`.
2. **YAML quoting.** `yaml_lite.unquote` (123-132) unescapes `''` inside a
   single-quoted scalar and does not unescape a double-quoted one, so titles
   are written single-quoted (FR-006).
3. **The scorer's paragraph rule** (`eval/patterns/duplicates.py` 85-137): the
   body is the text after the frontmatter; `## Decision` is found by
   `^## Decision[ \t]*$`; blocks are split on blank lines and skipped when they
   start with `#`, `>`, `|`, three backticks, `- `, `* `, `+ ` or match
   `^\d+[.)]\s`, or consist only of dashes; an empty string when `## Decision`
   holds nothing else. Three tildes are not skipped (FR-006 step 2 notes it).
   `_b_candidates` (191-198) compares with float division; FR-018 states the
   equivalent integer comparison.
4. **The findings scope and kind order.** `FINDING_KINDS` (`findings.py`
   93-108) ends with the two revision kinds 0.11.0 added; the conflict loop
   (291-297) reads the whole review set and keeps a finding that touches an
   in-scope page, listing only its in-scope pages. `possible-duplicate` follows
   that rule and is appended last (O11).
5. **Pinned tests.** `tests/test_findings.py` pins `api.findings`' parameters
   (205), the counts key set (172) and an every-kind fixture (112-132), so the
   fixture must produce the new kind (FR-035). No top-level result key is
   added, so `mcp_adapter/trace.py`'s `TOOL_RESULT_KEYS` stays as it is.
6. **Nightly drafts only two kinds** (`nightly.py` 47, 640, 742-749); every
   other kind lands in the report's curator list, so `nightly.py` needs no
   change for the kind to be listed and not drafted.
7. **The conflict scan's helpers** (`conflicts.py` `_body_lines` 68,
   `_marker_target` 80, `_resolve_target` 89, `scan_callouts` 105) are exactly
   what the related-line parser and the conflict skip need; its docstring
   (20) says `findings.py` is its only importer, which FR-029 updates.
8. **The switch's pattern.** `WIKI_STUDIO_GIT_CALL_LIMIT` (`paths.py` 38, 61,
   68, 292, 304, 341, 388-396) shows how a variable becomes a `WikiPaths`
   field through `for_root` and `resolve`, with `ValueError` on a bad value
   (FR-030, O3).
9. **Page types.** `page-types.md` defines `concept`, `workflow`, `incident`,
   `decision`, `playbook`, `glossary`, `open-question`, `index`, `overview`
   and `log`; D10 names five of them (FR-032, O5).
10. **The release state.** `CHANGELOG.md` has an empty `[Unreleased]` (7)
    above an undated `[0.11.0]`; `pyproject.toml` reads 0.11.0. 0.11.0 is
    merged and untagged; the pitch requires it tagged and released before
    anything under `src/` changes.
11. **The driver's phase diff.** `auto-build-loop.sh` fixes a phase's review
    diff base at HEAD the first time the phase starts (5188-5196), so a
    main-session commit made at a pause is outside the next phase's review
    diff; it is reviewed in the evidence PR. `CCT_REVIEW_DIFF_MAX_LINES` in
    the environment overrides `review.diff_max_lines` (829-847).
12. **`tests/__init__.py` exists**, so US2's test can import the six fixed
    items' raw texts from US1's test module.
13. **The disputed issue 54 pair** is the background pair
    `decisions/never-bypass-a-git-lock-with-an-alternate-index.md` /
    `incidents/git-safety-bypasses.md` (`eval/patterns/labels.json` 551-553).

## Departures from the pitch

Each is recorded so the origin-alignment record at approval can cite it.

1. **S6 is not in the build** (the owner's release rule, 2026-11-23). No phase
   bumps the version, dates or moves CHANGELOG entries, edits
   `docs/compatibility.md`, tags or publishes; user-visible changes accumulate
   under `[Unreleased]`. Release preparation for a version that carries the
   kind (the pitch's 0.12.0) happens only on the owner's explicit word,
   outside both runs (FR-040).
2. **Run 2 waits for the owner's 0.11.0 release.** The pitch's precondition
   stands (S4 starts only after 0.11.0 is tagged and released); it is an
   owner-run step and a gate on starting run 2, not an action any session
   takes (FR-027; owner step 6). The evidence (run 1) does not wait.
3. **Phases are cut around the main-session script runs** (lesson 1 of
   cycle 09). S1 is US1 (the extraction code) and US2 (the corpus checks) with
   the extraction run between them; S2 is US3 (the labels) and US4 (the
   freeze) with the extension rule, the review sample and the owner's review
   between them; S3 is US5 (the scorer) and US6 (the report) with the scoring
   run between them; S4 is US7 (the package rule) and US8 (the kind), each
   reviewed on one concern.
4. **The six per-form tests run twice**: in US1 on the raw items written out
   in the test, through extract.py's page builder, and in US2 on the extracted
   pages (FR-009, FR-012), so a rule error is caught before the run.
5. **The lint check is a CI test** on a temporary wiki (FR-012) rather than a
   one-off `wiki-studio lint` run; violations that come from an item's own
   text are listed in the README, never fixed (O2).
6. **The page form is fixed to the character**: `status: stable`,
   `last_reviewed` the pin's commit date, a single-quoted title, the slug
   `<cct|mk>-<spec>-<plan|spec>-<nn>`, no H1 line (facts 1-2; O8).
7. **The freeze pins `corpus.json`, and every page through it**, plus
   `review-sample.json` and the README, instead of one constant per page
   (FR-019): the same guarantee with a reviewable diff.
8. **The review sample is drawn by a committed, seeded script** (FR-008):
   base families only, the largest-remainder split that gives 8/1/11, drawn
   once from the labelling commit's labels and never re-drawn (O4).
9. **The threshold is compared in integers** (`4 * shared >= union`),
   equivalent to the study's 0.25 and free of rounding (FR-018).
10. **Results list candidate pairs one string per pair** (O9) and carry each
    true pair's score under both candidates and the false candidates per 100
    pages, so a post-hoc reading needs no re-run.
11. **extract.py drops inherited `GIT_` variables and refuses network
    protocols** (the 0.11.0 hardening, FR-002); the pitch says only "no shell,
    no network".
12. **The closing-keyword item is found by a pattern at extraction** and listed
    by id (FR-007), rather than hard-coded from the shaper's reading, so a
    second such item could not slip in.
13. **The extension procedure runs outside the driver**: an added family's
    extraction is a main-session commit and its labelling a fresh session
    started by hand under US3's instructions (FR-016).
14. **The title and label rules are written to the character** (FR-005,
    FR-006 step 1: the identifier pattern, the separator after a bold label,
    the first-sentence fallback), lesson 5 of cycle 09.
15. **CLAUDE.md layout lines land with their code** (US1 for
    `eval/duplicates/`, US7 for `duplicates.py`), not in S5.
16. **`possible-duplicate` is appended last** in `FINDING_KINDS`, after the
    revision kinds; "after the conflict kinds" still holds and no kind moves
    (O11).
17. **`conflicts.py`'s helpers are reused** by the related-line parser, and
    its docstring's "only importer" sentence is updated (FR-029); the pitch
    places the parser in `duplicates.py` without saying how.
18. **Existing tests are edited** where their fixtures now yield the
    on-by-default kind, to expect it, never by switching it off (FR-035).
19. **The 500-page time bound has a formula now** (O6); the amendment fills
    its inputs from `results/timing.json`.
20. **The kind's CHANGELOG entry lands with the kind** (US8), with the
    measured-only sentence; S5's documents follow in US9.
21. **With "none", there is no run 2 and no CHANGELOG entry**: the evidence
    under `eval/` is not user-visible; the amendment records the outcome and
    issue 121 stays open (FR-027).
22. **The secondary re-score cross-checks the study**: B0 as recorded must
    reproduce the frozen issue 54 signal b counts (FR-021).
23. **B1's identifier rule is broader than the pitch's letter list** (owner,
    2026-11-23, after the external review of this bundle). The pitch's rule
    (6) dropped only `d`, `s`, `a`, `r`, `us`, `fr-`, `nfr-` and `adr-`
    numbers; counted over the base decision sections, it dropped about 170
    identifier-shaped tokens and kept about 211 others (`e1`-`e7`, `g1`-`g5`,
    `o1`-`o4`, `t1`-`t7`, `h1`-`h3`, `l1`-`l4` and more) that unrelated specs
    share. Rule (6) is now one letter and one or two digits, or a `us`, `fr-`,
    `nfr-` or `adr-` number: about 334 dropped, content words such as
    `sha256`, `bm25` and `utf-8` kept. Settled before the freeze (FR-018,
    FR-022).

Close target: issue 121, by run 2's merge (`pr.closes: [121]`) only when the
kind ships; otherwise it stays open with the measurement as its evidence
(FR-039). No other issue is closed; the pitch PR (#132), the bet PR (#134), this
spec PR, its amendment and the evidence PR use no closing keyword.

## Architecture decisions

- **ADR-1: Extract, label, freeze, then measure.** The corpus is produced by a
  rule fixed before any page is read; labels are made without candidate code
  and reviewed by the owner; the protocol and the frozen test land before the
  scorer exists; the build implements only the frozen winner.
- **ADR-2: Data is produced by scripts the main session runs.** Driver phases
  write code, prose and tests; every committed data file (corpus, review
  sample, results) is produced by a script run at a pause and reproduced or
  pinned by CI.
- **ADR-3: The package reimplements, never imports, the study.** The package
  cannot import `eval/`; it reimplements the paragraph rule and B1's
  normalisation and imports `_tokenise`; a replay test binds it to the frozen
  results.
- **ADR-4: The silence line is a body line in the conflict callout's form**,
  parsed by the same helpers, registered by ADR-0006; no schema change.
- **ADR-5: Each phase is true on its own diff.** Prose and documents move only
  when what they describe exists; nothing is versioned.

## Files

| File | Phase | Change |
|---|---|---|
| `eval/duplicates/__init__.py`, `README.md` (new) | US1, US2, US3, US4 | Opening and corpus rule (US1); counts (US2); labelling rule (US3); protocol (US4) |
| `eval/duplicates/extract.py`, `sample.py` (new) | US1 | FR-002-FR-008 |
| `CLAUDE.md` | US1, US7 | Layout lines for `eval/duplicates/` and `duplicates.py` |
| `tests/test_duplicates_extract.py` (new) | US1 | FR-009 |
| `eval/duplicates/corpus/**`, `corpus.json` (new) | pause 1 (main session) | FR-010, as written |
| `tests/test_duplicates_corpus.py` (new) | US2 | FR-012 |
| `eval/duplicates/labels.json` (new) | US3 (and pause 2 for extensions and owner changes) | FR-013-FR-015 |
| `tests/test_duplicates_labels.py` (new) | US3 | FR-017 |
| `eval/duplicates/review-sample.json` (new) | pause 2 (main session) | FR-008 |
| `eval/duplicates/protocol.json` (new) | US4 | FR-018 |
| `tests/test_duplicates_frozen.py` (new) | US4 | FR-019; never edited after |
| `eval/duplicates/candidates.py` (new) | US5 | FR-020, FR-021 |
| `tests/test_duplicates_eval.py` (new) | US5 | FR-022 |
| `eval/duplicates/results/candidates.json`, `secondary.json`, `timing.json` (new) | pause 3 (main session) | FR-023, as written |
| `eval/duplicates/report.md` (new) | US6 | FR-024 |
| `tests/test_duplicates_results.py` (new) | US6 | FR-025 |
| `src/wiki_studio/duplicates.py` (new) | US7, US8 | Rule, parser (US7); `duplicate_pairs` (US8) |
| `src/wiki_studio/paths.py` | US7 | The switch |
| `src/wiki_studio/conflicts.py` | US7 | One docstring sentence |
| `tests/test_duplicates_rule.py` (new) | US7 | FR-031 |
| `src/wiki_studio/findings.py`, `api.py`, `cli.py` | US8 | The kind; docstring and help |
| `tests/test_possible_duplicate.py` (new); `tests/test_findings.py` and any test whose fixture now yields the kind | US8 | FR-035 |
| `docs/adr/0006-related-line.md` (new) | US9 | FR-036 |
| `src/wiki_studio/schema/citation-rules.md`, `docs/knowledge-contract.md`, `README.md`, `docs/patterns.md` | US9 | FR-037 |
| `CHANGELOG.md` | US8, US9 | `[Unreleased]` only |

## Interfaces

```python
# eval/duplicates — run by the main session at pauses, rerun or pinned by CI
#   python -m eval.duplicates.extract [--code-copilot-team PATH] [--memkernel PATH] [--extend N] [--cut-1] [--out DIR]
#   python -m eval.duplicates.sample [--out PATH]
#   python -m eval.duplicates.candidates [--out-dir DIR]

# src/wiki_studio/paths.py
ENV_DUPLICATE_CHECK = "WIKI_STUDIO_DUPLICATE_CHECK"
# WikiPaths gains: duplicate_check: bool = True   (for_root/resolve: duplicate_check: bool | None = None)

# src/wiki_studio/duplicates.py
RELATED_MARKER = "[!related]"
RELATED_MARKER_RE: re.Pattern[str]
RELATED_LINE_TEXT = "Not a duplicate of"
COMPARED_PAGE_TYPES = ("concept", "workflow", "incident", "playbook", "decision")
# B1 only: the link and URL patterns, the digit, hex and identifier patterns, TEMPLATE_WORDS (equal to protocol.json)

def first_paragraph(text: str) -> str: ...
def page_tokens(text: str) -> frozenset[str]: ...                     # the winner's token set
def similar(left: frozenset[str], right: frozenset[str]) -> tuple[int, int] | None: ...  # (shared, union) when 4*shared >= union > 0
def related_targets(page: str, text: str, wiki_dir: Path) -> set[str]: ...

@dataclass(frozen=True)
class DuplicatePair:
    left: str; right: str; shared: int; union: int; related_line: str

def duplicate_pairs(paths: WikiPaths) -> list[DuplicatePair]: ...    # US8: whole review set, same type, skips applied

# src/wiki_studio/findings.py
KIND_POSSIBLE_DUPLICATE = "possible-duplicate"                       # appended last to FINDING_KINDS
```

## Phases (one auto-build phase per `## US<n>:` group of tasks.md)

Every phase's gate is the full gate of the spec's Constraints (the driver's
`test.command`); the named tests are the ones each phase adds or must keep
green on its own files.

| Phase | Scope | Run | FRs | What | Phase tests | Pause after |
|---|---|---|---|---|---|---|
| US1 | S1 | 1 | FR-001-FR-009 | extract.py, sample.py, README corpus rule, six fixed items | `tests/test_duplicates_extract.py` | **yes**: the extraction run (FR-010) |
| US2 | S1 | 1 | FR-011-FR-012 | README counts; corpus tests, lint on a temporary wiki | `tests/test_duplicates_corpus.py`, `tests/test_duplicates_extract.py` | no |
| US3 | S2 | 1 | FR-013-FR-017 | labels by question, D9 summary and cross pairs | `tests/test_duplicates_labels.py` | **yes**: extension rule, review sample, owner's review |
| US4 | S2 | 1 | FR-018-FR-019 | protocol.json, the freeze test | `tests/test_duplicates_frozen.py`, `tests/test_duplicates_labels.py`, `tests/test_duplicates_corpus.py` | no |
| US5 | S3 | 1 | FR-020-FR-022 | candidates.py on synthetic inputs | `tests/test_duplicates_eval.py` | **yes**: the scoring run (FR-023) |
| US6 | S3 | 1 | FR-024-FR-026 | report.md, results tests, scope audit | `tests/test_duplicates_results.py`, `tests/test_duplicates_frozen.py` | **yes**: run 1 ends; evidence PR by hand |
| US7 | S4 | 2 | FR-027-FR-031 | duplicates.py rule, related-line parser, switch | `tests/test_duplicates_rule.py`, `tests/test_package_boundaries.py` | no |
| US8 | S4 | 2 | FR-032-FR-035 | `possible-duplicate` in findings, surfaces, CHANGELOG | `tests/test_possible_duplicate.py`, `tests/test_findings.py`, `tests/test_conflict_callouts.py`, `tests/test_mcp_adapter.py` | no |
| US9 | S5 | 2 | FR-036-FR-040 | ADR-0006, citation-rules, contract, README, patterns; audit | `tests/test_schema_fingerprint.py`, `tests/test_frozen_runs.py`, FR-039's audit | run 2 ends with the driver's PR |

Order follows the pitch: S1, S2, S3 (the evidence PR), the spec amendment, then
S4 and S5 only with a winner, and S6 only on the owner's word outside the runs.

## Runs, pauses and script runs (the lessons of cycle 09, built in)

1. **Sessions cannot run Python** (lesson 1). No driver phase runs a script
   that writes committed data. The scripts run at milestone pauses in the main
   session (or by the owner), and the main session commits their output as its
   own commit: the extraction after US1 (FR-010), any extension extraction and
   the review sample after US3 (FR-016, FR-008), the scoring after US5
   (FR-023). Each driver phase's tests pass on files that phase writes or that
   an earlier commit holds: US1's tests run on inputs written in the test; US2
   checks the extraction commit; US4's freeze test pins files already
   committed (its hashes come from a shell `shasum -a 256`, and the driver's
   gate is the first run of it); US5's tests use synthetic inputs; US6 checks
   the results commit. The tasks' milestone notes say the same at each pause.
2. **The driver cannot open a PR that closes nothing** (lesson 2): it falls
   back to `plan.md`'s origin issue. Run 1 therefore ends at the milestone
   after US6 with `max_phases: 6`, and is never resumed; the evidence PR is
   opened by hand from the main session after `scripts/pre-pr-check.sh`, and
   `gh pr view <n> --json closingIssuesReferences` must list nothing. If the
   driver opens a PR at the end of run 1 anyway, the owner closes it unmerged.
3. **`--resume` ignores `--start-phase`** (lesson 3). Run 2 is a fresh run:
   run 1's ledger (`.cct/auto-build/wiki-studio-duplicates-121/`) is moved
   aside first, and run 2 starts with `--start-phase 7` on a new branch from
   `main` after the amendment merges and after the 0.11.0 release. **A
   stopped run 2 is never resumed with a plain `--resume`**: run 2's ledger
   holds no record of steps 1-6, so the loop would start at step 1 and
   re-run US1 on the run 2 branch (cycle 09's failure). Either set the ledger
   aside and start a fresh run with `--start-phase <the stopped step>` on the
   same branch (tested in cycle 09; a fresh run checks out the existing
   branch as it is), or `--resume --start-phase <the stopped step>`
   (untested).
4. **The owner's shell sets `CCT_REVIEW_DIFF_MAX_LINES=4000`** (lesson 4),
   which overrides `review.diff_max_lines`. Both runs and every resume start
   with `env -u CCT_REVIEW_DIFF_MAX_LINES`, and `automation.json` carries
   `review.diff_max_lines: 8000`. Size estimate: the extraction commit is about
   9,000-10,000 lines (about 215 pages at about 28 lines each, 10 of frontmatter
   and the item's text, about 6,000 lines; `corpus.json` at about 14 lines per
   entry, about 3,000), but it is a main-session commit outside every phase's
   review diff (fact 11) and is reviewed in the evidence PR. The largest
   driver phase is US3: `labels.json` at about 60 groups, 300-400 in-group
   pairs at about 9 lines each and a summary of about 215 lines at about 5 lines
   each, about 3,000-5,000 lines, plus the README section and the test, so
   4,000-5,500 lines in all; 6,000 would be tight and 8,000 covers it. US1 is
   about 1,500 lines; US7-US9 are each well under 3,000.
5. **The scorer's input rules are exact before the freeze** (lesson 5): the
   body rule (FR-006: the label removed with its separator, one list marker
   and the indentation removed per line, the ADR lines moved without labels,
   no word changed), the title rule to the character (FR-005), the per-form
   tests checking that the scorer's paragraph equals **"the first paragraph of
   each item's text after its label"** (an item with several paragraphs is
   read only for its first) (FR-009, FR-012), and the README's count and list
   of empty first paragraphs (FR-011), allowed before the freeze because it
   compares no pages.
6. **Wall time lives in `results/timing.json`** (lesson 6), which CI checks
   for keys only; `results/candidates.json` and `results/secondary.json` are
   deterministic and CI reproduces them byte for byte (FR-021, FR-025).
7. **The amendment sets the winner or "none"; a flaw found after the freeze is
   post hoc** (lesson 7): a non-binding `post_hoc` block computed by the scorer
   and checked by CI, and a report section, never a change to a label, the
   bar or the winner line (FR-026). Shipping anything other than the frozen
   winner would be the owner's decision at the amendment, recorded as a
   departure with a replay against the post-hoc figures, as 0.11.0's departure
   23 did; it is not planned.

## Owner-run steps

1. **Before run 1**: answer O1-O12; approve this bundle; in the approval PR
   write run 1's `automation.json` and the origin-alignment record. Confirm the
   sibling checkouts `../code-copilot-team` and `../memkernel` hold `fd05256`
   and `8279d76` (they are read by commit, so later checkout moves do not
   matter) and that the build session may run read-only git there (US1 reads
   the six fixed items with `git show`); if not, the main session supplies the
   six raw section texts at the start of US1.
2. **Pause after US1** (end of week 1: trigger 1): run the extraction (FR-010),
   with `--cut-1` only if the owner invokes cut 1; commit it as its own commit;
   check both checkouts are unchanged; add `approved-by:` under the checkpoint;
   resume with `env -u CCT_REVIEW_DIFF_MAX_LINES`.
3. **Pause after US3**: the extension rule if `true_pairs` is below 8 (an
   extraction commit, then a hand-started labelling session's commit, per added
   family); run `sample.py` and commit `review-sample.json`; review every true
   and `companion` label, every listed cross pair and the 20 sampled false
   pairs, changing any label by a commit on the branch; check trigger 2 (end of
   week 2); `approved-by:`; resume.
4. **Pause after US5**: run the scorer (FR-023), commit the three results
   files as their own commit; `approved-by:`; resume.
5. **Pause after US6**: do not resume run 1. Run `scripts/pre-pr-check.sh`, open
   the evidence PR by hand (body names issue 121 without a closing keyword),
   confirm `closingIssuesReferences` is empty, send it to review, add the
   `reviewed` label after the review of its head, merge with a merge commit.
   Then the spec amendment: FR-027's winner (`B0`, `B1` or `none`), the
   triggers that fired, FR-035's time bound from `results/timing.json`,
   re-approval, and (with a winner) run 2's `automation.json`. With `none` the
   cycle ends here (trigger 3).
6. **Release 0.11.0** (the owner's own release, a precondition of run 2, not
   part of this bundle): the release PR, the tag, the release page with the
   workflow's wheel and sdist. Run 2 does not start before it.
7. **Run 2** (with a winner): `git fetch --tags` so the 0.11.0 tag check
   sees the tag on GitHub; move run 1's ledger aside; start fresh with
   `--start-phase 7` and `env -u CCT_REVIEW_DIFF_MAX_LINES`; if run 2 stops
   partway, restart it as plan item 3 says (a fresh run with `--start-phase
   <the stopped step>`, or `--resume --start-phase <step>`), never a plain
   `--resume`; trigger 4 at the
   middle of week 4 is the owner's escalation (FR-039). After the run, re-run
   the gate on the branch head before trusting `landed`, check no phase was
   bypassed without its record, and confirm an open PR exists on the branch tip
   with the closing line for issue 121; review and label.
8. **After the merge**: any release carrying the kind only on the owner's
   explicit word, outside the runs (FR-040). The hill chart is updated by hand.

## Unattended run

The owner writes the configurations at approval. This plan assumes 0.11.0's
shape (profile `pr`, the DeepSeek correctness reviewer gating, max 3 rounds per
phase, two fix sessions per phase, the gate of the spec's Constraints,
`merge.enabled: false`, `merge.method: "merge"`), with:

- **Run 1**: branch `feature/wiki-studio-duplicates-121-evidence` from `main`
  after this bundle's approval merges; phases from `tasks.md`,
  `milestone_every: 0`, `max_phases: 6` (the `<!-- milestone -->` markers pause
  after US1, US3, US5 and US6); `build.max_turns: 200` (the labelling phase
  reads every page of three families; O10); `review.diff_max_lines: 8000`; no
  `pr.closes`; started with
  `env -u CCT_REVIEW_DIFF_MAX_LINES CCT_PROJECT_DIR=$PWD ../code-copilot-team/scripts/auto-build-loop.sh wiki-studio-duplicates-121`
  and resumed at each pause with the same prefix and `--resume`.
- **Run 2** (written by the amendment, only with a winner): branch
  `feature/wiki-studio-duplicates-121` from `main`; `max_phases: 9`,
  started fresh with `--start-phase 7`; `pr.closes: [121]`; the build PR's
  title; `review.diff_max_lines: 8000`.

## Test strategy

- **Rule before data** (US1): every form, the title rule and each body step on
  inputs written in the test; the six fixed items through the page builder;
  git reading on a temporary repository with an injected `GIT_DIR`.
- **Data checked against the rule** (US2): every page pinned to `corpus.json`;
  input counts recomputed; the six pages byte-equal to the builder; exclusions
  absent; structural lint on a temporary wiki; the closing-keyword scan.
- **Labels by structure** (US3): every in-group pair labelled once, the
  within-family default, the summary's shape, cross pairs' scopes, the true
  count; the sample's shape.
- **The freeze** (US4): sha256 pins in a test never edited after the phase,
  and the history audit of US6.
- **The scorer by construction** (US5): each normalisation rule alone, the
  threshold at exactly one quarter, every bar condition at its edge, selection
  and the tie, the refusal on changed inputs, no writes outside `--out-dir`.
- **Reproduction** (US6): the committed results rerun byte for byte; the
  secondary re-score against the frozen issue 54 counts; one winner line.
- **Replay** (US7): the package rule over the frozen corpus equals the
  winner's committed pairs; the package paragraph and tokens equal eval's on
  every corpus page and every issue 54 fixture page.
- **Behaviour and neighbours** (US8): the related line round-trip from the
  description; page-type rules; skips; scope; the switch; strict lint, review
  state, `approve`, `find`, nightly and MCP unchanged or listing the kind; the
  500-page bound; read-only snapshot.
- **Shown commands** (US1-US6, US9): every `python -m eval.duplicates.…` line
  parses; changed CLI and docs lines get `--help` or parse checks.
- **Regression**: coverage at or above 92 percent; existing tests edited only
  as FR-035 lists.

## Risks

- **Too few true pairs.** Three families of extracted spec decisions may hold
  only a handful of duplicates. Mitigation: the minimum of 8, the fixed
  extension order, "not testable" as a stated outcome that ends the cycle
  early with the evidence published.
- **Family jargon.** Routing pages share `routing`, `profile`, `tier`; memkernel
  pages share `memory`, `recall`, `store`; Jaccard on short texts may flag many
  within-family pairs, so both candidates may fail the ratio rule. Mitigation:
  none in the candidates; that is what the measurement is for. A stop list per
  wiki, IDF weighting or a tuned threshold is a new bet.
- **The labeller learning the signal.** Mitigation: grouping by question with
  reasons naming it; no candidate code and no script run in the labelling
  phase (the sandbox cannot run Python at all); the owner's review of every
  true and companion label and a seeded false sample.
- **The labelling phase's size.** About 215 pages in one session may exhaust
  its turns or context. Mitigation: `build.max_turns: 200` (O10) and the
  driver's one continuation; the session may read a family's pages with one
  read-only shell command; if it still stops, the phase's fix session resumes
  the remaining families under the same instructions.
- **Extraction edge cases** (an H3 item without a `**Decision**:` line, a bold
  paragraph that heads a list, an amendment whose label is only an identifier
  and a date). Mitigation: precedence and fallbacks fixed in US1, items kept as
  written and listed, the rule never tuned after pages are read.
- **The sessions cannot read the sibling checkouts.** Mitigation: owner step 1
  confirms read-only git access; the main session can supply the six raw
  section texts; the extraction itself is a main-session run.
- **The driver opens a PR at the end of run 1.** Mitigation: the milestone
  after US6, `max_phases: 6`, never resuming; any such PR is closed unmerged.
- **The on-by-default kind fires in existing test fixtures.** Mitigation:
  FR-035 edits them to expect it; US8's checkpoint runs the whole suite.
- **The pairwise loop is slow on a large wiki.** Mitigation: the 500-page
  bound; a token index that skips pairs with no shared token, identical
  results, only if needed.
- **A third review round on one PR or phase.** Escalation to the owner, per
  the pitch's circuit breaker.

## Success criteria

1. The evidence PR publishes the corpus, the frozen labels and protocol, the
   scores of B0 and B1 and exactly one winner line, whatever they show; it
   changes only FR-026's allowed paths, nothing under `src/`, and
   `tests/test_duplicates_frozen.py` is touched by exactly one commit, US4's.
2. Every committed data file was produced by a script the main session ran
   at a pause and is reproduced (results) or pinned (corpus, labels, sample) by
   CI.
3. With a winner and after the 0.11.0 release, `possible-duplicate` reports
   exactly the frozen winner's pairs on the corpus, ends every finding with a
   related line that silences it, skips superseded, conflict-joined and
   related-joined pairs, and turns off with `WIKI_STUDIO_DUPLICATE_CHECK=off`;
   every place that documents it says only decision pages were measured.
4. No new exit code, frontmatter key, page type, capability, MCP tool or
   dependency; `findings_version` 1; `_tokenise` unchanged; `lint --health
   --strict` unchanged; gate green at 92 percent; no version bump, no
   CHANGELOG version section, no tag from any run.

## Open items for the spec review

Draft defaults; the spec is written on them. The owner's answers are recorded
here before approval.

**Owner's answers (2026-11-23):** every item takes its default. O1, two runs with four pauses in run 1, and O2, a lint violation caused by an item's own text is listed in the README and never fixed, were asked directly; the owner accepted the defaults of O3-O12 together.

1. **O1 — Phase structure.** Default: two runs from this bundle; run 1 is
   US1-US6 with pauses after US1, US3, US5 and US6 (the script runs and the
   owner's review between phases), ending with the evidence PR opened by hand;
   run 2 is US7-US9, fresh, only with a winner and after the 0.11.0 release.
   Alternative: fold US2 into the pause after US1 (the main session writes the
   corpus checks), one phase fewer but checks the driver's reviewer never sees.
2. **O2 — Lint violations from an item's own text** (a relative link in a spec
   that does not resolve in the temporary wiki). Default: listed in the README
   by page, never fixed; the test allows exactly those. Alternative: count
   such pages out of the corpus (changes the corpus by the lint result).
3. **O3 — The switch's values.** Default: unset or empty means on; `off` or
   `on` in any case after stripping; anything else raises `ValueError` (exit
   1), as an invalid lock timeout or call limit does. Alternative: anything
   but `off` means on (silently accepts a typo such as `of`).
4. **O4 — The review sample.** Default: the 20 false pairs are drawn from the
   three base families only, split by the largest-remainder method on
   within-family pair counts (which gives 8/1/11, or 10/0/10 under cut 1 with
   pi dropped), seed 121, drawn once from the labelling commit before any owner
   change. Alternative: include extension families in the split.
5. **O5 — Page types compared.** Default: exactly the five D10 names
   (`concept`, `workflow`, `incident`, `playbook`, `decision`); `glossary` and
   `open-question` pages never. Alternative: every type except `index`,
   `overview` and `log`.
6. **O6 — The 500-page time bound.** Default: `max(10, ceil(10 * t * 124750 /
   P))` seconds, `t` the winner's recorded scoring time on the corpus and `P`
   its recorded pair count (124,750 is the pair count of 500 pages), recomputed
   by the test from `results/timing.json`. Alternative: a fixed bound set by
   the amendment.
7. **O7 — The related line in a finding.** Default: `> [!related] Not a
   duplicate of [<title>](<link>)`, added to the first page of the sorted
   pair, `<title>` the second page's title with `[` and `]` removed (its file
   stem when it has none), `<link>` relative from the first page's directory.
   Alternative: always the wiki-root-relative form `../<dir>/<file>.md`.
8. **O8 — The corpus page form.** Default: `status: stable`, `last_reviewed`
   the pin's commit date, a single-quoted title, slug
   `<cct|mk>-<spec>-<plan|spec>-<nn>`, no H1 line, `## Decision` (or the ADR
   sections) only. Alternative: an H1 with the title (skipped by the scorer, so
   it changes no score, but it writes the title twice).
9. **O9 — The results' pair lists.** Default: `candidate_pairs` and
   `true_pair_scores` as one string per pair inside `candidates.json`, so the
   file stays reviewable even if a candidate flags thousands of pairs.
   Alternative: one JSON object per pair (several lines each).
10. **O10 — Run 1's session and review limits.** Default: `build.max_turns:
    200`, `review.diff_max_lines: 8000`, both runs started with
    `env -u CCT_REVIEW_DIFF_MAX_LINES`. Alternative: 0.11.0's 120 turns and
    6,000 lines.
11. **O11 — The kind's place in `FINDING_KINDS`.** Default: appended last,
    after `source-revision-changed`; no kind moves. Alternative: inserted right
    after the conflict kinds (reorders the revision kinds in `counts` and the
    text output).
12. **O12 — The title identifier pattern and the six fixed items.** Default:
    FR-005's pattern as written, and the six items chosen by the US1 session
    from the pinned specs (one per form in each repository, none quoting
    closing-keyword text) and named in the test and the README. Alternative:
    the owner names the six items, or adjusts the pattern, before approval.
