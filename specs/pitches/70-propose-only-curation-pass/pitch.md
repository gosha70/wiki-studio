---
pitch_id: 70-propose-only-curation-pass
title: "A scheduled, propose-only curation pass: one verb writes a report of lint and findings and, with an explicit backend, drafts bounded proposals, and never promotes or approves"
appetite: 4w
bet_status: building
cycle: "07"
circuit_breaker: "Core is all six scopes (D1, D3): the nightly verb that runs structural lint, the audit-format pass and findings and writes one report (S1, S2), drafts bounded proposals with an explicit --backend (S3) and creates no duplicate on rerun (S4), with its cron and CI recipe checked (S5) and the release (S6). Never S3 without S4. Cut order, first to last, each with its trigger: (1) end of week 1, if S1 and S2 are not downhill: the --json report (D8) and the pending-proposals section of the report; (2) end of week 2, if S3 is not over the hill (the curate prompt and the bounds check settled and passing with the test backend): weak-orphan drafting, keeping missing-cross-link drafting (D5); (3) last resort, end of week 3, if S3 is not downhill: S3 and S4 together, the verb ships without --backend and --max-proposals, a follow-up issue carries drafting, and the build PR names #70 without a closing keyword (D16). End of week 4: S6 ships what is true; if the release cannot be cut, the change waits under [Unreleased]. Never, to save time: call promote, approve or anything in promoter.py from the pass; write into the wiki directory, the .audit tree included; hold the wiki lock across a backend call; accept a draft that changes anything but the links D5 allows (the link-only check); resolve a backend by environment or auto-detect in the pass (D12); put a model on any path from findings, approve or review_state; add a runtime dependency, a new exit code or an MCP tool; change the page schema or the patch-set format; weaken or skip a test."
shaped_by: "pitch-shaper (Claude Code) for gosha70"
shaped_date: 2026-11-15
---

<!-- Shape-Up pitch. Origin: https://github.com/gosha70/wiki-studio/issues/70 (no comments on 2026-11-15). Related: #54, gosha70/memkernel#59 Phase 3. -->
<!-- specs/retros/cooldown-after-05.md: the owner's order for shaping is #69, then #70, then #54. #69 shipped in PR #103 (0.9.2, merged at e2a80c7, not yet tagged). This pitch shapes the issue; it does not replace it. -->

# Pitch: A propose-only curation pass

## Problem

wiki-studio can tell a curator what is wrong with a wiki: `lint` finds
structural violations, and `findings` finds stale claims, weak orphans,
missing cross-links, unapproved pages and open conflicts. Someone has to
run those commands and then fix each item by hand. Nothing runs the
checks unattended, and nothing drafts a fix while the curator is away.

Issue #70 asks for that run, with one condition: it prepares and stops.
It may draft proposals into the proposals directory, but it never
promotes or approves. A curator reviews what it drafted with the
existing commands. The issue cites the "librarian" pattern: organise the
workspace before anyone asks, so later questions are cheaper. The same
summary warns that a prepared workspace goes stale, which is why the
pass must be repeatable without piling up duplicates.

Today a team that wants this writes its own cron script around
`wiki-studio findings`. It gets a list and no drafts, and each script
handles lint failure, duplicates and the proposals directory its own
way.

## Findings from the code

wiki-studio was read at main `e2a80c7` (0.9.2 merged, not yet tagged) on
2026-11-15. These facts drive the decisions and the rabbit holes.

1. **`findings` already is the report's body, but it cannot draft.**
   `findings.findings` (`src/wiki_studio/findings.py` line 187)
   aggregates the deterministic health kinds (`lint_health` with
   `backend=None`), the review kinds, `superseded-still-indexed`,
   `no-page-id` and the three conflict kinds. It takes no lock and no
   backend, and `tests/test_findings.py` (lines 160-171) asserts that
   backend resolution is never reached. CLAUDE.md makes "no code path
   from `findings` … reaches a model" a rule. So drafting cannot be a
   mode of `findings`; a drafting pass must be a separate caller of it.
2. **`lint` is the other half, and its exit code is the CI gate.**
   `api.lint` (`api.py` line 1223) returns structural violations and
   audit-format errors. `LintResult.passed` fails on any structural
   violation and on audit, health or prose findings only under
   `--strict`. `lint` exits 1 on failure. `findings` exits 0 on any
   completed run.
3. **An unlinked page already fails lint.** Structural lint makes every
   page except `log.md` reachable from `index.md` (`lint.py` line 433,
   "orphan — not reachable from index.md"). So the issue's "index
   entries for unlinked pages" cannot mean a fully unlinked page: that
   wiki fails lint, and the issue's own rule ("touches nothing when lint
   fails") stops the pass. The reachable case is a `weak-orphan`
   (`health_lint.py` line 158): a page with exactly one inbound link.
   When that one link is not from `index.md`, an `append-index` entry
   gives it a second one.
4. **The deterministic kinds are not all fixable without judgment.**
   `missing-cross-link` (line 236) names the canonical page and up to
   five pages that mention it without linking. A fix edits those pages'
   prose, which needs a model. `stale-claim` (line 110) means a cited
   `path:` no longer exists. The model sees page text, not the
   repository, so it would guess where the source went.
   `no-page-id` and `superseded-still-indexed` have mechanical fixes,
   but the issue's acceptance says a run without a backend "creates no
   proposal". Review and conflict kinds need a person or a deciding
   source.
5. **`api.propose` is the safe write path, and its name check is the
   dedup.** `api.propose` (`api.py` line 596) validates the edits, takes
   the wiki lock, and creates `<proposals-dir>/<name>/` exclusively
   (`COLLISION_ERROR`, line 679). An existing name raises
   `OutputWriteError` and writes nothing. It never touches the ingest
   log, never promotes, and records `source` as `plan.json`'s
   `source_path`, which `docs/patch-set-format.md` line 71 calls "free
   text for `propose`". A deterministic proposal name per finding
   therefore gives race-free dedup with no new state file and no format
   change. On promote the directory moves to `.applied/` (`paths.py`
   line 74), so a pending proposal blocks a redraft and an applied one
   does not.
