# Tasks: reusable engineering patterns, a research spike (issue 54)

<!-- status: draft -->
<!-- One `## US<n>:` group = one auto-build phase = one commit. [US#]/FR tags trace to spec.md. US1 is pitch scope S1, US2 S2, US3 S4's labels with S3's gold, US4 S3, US5 S4's run, US6 S5, US7 S6. -->
<!-- Read first: CLAUDE.md, spec.md, plan.md (facts and departures), specs/pitches/54-reusable-patterns/pitch.md, src/wiki_studio/schema/page-types.md (11-49, 104-121, 188-212), src/wiki_studio/lint.py (1-33), src/wiki_studio/prose_lint.py (1-27), src/wiki_studio/health_lint.py (110-155, 199-315, 371-417), src/wiki_studio/findings.py (57-184), src/wiki_studio/review.py (1-21), src/wiki_studio/discovery.py (1-162, 270-290), src/wiki_studio/api.py (find 1158-1207), src/wiki_studio/wiki_state.py (43-146), docs/adr/0004-conflict-callout.md, eval/navigation/discovery.py (1-20, 190-225), eval/composition/successor-issue.md, tests/test_discovery.py (40-50, 190-200, 265-275), tests/test_frozen_runs.py (45-60, 440-460), tests/test_discovery_eval.py (1-40), tests/conftest.py (run_cli). memkernel (read-only): eval/decisions-57/corpus.md at tag v0.9.0. code-copilot-team (read-only): knowledge/wiki/ at commit 00d49c0. -->
<!-- Run per phase: poetry run ruff check src/ tests/ eval/ conformance/ examples/ && poetry run ruff format --check src/ tests/ eval/ conformance/ examples/ && poetry run mypy src/ && poetry run pytest -q -p no:cacheprovider --cov=wiki_studio --cov-fail-under=92 -->
<!-- Each phase is reviewed on its own diff: every file a phase writes must be true at the end of that phase. A README section describes only what exists at the end of its phase; no results file, README line or test refers to a later phase's script or result; the report, its recommendation, the issue drafts and docs/patterns.md exist only in US7. Each behaviour is stated once, in its owning FR (pins FR-005, convention FR-006, Y-statement FR-008, background FR-009, labels FR-012, signals/thresholds/scope/pass bar FR-014, trace FR-017, retrieval FR-018, pass-bar report FR-024, staleness FR-026, recommendation line FR-030, closure FR-035); scripts, tests and README cite the FR, they do not restate a second rule. -->
<!-- Invariants: nothing under src/wiki_studio/ changes (no verb, flag, exit code, MCP tool, findings kind, lint rule, prompt, persona or packaged schema document); no page-schema change (no frontmatter key, page type, directory, schema.version or findings_version change) and no ADR; pattern pages use only existing keys and the four existing decision H2s. labels.json, questions.json, protocol.json and tests/test_patterns_frozen.py are written in US3 and never edited after it; no signal code exists before US5's duplicates.py, and US3 runs no overlap computation. No backend or model is invoked by any script or test; no claim about agent behaviour. Standard library and wiki_studio only; no runtime dependency; no network in a test; git runs against the memkernel and code-copilot-team checkouts are read-only (rev-parse, show, cat-file, merge-base, diff --quiet, ls-tree) and by hand; no edit to memkernel, code-copilot-team, eval/navigation, eval/composition or the frozen persona copy. No script writes under eval/ except through --out, and every run of the trace and retrieval uses a temporary copy. No automatic merge, prune, approve or rewrite of a page. Every new .py file starts with the two-line EGOGE / Apache-2.0 header; from __future__ import annotations; type hints. Every shown command (README, report, docs/patterns.md) gets a real check. No closing keyword in any file or commit message (only automation.json's pr.closes closes issue 54); history is written "closed by #N" or "issue N". No version bump and no release. No commit, push or branch change inside the session; the driver owns git. Never weaken or skip a test. -->

