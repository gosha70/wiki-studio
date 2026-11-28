---
spec_mode: full
feature_id: wiki-studio-duplicate-audit-121
risk_category: feature
justification: "A measurement whose value rests on a protocol, a stop rule, a restatement rule and a bar frozen and signed off before any score, a development stage that can end the bet, a fresh held-out set extracted at pinned commits and labelled by an isolated session, and four main-session script runs between phases; then, only with a pass, an on-by-default findings kind run at session start and over MCP, a new findings object, two additive SearchIndex methods, a body-line convention needing ADR-0006, and a change to WikiPaths.for_root that makes a mistyped switch fail every library caller, memkernel included. A full spec pins each rule, the per-phase truth rule, the hand-opened PRs that close nothing and the cut path before two unattended runs."
status: approved
date: 2026-11-27
collaboration_mode: single
origin:
  issue: 121
  urls:
    - https://github.com/gosha70/wiki-studio/issues/121
    - https://github.com/gosha70/wiki-studio/blob/main/specs/pitches/121-duplicate-audit/pitch.md
    - https://github.com/gosha70/wiki-studio/pull/151
    - https://github.com/gosha70/wiki-studio/pull/152
    - https://github.com/gosha70/wiki-studio/blob/main/eval/duplicates/report.md
    - https://github.com/gosha70/wiki-studio/blob/main/eval/similar/report.md
    - https://github.com/gosha70/wiki-studio/pull/146
    - https://github.com/gosha70/wiki-studio/pull/148
  origin_claim: |
    Issue 121 (filed by the owner on 2026-11-22, open) asks for a way to tell
    a curator that two pages record the same thing. Cycle 10 measured word
    overlap of title and first paragraph and found 3 of 8 true pairs against
    a bar of 6, so nothing was built (eval/duplicates/report.md). Cycle 11
    measured and shipped a hint at writing time: propose lists the 5 most
    similar pages of the same type (eval/similar/report.md, evidence PR #146,
    build PR #148). In the owner's comments on issue 121 of 2026-11-26 the
    issue stays open for an after-the-fact audit: a model-free findings kind
    that reports, for pages already in the wiki, that two of them may record
    the same thing. The issue body (2026-11-19) holds the owner's preferred
    shape for a finding. The bet pitch specs/pitches/121-duplicate-audit/pitch.md
    (shaped, reviewed twice and merged in PR #151; bet for cycle 12 in PR
    #152) proposes mutual rank under the hint's ranker at k = 1, 3, 5,
    measured before anything is built. The owner's decisions (2026-11-26):
    D1 4w with a fresh held-out labelled set that alone decides; D2
    wiki-studio's own spec and pitch decisions plus memkernel's two spec
    directories added since cycle 10's pin (code-copilot-team's new
    directories excluded as session-analytics work, so it contributes none);
    D3 mutual top-k at k = 1, 3, 5, fewest false per true wins, tie to the
    smaller k; D4 cycle 10's bar on the held-out set; D5 at most 10 s added
    to findings on a 500-page synthetic wiki, the kind cut if the frozen rule
    misses it; D6 the for_root switch gap fixed in this bet for both
    switches, independent of the verdict, cut first; D7 a development stage
    on cycle 10's frozen corpus first, under a stop rule frozen in S1 (the
    held-out stage goes ahead only if at least one candidate's false pairs
    there do not outnumber its true pairs); D8 a bad switch value raises in
    library calls too. After the second external review (2026-11-27): a
    fourth bar condition, at least 2 found true pairs that are not
    restatements, with a mechanical restatement rule (same spec directory; a
    pitch and the spec bundle whose plan.md origin.issue equals the pitch's
    leading number; two pitch files); the development stage uses the
    held-out run's index rule and its counts are copied, not recomputed; the
    synthetic wiki is the held-out pages cycled to 500. Settled: no model,
    findings writes nothing, no new frontmatter key, page type, exit code,
    MCP tool or dependency, findings_version 1, lint --health and --strict
    unchanged, frozen eval files never edited, no release step, issue 121
    closed by no PR.
---

# Plan: a duplicate audit in findings (issue 121, cycle 12)

