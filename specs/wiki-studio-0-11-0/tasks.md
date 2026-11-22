# Tasks: wiki-studio 0.11.0 — a revision-aware check for a page's cited sources

<!-- status: draft -->
<!-- One `## US<n>:` group = one auto-build phase = one commit. [US#]/FR tags trace to spec.md. The (S<n>) token in each heading is the pitch scope the phase moves. Run 1 (evidence PR) is US1-US3; run 2 (build PR) is US4-US8 and starts only after the spec amendment of FR-016 merges. -->
<!-- Read first: CLAUDE.md, spec.md, plan.md (facts, departures, open items), specs/pitches/120-revision-aware-stale-check/pitch.md, eval/patterns/README.md (609-681, 249), eval/patterns/results/staleness.json, eval/patterns/wiki/decisions/, eval/patterns/corpus/decisions-57.md (143-151), tests/test_patterns_frozen.py, src/wiki_studio/findings.py, src/wiki_studio/health_lint.py (110-155, 469-496), src/wiki_studio/paths.py (30-110, 235-375), src/wiki_studio/fact_diff.py (25-130), src/wiki_studio/wiki_state.py (40-80, 142-146), src/wiki_studio/cli.py (96-125, 410-436, 841-851, 908-960), src/wiki_studio/nightly.py (250-335, 1055-1070), src/wiki_studio/mcp_adapter/ (config.py 97-125, tools.py 281-283, trace.py 118-147), tests/test_findings.py, tests/test_package_boundaries.py, tests/conftest.py (make_repo_layout, run_cli). code-copilot-team (read-only, offline): the checkout the owner confirmed (plan, owner step 1). -->
<!-- Run per phase: poetry run ruff check src/ tests/ eval/ conformance/ examples/ && poetry run ruff format --check src/ tests/ eval/ conformance/ examples/ && poetry run mypy src/ && poetry run pytest -q -p no:cacheprovider --cov=wiki_studio --cov-fail-under=92 -->
<!-- Each phase is reviewed on its own diff: every file a phase writes must be true at the end of that phase. No README, report, docstring, help text, doc, ADR or CHANGELOG line states later-phase work as done. Each behaviour is stated once, in its owning FR (candidates/bar/call plan FR-008, fence FR-009, freeze FR-011, command set FR-017, environment FR-018, classification FR-019, validation FR-020, matching and ambiguity FR-021, cap and timeout FR-022, exact kind FR-025, revision_check FR-026, winner FR-031, cut FR-036, closure FR-046); code comments and tests cite the FR. -->
<!-- Invariants: no model on any path from findings, approve or review_state; nothing in lint, lint --health or --strict changes; stale-claim unchanged; findings writes nothing anywhere and exits 0 on a completed run. No network: no fetch, URL read, issue lookup or lazy blob fetch; nothing written to or fetched into the root's repository, a source root or the code-copilot-team checkout. In the package, git runs only through revisions.py's runner: FR-017's read-only shapes with --no-pager -c core.fsmonitor=false -c core.hooksPath=<os.devnull> -c protocol.allow=never, --no-ext-diff --no-textconv on every diff, argument lists, no shell, FR-018's environment (every inherited GIT_ variable dropped except GIT_CONFIG_GLOBAL, GIT_CONFIG_SYSTEM and GIT_CONFIG_NOSYSTEM), a timeout and the per-run cap; no safe.directory override; a source root must be the top of its own work tree; a sha: under 7 characters is never checked; an ambiguous prefix stops the search. No new exit code, frontmatter key, page type, directory, capability, MCP tool or runtime dependency; no findings_version or schema.version change. The fence (FR-009): no text from the pages under eval/revisions/cases/keyword-quoting/ or from their correcting commits' messages (code-copilot-team 87bbc65, a9628e5) appears anywhere else, including commit messages, PR text, issues and specs; those cases are named by id and path only; no closing-keyword exclusion reaches beyond that directory. No label, case, candidate definition or bar is edited after US2; no case is added after the run. No edit to eval/patterns/'s frozen files, eval/navigation, memkernel or code-copilot-team. Package modules spell none of code-copilot-team, shared/, specs/, doc_internal, knowledge/wiki (tests/test_package_boundaries.py). Every new .py file starts with the two-line EGOGE / Apache-2.0 header; from __future__ import annotations; type hints. Every shown command gets a real check. No closing keyword in any file or commit message (issue 120 is shut only through run 2's automation.json pr.closes, and only with a winner). No commit, push or branch change inside the session; the driver owns git. Never weaken or skip a test. -->

## US1: Real cases and labels, for the owner's review (S1)

<!-- milestone -->

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 1 | | `eval/revisions/__init__.py` (header only) and `README.md` opening per FR-001 (issue 120, the pitch, the branch base's full hash, what is and is not measured, `eval/patterns/` read only, no model). `CLAUDE.md` Layout gains `eval/revisions/          the revision-check study (issue 120): labels, real cases, candidates, results, report` after the `eval/patterns/` line (FR-001) | `eval/revisions/__init__.py`, `eval/revisions/README.md`, `CLAUDE.md` | build | [ ] |
| 2 | | `labels.json`: 14 pages in `staleness.json` order, `superseded` from each page's frontmatter, 24 sources with `path`, `sha`, `revision_check`, `judgment` (the README judgment cell verbatim, null for "—"), `needs_review` (only the merge page's `a24a00e` entry), `citation_error` (only `spearman.py` @ `dafbc5b`). README: the judgments were made after the plain check ran and before any filter existed; finding 9's table (15/14/13, -3/-2/-2, 12/12/11, -1/-1/-1, 11/11/10) and its recipe (FR-002, FR-003) | `eval/revisions/labels.json`, `eval/revisions/README.md` | build | [ ] |
| 3 | | The inventory, read offline with read-only `git rev-parse`, `git show` and `git log` in the confirmed code-copilot-team checkout (nothing fetched, nothing written there): the seven candidates of FR-004 with full hashes, each case's correcting commit and read commit by FR-004's rule (the five same-commit cases read at the correcting commit, `read_rule: "correcting"`, and named counterfactual in the README), rejected candidates listed with reasons. Case fixtures per FR-005: `cases/vllm-backend-doc/`, `cases/run-wiki-ingest-rules/`, `cases/provider-config-guarantee/`, `cases/benchmark-provider-id/`, and `cases/keyword-quoting/pre-pr-strict-mode/`, `.../pre-pr-keyword-set/`, `.../pre-pr-doc-audit/`, each with `page.md` (verbatim at the correcting commit's parent, a derived `sha:` named as such where the page had none; for the two spec cases a built `decision` page from the spec's decision text, anchors only what that text backticks) and `case.json` (every key of FR-005; `sha256.source_at_sha` and `sha256.source_at_read` computed from `git show <commit>:<path>` bytes; `evidence` names commits and paths, quotes nothing) (FR-004, FR-005) | `eval/revisions/cases/**`, `eval/revisions/README.md` | build | [ ] |
| 4 | | Labels for the cases: `should_flag` and a one-line `reason` from the recorded correction evidence only; matched negatives where the history offers one (`<case-id>-negative`, `negative: true`, `should_flag: false`, under `keyword-quoting/` for pre-pr pages). For the keyword-quoting cases the reasons are in the labeller's own words, quote nothing from the page or the commit message, and carry no closing-keyword phrase; README, `labels.json` and `protocol.json` name those cases by id and path only (FR-006, FR-009) | `eval/revisions/cases/**` | build | [ ] |
| 5 | | The pre-successor copy: the fixture merge page with exactly FR-007's five edits; the README names each edit beside the memkernel #57 record line it rests on (FR-007) | `eval/revisions/pre-successor/merge-require-green-ci-was-never-read.md`, `eval/revisions/README.md` | build | [ ] |
| 6 | | README protocol section and `protocol.json` per FR-008: the three structural rules; changed lines; C0-C4 exactly (C2's anchors via `fact_diff`'s regexes plus the last dotted component, its heading rule on the old side; C3's `Revisit when:` parse rule and token rule; the C1 fallbacks); the 10 pages and 11 entries; the bar's three conditions (5 of 10 pages binding, entries reported; the `a24a00e` flag on the pre-successor copy; D18's minimum 4 and three quarters rounded up, else "not testable"); the selection rule with O5's tie-break; the winner line forms `Winner: C<n>` / `Winner: none`; the cost measure and the call plan p1-p7; the cut-1 rule; no case after the run. No `.py` file other than `__init__.py`; no diff, token or anchor computation run (FR-008, FR-009) | `eval/revisions/README.md`, `eval/revisions/protocol.json` | build | [ ] |
| 7 | | `tests/test_revisions_fixture.py` (EGOGE header): FR-010 (the derivation recomputed and equal to `protocol.json`; the 24 labels keyed and counted; every case directory and `case.json` key; `page_md` sha256; full hashes; the pre-pr cases only under `keyword-quoting/`; the pre-successor diff is exactly FR-007's edits; every `should_flag: true` case's `source_at_sha` and `source_at_read` hashes differ (C0 by construction); the closing-keyword scan of `eval/revisions/` excluding exactly `eval/revisions/cases/keyword-quoting/`) (FR-010) | `tests/test_revisions_fixture.py` | build | [ ] |

**Checkpoint US1** — verify before continuing:
- [ ] `git status --porcelain` (this phase's changes) lists only `eval/revisions/**` (no `.py` but `__init__.py`), `tests/test_revisions_fixture.py` and `CLAUDE.md`
- [ ] `git -C <code-copilot-team checkout> status --porcelain` is as before the phase
- [ ] `git grep -n -i -E '(close[sd]?|fix(e[sd])?|resolve[sd]?) +#[0-9]' -- eval/revisions ':(exclude)eval/revisions/cases/keyword-quoting/'` finds nothing
- [ ] `poetry run pytest -q tests/test_revisions_fixture.py tests/test_patterns_frozen.py` passes
- [ ] Full gate green
- [ ] Milestone: the run pauses for the owner's review of this commit (plan, owner step 2)

---

## US2: The freeze (S1)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 8 | | If the owner invoked cut 1 at the milestone: narrow `protocol.json`'s candidates to C0, C1, C2 and name C3 and C4 unmeasured in the README; no other content change. Then `tests/test_revisions_frozen.py` (EGOGE header): constants with the sha256 of `labels.json`, `protocol.json`, `README.md`, the pre-successor copy and every file under `cases/` (an explicit list), each asserted, and the list asserted equal to the case files present. Written once, never edited after this phase (FR-011) | `tests/test_revisions_frozen.py`, `eval/revisions/protocol.json` and `README.md` (cut 1 only) | build | [ ] |

**Checkpoint US2** — verify before continuing:
- [ ] `git status --porcelain` (this phase's changes) lists only `tests/test_revisions_frozen.py` (and, under cut 1, `protocol.json` and `README.md`)
- [ ] No `.py` file under `eval/revisions/` other than `__init__.py` exists
- [ ] `poetry run pytest -q tests/test_revisions_frozen.py tests/test_revisions_fixture.py` passes
- [ ] Full gate green

---

## US3: The measurement and its recommendation (S2)

<!-- milestone -->

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 9 | | `eval/revisions/record.py` (EGOGE header; `main(argv)`, `--checkout`, `--out`): local setup in a `tempfile.TemporaryDirectory()` (`git clone --no-hardlinks --no-checkout`, `checkout --quiet --detach`), one clone at `00d49c0` and one per case at its read commit; case pins verified against the checkout before recording (stop naming the case on a mismatch); the study run with the wiki-studio checkout as the root and the pin clone as the source root, in FR-008's call plan and D6's order, with FR-017's prefix and FR-018's environment, argument lists, no shell, no network; per source the matched repository (a wiki-studio match reported), presence at HEAD and at the `sha:`, p6 hunks, p5 result, Markdown headings; per step p1-p7 the process count and wall time, for the study run and per case; output `results/hunks.json`, and everything for a keyword-quoting case to that case's own `cases/keyword-quoting/<id>/hunks.json`, none of its hunk text in `results/hunks.json` (FR-012) | `eval/revisions/record.py` | build | [ ] |
| 10 | | Run it once on the confirmed checkout (or commit the owner's run, plan step 1); commit both hunks files as recorded (FR-012) | `eval/revisions/results/hunks.json`, `eval/revisions/cases/keyword-quoting/<id>/hunks.json` (one per case) | build | [ ] |
| 11 | | `eval/revisions/candidates.py` (EGOGE header; `main(argv)`, `--out`): reads `protocol.json`, the hunks, the fixture pages in place, the pre-successor copy and the case pages; imports `wiki_studio.fact_diff` and `wiki_studio.wiki_state._tokenise` read-only; runs no git; per candidate FR-013's figures and bar verdicts; the winner by FR-008's rule; `process_counts` (the exact kind's plan p1-p4, that plus each candidate's steps, the slowest single call). Commit its output as `results/candidates.json` (FR-013) | `eval/revisions/candidates.py`, `eval/revisions/results/candidates.json` | build | [ ] |
| 12 | | `eval/revisions/report.md`: FR-014's table, exactly one winner line, the process counts and slowest call FR-022 derives from, the limits stated plainly, disputed labels reported not edited, cuts taken, keyword-quoting cases by id and path only, numbers "as recorded" (FR-014) | `eval/revisions/report.md` | build | [ ] |
| 13 | | `tests/test_revisions_eval.py` (EGOGE header): the scorer equals `results/candidates.json`; one winner line equal to the results' winner; the hunks cover every case directory present at the freeze; an `eval/revisions/` snapshot equal before and after the scorer; `--help` exits 0 for both scripts; `record.py`'s recording function on a temporary three-commit repository (git-gated); every `python -m eval.revisions.…` line in the README and report parses (FR-015) | `tests/test_revisions_eval.py` | build | [ ] |
| 14 | | The evidence PR's scope audit (FR-016), against the run-1 branch base: `git diff <base> --stat` lists only `eval/revisions/**`, the three `tests/test_revisions_*.py` modules, `CLAUDE.md` and the driver's run records under `specs/wiki-studio-0-11-0/` (`automation-summary.md`, `collaboration/`); `git diff <base> -- src/` empty; `git diff <base> -- CLAUDE.md` adds exactly FR-001's line and removes none; `git log --format=%H <base>..HEAD -- tests/test_revisions_frozen.py` prints exactly US2's commit; `git log --format=%H <US2 commit>..HEAD` over the pinned files (FR-016) prints nothing. Any other path is removed before the milestone, or the run stops | — | build | [ ] |

**Checkpoint US3** — verify before continuing:
- [ ] `git diff <run-1 base> -- src/` is empty, and task 14's scope audit passes (only FR-016's allowed paths; `tests/test_revisions_frozen.py` touched by exactly one commit, US2's)
- [ ] `git log --format=%H <run-1 base>..HEAD -- eval/revisions/labels.json eval/revisions/protocol.json eval/revisions/README.md eval/revisions/pre-successor eval/revisions/cases ':(exclude)eval/revisions/cases/keyword-quoting/*/hunks.json' tests/test_revisions_frozen.py` lists only US1's, any owner label commit before the freeze, and US2's commits
- [ ] `poetry run python -m eval.revisions.candidates` prints JSON equal to `results/candidates.json`, and `git status --porcelain eval/` is clean afterwards
- [ ] `grep -n "shell=True\|fetch" eval/revisions/record.py` finds nothing
- [ ] The fence grep of US1's checkpoint still finds nothing; the report names the keyword-quoting cases by id and path only
- [ ] Full gate green
- [ ] Milestone: the evidence PR goes to review; run 2 waits for the spec amendment (FR-016)

---

## US4: The hardened read-only git layer (S3)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 15 | | `paths.py`: `ENV_GIT_CALL_LIMIT = "WIKI_STUDIO_GIT_CALL_LIMIT"` beside `ENV_LOCK_TIMEOUT`; `DEFAULT_GIT_CALL_LIMIT` beside `DEFAULT_LOCK_TIMEOUT`, its value FR-022's formula over `results/candidates.json` (the shipped plan: p1-p4, plus the winner's steps when FR-031 names one), its comment naming the recorded count and the headroom; `WikiPaths.git_call_limit` with that default, `for_root` and `resolve` taking it, the variable parsed as a non-negative integer else `ValueError`, as the lock timeout (FR-022) | `src/wiki_studio/paths.py` | build | [ ] |
| 16 | | `src/wiki_studio/revisions.py` (EGOGE header; standard library only; no forbidden layout string): `GitRunner` with the allowlist of FR-017 (p1-p4, plus p5-p7 only if the amended FR-031's winner needs them), the fixed prefix, FR-018's environment (`KEPT_GIT_ENV`; `GIT_CEILING_DIRECTORIES`, `GIT_TERMINAL_PROMPT=0`, `LC_ALL=C`), `GIT_CALL_TIMEOUT_SECONDS` (FR-022's formula), the cap and its counter; a refused request raises before any process (FR-017, FR-018, FR-022) | `src/wiki_studio/revisions.py` | build | [ ] |
| 17 | | Repository list and classification (FR-019): root first then source roots in `paths.source_roots` order; p1 and p2 once each; the root's ceiling from its toplevel, a source root's from its parent and the top-of-work-tree equality; the reason constants; `OSError` → state off `git not found`; a timed-out repository skipped for the run. Validation (FR-020): 7-40 lowercase hex, `too short`, malformed, lexical path containment, the full commit used downstream. Matching (FR-021, O2): p3 without `--quiet`, `is ambiguous` stops the search, `Needed a single revision` moves on, anything else skips the repository; the no-match rules. Batching (FR-023): one p4 per (repository, commit) with `A`/`D`/`M`/`T` statuses, paths relative to the matched directory. `check_sources(paths, pages)` returns a `RevisionCheck` with per-source outcomes, and `as_dict()`/`summary()` per FR-026/FR-027 | `src/wiki_studio/revisions.py` | build | [ ] |
| 18 | [P] | `CLAUDE.md` Layout gains `src/wiki_studio/revisions.py    the read-only git layer of the revision check: repository list, sha matching, hardened plumbing calls (never writes, never fetches)` after the `findings.py` line | `CLAUDE.md` | build | [ ] |
| 19 | | `tests/test_revisions.py` (EGOGE header), temporary repositories, git-gated: every case of FR-024, including the four ambiguity fixtures from fixed object contents written with `git hash-object -t <type> -w --stdin` (the 7-character collision asserted first; contents found offline once and committed as test constants), the `GIT_` injection with a `subprocess.run` spy, the marker scripts (fsmonitor, `diff.external`, `diff=<driver>` with `command`, `textconv`), the promisor remote, the subdirectory source root, the cap with a counting wrapper, the timeout, the ownership message, the allowlist refusal, and the formula test for `DEFAULT_GIT_CALL_LIMIT` and `GIT_CALL_TIMEOUT_SECONDS` (FR-024) | `tests/test_revisions.py` | build | [ ] |

**Checkpoint US4** — verify before continuing:
- [ ] `grep -n "subprocess" src/wiki_studio/revisions.py` shows one call site, inside `GitRunner`; `grep -n "shell=True\|fetch\|safe.directory" src/wiki_studio/revisions.py` finds nothing
- [ ] `git diff <run-2 base> -- src/wiki_studio/findings.py src/wiki_studio/health_lint.py src/wiki_studio/lint.py` is empty
- [ ] `poetry run pytest -q tests/test_revisions.py tests/test_package_boundaries.py tests/test_findings.py` passes, with no test of `tests/test_revisions.py` skipped where `git` is installed
- [ ] Full gate green

---

## US5: The exact finding and the run state (S3)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 20 | | `findings.py`: `KIND_SOURCE_NOT_AT_REVISION` appended to `FINDING_KINDS`; `findings()` runs `revisions.check_sources` over the in-scope pages without `superseded_by` and emits one warning per source for FR-025's three causes with their descriptions; `FindingsResult.revision_check` and the `revision_check` key in `as_dict()` per FR-026; a `path:` without `sha:` counted `no sha`, no finding. `api.findings`' signature unchanged; its docstring names the kind and the run state (FR-025, FR-026, FR-028) | `src/wiki_studio/findings.py`, `src/wiki_studio/api.py` | build | [ ] |
| 21 | | Surfaces: `cli.py` `findings` description (414-422) names the kind and the run state, `_do_findings` prints FR-027's line after the counts; `nightly.py`'s header list gains `- Revision check: …` after the drafting line, the kind report-only; `mcp_adapter/trace.py` `TOOL_RESULT_KEYS` for `findings` gains `revision_check` (FR-026, FR-027) | `src/wiki_studio/cli.py`, `src/wiki_studio/nightly.py`, `src/wiki_studio/mcp_adapter/trace.py` | build | [ ] |
| 22 | | `tests/test_revision_findings.py` (EGOGE header): FR-029's cases (three causes in the root and in a source root; superseded page skipped; `no sha` counted; scope; the object for a used root, a skipped source root and git missing; the text and nightly lines; the MCP tool carrying the object, gated on the `mcp` extra as the adapter tests are; `lint --health --strict` unchanged; the snapshot of wiki, proposals directory and every repository equal). Existing tests edited only as FR-029 lists: `tests/test_findings.py` key set gains `revision_check` and its fixture becomes a git repository producing `source-not-at-revision`; nightly tests pinning the header list gain the line; the backend-not-reached test unedited (FR-029) | `tests/test_revision_findings.py`, `tests/test_findings.py`, nightly tests as needed | build | [ ] |
| 23 | [P] | `CHANGELOG.md` `[Unreleased]` **Added**: `source-not-at-revision`, the `revision_check` object, source roots also searched for cited commits, `WIKI_STUDIO_GIT_CALL_LIMIT`; no closing keyword (FR-030) | `CHANGELOG.md` | build | [ ] |

**Checkpoint US5** — verify before continuing:
- [ ] `git diff <run-2 base> -- src/wiki_studio/health_lint.py src/wiki_studio/lint.py src/wiki_studio/review.py src/wiki_studio/discovery.py src/wiki_studio/promoter.py` is empty
- [ ] `grep -n "FINDINGS_FORMAT_VERSION = 1" src/wiki_studio/contract.py` still matches; `CAPABILITIES` unchanged (`tests/test_info_contract.py` passes unedited)
- [ ] In a temporary git repository with a page citing a path at a commit that lacks it, `poetry run wiki-studio findings --json` reports one `source-not-at-revision` and `revision_check.state == "on"`; outside any repository it reports `state == "off"` and exits 0
- [ ] `poetry run wiki-studio lint --health --strict` gives the same exit code before and after on that repository
- [ ] Full gate green

---

## US6: source-revision-changed by the winning candidate, or the recorded cut (S4)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 24 | | Read FR-031. With `none` (or a trigger-3 cut), do only task 28 | — | build | [ ] |
| 25 | | With a winner: `revisions.py` gains the winner's pure decision function per FR-008's definition (and the C1 fallback where FR-008 names it) and the p5-p7 calls it needs in the allowlist; `findings.py` gains `KIND_SOURCE_REVISION_CHANGED` appended to `FINDING_KINDS`, one warning per live page and changed source the winner flags, the description naming path, `sha:`, repository and HEAD and quoting the page's `Revisit when:` line (or saying it records none); no such finding beside `source-not-at-revision` or for a path missing at HEAD; `cli.py`'s `findings` description and `api.findings`' docstring name it (FR-032) | `src/wiki_studio/revisions.py`, `src/wiki_studio/findings.py`, `src/wiki_studio/cli.py`, `src/wiki_studio/api.py` | build | [ ] |
| 26 | | Tests in `tests/test_revision_findings.py`: flag, still return (review state unchanged, `approve` works, `find` selects; `nightly` report and JSON list the kind; the MCP tool carries it; `lint --health --strict` unaffected); the study replayed (the decision function over both hunks files equals `results/candidates.json`'s winner flags); `tests/test_findings.py`'s fixture also produces this kind (FR-033, FR-034) | `tests/test_revision_findings.py`, `tests/test_findings.py` | build | [ ] |
| 27 | | `docs/adr/0005-revisit-when-line.md`: `Revisit when:` as an optional body line `findings` reads (FR-008's parse rule), no frontmatter key, page type or schema version change, memkernel's bridge carrying the body unchanged. `CHANGELOG.md` `[Unreleased]` **Added** gains the kind (FR-035) | `docs/adr/0005-revisit-when-line.md`, `CHANGELOG.md` | build | [ ] |
| 28 | | The recorded cut (only with `none` or a trigger-3 cut): `CHANGELOG.md` `[Unreleased]` **Notes** gains one entry: `source-revision-changed` is not shipped because no candidate cleared the bar frozen in `eval/revisions/` (link to `report.md`), and issue 120 stays open with the measurement as its evidence. No kind, no `Revisit when:` parser, no p5-p7, no ADR-0005; after a trigger-3 cut, any code of tasks 24-26 already committed is removed by a follow-up commit (FR-036) | `CHANGELOG.md` | build | [ ] |

**Checkpoint US6** — verify before continuing:
- [ ] With a winner: `FINDING_KINDS` ends with `source-not-at-revision`, `source-revision-changed`; ADR-0005 exists; the replay test passes
- [ ] With the cut: `grep -rn "source-revision-changed\|Revisit when" src/wiki_studio/*.py` finds nothing; `docs/adr/0005-*` does not exist; the Notes entry exists
- [ ] `git diff <run-2 base> -- src/wiki_studio/health_lint.py src/wiki_studio/lint.py` is empty
- [ ] Full gate green

---

## US7: Contract, documents and the recipe (S5)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 29 | | Source roots' second role, one sentence each pointing to the contract: README 49 and 502; `docs/mcp-adapter.md` 35; packaged `schema/lint-rules.md` 75 (lint meaning unchanged); `cli.py` `--source-root` help (104-113) and `info`'s `source-roots:` line (959); `mcp_adapter/config.py` `--source-root` help (108-115); `paths.py` `ENV_SOURCE_ROOTS` comment (37) and `WikiPaths.source_roots` docstring (257-261). `lint.py`, CHANGELOG history and ADR-0003 untouched (FR-037) | `README.md`, `docs/mcp-adapter.md`, `src/wiki_studio/schema/lint-rules.md`, `src/wiki_studio/cli.py`, `src/wiki_studio/mcp_adapter/config.py`, `src/wiki_studio/paths.py` | build | [ ] |
| 30 | | `docs/knowledge-contract.md` Findings: rows for the kinds that ship; the D6 rule in full; the `revision_check` object with an example, additive within `findings_version: 1`; `WIKI_STUDIO_GIT_CALL_LIMIT`, its default and what reaching it reports (FR-038) | `docs/knowledge-contract.md` | build | [ ] |
| 31 | | Packaged `citation-rules.md`: replace the drift sentence (23-24) with what `findings` checks and does not. `docs/patterns.md` "Revisiting and superseding": the shipped finding's meaning (and, with a winner, reading it against `Revisit when:`). README `findings` section (248-267): the new kind(s), the run-state line, `revision_check` in the `--json` row (FR-039) | `src/wiki_studio/schema/citation-rules.md`, `docs/patterns.md`, `README.md` | build | [ ] |
| 32 | | `docs/nightly.md`: `with: fetch-depth: 0` on both `actions/checkout@v4` steps (116, 146) with one sentence on why; `tests/test_nightly_recipe.py` asserts it in both workflows. README 275 and `docs/nightly.md` 5 and 163: never commits, pushes or checks out; its findings step reads repositories read-only. Every command a changed page shows gets its check (FR-040) | `docs/nightly.md`, `README.md`, `tests/test_nightly_recipe.py` | build | [ ] |
| 33 | [P] | `CHANGELOG.md` `[Unreleased]` **Changed**: the packaged `citation-rules.md` sentence; the recipe's `fetch-depth: 0` (FR-041) | `CHANGELOG.md` | build | [ ] |

**Checkpoint US7** — verify before continuing:
- [ ] `grep -n "never runs git\|no git work" README.md docs/nightly.md` finds nothing
- [ ] `grep -n "does not auto-detect drift" src/wiki_studio/schema/citation-rules.md` finds nothing
- [ ] `poetry run wiki-studio --help`, `poetry run wiki-studio findings --help` and `poetry run wiki-studio-mcp --help` succeed and the `--source-root` help names the second role
- [ ] `poetry run pytest -q tests/test_nightly_recipe.py tests/test_schema_fingerprint.py tests/test_frozen_runs.py` passes
- [ ] No document describes `source-revision-changed` unless US6 shipped it
- [ ] Full gate green

---

## US8: Release preparation for 0.11.0 (S6)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 34 | | CHANGELOG: every `[Unreleased]` entry (the two existing Docs entries included) moves under `## [0.11.0]` (undated), with a one-line summary and a **Notes** line (no new exit code, MCP tool, frontmatter key, page type, capability or dependency; `findings_version` 1; issue 120 named without a closing keyword; any cut named); `[Unreleased]` left empty (FR-042) | `CHANGELOG.md` | build | [ ] |
| 35 | | Version 0.11.0 in `pyproject.toml` (6), `src/wiki_studio/__init__.py` (5), README's `# 0.10.0` comment (26), `docs/quickstart-memkernel.md` (27, 38), `tests/integration/test_quickstart_memkernel.py` (58-59), `tests/test_cli_contract.py` (149); no other line of those files (FR-043) | `pyproject.toml`, `src/wiki_studio/__init__.py`, `README.md`, `docs/quickstart-memkernel.md`, `tests/integration/test_quickstart_memkernel.py`, `tests/test_cli_contract.py` | build | [ ] |
| 36 | | Invariant and cut audit (FR-045): the untouched-files `git diff` is empty; `git diff <base> --stat -- src/` lists only FR-045's files; `FINDINGS_FORMAT_VERSION`, `SCHEMA_VERSION`, `CAPABILITIES`, `FORMATS` unchanged; `FINDING_KINDS` is the 0.10.0 tuple plus exactly the shipped kinds; exit codes unchanged (`tests/test_cli_contract.py`); no runtime dependency; the fence-aware closing-keyword `git grep` of FR-045 finds nothing; `docs/compatibility.md` untouched; any cut named in the CHANGELOG and no doc describes a cut feature (FR-044, FR-045, FR-046) | `CHANGELOG.md` | build | [ ] |

**Checkpoint US8** — verify before continuing:
- [ ] `poetry run wiki-studio --version` prints 0.11.0; `poetry build` succeeds; `pip install --dry-run --find-links dist/` resolves every install line of the pages in `ci.yml`'s `PAGES`
- [ ] `poetry run wiki-studio info --json` lists the same `capabilities` and `formats` as 0.10.0
- [ ] `docs/compatibility.md` unchanged; no tag, no release
- [ ] Full gate green

---

## Final Verification

- [ ] Type checker: 0 errors; linter and formatter: 0 errors on `src/ tests/ eval/ conformance/ examples/`
- [ ] Full suite green with coverage at or above 92 percent; the git-gated tests ran in CI
- [ ] The evidence PR (run 1) has one commit per phase plus any owner label commit and sign-offs, merged with a merge commit, never squashed, no change under `src/wiki_studio/`, no closing keyword
- [ ] Labels, cases, the pre-successor copy, the protocol and the README were committed before any candidate code and unchanged after US2
- [ ] `findings` writes nothing, takes no backend, exits 0 on a completed run; no marker script ran; no `GIT_` variable leaked; no network call was made
- [ ] `source-revision-changed` ships exactly when FR-031 names a winner; otherwise the cut is recorded and issue 120 stays open
- [ ] No new exit code, frontmatter key, page type, capability, MCP tool or dependency; `findings_version` 1; `lint --health --strict` unchanged
- [ ] The build PR's body carries the closing line from `pr.closes: [120]` only with a winner (else names issue 120 without a closing keyword); the session closed no issue
- [ ] Nothing from the keyword-quoting cases' pages or correcting commits' messages appears outside `eval/revisions/cases/keyword-quoting/`, in any file, commit message or PR text