## US1: The inventory and the fit map

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 1 | | `eval/patterns/__init__.py` with the two-line EGOGE / Apache-2.0 header only. `eval/patterns/README.md` opening: issue 54, a research spike whose deliverable is a recommendation; the wiki-studio commit the inventory reads (the branch base, full hash); what is measured and what is not (agent behaviour with patterns in reach is not measured, issue 75; no result depends on a model); nothing under `src/wiki_studio/` changes. No section about later phases (FR-001) | `eval/patterns/__init__.py`, `eval/patterns/README.md` | build | [ ] |
| 2 | | The fit map: one row per issue 54 field (intent, applicable constraints, canonical implementation link, rejected alternatives, validation evidence, owner and status, revisit criteria) × where it lives today, what checks it ("nothing" where nothing does), what reaches memkernel; the owner row (approver in the record, `--by`; no maintainer slot); the status row (`status:` never approves) (FR-002) | `eval/patterns/README.md` | build | [ ] |
| 3 | | The behaviour inventory, one paragraph each with file and line at the recorded commit: page types and the `decision` template; `propose --from` and `promote`; approval and `review_state`; citations; structural lint (no section rule) and prose lint (advisory, 25-word limit); `stale-claim` (path existence only); `findings` (twelve kinds, none for similarity); discovery (index-linked candidates, two rankers, the FTS5 fallback, superseded ineligible); supersession; the conflict callout. Then the compatibility section: #38, #51, memkernel #48 closed and their contracts unchanged; memkernel #57 and #123 the runtime side (FR-003, FR-004) | `eval/patterns/README.md` | build | [ ] |
| 4 | [P] | `CLAUDE.md` Layout block: one line `eval/patterns/           the reusable-patterns study (issue 54): fixture, labels, scripts, results, report`, after the `eval/composition/` line (FR-001) | `CLAUDE.md` | build | [ ] |

**Checkpoint US1** — verify before continuing:
- [ ] `git diff main --stat` lists only `eval/patterns/__init__.py`, `eval/patterns/README.md` and `CLAUDE.md`
- [ ] Every file and line the inventory cites opens at that line at the recorded commit
- [ ] The README names no script, fixture page, label or result that does not exist yet
- [ ] Full gate green

---