The bet pitch `specs/pitches/121-duplicate-audit/pitch.md` is the shaping
record (owner decisions D1-D8 of 26 November; the second review's changes of
27 November; bet PR #152). Its "Findings from the code and the evidence" were
re-checked on `main` at 04009ee and hold; the line numbers are below. Issue 121
and its comments of 2026-11-26 were not re-fetched (no shell in the writing
session); their words come from the pitch, and the origin-alignment record at
approval reads the issue itself.

## Facts (checked at 04009ee, 27 November 2026)

1. **`findings` and its kinds.** `findings.py`: docstring 3-35 ("Nothing here
   takes a backend or resolves one, takes the wiki lock or writes", 32);
   `KIND_*` 78-91; `FINDING_KINDS` 93-108, the conflict kinds at 103-105 and
   the two revision kinds after them at 106-107; `FindingsResult` 138-159,
   `as_dict` 151-159 ending with `revision_check`; the conflict scope loop
   291-297 (whole review set, kept when it touches the scope); `findings`
   263-309.
2. **The `revision_check` precedent.** `revisions.py` `RevisionCheck` 465,
   `as_dict` 490-497 (`state`, `reason`, ...), `summary` 503-509 with the
   prefix `revision check: `; `cli.py` `_do_findings` 875-886 prints it at
   883; `nightly.py` 293 puts it in the report header.
3. **The marker helpers.** `conflicts.py`: docstring 3-21 ("`findings.py` is
   its only importer", 20); `CONFLICT_MARKER_RE` 44-45; `_body_lines` 68-77;
   `_marker_target` 80-86; `_resolve_target` 89-102; `scan_callouts`
   105-136; `conflict_findings` 167-247.
4. **The hint and the ranker.** `discovery.py`: `RankerConfig` 98-105,
   `DEFAULT_RANKER_CONFIG` 108-113, `ranker_config_hash` 116-126,
   `fts5_available` 160-164, `_read_eligible` 268-282, `_read_index`
   285-296, `select` 377-462 (eligibility 412-426: `index.md` links
   normalised and deduplicated, `index.md` and `log.md` never; `_rank_fts5`
   goes through the on-disk cache, 346-360), `SIMILAR_PAGES_K` 474,
   `similar_query` 503-506, `similar_pages` 509-543 (calls `select`, so it
   refreshes the cache: the audit cannot reuse it, pitch finding 1).
5. **The index.** `search_index.py`: `TABLE_NAME` 49, `INDEXED_COLUMNS` 56,
   `SearchDocument` 130-137, `build_document` 151-163, `build_query` 181-186,
   `SearchIndex` 189-239 (constructor takes a connection, 192; `rank`
   211-239, ties by position in `order`), `create_table` 242-247 (public),
   `_INSERT_PAGE` 262 (private), `build_in_memory` 269-278. No method removes
   or inserts a row (pitch finding 12). `audit.py` can therefore own its
   connection through the public `create_table` and `SearchIndex(connection)`
   and touch no private name of the package.
6. **The switches.** `paths.py`: `ENV_SIMILAR_PAGES` 40,
   `SIMILAR_PAGES_ON`/`OFF` 41-42, the field 300 and its docstring 285-287,
   `for_root` 302-339 (reads no environment variable; `similar_pages` None
   means on, 338), `resolve` 341-431 (the switch read at 412-420, `ValueError`
   on a bad value), `with_wiki_dir` 433-444 (`dataclasses.replace`, so a new
   field is carried). `README.md` 423 and 533 (the switch), 588 (a `for_root`
   example); `docs/consumers.md` 98 and 117 (two `for_root` examples, one of
   them memkernel's). The cycle 11 cooldown measured the gap (pitch finding
   6).
7. **The MCP surface.** `mcp_adapter/tools.py` 313-315 returns
   `api.findings(...).as_dict()`; `mcp_adapter/trace.py` 145 lists the
   `findings` result keys (`findings_version`, `counts`, `pages_checked`,
   `findings`, `revision_check`), so a new top-level key must join it.
8. **The page types.** `schema/__init__.py` `PAGE_TYPES` 47-77: concept,
   workflow, incident, decision, playbook, glossary, open-question
   promotable; index, log, overview not. Cycle 10 D10 (its pitch 867-875)
   compares concept, workflow, incident, playbook and decision.
9. **Cycle 10's extraction code is reusable by import.** `eval/duplicates/extract.py`:
   `CLOSING_KEYWORD_RE` 126, `verify_pin` 231-236, `read_snapshot` 239-252
   (generic: a repository label, a checkout, a pin), `spec_names` 270-277
   (three-part `specs/<name>/<file>` paths only), `file_items` 395-401,
   `build_page` 526-543 (generic), `write_corpus` 642-660 (generic). Fixed to
   cycle 10: `PINS` 58-61, `SLUG_PREFIXES` 62 (used by `slug_for` 517-519),
   the family logic of `extract_corpus` 577-596. `sample.py`'s families are
   fixed at 38. `tests/test_duplicates_extract.py` holds the six fixed items'
   raw texts.
10. **Cycle 11's rule is reusable by import.** `eval/similar/rank.py`:
    `check_frozen` 153-167, `slug_of` 187-189, `slug_paths` 192-215,
    `query_text` 229-232 (the same as `similar_query`), `compared_pages`
    365-382 (a fresh index per try without the query page, 369; pitch
    finding 3), `render` 546-548.
11. **The development inputs.** `eval/duplicates/corpus.json`: pins 5-12,
    `extend: 8` 15-18, 299 pages from 208; its sha256 `fc0f710a…` and
    `labels.json`'s `e1c34ca9…` are pinned by `tests/test_duplicates_frozen.py`
    (and restated in `eval/similar/protocol.json`). `eval/duplicates/protocol.json`
    84-105 is the bar this cycle keeps (conditions 1-3).
12. **The held-out sources at 04009ee.** 18 spec directories under
    `specs/`; 12 pitch files under `specs/pitches/` (11 at the pitch's read,
    plus this cycle's own, whose only decision section holds list items
    without a bold label and so yields no item under cycle 10's rule).
    Decision H2 lines in pitches: `10` 370, `120` 953, `121-duplicate-audit`
    424, `121-near-duplicate-finding` 800, `121-similar-pages-at-propose` 327
    and 343, `28` 467, `38-release-b` 684 and 831, `38-release-c` 645, `54`
    440, `69` 474, `70` 524, `71` 357. `plan.md` `origin.issue`: an integer in
    16 bundles; **absent in `wiki-studio-0-1-0` and `wiki-studio-0-6-0`**
    (their `origin:` blocks hold `urls:` only, 9-14 of each). Pitch ids start
    with 10, 28, 38 (two), 54, 69, 70, 71, 120, 121 (three); bundles with the
    same origin issue exist for each.
13. **memkernel.** The two directories added since cycle 10's pin
    (`corpus.json` 157-205 lists the 24 at the pin) are
    `memkernel-0-17-supersede-and-canonical-hash` and
    `memkernel-0-18-imported-page-collapse`; decision sections at their
    `spec.md` 84 and 112, 124. Their `plan.md` `origin.issue` is a string
    naming a memkernel issue, never an integer. The local checkout's `main`
    pointed at `f3cb8d56536464e64141f9b8b4d730c6290f71cc` on 27 November
    (read from the ref file, not verified with git).
14. **The documents.** `docs/knowledge-contract.md` Findings 372, "Kinds may
    be added within `findings_version: 1`" 403, the revision check 430, the
    `revision_check` object 504-509, Nightly 554. `docs/adr/` holds 0001-0005.
    `CHANGELOG.md` `[Unreleased]` holds the similar-pages entry.
15. **The driver** (cycles 09-11): sessions cannot run Python; a phase's
    review diff base is fixed when the phase starts, so a main-session commit
    at a pause is reviewed in the PR; `CCT_REVIEW_DIFF_MAX_LINES` in the
    owner's shell (4000) overrides `review.diff_max_lines`; the driver falls
    back to `plan.md`'s origin issue when it opens a PR; `--resume` does not
    remember `--start-phase`; the driver moves only a `hill.json` in the spec
    directory it runs on, so this bundle carries its own `hill.json` for the
    driver (O10) and the pitch's chart is copied from it by hand.

## Departures from the pitch

Each is recorded so the origin-alignment record at approval can cite it.

1. **The study directory is `eval/duplicate_audit/`**, not
   `eval/duplicate-audit/` (O1): a hyphen cannot be in a Python package path,
   and the scripts import `eval.similar.rank` and `eval.duplicates.extract`
   as the other studies import each other.
2. **The held-out data lives in `eval/duplicate_audit/held-out/`** with its
   own `README.md` (counts, labelling notes). The study README is frozen with
   the protocol in US1 and holds the protocol only (cycle 11 departure 4).
3. **The development stage gets its own recording phase, US3** (O4), so a
   `stop` ends run 1 with a reviewed report, and a `go` moves the
   development section of the report forward instead of adding work.
4. **"No candidate code in the tree" at labelling is read as "the labelling
   session never opens it"** (O6). D7 put the development stage, and so
   `audit.py`, before the held-out set; the pitch's S2 wording predates D7.
   The labelling phase opens no audit code and no result, runs no script,
   and the history audit checks that its commit touched only labelling
   files.
5. **`freeze.json` gates the held-out run mechanically.** `audit.py
   --set held-out` refuses unless it exists and every pinned hash matches,
   so no candidate can touch the held-out set before the freeze.
6. **Restatement rule (b) is read within one repository and on integers**
   (O3): issue numbers are per repository, and memkernel's `origin.issue`
   is a string. A bundle with no `origin.issue` never meets (b).
7. **`possible-duplicate` is appended last to `FINDING_KINDS`** (O9), after
   the revision kinds too, so no existing kind moves (cycle 10 FR-032's
   precedent). The pitch said "after the conflict kinds".
8. **`duplicate_check`'s shape and its CLI line** are set here (O8), after
   `revision_check`.
9. **S6 is the first phase of run 2 (US8)** (O5), so run 2 starts at the same
   phase with or without a pass, and the duplicate switch in US9 is read by
   both constructors from the start. `for_root` gains an `env` keyword so the
   tests need not edit `os.environ`.
10. **The development stage is reproduced in CI, never re-read** (O7): the
    results test reruns it and compares bytes; the report copies the committed
    numbers.
11. **The time bound is measured as `findings` on minus off** (O12), on the
    synthetic wiki the pitch defines, with copies after the first placed
    under `<slug>-c<n>.md`.
12. **The memkernel pin is its local `main` when US1 runs** (O2), recorded in
    full and confirmed by the owner at sign-off; the pitch said "a pinned
    commit".
13. **The kind spans two phases (US9 the rule, US10 the kind)** for review
    size, as cycle 10 planned.
14. **`mcp_adapter/trace.py` gains `duplicate_check`** (fact 7); the tool set
    and the conformance suite are unchanged.
15. **Both runs end at a pause and both PRs are opened by hand** with
    `pre-pr-check.sh --closes none`, since the driver names the origin issue
    for closure and issue 121 must stay open.
16. **The development stage line and the winner line** have fixed spellings
    (`Development stage: go|stop`, `Winner: mutual-top-1|3|5|none`) so tests
    can check them.
17. **Cut order with a winner (the owner, 2026-11-27, after the review of
    PR #153).** The pitch's trigger 1 cuts S6 first whenever the work is
    late. Here US8 (S6) can be cut only without a winner: once FR-035 records
    one, US8 ships with the kind, because memkernel's session-start hook
    (`curation_findings` in `studio.py`) calls `api.findings` with `for_root`
    paths and could not turn a 10 s scan off otherwise.
18. **An SQLite error in the scan is caught** (the owner, O8's alternative):
    `duplicate_check` gains a `not-computed` state, and the other kinds still
    report.
19. **The verdict is stop** (spec amendment, 2026-11-27). The development
    stage (evidence PR #157) found every candidate's false pairs far above
    its true pairs on cycle 10's frozen corpus (top-1 47 against 4, top-3 164
    against 5, top-5 278 against 6), confirming the pitch's finding 10.
    Trigger 0 fired: S2, S4 and S5 are cut (US4-US7, US9-US11). **Run 2's
    settings** (`automation.json`): branch `feature/wiki-studio-duplicate-audit-121`
    from `main` after this amendment merges; `max_phases: 8`, started fresh
    with `--start-phase 8` after run 1's ledger
    (`.cct/auto-build/wiki-studio-duplicate-audit-121/`) is moved aside; the
    marker pauses after US8, where run 2 ends (not resumed; its PR opened by
    hand with `pre-pr-check.sh --closes none`); a resume before that, if
    ever needed, is `--resume --start-phase 8`; `build.max_turns: 120`;
    `review.diff_max_lines: 6000`; no `pr.closes`; every start with
    `env -u CCT_REVIEW_DIFF_MAX_LINES`. The hill charts: S1 and S3 done (the
    measurement ran and its evidence PR merged), S2, S4 and S5 cut and left
    uphill (no cut status), S6 for run 2.

Close target: none. Issue 121 stays open whatever the verdict; no PR, commit
message or artifact names it after a closing keyword, and no other issue is
closed.

## Architecture decisions

- **ADR-1: Protocol, sign-off, script, development stage, held-out set,
  freeze, run, report.** Each step lands before the next can exist; the
  history audit checks the order.
- **ADR-2: Data is produced by scripts the main session runs** at pauses,
  and CI reruns the results byte for byte.
- **ADR-3: The audit is the hint's ranker in one index.** One in-memory
  index per run, each page removed for its own query; no new ranking, no
  floor.
- **ADR-4: The kind replays the measurement.** The package scan is tested
  against the committed winner's pairs on the frozen held-out pages.
- **ADR-5: Each phase is true on its own diff;** nothing is versioned.

## Files

| File | Phase | Change |
|---|---|---|
| `eval/duplicate_audit/__init__.py`, `README.md`, `protocol.json` (new) | US1 (pause 1 only for an owner-asked change) | FR-001-FR-012 |
| `tests/test_duplicate_audit_frozen.py` (new) | US1 | FR-013 |
| `CLAUDE.md` | US1, US9 | Layout lines for `eval/duplicate_audit/` and `duplicates.py` |
| `eval/duplicate_audit/audit.py` (new) | US2 | FR-015, FR-016 |
| `tests/test_duplicate_audit_script.py` (new) | US2 | FR-017 |
| `eval/duplicate_audit/results/development.json`, `development-timing.json` (new) | pause 2 (main session) | FR-018, as written |
| `eval/duplicate_audit/report.md` (new) | US3, US7 | FR-019, FR-032 |
| `tests/test_duplicate_audit_development.py` (new) | US3 | FR-020 |
| `eval/duplicate_audit/extract.py`, `sample.py` (new) | US4 | FR-022, FR-023 |
| `tests/test_duplicate_audit_extract.py` (new) | US4 | FR-024 |
| `eval/duplicate_audit/held-out/corpus/`, `corpus.json` (new) | pause 4 (main session) | FR-025, as written |
| `eval/duplicate_audit/held-out/labels.json`, `README.md` (new) | US5 | FR-026 |
| `tests/test_duplicate_audit_labels.py` (new) | US5 | FR-027 |
| `eval/duplicate_audit/held-out/review-sample.json` (new) | pause 5 (main session) | FR-028, as written |
| `eval/duplicate_audit/held-out/freeze.json` (new), `held-out/README.md` | US6 | FR-029 |
| `tests/test_duplicate_audit_corpus.py`, `tests/test_duplicate_audit_heldout_frozen.py` (new) | US6 | FR-030 |
| `eval/duplicate_audit/results/held-out.json`, `held-out-timing.json` (new) | pause 6 (main session) | FR-031, as written |
| `tests/test_duplicate_audit_results.py` (new) | US7 | FR-033 |
| `src/wiki_studio/paths.py` | US8, US9 | FR-036, FR-042 |
| `README.md`, `docs/consumers.md`, `CHANGELOG.md` | US8, US11 | FR-037; FR-048, FR-049 |
| `tests/test_paths.py` | US8 | FR-038 |
| `src/wiki_studio/search_index.py` | US9 | FR-039 (additions only) |
| `src/wiki_studio/duplicates.py` (new), `conflicts.py` (one docstring sentence) | US9 | FR-040, FR-041 |
| `tests/test_duplicate_scan.py` (new) | US9 | FR-043 |
| `src/wiki_studio/findings.py`, `cli.py`, `api.py` (docstring), `mcp_adapter/trace.py` | US10 | FR-044, FR-045 |
| `tests/test_possible_duplicate.py` (new), `tests/test_findings.py` | US10 | FR-046 |
| `docs/adr/0006-related-line.md` (new), `src/wiki_studio/schema/citation-rules.md`, `docs/knowledge-contract.md`, `docs/patterns.md` | US11 | FR-047, FR-048 |

## Interfaces

```python
# eval/duplicate_audit — run by the main session at pauses, rerun by CI
#   python -m eval.duplicate_audit.audit --set {development,held-out} [--out-dir DIR]
#   python -m eval.duplicate_audit.extract [--wiki-studio PATH] [--memkernel PATH] [--wiki-studio-only] [--out DIR]
#   python -m eval.duplicate_audit.sample [--out PATH]
def page_lists(pages: Sequence[Page]) -> dict[str, list[str]]: ...            # FR-003: each page's same-type list, best first
def flagged(lists: Mapping[str, Sequence[str]], k: int) -> list[tuple[str, str, int, int]]: ...  # FR-004
def is_restatement(a: Mapping[str, Any], b: Mapping[str, Any]) -> str | None: ...  # FR-005: "a", "b", "c" or None

# src/wiki_studio/search_index.py (additions only, US9)
class SearchIndex:
    def remove(self, path: str) -> None: ...
    def add(self, document: SearchDocument) -> None: ...

# src/wiki_studio/duplicates.py (new, US9)
DUPLICATE_K: int                      # the winner's k, set by the amendment
COMPARED_PAGE_TYPES = ("concept", "workflow", "incident", "playbook", "decision")
RELATED_MARKER = "[!related]"

@dataclass(frozen=True)
class DuplicatePair:
    pages: tuple[str, str]            # sorted
    ranks: tuple[int, int]            # second in first's list, first in second's list
    related_line: str

@dataclass(frozen=True)
class DuplicateCheck:
    state: str                        # "ran" | "off" | "fts5-missing" | "not-computed"
    reason: str | None
    pages_compared: int
    def as_dict(self) -> dict[str, Any]: ...
    def summary(self) -> str: ...     # "duplicate check: ..."

def duplicate_scan(paths: WikiPaths) -> tuple[tuple[DuplicatePair, ...], DuplicateCheck]: ...

# src/wiki_studio/paths.py
ENV_DUPLICATE_CHECK = "WIKI_STUDIO_DUPLICATE_CHECK"      # US9
# for_root gains env: Mapping[str, str] | None = None (US8); duplicate_check: bool | None = None (US9)
```

`findings --json`, with the kind:

```json
{"findings_version": 1, "counts": {"...": 0, "possible-duplicate": 1}, "pages_checked": 12,
 "findings": [{"kind": "possible-duplicate", "severity": "warning",
               "pages": ["decisions/a.md", "decisions/b.md"],
               "description": "... add this line to decisions/a.md: > [!related] Not a duplicate of [B](b.md)."}],
 "revision_check": {"...": "..."},
 "duplicate_check": {"state": "ran", "reason": null, "pages_compared": 12}}
```

## Phases (one auto-build phase per `## US<n>:` group of tasks.md)

Every phase's gate is the full gate of the spec's Constraints.

| Phase | Scope | Run | FRs | What | Phase tests | Pause after |
|---|---|---|---|---|---|---|
| US1 | S1 | 1 | FR-001-FR-014 | README, protocol.json, frozen test | `test_duplicate_audit_frozen`, `test_duplicates_frozen`, `test_similar_frozen` | **yes**: owner sign-off |
| US2 | S3 | 1 | FR-015-FR-018 | audit.py on synthetic inputs | `test_duplicate_audit_script`, `test_duplicate_audit_frozen` | **yes**: development stage run |
| US3 | S1 | 1 | FR-019-FR-021 | report's development section, test, audit | `test_duplicate_audit_development` | **yes**: trigger 0 (`stop` ends run 1) |
| US4 | S2 | 1 | FR-022-FR-025 | held-out extract.py, sample.py | `test_duplicate_audit_extract`, `test_duplicates_extract` | **yes**: extraction run |
| US5 | S2 | 1 | FR-026-FR-028 | labels by an isolated session | `test_duplicate_audit_labels` | **yes**: sample, owner review |
| US6 | S2 | 1 | FR-029-FR-031 | freeze.json, corpus section, tests | `test_duplicate_audit_corpus`, `test_duplicate_audit_heldout_frozen` | **yes**: held-out run |
| US7 | S3 | 1 | FR-032-FR-035 | report's held-out section, results test, audit | `test_duplicate_audit_results` | **yes**: run 1 ends; evidence PR by hand |
| US8 | S6 | 2 | FR-036-FR-038 | `for_root` reads the switch | `test_paths` | **yes**: without a winner run 2 ends |
| US9 | S4 | 2 | FR-039-FR-043 | SearchIndex methods, duplicates.py, related line, switch | `test_duplicate_scan`, `test_search_index`, `test_conflict_callouts`, `test_package_boundaries` | no |
| US10 | S4 | 2 | FR-044-FR-046 | the kind, `duplicate_check`, surfaces, time bound | `test_possible_duplicate`, `test_findings`, `test_mcp_adapter`, `test_info_contract` | **yes**: trigger 5 |
| US11 | S5 | 2 | FR-047-FR-050 | ADR-0006, docs, CHANGELOG, invariant audit | `test_quickstart`, FR-050's audit | **yes**: run 2 ends; build PR by hand |

## Runs, pauses and script runs (the lessons of cycles 09-11, built in)

1. **Sessions cannot run Python.** No driver phase runs `audit.py`,
   `extract.py` or `sample.py` to produce committed data. The development
   stage (pause 2), the extraction (pause 4), the sample (pause 5) and the
   held-out run (pause 6) are main-session steps, each committed as its own
   commit. US1's and US6's hashes come from a shell `shasum -a 256`, and the
   driver's gate is the frozen tests' first run. Sessions may run read-only
   git (US1 resolves the pins).
2. **The driver cannot open a PR that closes nothing**: it falls back to
   `plan.md`'s origin issue. Run 1 ends at the milestone after US7 (or after
   US3 with `stop`) and is never resumed; run 2 ends after US11 (or after US8
   without a winner) and is never resumed. Each PR is opened by hand after
   `../code-copilot-team/scripts/pre-pr-check.sh --closes none --title
   <title> --body-file <file> --base main`, and `gh pr view <n> --json
   closingIssuesReferences` must list nothing. If the driver opens a PR
   anyway, the owner closes it unmerged.
3. **`--resume` does not remember `--start-phase`.** Run 1 starts at phase 1,
   so every run-1 resume is a plain `--resume` (the driver's start defaults
   to 1 and it skips the steps its ledger marks done). If run 1 is ever
   restarted fresh from a later phase with `--start-phase <n>`, every resume
   after that repeats `--resume --start-phase <n>`. Run 2 is a fresh run:
   run 1's ledger (`.cct/auto-build/wiki-studio-duplicate-audit-121/`) is
   moved aside first, run 2 starts with `--start-phase 8`, and **every run-2
   resume is `--resume --start-phase 8`**, never a plain `--resume`, which
   would rebuild steps 1-7 on the run-2 branch.
4. **The owner's shell sets `CCT_REVIEW_DIFF_MAX_LINES=4000`**, which
   overrides `review.diff_max_lines`. Every start and resume begins with
   `env -u CCT_REVIEW_DIFF_MAX_LINES`, and `automation.json` carries
   `review.diff_max_lines: 6000`. Size estimate: US1 about 600 lines, US2
   about 1100, US3 about 300, US4 about 700, US5 about 2500 (labels), US6
   about 500, US7 about 400; the main-session commits (development results
   about 900, the corpus about 290 pages, held-out results about 900) are
   reviewed in the PR. Run 2: US8 about 250, US9 about 900, US10 about 900,
   US11 about 300.
5. **The hill chart (O10, the owner's choice).** The driver moves only a
   `hill.json` in the spec directory, so this bundle carries
   `specs/wiki-studio-duplicate-audit-121/hill.json`, a copy of the pitch's
   chart with the same scope ids (S1-S6, the `(S<n>)` tokens of the
   `tasks.md` headings), written at approval. The driver moves and commits it
   each phase. The pitch's chart under `specs/pitches/` stays the pitch's
   record: the build session copies the scope statuses into it by hand at
   each spec amendment and at cycle close, so the two never disagree in a
   merged PR.
6. **Wall time lives in the timing files**, checked for keys only; the
   results files are reproduced byte for byte.
7. **A flaw found after a run is post hoc** (FR-011): never a change to the
   protocol, a label or a verdict line.

## Owner-run steps

1. **Before run 1**: answer O1-O12; approve this bundle; in the approval PR
   write run 1's `automation.json` and the origin-alignment record
   (`CCT_SPECS_DIR=$PWD/specs ../code-copilot-team/scripts/check-origin-alignment.sh wiki-studio-duplicate-audit-121`).
2. **Pause after US1**: review the README and `protocol.json` (the
   candidates, the index rule, the restatement rule with O3, the bar, the
   stop rule, both pins, the labelling rule, the time bound); any change by
   one commit with the frozen test's constants (FR-014); `approved-by:`
   yourself; resume: `env -u CCT_REVIEW_DIFF_MAX_LINES CCT_PROJECT_DIR=$PWD
   ../code-copilot-team/scripts/auto-build-loop.sh wiki-studio-duplicate-audit-121 --resume`.
3. **Pause after US2**: run `python -m eval.duplicate_audit.audit --set
   development` once; commit both results files as written, as their own
   commit; read `stop_rule.outcome`; resume with the same plain `--resume`.
4. **Pause after US3**: with `stop`, do not resume: open the evidence PR by
   hand (FR-034), then the amendment (trigger 0; run 2 is US8 alone unless
   trigger 1 cut it). With `go`, resume with the plain `--resume`.
5. **Pause after US4**: end of week 1, take trigger 2 if needed
   (`--wiki-studio-only`); run `python -m eval.duplicate_audit.extract`
   once; commit `held-out/corpus/` and `held-out/corpus.json` as written;
   check `git -C ../memkernel status --porcelain` is unchanged; resume with
   the plain `--resume`.
6. **Pause after US5**: run `python -m eval.duplicate_audit.sample` once and
   commit `review-sample.json` before any label change; review every true
   and `companion` label, every cross pair and the 20 sampled pairs; commit
   any change with `true_pairs` and the README count; end of week 2, take
   trigger 3 if needed; resume with the plain `--resume`.
7. **Pause after US6**: run `python -m eval.duplicate_audit.audit --set
   held-out` once; commit both results files as written; resume with the
   plain `--resume`.
8. **Pause after US7**: do not resume run 1. `pre-pr-check.sh --closes none`;
   open the evidence PR by hand; confirm `closingIssuesReferences` is empty;
   send it to external review; add the `reviewed` label after the review of
   its head; merge with a merge commit. Then the amendment: FR-035's slot,
   the triggers that fired, `DUPLICATE_K`, run 2's `automation.json`,
   re-approval. Copy the driver's chart (this bundle's `hill.json`) into the
   pitch's chart by hand.
9. **Run 2**: move run 1's ledger aside; start fresh on a new branch from
   `main` with `env -u CCT_REVIEW_DIFF_MAX_LINES CCT_PROJECT_DIR=$PWD
   ../code-copilot-team/scripts/auto-build-loop.sh wiki-studio-duplicate-audit-121 --start-phase 8`.
   After US8: without a winner, do not resume (build PR by hand); with a
   winner, resume with `… --resume --start-phase 8`. After US10, check
   trigger 5 (the time-bound test and the hill), then resume with `…
   --resume --start-phase 8` or cut. After US11, do not resume: re-run the
   gate on the branch head before trusting `landed`, check no phase was
   bypassed without its record, confirm an open PR exists only after you
   open it by hand with `pre-pr-check.sh --closes none`; review and label.
10. **After the merge**: issue 121's fate is the owner's, by hand. Any
    release only on the owner's explicit word, outside the runs.

## Unattended run

The owner writes the configurations at approval. This plan assumes cycle 11's
shape (profile `pr`, the DeepSeek correctness reviewer gating, max 3 rounds per
phase, two fix sessions per phase, the gate of the spec's Constraints,
`merge.enabled: false`, `merge.method: "merge"`), with:

- **Run 1**: branch `feature/wiki-studio-duplicate-audit-121-evidence` from
  `main` after this bundle's approval merges; `milestone_every: 0`,
  `max_phases: 7` (the `<!-- milestone -->` markers pause after every phase
  US1-US7); `build.max_turns: 120`; `review.diff_max_lines: 6000`; no
  `pr.closes`; started with `env -u CCT_REVIEW_DIFF_MAX_LINES
  CCT_PROJECT_DIR=$PWD ../code-copilot-team/scripts/auto-build-loop.sh
  wiki-studio-duplicate-audit-121`, resumed with the same prefix and a plain
  `--resume`.
- **Run 2** (written by the amendment): branch
  `feature/wiki-studio-duplicate-audit-121` from `main`; started fresh with
  `--start-phase 8`; `max_phases: 11` with a winner, `8` without; markers
  pause after US8, US10 and US11; every resume `--resume --start-phase 8`; no
  `pr.closes`; `review.diff_max_lines: 6000`.

## Test strategy

- **Protocol pinned** (US1): sha256 of the README and `protocol.json`, the
  development inputs, k and the bar; the history audits of US3 and US7.
- **Script by construction** (US2): remove-and-insert equal to a fresh index,
  mutual flags at three k, both ranks, every restatement rule, the bar and
  the stop rule at their edges, refusals, determinism, no writes outside
  `--out-dir`.
- **Reproduction** (US3, US7): both results files rerun byte for byte; one
  stage line and one winner line equal to the files'.
- **Held-out set pinned** (US4-US6): extraction by construction and through
  cycle 10's own functions; labels' structure; corpus and freeze hashes.
- **Replay** (US9): the package scan gives the committed winner's pairs and
  ranks on the frozen held-out pages.
- **Behaviour and neighbours** (US8, US10): both constructors and the switch
  values; the related line round trip; skips; scope; FTS5 missing; nothing
  written; the time bound; `lint --health --strict`, review state, `approve`,
  `find` and `nightly` unchanged.
- **Shown commands** (US3, US7, US8, US11): every `python -m
  eval.duplicate_audit.…` line parses; changed docs lines get `--help` or a
  parse.
- **Regression**: coverage at or above 92 percent; existing tests edited only
  where a fixture now yields the new kind or keys.

## Risks

- **Every candidate fails the development stage** (finding 10: mutual top-1
  flagged 79 pairs on 292 neutral pages, and cycle 10's corpus holds 8 true
  pairs). Mitigation: none in the rule; trigger 0 ends the bet after about
  an hour instead of 5-7 hours of labelling, with the evidence published.
- **Too few true pairs, or too many restatements.** The held-out set may hold
  fewer than 8 true pairs, or a pass could rest on pitch and spec restating
  each other. Mitigation: `not testable` is a stated outcome; condition 4
  needs 2 found non-restatements.
- **A heavy owner review.** Pitch and spec restate each other, so the true
  and `companion` labels to review may run to dozens. Mitigation: the
  labelling notes group them by question; trigger 3 freezes as reviewed.
- **Extraction on new formats.** Pitch decision lists without a bold label
  yield no item (fact 12). Mitigation: the rule is not tuned; the counts and
  the badly extracted items are reported.
- **The labeller learns the rule.** The README describes mutual rank.
  Mitigation: labels are by content; the labeller never sees code, ranks or
  results, and the history audit checks its commit.
- **`for_root` now fails on a typo** in every library caller, memkernel
  included (D8). Mitigation: documented in README, CHANGELOG and
  `docs/consumers.md`; an explicit argument bypasses the variable.
- **The time bound.** Cost grows with page length and 500 queries run per
  `findings`. Mitigation: the script's synthetic pass is an early sign; the
  test enforces 10 s; trigger 5 cuts the kind.
- **The driver opens a PR at the end of a run.** Mitigation: milestones on
  the last phase, never resuming it; any such PR is closed unmerged.
- **A third review round on one PR or phase.** Escalation to the owner, per
  the pitch's circuit breaker.

## Success criteria

1. The evidence PR publishes the protocol, the script, the development stage,
   and (with `go`) the held-out set, the binding run and exactly one winner
   line, whatever they show; it changes only FR-034's allowed paths and
   nothing under `src/`; the history shows the order protocol, script,
   development stage, extraction, labels, freeze, run.
2. Every committed results file was produced by the main session at a pause
   and CI reproduces it byte for byte.
3. `WikiPaths.for_root` reads the similar-pages switch, a bad value raises,
   and the change is documented for memkernel.
4. With a winner, `findings` reports `possible-duplicate` exactly as the
   frozen winner flags pairs, silenced by the related line, within 10 s on
   500 pages, writing nothing.
5. No new exit code, frontmatter key, page type, capability, MCP tool or
   dependency; `findings_version` 1; gate green at 92 percent; no version
   bump, CHANGELOG version section or tag; issue 121 open.

## Open items for the spec review

Draft defaults; the spec is written on them. **The owner decided on
2026-11-27 (asked by the build session before the spec PR):** O1-O7, O9 and O12
take their defaults (O8 too at first; after the review of PR #153 the owner
chose O8's alternative, `not-computed`, departure 18) (O3 as written: a pitch paired with `wiki-studio-0-1-0`
or `wiki-studio-0-6-0` is not a restatement, and the report lists such found
pairs separately; O6: one labelling session per repository, never opening
the audit code or any results); **O10 takes the alternative** (this bundle
carries its own `hill.json` for the driver, copied into the pitch's chart by
hand, plan "Runs, pauses and script runs" item 5); **O11 takes the
alternative** (a fixed 16 + 4 review sample, FR-023). The alternatives stay
recorded for the review.

1. **O1 — The study directory's name.** Default: `eval/duplicate_audit/`, a
   package like the other studies, run as `python -m eval.duplicate_audit.…`.
   Alternative: the pitch's `eval/duplicate-audit/`, run by file path with
   tests loading it through `importlib` (as `examples/correction-loop/` is),
   which then cannot import `eval.similar.rank` or `eval.duplicates.extract`
   without editing `sys.path`.
2. **O2 — The held-out pins and base.** Default: wiki-studio at 04009ee (main
   after the pitch merged, before this bundle exists), every spec bundle and
   every pitch there, no topic exclusion; memkernel at its local `main` when
   US1 runs (probably `f3cb8d5`, fact 13), its two new directories only.
   Alternatives: wiki-studio at the run-1 branch base, which would add this
   bundle's own decisions about the study; leaving out the issue 121 bundles
   and pitches; memkernel at a release tag the owner names.
3. **O3 — A pitch paired with `wiki-studio-0-1-0` or `wiki-studio-0-6-0`.**
   These two bundles have no `origin.issue`. Default: such a pair is not a
   restatement (the frozen rule read as written); the report lists, not
   binding, every found non-restatement pair that involves either bundle, so
   a reader can see whether condition 4 rests on them. Alternative: count a
   pitch paired with any bundle that has no `origin.issue` as a restatement
   (stricter on condition 4).
4. **O4 — The phase structure.** Default: run 1 has seven phases, each ending
   at a pause, including US3 to record the development stage (a `stop` then
   ends run 1 with a reviewed report); run 2 is US8 (S6), US9-US10 (S4),
   US11 (S5). Alternative: no US3, with the development counts only in the
   results file and the amendment (one phase fewer; a `stop` evidence PR
   then carries no report).
5. **O5 — Where S6 lands.** Default: US8, the first phase of run 2, with or
   without a winner; with a winner it shares the build PR. Alternative: its
   own one-phase run before run 1 (it lands sooner and alone, but the
   evidence work waits a day); or the last phase of run 2 (then trigger 1
   can cut it late, and its text must cover both switches).
6. **O6 — Who labels and how.** Default: one family per repository
   (wiki-studio about 270 pages, memkernel about 20); the labelling session
   never opens `audit.py`, the report or any results, though `audit.py` is in
   the tree (departure 4). Alternatives: one family per feature (a pitch with
   its spec bundles), with more pairs left to the summary pass; or labelling
   in a separate worktree that does not contain `audit.py`.
7. **O7 — CI and the development stage.** Default: a CI test reruns the
   development stage and compares the bytes with the committed file (a
   reproduction, not a new reading; the report copies the committed
   numbers). Alternative: pin `development.json` by sha256 only and never
   rerun the candidates on cycle 10's corpus.
8. **O8 — `duplicate_check`.** Default: `{"state": "ran" | "off" |
   "fts5-missing", "reason", "pages_compared"}` after `revision_check`, and a
   CLI line `duplicate check: ...` after the revision check line; an SQLite
   error is not caught. Alternative: a fourth state `not-computed` that
   catches `sqlite3.Error` and keeps `findings` at exit 0, as the hint does.
9. **O9 — Where the kind sits in `FINDING_KINDS`.** Default: last, after the
   revision kinds, so no kind moves. Alternative: right after the conflict
   kinds, as the pitch wrote, which moves the two revision kinds one place
   in the listed order.
10. **O10 — Session limits and the hill chart.** Default:
    `build.max_turns: 120`, `review.diff_max_lines: 6000`, every start and
    resume with `env -u CCT_REVIEW_DIFF_MAX_LINES`; no `hill.json` in the
    spec directory, the pitch's chart set by hand. Alternative: add a
    `hill.json` to the spec directory at approval so the driver moves it
    (the carryover item).
11. **O11 — The review sample's split.** Default: 20 pairs split by the
    largest-remainder method over within-family pairs, which likely gives
    all 20 to wiki-studio (about 36,000 pairs against 190). Alternative: a
    fixed split such as 16 and 4, so memkernel's labels are sampled too.
12. **O12 — How the time bound is measured.** Default: one `findings` run
    with the switch on minus one with it off, on the synthetic wiki, on the
    CI runner, at most 10 s. Alternative: time the scan function alone,
    without the rest of `findings` (one timing instead of two, so less
    noise from the other kinds).