6. **The drafting pieces exist; the prompt does not.**
   `DefaultMultiIngestor.ingest_multi` (`ingestor_multi.py` lines
   75-185) shows the sequence: compose a prompt with schema excerpts and
   `wiki_state.candidate_pages`, call the backend, parse with
   `parse_patch_set_response`, build `PageEdit`s with `base_sha256` from
   the bytes the prompt showed, then run `validate_page_edit_semantics`
   and `validate_patch_set`. Its prompt is about integrating a new
   source behind the four-question gate, which is the wrong task for
   "fix this finding". The copilot CLI renderer
   (`backends/copilot_cli.py` lines 138-280) is generic over `task`, so
   a new task needs a new system instruction and a test-backend branch
   (`backends/test.py` line 59), not a renderer change.
   `INDEX_LOG_ACTION_RULE` (`prompt.py` line 64) already limits index
   and log changes to one-line appends.
7. **A held lock is a bounded wait, not a hang.** `WikiLock` raises
   `PromoteApplyError` with `reason="lock_timeout"` (exit 10) after
   `--lock-timeout` seconds (default 30). It is not reentrant. `findings`
   and `lint` take no lock. A backend call can take two minutes
   (`CopilotCliBackend` timeout 120 s), so holding the lock across one
   would block every promote for that long.
8. **A new verb needs three edits in `cli.py`, and two outside it.** In
   `cli.py`: the dispatch table in `main`, the verb list in the parser
   description and epilog, and `_VERBS` (line 990). Without the last,
   the legacy shim reads `wiki-studio nightly` as
   `ingest --legacy-single-source nightly`. Outside it:
   `tests/test_cli_contract.py` keeps its own `_VERBS` (line 29), which
   its help test loops over, and CLAUDE.md's layout line for `cli.py`
   (line 33) lists the verbs.
9. **`lint --health --backend` is the precedent for "backend only when
   asked".** `api.lint` resolves a backend only when one is passed
   (`backend is not None`); omitted, the contradiction check is skipped.
   `lint`'s `--backend` help says so (`cli.py` lines 405-410: "When
   omitted, contradictions are skipped"). `ingest` and `query` instead
   fall back to `WIKI_STUDIO_BACKEND` and then PATH auto-detect
   (`_BACKEND_HELP_SUFFIX`, `cli.py` line 71, used at lines 223 and 342;
   `prepare_backend`, `api.py` line 252).
10. **A packaged prompt document says there is no scheduler.**
    `schema/ingest-rules.md` lines 82-88, "Manual-only in v1": "There is
    no background scheduler, no auto-promotion on commit … Automated
    ingest is deferred to a follow-up issue." Its first sentence
    (promotion is always started by a person or an explicit agent call)
    stays true under this pitch; "no background scheduler" does not.
    `ingest-rules.md` is one of the three prompt documents; a packaged
    edit changes no fingerprint (only project overrides are hashed), and
    the frozen eval copy (`tests/test_frozen_runs.py` line 222) is a
    separate file that is not edited.
11. **The single-writer and boundary tests cover the new module
    automatically.** `tests/test_package_boundaries.py` scans every
    package module for standard-library-only imports and for layout
    names. CLAUDE.md's "promoter.py is the single writer into the wiki
    directory" test scans the package too. A pass that writes its report
    with `open()` must refuse a report path inside the wiki directory, or
    it is a second writer there. `--search-cache` already refuses a path
    inside the wiki (exit 1), which is the precedent.
12. **Promote may approve.** A wiki whose manifest sets
    `auto_approve_on_promote` approves the pages a promote writes
    (`api.py` line 749). The pass never promotes, so its drafts are
    approved only when a curator promotes them under that policy. The
    persona's "Who approves" step (0.9.2) already governs that.

## Appetite

**4w** (D1, decided by the owner, 2026-11-16, against the 2w default:
drafting ships for certain), one bet. The work content for an LLM
executor is unchanged, about 14-20 hours across six scopes:

| Scope | Estimate |
|-------|----------|
| S1 The pass and its report, model-free | 3-4h |
| S2 The verb on the CLI contract | 1.5-2h |
| S3 Drafting with an explicit backend | 5-7h |
| S4 No duplicate on rerun | 1.5-2h |
| S5 The recipe and the guidance | 2-3h |
| S6 Release | 1-1.5h |

The model-free part (S1, S2, the report-only part of S5, S6) is about
8-10 hours. Drafting (S3, S4) is the novel part: a new prompt task, its
bounds and the failure paths. The estimates are not padded. The extra
two weeks are wall-clock room for three things the hour count does not
show:

- **Review rounds.** The external reviewer reviews the pitch PR, the
  spec and the build, and a merge needs the `reviewed` label on the
  reviewed head (each new commit removes it). Cycle 05's first phase
  passed the gating reviewer on its fourth round. A new verb is a
  contract addition (the verb, its flags, its exit codes and the
  report's JSON form are public once released), and a new model path
  will draw at least as many rounds.
- **Prompt design for drafting.** The test backend proves the plumbing,
  not the quality of a draft. The `curate` prompt is revised against
  one real backend until its drafts stay minimal (S3's manual check).
- **The dedup edge cases.** Two overlapping runs, a finding that
  persists after its proposal is promoted, a draft a curator deleted,
  and two findings in one run that touch the same page (S3, S4).

The release is cut by the owner by the steps in the header of
`.github/workflows/release.yml`, after 0.9.2 is tagged.

Planned order:

- **Week 1:** S1 and S2, then S4's naming rule (S3 depends on it), then
  a first `curate` prompt answered by the test backend. Check trigger 1.
- **Week 2:** S3: the prompt, the edits, the bounds check, the manual
  real-backend run and the prompt revisions it calls for; S4's tests,
  the overlapping-run case included. Check trigger 2.
- **Week 3:** S3's failure paths (backend error, invalid response, bounds
  refusal, lock timeout, governed drift) and S5. The build PR goes to
  review. Check trigger 3, the last resort.
- **Week 4:** review rounds and their fixes, then S6.

## Solution shape

One new verb over existing pieces. No change to `findings`, `lint`,
`promoter.py`, the page schema, the patch-set format or the exit-code
table's meanings.

```
wiki-studio nightly [--report PATH] [--json] [--backend NAME] [--max-proposals N] [--by NAME]

1  lint (structural + audit-format)   api.lint, no lock
     structural violation? ─────────► report: violations, then findings ─► exit 1, no proposal
2  findings                           api.findings, no lock, no backend
3  draft (only with --backend)        for each draftable finding, in order, up to N:
     name = nightly-<kind>-<key>      key = sha256(kind, sorted pages)[:12]
     pending dir with that name? ───► skip ("already proposed"), no model call
     prompt (task "curate") ─► backend ─► validate ─► bounds check ─► api.propose(name, by)
                                                         (lock taken and released inside propose)
4  report                             markdown to PATH or stdout; --json object to stdout

never: api.promote, api.approve, promoter.py, a write under the wiki directory
```

**The pass (S1).** `api.nightly(paths, *, backend=None, max_proposals=…,
by=None) -> NightlyResult` is the library entry; the CLI renders it. It
runs `api.lint` (no health tier, no strict) and `api.findings`. When
structural lint fails, it writes the report and stops: no draft, exit 1
(D10). Otherwise the report has four parts: lint (violations, audit
errors), findings (counts by kind, then each finding), proposals (created,
already pending, skipped by the cap, failed), and "needs a curator" (the
review and conflict kinds, report-only kinds, and the pending proposal
directories). Without `--backend` the proposals part says drafting was
off, and nothing is written but the report.

**Drafting (S3).** Only with an explicit `--backend NAME` (D12), and only
for two kinds (D5):

- `missing-cross-link`: the prompt shows the canonical page and the
  unlinked pages from the finding. The draft may `update` those pages to
  link the canonical page, plus one `append-log` line.
- `weak-orphan` whose one inbound link is not from `index.md`: the
  prompt shows the page and `index.md`. The draft may add one
  `append-index` line and one `append-log` line.

A bounds check refuses a draft that creates a page, edits a page the
prompt did not show, or changes anything but links (D5, revised after
the #104 review): a `missing-cross-link` update with its new links to
the canonical page removed must equal the original page byte for byte,
and a weak-orphan `append-index` line links that page and nothing else.
The refusal is a failed draft in the report, not a proposal. Every `update` carries the
`base_sha256` of the bytes the prompt showed, so a draft that goes stale
before review is refused at promote (exit 9). Each finding gets its own
proposal, so a curator can promote, edit or discard each one alone.

**No duplicates (S4).** The proposal name is deterministic per finding
(D6). The pass skips a finding whose name is already a pending directory
before any model call, and `api.propose`'s exclusive create settles a
race between two overlapping runs.

## Scopes

Build order: S1 first. S2 needs S1's result type. S4's naming rule
lands before S3. S5 and S6 need the others.

### S1: The pass and its report, model-free, ~3-4h

- **Module and API.** A new `src/wiki_studio/nightly.py` holds the pass
  and the report rendering. `api.nightly(...)` is additive, with
  defaults only. It calls `api.lint` and `api.findings` and nothing that
  takes the lock.
- **Report.** Markdown with fixed headings in the order above (lint,
  findings, proposals, needs a curator), the run's date, the resolved
  wiki and proposals directories, and the package version. "Needs a
  curator" lists the review kinds, the conflict kinds, the report-only
  health kinds (`stale-claim`, `avoid-format`, a weak orphan whose only
  link is from `index.md`), `superseded-still-indexed`, `no-page-id`, and
  the pending proposal directories (name and edit count; cut-able,
  circuit-breaker step 1).
- **Where it goes (D8).** `--report PATH` writes the file (parents
  created, written to a temporary file beside it and renamed, an
  existing file replaced). The path is resolved, symlinks included,
  before the check, and a path that resolves inside the wiki directory
  is refused before anything runs (exit 1), as `--search-cache` is. Without
  `--report`, the markdown goes to stdout. `--json` prints the result
  object (D8) to stdout instead of the markdown.
- **Lint failure (D10).** The report puts the structural violations
  first, still lists the findings as information, and says no proposal
  was drafted because lint failed.
- **Tests.** Fixture wikis: clean (empty sections, exit 0); with health
  and review findings and no backend (the report lists them, no
  directory appears under the proposals directory, exit 0, the issue's
  first acceptance line); structurally broken (report written, exit 1,
  no proposal); a report path inside the wiki refused, and so is a path
  outside it that reaches the wiki through a symlinked directory; the whole wiki
  directory, `.audit/` included, byte-identical before and after each
  run (every file's sha256 compared).

### S2: The verb on the CLI contract, ~1.5-2h

- **The verb (D2).** `nightly` in the dispatch table, `_VERBS` (finding
  8), the parser description and its own `--help`; also in
  `tests/test_cli_contract.py`'s `_VERBS` (line 29) and in CLAUDE.md's
  layout line for `cli.py` (line 33). Flags: `--report`,
  `--json`, `--backend`, `--max-proposals`, `--by`, and the global path
  and `--lock-timeout` options every verb takes.
- **Exit codes (D9).** No new code. The README exit-code table and the
  parser epilog gain the verb's uses of 0, 1, 2, 3, 4, 6 and 10, and the
  README states D9's precedence: a lock timeout (10) over a write
  failure (6) over the first draft failure (3 or 4); a lint failure (1)
  stops before drafting and never combines with them.
- **Contract surfaces.** README gets a `### wiki-studio nightly` section
  in Verbs. `info` lists a `nightly` capability and, if D8's JSON form
  ships, its format version (D15). `docs/knowledge-contract.md` documents
  the JSON object.
- **The no-write guarantee in code.** A test asserts that `nightly.py`
  imports neither `promoter` nor `api.promote` / `api.approve`, and that
  a run with `api.promote`, `api.approve` and every `promoter` entry
  point patched to raise still completes.
- **Tests.** In-process `cli.main([...])` for each exit code the verb
  can give, and one per precedence case: a lock timeout after a failed
  draft exits 10; a write failure after a failed draft exits 6; a
  backend failure (3) then an invalid response (4) exits 3, and the
  reverse exits 4; `--help` lists the flags; `wiki-studio nightly` is not
  swallowed by the legacy shim.

### S3: Drafting with an explicit backend, ~5-7h

- **Backend resolution (D12).** Only `--backend NAME` turns drafting on;
  `WIKI_STUDIO_BACKEND` and PATH auto-detect are not consulted.
  `--max-proposals 0` turns it off even with a backend. An unknown name
  exits 2 before lint runs.
- **The prompt.** A new `task: "curate"` composed in `prompt.py` with
  the schema excerpts, the finding (kind, pages, description) as the
  source content, and `wiki_state.candidate_pages` limited to the pages
  D5 allows. The response is the existing patch-set shape
  (`_PATCH_SET_RESPONSE_SCHEMA`), parsed with `parse_patch_set_response`.
  The test backend gets a deterministic `curate` branch that returns a
  valid draft for each drafted kind.
- **Building the edits.** As `ingest_multi` does (finding 6):
  `base_sha256` from the shown bytes, then `validate_page_edit_semantics`
  and `validate_patch_set`. The ingest code is not refactored; a small
  helper may be extracted only if it leaves `ingest_multi`'s behaviour
  byte-identical under its existing tests.
- **Bounds.** Per D5: only the allowed actions, only on shown pages, no
  `create`. A finding whose candidate pages overlap a page already
  drafted in this run is skipped as "overlaps an earlier draft" (two
  updates from one base would make the second stale at promote).
- **The link-only check (D5, after the #104 review).** Syntactic, no
  semantic diff. Each candidate page is read once with `api.read_page`;
  that text is what the prompt shows, and its `sha256` becomes the
  edit's `base_sha256` in `plan.json`, so promote applies the update only
  to those exact bytes. For a `missing-cross-link` `update`, every link
  whose target resolves to the canonical page is removed from the draft
  and from that original, a link `[text](target)` becoming its `text`;
  the two results must be equal byte for byte, and the draft must hold
  more links to the canonical page than the original. A weak-orphan
  `append-index` line holds exactly one link, and it resolves to the
  orphan page. The `append-log` line holds no link. Anything else (a
  reworded sentence, a new "See also" line, a changed frontmatter line,
  a second link in the index line) is refused as out of bounds: a failed
  draft in the report, exit 4 by D9.
- **Writing.** `api.propose(edits, paths, name=…, source="nightly
  <kind>: <pages>", rationale=<finding description>, backend=<name>,
  by=…)`. The lock is taken and released inside each call (D11). The
  report lists each created directory and its fact-warning count from
  `plan.json`.
- **Cap and order (D7).** `--max-proposals N`, default 5. Draftable
  findings are taken in the order `findings` lists them (deterministic
  for a given wiki); the rest are listed as "not drafted (cap)".
- **Failures (D9).** A backend failure, an invalid response or a bounds
  refusal is recorded for that finding and the pass goes on to the next.
  An `OutputWriteError` from `api.propose` whose cause is
  `FileExistsError`, or after which the directory exists, is "already
  proposed" (S4); any other `OutputWriteError` (a full disk, say) is a
  failed draft and makes the run exit 6.
  A lock timeout stops drafting, since every later write would wait too.
  Governed schema drift (`check_write_contract`) is checked once before
  drafting; drift skips drafting and is reported.
- **Tests.** With the test backend: proposals exist under the proposals
  directory and the wiki directory is byte-identical before and after
  (the issue's second acceptance line); each bounds refusal; an
  over-reaching draft from the test backend refused by the link-only
  check (an update that adds the link and rewords a sentence, one that
  adds a "See also" line, an `append-index` line with a second link),
  with no directory written and exit 4; an `OutputWriteError` not caused
  by an existing directory (exit 6); the cap;
  a backend raising `BackendInvocationError` on one finding while the
  next is still drafted; a held lock (exit 10, report written); every
  created proposal promotes cleanly with `api.promote` in the test (the
  test, not the pass, promotes).
- **A real-backend check (manual, not CI; added at shaping, kept by the owner on 2026-11-16).** One `nightly --backend
  <installed CLI>` run on a copy of the S1 fixture wiki, with its report
  and drafts attached to the build PR, to judge that the drafts stay
  minimal. The prompt is revised from it in week 2. CI keeps the test
  backend only.

### S4: No duplicate on rerun, ~1.5-2h

- **The name (D6).** `nightly-<kind>-<key>`, where `key` is the first
  12 hex digits of the sha256 of the kind and the finding's sorted
  pages. It passes `check_proposal_name`. A named constant holds the
  prefix.
- **The check.** Before the backend call, a pending directory of that
  name under the proposals directory means "already proposed": no model
  call, listed in the report. An `OutputWriteError` from `api.propose`
  whose cause is `FileExistsError`, or after which the directory exists
  (a concurrent run), is treated the same way (D9).
  `.applied/` is not consulted.
- **Tests.** The issue's third acceptance line: a second run on an
  unchanged wiki creates no directory and makes no backend call (a
  counting test backend). Also: after the proposal is promoted (moved to
  `.applied/`) and the finding persists, a rerun drafts again; after a
  curator deletes a pending proposal, a rerun drafts again; two
  overlapping runs (the second `api.propose` racing the first) leave one
  directory.

### S5: The recipe and the guidance, ~2-3h

- **`docs/nightly.md`.** A cron line and a GitHub Actions workflow. The
  cron line uses a small wrapper script, because `%` in a crontab entry
  must be escaped (`$(date +\%F)`). Both forms pass `--by <agent-name>`,
  so a cron run records a proposer without relying on
  `WIKI_STUDIO_ACTOR`. The workflow runs the verb on a
  schedule and uploads the report and the proposals directory as a
  workflow artifact. The verb does no git work; the recipe says that a
  curator promotes from a checkout. Both forms show the no-backend run
  first and the backend run second.
- **Checks (CLAUDE.md: every shown command is checked).** A test
  extracts the page's command lines and runs them in-process against a
  temporary wiki with `--backend test` substituted for the real backend
  name, and runs the wrapper script once. The workflow block is checked
  for the keys the recipe relies on (`on.schedule`, the run step, the
  upload step) with a structural assertion; no YAML dependency is added.
  The page joins the `quickstart-memkernel` job's install-line list only
  if it shows a `pip install` line.
- **`WIKI_MAINTAINER.md` (D21).** One short paragraph in the curator
  loop: proposals named `nightly-*` were drafted unattended by a model.
  The agent may review and promote one, but approving one is a person's
  step: for a `nightly-*` proposal the agent follows the "Who approves"
  step (0.9.2) as for a project that reserves approval, so on a wiki
  whose policy approves on promote it stops at propose and reports the
  directory. The paragraph points to that step and does not restate its
  outcomes. The persona's existing command-check tests cover the new
  command, and one check asserts the paragraph names `nightly-*`, the
  person's approval and the "Who approves" step.
- **`ingest-rules.md` (D14).** The "Manual-only in v1" paragraph keeps
  "promotion is always initiated by a human or by an explicit agent
  invocation" and replaces "There is no background scheduler" with: a
  scheduled `nightly` run may draft proposals, and never promotes.

### S6: Release, ~1-1.5h

- `CHANGELOG.md` `[Unreleased]`, Added: the verb, the report, drafting
  (unless the last-resort cut drops it) and the recipe. Changed: the `ingest-rules.md` and
  persona paragraphs.
- The version in `pyproject.toml` and `src/wiki_studio/__init__.py`
  moves to the number D15 settles, with the `==X.Y.Z` pins in
  `docs/quickstart-memkernel.md` and the README `--version` comment.
- Issue #70 closes by D16. The pitch PR body uses no closing keyword.

## Rabbit holes

- **Drafting fixes for every kind.** Stale claims, superseded index
  entries, missing page ids and conflicts each look draftable.
  *Workaround:* D5 drafts two kinds whose fix is "add a link". The rest
  are listed under "needs a curator". Mechanical fixes for
  `no-page-id` and `superseded-still-indexed` are a follow-up issue.
- **A curating prompt that rewrites prose.** Asked to add a link, a
  model may also reword the page. *Workaround:* the link-only check (S3,
  D5): with its new links to the canonical page removed, an update must
  equal the original byte for byte, so a reworded draft is refused, not
  proposed. The prompt asks for the smallest edit. No semantic diff is
  attempted; the check is syntactic.
- **Overlapping pending proposals.** When the pages a
  `missing-cross-link` finding names change (a new page mentions the
  entity), its key changes, so a second pending proposal can overlap
  the first. *Accepted* (D6): both carry base hashes, so once one is
  promoted the other fails promote with exit 9, and the curator
  discards it.
- **Declined proposals come back.** A curator who deletes a draft gets
  it again on the next run while the finding persists. *Workaround:* none
  in this pitch, by D6. The finding itself recurs nightly until fixed,
  and the cap bounds the cost. A `.declined/` convention is the
  alternative listed under D6, not built.
- **Picking a related page for a weak orphan.** A weak orphan linked
  only from `index.md` needs a second link from a related page, and
  choosing one means ranking the wiki. *Workaround:* that case is
  report-only (D5). Only the case an `append-index` line fixes is
  drafted.
- **Reading while a promote runs.** The pass reads without the lock, as
  `findings` does, so it can see a half-applied promote. *Workaround:*
  accepted, as for `findings`. Every drafted `update` carries its base
  hash, so a draft made from a half-applied page fails promote's
  precondition (exit 9) instead of overwriting.
- **Checking a YAML workflow with no YAML library.** *Workaround:* the
  run lines are executed and the block's structure is asserted on the
  lines the recipe depends on (S5), not parsed in full.

## No-gos

- No promote, approve or `promoter.py` call from the pass, and no
  `--promote` flag. A curator promotes with the existing commands.
- No code that refuses or flags the approval of a page that came from a
  `nightly-*` proposal. D21 is persona guidance; `approve` and
  `review_state` are unchanged.
- No write under the wiki directory, the `.audit/` tree included, and
  no ingest-log record (`api.propose` writes none). The report is
  refused inside the wiki directory.
- No change to `findings`, its kinds, `findings_version`, `lint`,
  `lint --health` or `review_state`. No model on any path from them.
- No contradiction check in the pass (D13).
- No new exit code. 0 and 2..11 keep their meaning, and 1 stays fatal
  lint.
- No MCP tool (D17). No change to `mcp_adapter/`.
- No page-schema change, no patch-set format change (`source_path` is
  already free text for `propose`) and no ADR (D18).
- No runtime dependency and no network access in a test.
- No scheduler inside wiki-studio, no daemon and no git operation by the
  verb. Scheduling is the recipe's job (cron or CI).
- No `--paths` scoping of the pass in this pitch.
- No workflow in this repository that runs the pass on a schedule; the
  recipe is documentation, checked by tests.
- Coverage stays at or above 92 percent, and every executable artifact
  (the wrapper script, the shown commands) is run at least once before
  commit.

## Decisions

The owner **decided D1-D16** on 2026-11-15/16 in the main session. D1
went against the recommended default (4w instead of 2w, so drafting
ships for certain); D3 follows from it; the other fourteen took the
default. After the external review of PR #104 (head `5d28a82`), the
owner extended D5, D6 and D9 and added D21 on 2026-11-16. Each item
keeps the default, its reason and the alternatives, so the record shows
what was weighed. D17-D20 are *settled* by the issue
or the code, and are listed so the spec does not reopen them.

- **D1. Appetite (decided by the owner, 2026-11-16: NOT the default).**
  Owner, 2026-11-16: **4w, so drafting ships for certain.** S3 and S4
  are core, and the circuit breaker cuts drafting only as a last resort
  at the end of week 3. The default was **2w, bet for cycle 07**, after
  0.9.2 is tagged. The work content is 14-20 hours; the model-free core
  is 8-10 of them, and the circuit breaker cuts drafting cleanly.
  Alternative: **4w**, if the owner wants drafting to ship with
  certainty rather than as the first cut.
- **D2. A new verb, and its name (decided by the owner, 2026-11-16: the
  default).** Owner, 2026-11-16: the verb is `nightly`. The default was
  **a new verb, `nightly`**, the issue's own example. It cannot be a
  mode of `findings` (finding 1: no model on that path) or of `lint`
  (finding 2: its exit code is the CI gate and `--strict` means
  something else there). The name says "the unattended run" and does not
  collide with the persona's "curator" or with `promote`. Alternatives:
  `curate` (reads as applying changes), `sweep`, `curation-pass`.
- **D3. Drafting in scope (decided by the owner, 2026-11-16: in scope,
  as core).** Owner, 2026-11-16: drafting is in scope; with D1 it is
  core, not the first cut. The default was **yes, as S3 and S4, cut
  first** by the circuit breaker (the 2w plan). The issue's acceptance
  has a backend line, and finding 5 and 6 make it affordable.
  Alternative: a report-only pitch, with drafting as a follow-up issue
  (then #70 is split or stays open, see D16).
- **D4. Proposals without a model (decided by the owner, 2026-11-16: the
  default).** Owner, 2026-11-16: the default, none. The default was
  **none**: a run without `--backend` writes only the report, as the
  issue's acceptance says. Alternative: draft the mechanical fixes
  model-free (`no-page-id`: add a `page_id`; `superseded-still-indexed`:
  repoint the index line; the weak-orphan `append-index` line from the
  page's title), which changes the issue's first acceptance line.
- **D5. Which kinds are drafted, and the bounds (decided by the owner,
  2026-11-16: the default).** Owner, 2026-11-16: the default, the two
  kinds with these bounds. The default was
  **`missing-cross-link` (updates to the shown unlinked pages, plus one
  log line) and `weak-orphan` whose one inbound link is not from
  `index.md` (one `append-index` line, plus one log line); no `create`;
  edits only to pages the prompt showed.** Everything else is
  report-only. Reason: both fixes are "add a link", are checkable, and
  need no knowledge the model lacks (finding 3, 4). Alternative: also
  draft `stale-claim` re-checks, which asks the model to guess where a
  source moved. Owner, 2026-11-16, after the #104 review: **drafts add
  links only, and that is checked**, syntactically, with no semantic
  diff. A `missing-cross-link` update, with its new links to the
  canonical page removed, must equal the original page text byte for
  byte; the original is read once with `api.read_page`, and its sha256
  is the edit's `base_sha256`, which binds the check to the bytes
  promote will replace. A weak-orphan `append-index` line links that
  page and nothing else. Anything else is refused as out of bounds and
  recorded as a failed draft (S3). Reading used here: removing a link
  replaces `[text](target)` with `text`, so a draft can only turn
  existing words into links; a new "See also" line is refused. Owner,
  2026-11-16: confirmed, link existing words only.
- **D6. How a duplicate is recognised (decided by the owner, 2026-11-16:
  the default).** Owner, 2026-11-16: the default, the deterministic
  name. The default was **the proposal directory name
  `nightly-<kind>-<sha256(kind, sorted pages)[:12]>`; a pending
  directory of that name means "already proposed"; `.applied/` does not
  block; a deleted proposal is redrafted while the finding persists.**
  The name check is race-free through `api.propose`'s exclusive create,
  needs no state file and no format change (finding 5). `plan.json`'s
  `source_path` records the kind and pages for the reader. Alternatives:
  (a) put the pages' sha256s in the key, so a changed page gets a fresh
  draft beside the stale pending one; (b) scan `plan.json` files instead
  of names, which survives a rename; (c) a `.declined/` directory a
  curator moves a draft into, which the check also reads. Owner,
  2026-11-16, after the #104 review, recorded as accepted: when the
  pages a `missing-cross-link` finding names change, the key changes, so
  a second pending proposal can overlap the first; once one is promoted
  the other fails promote with exit 9, and the curator resolves it.
- **D7. The cap (decided by the owner, 2026-11-16: the default).**
  Owner, 2026-11-16: the default, 5. The default was **`--max-proposals
  5`, one proposal per finding, in `findings` order; 0 turns drafting
  off.** Five backend calls bound a run to about ten minutes at the CLI
  timeout. Alternatives: 10; one patch-set per run holding every draft
  (one review, but one bad edit blocks all of them at promote).
- **D8. Report format and location (decided by the owner, 2026-11-16:
  the default).** Owner, 2026-11-16: the default, markdown plus
  `--json`. The default was **markdown to `--report PATH`, or stdout
  without it; `--json` prints one object with `nightly_version: 1`, the
  `findings` object as `findings --json` prints it, the lint violations,
  and the proposals created, pending, capped and failed.** A path inside
  the wiki directory is refused (exit 1). The JSON form lets a host
  (memkernel's curation report) read the run the way it reads
  `findings`. Alternative: markdown only, and the JSON form later; it is
  circuit-breaker cut 1 either way.
- **D9. Exit codes (decided by the owner, 2026-11-16: the default).**
  Owner, 2026-11-16: the default, a code per outcome (0, 1, 2, 3 or 4,
  6, 10). The default was: **0** a completed run, whatever it found or
  drafted; **1** structural lint failed (report written, no proposal);
  **2** unknown or missing backend, before anything runs; **3** or **4**
  at the end when a draft failed (the first failure's code: backend
  error 3, invalid response or bounds refusal 4, or governed drift 4),
  after the report is written and the other drafts kept; **6** the
  report could not be written; **10** a lock timeout while writing a
  proposal (drafting stops, report written). Reason: CI sees a broken
  backend, while one bad draft does not lose the rest. Alternative: like
  `findings`, 0 for every completed run and the failures only in the
  report. Owner, 2026-11-16, after the #104 review: **(a)** an
  `OutputWriteError` from `api.propose` whose cause is `FileExistsError`,
  or after which the directory exists, means "already proposed" (S4);
  any other `OutputWriteError` (a full disk, say) records a failed draft
  and the run exits 6. **(b)** Precedence when several things fail in
  one run: a lock timeout stops drafting, so **10** wins; else a write
  failure (a proposal or the report), **6**; else the first draft
  failure's code, **3** or **4**. A lint failure (**1**) stops before
  drafting, so it never combines with them. The README exit-code table
  states this, and S2 tests each case.
- **D10. When lint fails (decided by the owner, 2026-11-16: the
  default).** Owner, 2026-11-16: the default, the report is written. The
  default was **write the report (violations first, findings as
  information), create no proposal, exit 1.** The report says why
  nothing was drafted, and exit 1 means what it means for `lint`.
  Audit-format errors are reported and do not stop drafting (they fail
  `lint` only under `--strict`). Alternative: the issue's literal
  "touches nothing": no report either, only stderr.
- **D11. The wiki lock (decided by the owner, 2026-11-16: the
  default).** Owner, 2026-11-16: the default. The default was **no lock
  for the reads, as `findings`; each proposal takes and releases the
  lock inside `api.propose`, with `--lock-timeout`; never held across a
  backend call** (finding 7). Alternative: take the lock for the read
  phase to see a consistent wiki, then release it before drafting; it
  blocks promotes during the reads and gains little, since base hashes
  already catch a stale draft.
- **D12. Backend selection (decided by the owner, 2026-11-16: the
  default).** Owner, 2026-11-16: the default, explicit `--backend` only.
  Verified in the main session: `lint --health --backend` is
  explicit-only (`cli.py` lines 405-410, "When omitted, contradictions
  are skipped"), while `ingest` and `query` fall back to
  `WIKI_STUDIO_BACKEND` and then auto-detect (`cli.py` lines 71, 223,
  342). The default was **only an explicit `--backend NAME`; no
  `WIKI_STUDIO_BACKEND`, no auto-detect**, as `lint --health --backend`
  does (finding 9). A cron job must not start calling a model because a
  CLI appeared on PATH or an environment variable set for `ingest` is
  inherited. Alternative: honour `WIKI_STUDIO_BACKEND` but not
  auto-detect.
- **D13. The contradiction check (decided by the owner, 2026-11-16: the
  default).** Owner, 2026-11-16: the default, not run. The default was
  **not run**: the report's findings are the model-free set, and the
  backend is used only for drafting, so the findings part of the report
  is the same with or without `--backend`. Alternative: a
  `--contradictions` flag that runs `lint_health`'s model check and
  reports its pairs.
- **D14. Guidance documents (decided by the owner, 2026-11-16: the
  default).** Owner, 2026-11-16: the default, both paragraphs. The
  default was **amend the "Manual-only in v1" paragraph of
  `ingest-rules.md` (finding 10) and add one paragraph to the persona**
  (S5). The paragraph reaches every ingest prompt through the packaged
  copy; code-copilot-team's override is not edited. Alternative: leave
  `ingest-rules.md` alone and say in the recipe that the pass does not
  promote; the prompt then keeps a sentence that is no longer true.
- **D15. Release vehicle and contract additions (decided by the owner,
  2026-11-16: the default).** Owner, 2026-11-16: the default, 0.10.0
  after 0.9.2 is tagged. The default was: Default **0.10.0**, released
  after 0.9.2 is tagged, not folded into it. A new verb, a capability
  (`nightly`) and, with D8, a format version (`nightly`) in `info` are
  minor additions. Alternative: 0.9.3, as no existing behaviour changes.
- **D16. How #70 closes (decided by the owner, 2026-11-16: the
  default).** Owner, 2026-11-16: **the build PR closes #70**, since
  drafting is planned to ship. The fallback stands: if the last-resort
  cut drops drafting, the build PR names #70 without a closing keyword
  and a follow-up issue carries drafting. The default was **the build PR
  closes #70 when S3 and S4 ship. If drafting is cut, the build PR names
  #70 without a closing keyword, a follow-up issue carries drafting, and
  #70 stays open until a release carries it.** The pitch PR uses no
  closing keyword. Alternative: close #70 with the report-only verb and
  track drafting only in the follow-up.
- **D17. No MCP tool (settled).** The pass is a headless scheduled job.
  An MCP host already has `findings` and `propose`; a tool that calls a
  backend from inside the server adds a model path to the adapter.
- **D18. No ADR, no schema change (settled).** The page schema, the
  patch-set format (`source_path` is free text, finding 5) and
  `findings_version` are unchanged. The verb and its JSON form are
  documented in the README and `docs/knowledge-contract.md`, like
  `findings` was.
- **D19. Attribution (settled).** Proposals record `proposer` from
  `--by`, else `WIKI_STUDIO_ACTOR`, else none, as `propose` does today;
  `plan.json`'s `backend` names the backend.
- **D20. The verb never promotes (settled).** This is the issue's core
  constraint. S2's import and patch tests and S1's byte-identical wiki
  test hold it.
- **D21. A person approves a nightly draft (decided by the owner,
  2026-11-16, after the #104 review).** Owner, 2026-11-16, after the
  #104 review: an agent may review and promote a `nightly-*` proposal,
  but approving one is a person's step. On a wiki whose policy sets
  `auto_approve_on_promote`, the agent stops at propose for a nightly
  proposal, as for a project that reserves approval, because its
  promote would approve (finding 12). The S5 persona paragraph says this
  and points to 0.9.2's "Who approves" step without restating it. This
  keeps a person in the chain from a model draft to memkernel's governed
  import, which takes approved pages only. Guidance only: no code
  refuses such an approval (No-gos). Alternative not taken: treat the
  agent's review as authorship, so the agent approves a nightly page as
  it approves its own.

## Circuit breaker

Core is all six scopes (D1, D3): the `nightly` verb that runs lint and
findings and writes one report (S1, S2), drafts bounded proposals with
an explicit `--backend` (S3) and creates no duplicate on rerun (S4),
with its recipe checked (S5) and the release (S6). Never S3 without S4:
drafting without the dedup check creates duplicates every night.

The cut order, first to last, each with its trigger:

1. **End of week 1, if S1 and S2 are not downhill:** cut the `--json`
   report (D8) and the pending-proposals section of the report.
2. **End of week 2, if S3 is not over the hill** (the `curate` prompt
   and the bounds check settled and passing with the test backend): cut
   weak-orphan drafting; `missing-cross-link` drafting stays (D5).
3. **Last resort, end of week 3, if S3 is not downhill:** cut S3 and S4
   together. The verb ships without `--backend` and `--max-proposals`
   (no flag for an unbuilt feature), a follow-up issue carries drafting,
   and the build PR names #70 without a closing keyword (D16).

- **End of week 4.** S6 ships what is true. If the release cannot be
  cut, the change waits under `[Unreleased]`.
- **Never, to save time:** call promote, approve or `promoter.py` from
  the pass; write into the wiki directory, `.audit/` included; hold the
  wiki lock across a backend call; accept a draft that changes anything
  but the links D5 allows (the link-only check); resolve a backend by
  environment or auto-detect in the pass; put a model on any path from `findings`,
  `approve` or `review_state`; add a runtime dependency, an exit code or
  an MCP tool; change the page schema or the patch-set format; weaken
  or skip a test.

"Exhausted" means four working weeks have passed. A third review round
on one scope is not exhaustion. It is an escalation to the owner, who
chooses a fix session, a cut from the list above, or a hold.

## Questions for the owner

Asked by the main session on 2026-11-15/16; all answered. The owner
chose the default for fifteen of the sixteen and decided D1 against it.
D1 **4w, so drafting ships for certain** (S3 and S4 core; drafting cut
only as a last resort at the end of week 3); D2 the verb is `nightly`;
D3 drafting in scope, as core; D4 no proposal without a model; D5
`missing-cross-link` and the `append-index` weak-orphan case, no
`create`, only shown pages; D6 the deterministic
`nightly-<kind>-<key>` name, pending directories only; D7 a cap of 5;
D8 markdown to `--report` or stdout, plus `--json`; D9 a code per
outcome (0, 1, 2, 3 or 4, 6, 10); D10 a lint failure still writes the
report, with no proposal and exit 1; D11 no lock for the reads, the
lock only inside `api.propose`; D12 drafting only with an explicit
`--backend`; D13 no contradiction check; D14 amend `ingest-rules.md`
and add the persona paragraph; D15 release 0.10.0 after 0.9.2 is
tagged; D16 the build PR closes #70, with the fallback if the
last-resort cut drops drafting.

After the external review of PR #104 (head `5d28a82`), the owner decided
three more points on 2026-11-16: D5 drafts add links only, enforced by
the syntactic link-only check; D21 a person approves a nightly draft,
and on an auto-approving wiki the agent stops at propose; D9 an
`OutputWriteError` caused by an existing directory is "already
proposed" and any other exits 6, with the precedence 10, then 6, then
the first draft failure's 3 or 4. D6 records the overlapping-proposal
case as accepted.

## Bet log

| Date | bet_status | Note |
|------|------------|------|
| 2026-11-15 | shaping | Pitch drafted from wiki-studio #70 (no comments) and cooldown-after-05 (the owner's order: #69, then #70, then #54). wiki-studio read at main e2a80c7 (0.9.2 merged, not tagged): `findings.py`, `health_lint.py`, `lint.py`, `api.py` (lint, propose, ingest, prepare_backend), `ingestor_multi.py`, `prompt.py`, `backends/` (copilot_cli, test), `wikilock.py`, `cli.py`, `paths.py`, `contract.py`, the persona and `ingest-rules.md`. |
| 2026-11-15 | shaping → shaped | 6 scopes, 2w, work content 14-20h (model-free core 8-10h). Core: S1 (pass and report), S2 (verb), S5's report-only recipe, S6. Cut first: `--json`, then weak-orphan drafting, then S3 and S4 together. 20 decisions; D1-D16 open for the owner with defaults, not yet asked (AskUserQuestion was unavailable to the shaping agent). |
| 2026-11-16 | shaped (decided) | Owner answered D1-D16 in the main session (2026-11-15/16). Fifteen defaults; D1 against the default: 4w, so drafting ships for certain. Updated: frontmatter (`appetite: 4w`, circuit breaker), finding 9 (cites `cli.py` 405-410 and 71, 223, 342, verified by the main session for D12), Appetite (same 14-20h estimate; the extra time buys review rounds, prompt design against a real backend and the dedup edge cases; a four-week layout), S3 (a manual real-backend check attached to the build PR), S6, Decisions (each answer recorded), Circuit breaker (all six scopes core; cuts at the end of weeks 1, 2 and 3, drafting only as the week-3 last resort, never S3 without S4), Questions for the owner (answered). The owner kept S3's manual real-backend check (2026-11-16), a by-hand step on the build PR. |
| 2026-11-16 | shaped (revised after review) | External review of PR #104 (head 5d28a82) asked for changes; the owner decided three points the same day. D5 extended: drafts add links only, checked syntactically (a missing-cross-link update with its new canonical links removed equals the `api.read_page` original byte for byte, bound by `base_sha256`; a weak-orphan index line links that page only; anything else a failed draft). D21 added: a person approves a nightly draft; on an auto-approving wiki the agent stops at propose. D9 extended: `OutputWriteError` from an existing directory is "already proposed", any other exits 6; precedence 10 over 6 over the first 3 or 4, and 1 never combines. Smaller fixes: finding 8 and S2 add `tests/test_cli_contract.py`'s `_VERBS` (line 29) and CLAUDE.md's `cli.py` layout line (line 33); S5's recipe passes `--by`; S1 resolves symlinks before refusing a report path inside the wiki; D6 and a rabbit hole accept overlapping pending proposals after a finding's page set changes (one fails promote with exit 9). Updated: frontmatter circuit breaker (never list), finding 8, Solution shape, S1, S2, S3, S4, S5, rabbit holes, no-gos, Decisions (intro, D5, D6, D9, D21), Circuit breaker (never list), Questions for the owner. |
| 2026-11-16 | bet | Bet for cycle 07. |
| 2026-11-16 | building | Cycle 07 started; hill chart initialized. |