## US2: The pattern corpus

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 5 | | Pins (read-only git): `git -C /Users/gosha/dev/repo/memkernel rev-parse v0.9.0^{commit}`; `git -C … show v0.9.0:eval/decisions-57/corpus.md` written unchanged to `eval/patterns/corpus/decisions-57.md`; its sha256. code-copilot-team: resolve `00d49c0` to its full hash; `git merge-base --is-ancestor <sha> <pin>` for every commit the corpus cites, failures recorded. `manifest.json` `pins` (`memkernel` {`tag`, `commit`, `path`, `sha256`}, `code_copilot_team` {`commit`}). If a tag, file or pin cannot be read, or a cited commit a page needs is not an ancestor: stop the phase and report plainly; never substitute another tag or commit (FR-005) | `eval/patterns/corpus/decisions-57.md`, `eval/patterns/manifest.json` | build | [ ] |
| 6 | | The 12 record pages under `eval/patterns/wiki/decisions/<slug>.md` per FR-006: frontmatter (`page_type: decision`, `slug`, `title`, `status`, `last_reviewed:` the record's date, `sources:` as `path:` + `sha:` from each `code-copilot-team@<sha> <path>` item and `issue:`/`pr:` as `gosha70/code-copilot-team#<n>`; no `page_id`, no other key; no invented `sha:` for a test path); body in the four H2s in template order: `## Decision` (the Y-statement, split into two sentences where it exceeds 25 words, FR-008; then `Chosen:`), `## Context` (requirement, `Applies when:`, `Does not apply when:`, or `not recorded in the source record`), `## Alternatives considered` (one bullet per rejected option), `## Consequences` (`Revisit when:`, tests and confidence, links to the fixture pages the record names); the conflict pair's ADR-0004 callouts naming each other; no body link outside the fixture except GitHub URLs at a pinned or cited commit; nothing the record and its cited files do not say (FR-006, FR-008) | `eval/patterns/wiki/decisions/*.md` | build | [ ] |
| 7 | | The two successor pages in the same convention, each from the record's superseding or correction evidence and the cited file read with `git show <sha>:<path>`, saying nothing else; `superseded_by: decisions/<successor>.md` and `status: deprecated` on the two stale pages; the five issue 54 examples marked in `manifest.json` (FR-007) | `eval/patterns/wiki/decisions/*.md`, `eval/patterns/manifest.json` | build | [ ] |
| 8 | | The background: every `knowledge/wiki/` page at the pin outside `schema/`, except `index.md`, `log.md` and `playbooks/pre-pr-close-keyword-audit.md`, copied by `git show <pin>:knowledge/wiki/<path>` to the same path under `eval/patterns/wiki/`; only links leaving the copied set rewritten to `https://github.com/gosha70/code-copilot-team/blob/<pin>/<repo path>`; a page still failing structural lint excluded and named with its violation; `manifest.json` `background` (`path`, `sha256_at_pin`, `sha256`, `links_rewritten`) (FR-009) | `eval/patterns/wiki/**`, `eval/patterns/manifest.json` | build | [ ] |
| 9 | | `wiki/index.md` (`page_type: index`; "Patterns" and "Background" sections linking every page except the two superseded ones, each reachable through its successor's link) and `wiki/log.md` (`page_type: log`; one fixed-form line per pattern page with the record's date). `manifest.json` `pages` (`path`, `record`, `kind`, `example`, `successor_of`, `y_statement_split`, `words_page`, `words_record`). README "Corpus" section: the pins verbatim, the page table, the background rule and exclusions (FR-010, FR-011) | `eval/patterns/wiki/index.md`, `eval/patterns/wiki/log.md`, `eval/patterns/manifest.json`, `eval/patterns/README.md` | build | [ ] |
| 10 | | `tests/test_patterns_eval.py` (EGOGE header, unittest style), on a temporary copy of the fixture as the wiki: structural `api.lint` clean; each pattern page `decision` with exactly the four H2s in order, `## Decision` opening `In the context of`, `Applies when:` / `Does not apply when:` in Context, `Revisit when:` in Consequences, no frontmatter key outside the required keys, `sources`, `superseded_by`, `corrects`; no prose finding on a pattern page; exactly the two stale pages carry `superseded_by` naming their successors; the corpus copy hashes to `pins.memkernel.sha256`; every `record` heading occurs in the copy; every background copy hashes to its entry and no excluded page is present; word counts recompute; the README contains each pin value (FR-011) | `tests/test_patterns_eval.py` | build | [ ] |

**Checkpoint US2** — verify before continuing:
- [ ] `git diff main --stat -- src/ eval/navigation eval/composition` is empty
- [ ] `poetry run wiki-studio --root <tmp> --wiki-dir <tmp>/wiki lint` on a copy of `eval/patterns/wiki` reports 0 violations
- [ ] `grep -rn -i -E "(close[sd]?|fix(e[sd])?|resolve[sd]?) #[0-9]" eval/patterns/` finds nothing
- [ ] `git -C /Users/gosha/dev/repo/memkernel status --porcelain` and `git -C /Users/gosha/dev/repo/code-copilot-team status --porcelain` are as before the phase
- [ ] Full gate green

---

## US3: Labels and gold, frozen before any signal runs

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 11 | | `labels.json`: `pattern_pairs`, all 91 unordered pairs of the 14 pattern pages (sorted `pair`, `disposition` in `redundant` / `distinct-by-precondition` / `conflicting` / `unrelated`, a one-sentence `reason` from the page text, `annotation` quoting the corpus line or null), the annotated pairs first; `background_pairs`, only pattern–background pairs a record names (the git-lock record and `incidents/git-safety-bypasses.md`). Labelled from the page text and the corpus copy only; no signal code exists and no overlap is computed (FR-012) | `eval/patterns/labels.json` | build | [ ] |
| 12 | | `questions.json`: 12 entries (`id`, `record`, `question` = the `later-task:` text verbatim, `gold` by the `seed:` rule, `reuse_target`, `trap`, `superseded`) (FR-013) | `eval/patterns/questions.json` | build | [ ] |
| 13 | | `protocol.json`: the three signals and `combined` with thresholds (b) Jaccard ≥ 0.25, (c) ≥ 2 shared entities; eligibility (no `superseded_by`); scope (66 eligible pattern pairs, every eligible pattern–background and background–background pair; the 91-pair table secondary); true and false; the pass bar and "not testable"; the retrieval metrics; `labels_sha256` and `questions_sha256` of the committed files. README "Protocol" section in words, saying these three files were committed in this phase before any signal code and are never edited after it (FR-014, FR-015) | `eval/patterns/protocol.json`, `eval/patterns/README.md` | build | [ ] |
| 14 | | `tests/test_patterns_frozen.py` (EGOGE header): module constants with the sha256 of `labels.json`, `questions.json`, `protocol.json`, each asserted; `protocol.json`'s two hashes equal the files'; the labels' structure (all pairs of the manifest's pattern pages once each, four dispositions, annotated pairs present with an annotation); the questions' text verbatim in the corpus copy and their pages present in the fixture. Written once, never edited after this phase (FR-016) | `tests/test_patterns_frozen.py` | build | [ ] |

**Checkpoint US3** — verify before continuing:
- [ ] `git status --porcelain` (this phase's changes, before the driver commits) lists only the three JSON files, `tests/test_patterns_frozen.py` and `eval/patterns/README.md`
- [ ] No `.py` file under `eval/patterns/` other than `__init__.py` exists
- [ ] `poetry run pytest -q tests/test_patterns_frozen.py tests/test_patterns_eval.py` passes
- [ ] Full gate green

---

## US4: The lifecycle trace and retrieval

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 15 | | `eval/patterns/trace.py` (EGOGE header; `main(argv)`, `--out`): temporary root with the fixture minus example page P (the native-feature page unless another page links it; the README names P) and its index line; the FR-017 steps in order through `wiki_studio.cli.main` with `--root`, `--wiki-dir`, `--proposals-dir` in the temporary root and `--by trace-agent`: `init`; `propose --from` P as `trace-candidate`; a draft with a broken link refused; `promote`; `lint`; a file at P's first cited path; `findings --json`; `read --json`; `approve --revision`; `find --ranker index-first --json` with P's later-task from `questions.json`; a guarded update (approval stale); a successor plus `superseded_by` (P ineligible, successor selected, `superseded-still-indexed`); the cited file changed (nothing reports). Each step: `argv` with `<root>`, exit code, a deterministic `observation`. Commit its output as `results/trace.json` (FR-017) | `eval/patterns/trace.py`, `eval/patterns/results/trace.json` | build | [ ] |
| 16 | | `eval/patterns/retrieval.py` (EGOGE header; `main(argv)`, `--out`): a temporary copy; `api.find(q, paths, max_pages=5, ranker=r)` for each question and each `r` in `discovery.RANKERS`; per question and ranker the ranked pages, `ran_as`, hit at 1, hit at 5, trap outranks, superseded ineligible; totals per ranker; `questions_sha256`. Commit the output of a run with FTS5 available as `results/retrieval.json`; the README records that run's Python and SQLite versions. The navigation runner is neither used nor edited (FR-018) | `eval/patterns/retrieval.py`, `eval/patterns/results/retrieval.json` | build | [ ] |
| 17 | | README sections: the trace (command, P, what each step shows); retrieval (command, the metrics, results as recorded); the evidence checklist (five items, the five examples × five items table from the pages); citing without binding (`wiki-studio find "<question>" --json`, `wiki-studio findings --json` or the MCP `review_state` tool, `wiki-studio read <page> --json`, then the `Applies when:` / `Does not apply when:` lines; the corpus cases where a found pattern must not be reused) (FR-017..FR-020) | `eval/patterns/README.md` | build | [ ] |
| 18 | | Tests in `tests/test_patterns_eval.py`: the trace equals `results/trace.json`; retrieval equals `results/retrieval.json` for `index-first` always and for `fts5` only when `discovery.fts5_available().available`, else `self.skipTest("this Python's SQLite has no FTS5")` (as `tests/test_discovery.py` 44, 195, 271); `questions_sha256` equals the file's hash; an `eval/patterns/` snapshot (path, sha256) equal before and after each script; `main(["--help"])` exits 0 for both; every `wiki-studio …` and `python -m eval.patterns.…` line in the README parses with full flag spelling (FR-021) | `tests/test_patterns_eval.py` | build | [ ] |

**Checkpoint US4** — verify before continuing:
- [ ] `poetry run python -m eval.patterns.trace` and `poetry run python -m eval.patterns.retrieval` print JSON equal to the committed results, and `git status --porcelain eval/` is clean afterwards
- [ ] `grep -n "backend" eval/patterns/trace.py eval/patterns/retrieval.py` shows no backend selection
- [ ] `git status --porcelain` (this phase's changes) names none of `labels.json`, `questions.json`, `protocol.json`, `tests/test_patterns_frozen.py`
- [ ] Full gate green

---

## US5: Duplicate candidates on the frozen labels

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 19 | | `eval/patterns/duplicates.py` (EGOGE header; `main(argv)`, `--out`): `check_frozen` exits 1 naming both values when `labels.json`'s sha256 differs from `protocol.json`'s `labels_sha256`; signals (a), (b), (c) and `combined` with the thresholds read from `protocol.json`, importing `health_lint._candidate_pairs`, `health_lint._entity_mentions`, `prose_lint.load_avoid_map`, `wiki_state._tokenise`, `review.superseded_by` read-only; output per FR-023 (category, label or "background, unlisted", true or false, the part of (a) that fired; true, false by reason, missed; the 91-pair table; pairs removed by the superseded exclusion; `labels_sha256`, `protocol_sha256`) and FR-024 (verdict with its counts; the "rests on N pairs" line when N ≤ 2; a pass grounds an issue draft only). Reads the fixture in place, writes only `--out`, never writes the three frozen files (FR-022..FR-024) | `eval/patterns/duplicates.py` | build | [ ] |
| 20 | | Run it once; commit the output as `results/duplicates.json`; README section: the command, the frozen inputs used, results as recorded, the pass-bar counts and their meaning (FR-024, FR-025) | `eval/patterns/results/duplicates.json`, `eval/patterns/README.md` | build | [ ] |
| 21 | | Tests in `tests/test_patterns_eval.py`: output equals `results/duplicates.json`; its recorded hashes equal the files'; on a temporary copy of `eval/patterns/` with one disposition changed it exits 1 and writes nothing; the `eval/patterns/` snapshot equal before and after; `main(["--help"])` exits 0 (FR-025) | `tests/test_patterns_eval.py` | build | [ ] |

**Checkpoint US5** — verify before continuing:
- [ ] `git status --porcelain` (this phase's changes) names none of `labels.json`, `questions.json`, `protocol.json`, `tests/test_patterns_frozen.py`
- [ ] `git log --format=%H main..HEAD -- eval/patterns/labels.json eval/patterns/questions.json eval/patterns/protocol.json tests/test_patterns_frozen.py` prints one commit, US3's
- [ ] Under cut 2, `results/duplicates.json` holds signal (a) only and the README says so
- [ ] Full gate green

---

## US6: Revisit signals

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 22 | | `eval/patterns/staleness.py` (EGOGE header; `main(argv)`, `--checkout`, `--out`): every `path:` + `sha:` source of the 14 pattern pages and the pin from `manifest.json`; per source `git -C <checkout> cat-file -e <pin>:<path>` and, when the `sha:` is known, `git -C <checkout> diff --quiet <sha> <pin> -- <path>`, via `subprocess.run` with an argument list; records `stale_claim` (flagged exactly when missing at the pin), `revision_check` (changed, unchanged, or null with a reason) and the page's `Revisit when:` line; no fetch; writes only `--out` (FR-026) | `eval/patterns/staleness.py` | build | [ ] |
| 23 | | Run once on `/Users/gosha/dev/repo/code-copilot-team`; commit `results/staleness.json`. README sections: the per-pattern comparison (stale-claim, revision check, a post-run one-line judgment per changed file against `Revisit when:`, labelled as such; false flags of each check counted; whether "flag, still return" fits the wiki) and the triggers table (changed source, new spec revision, security finding, failed test: which a `sources:` entry can carry, what checks it, which none can) (FR-027, FR-028) | `eval/patterns/results/staleness.json`, `eval/patterns/README.md` | build | [ ] |
| 24 | | Tests in `tests/test_patterns_eval.py`, skipped unless `git` is on PATH: a temporary git repository with two commits (one file unchanged, one changed, one deleted) reports unchanged, changed and missing through `check_sources`; `main(["--help"])` exits 0; `results/staleness.json` lists exactly the pattern pages' `path:` sources. Cut 3, if the checkout cannot be read: no `staleness.py`, no results file, no test; the README's revisit section is the triggers table plus the analytic statement from `health_lint.py` 110-155 and says the revision check was not measured (FR-029) | `tests/test_patterns_eval.py` | build | [ ] |

**Checkpoint US6** — verify before continuing:
- [ ] `git -C /Users/gosha/dev/repo/code-copilot-team status --porcelain` is as before the phase
- [ ] `grep -n "fetch\|shell=True" eval/patterns/staleness.py` finds nothing
- [ ] `git status --porcelain` (this phase's changes) names none of the frozen files
- [ ] Full gate green

---

## US7: Recommendation and closure

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 25 | | `eval/patterns/report.md` per FR-030: one section per issue 54 question (1)-(6) with evidence and limits, (6) carrying D6's memkernel text; the overhead table (pattern pages, words per page against the record, Y-statements split, retrieval hits per ranker, false candidates per signal, false staleness flags; conversion time not measured, said so); the assessment of approval, audit, revision, citation, containment and rollback from the trace; any disputed label reported, not edited; the cuts taken; the unmeasured (agent behaviour, issue 75; what cuts removed); 0.10.0 shipped and nothing depends on it (D9); exactly one line `Recommendation: docs and a template.`, `Recommendation: a separately specified enhancement.` or `Recommendation: no change.` with its reasons; numbers copied from the results "as recorded" (FR-030) | `eval/patterns/report.md` | build | [ ] |
| 26 | [P] | One draft per proposed enhancement as `eval/patterns/issues/<slug>.md` in the form of `eval/composition/successor-issue.md` (a leading HTML comment: not filed by the build, the owner files it and replaces `{permalink}` placeholders; title, problem, evidence, proposal, out of scope); issue 54 named as "issue 54"; no closing keyword; none with the outcome "no change" (FR-031) | `eval/patterns/issues/*.md` | build | [ ] |
| 27 | | Only with `Recommendation: docs and a template.`: `docs/patterns.md` (the pattern template as the study wrote it, adjusted by its findings; the evidence checklist; the find, findings, read sequence; revisit guidance; what memkernel keeps; no `pip install` line, a link to README's install section) and one **Docs** line under `CHANGELOG.md` `[Unreleased]`; a test in `tests/test_patterns_eval.py` parsing every `wiki-studio …` line of the page with full flag spelling and running each in-process through `run_cli` against a temporary copy of the fixture, each exiting 0. Otherwise neither file changes (FR-032) | `docs/patterns.md`, `CHANGELOG.md`, `tests/test_patterns_eval.py` | build | [ ] |
| 28 | | Tests in `tests/test_patterns_eval.py`: `report.md` holds the six question sections in order and exactly one recommendation line of the three forms; every results file it cites exists; `docs/patterns.md` exists exactly when the line is `Recommendation: docs and a template.`; every `wiki-studio …` line it shows parses (FR-033) | `tests/test_patterns_eval.py` | build | [ ] |
| 29 | | Circuit-breaker and invariant audit (FR-034): `git diff main -- src/` empty; `git diff main --stat` lists only `eval/patterns/**`, the two test modules, `CLAUDE.md` and, with the template outcome, `docs/patterns.md` and `CHANGELOG.md`; `git diff main -- eval/navigation eval/composition pyproject.toml .github/ docs/adr` empty; `git log --format=%H main..HEAD -- eval/patterns/labels.json eval/patterns/questions.json eval/patterns/protocol.json tests/test_patterns_frozen.py` prints exactly US3's commit; `grep -rn -i -E "(close[sd]?|fix(e[sd])?|resolve[sd]?) #[0-9]" eval/patterns/ docs/ CHANGELOG.md specs/wiki-studio-patterns-54/` finds nothing; `FINDING_KINDS`, `FINDINGS_FORMAT_VERSION`, `SCHEMA_VERSION`, the version and the exit codes unchanged; every cut named in the README and the report (FR-034, FR-035) | — | build | [ ] |

**Checkpoint US7** — verify before continuing:
- [ ] `report.md` ends in exactly one recommendation line, and its numbers match the committed results
- [ ] `docs/patterns.md` and the CHANGELOG line exist exactly with the template outcome
- [ ] Task 29's audit commands give the stated results
- [ ] Full gate green

---

## Final Verification

- [ ] Linter and formatter: 0 errors on `src/ tests/ eval/ conformance/ examples/`; type checker on `src/`: 0 errors
- [ ] Full suite green with coverage at or above 92 percent; the `fts5` comparison ran or was skipped with its reason
- [ ] Nothing under `src/wiki_studio/` changed; no schema, `findings`, lint, exit-code, MCP or dependency change; no version bump
- [ ] labels, questions and protocol were committed in US3 only, before any signal code; the run phases never edited them
- [ ] The trace, retrieval and duplicates reproduce their committed results; no run wrote under `eval/`
- [ ] The corpus copy and every background page hash to their manifest entries; the pins appear in the README
- [ ] memkernel and code-copilot-team were only read
- [ ] The evidence PR has one commit per phase, its body carries the closing line from `pr.closes: [54]`, it is merged with a merge commit and never squashed; the session closed no issue
