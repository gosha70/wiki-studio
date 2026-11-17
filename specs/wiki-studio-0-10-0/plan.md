---
spec_mode: full
feature_id: wiki-studio-0-10-0
risk_category: feature
justification: "A new public verb with flags, a JSON form, exit-code uses and an info capability (a released contract), the first unattended model path in the package, writing proposals beside a wiki shared with memkernel's governed import, with a link-only check that is the only thing standing between a model's rewrite and a proposal, a dedup rule that must survive concurrent runs, a checked cron and CI recipe, persona guidance on who approves, and a release; a full spec pins the check's grammar, the exit precedence, the per-phase truth rule and the cut order before an unattended build."
status: approved
date: 2026-11-16
collaboration_mode: single
origin:
  issue: 70
  urls:
    - https://github.com/gosha70/wiki-studio/blob/main/specs/pitches/70-propose-only-curation-pass/pitch.md
    - https://github.com/gosha70/wiki-studio/issues/70
    - https://github.com/gosha70/wiki-studio/pull/104
    - https://github.com/gosha70/wiki-studio/pull/107
    - https://github.com/gosha70/wiki-studio/issues/54
    - https://github.com/gosha70/memkernel/issues/59
    - https://github.com/gosha70/wiki-studio/blob/main/specs/retros/cooldown-after-05.md
  origin_claim: |
    Issue #70 (no comments on 2026-11-15), shaped by the bet pitch
    specs/pitches/70-propose-only-curation-pass/pitch.md (cycle 07,
    building; reviewed in PR #104 over two rounds, merged 51114b5; bet and
    cycle start PR #107 at 22803c6) from specs/retros/cooldown-after-05.md
    (the owner's shaping order: #69, then #70, then #54). Related: #54 and
    gosha70/memkernel#59 Phase 3. Problem, as the pitch states it: "Nothing
    runs the checks unattended, and nothing drafts a fix while the curator
    is away. Issue #70 asks for that run, with one condition: it prepares
    and stops. It may draft proposals into the proposals directory, but it
    never promotes or approves. A curator reviews what it drafted with the
    existing commands." The pass "must be repeatable without piling up
    duplicates". The issue's acceptance lines, as the pitch carries them:
    a run without a backend creates no proposal; with the test backend
    proposals exist under the proposals directory and the wiki directory is
    byte-identical before and after; a second run on an unchanged wiki
    creates no directory and makes no backend call; and the pass touches
    nothing when lint fails. Solution shape: "One new verb over existing
    pieces. No change to findings, lint, promoter.py, the page schema, the
    patch-set format or the exit-code table's meanings." Owner decisions
    D1-D16 (2026-11-15/16; D1 against the default: 4w, drafting ships for
    certain), D5, D6 and D9 extended and D21 added after the #104 review
    (2026-11-16): drafts add links only, checked syntactically against the
    api.read_page original whose sha256 is the edit's base_sha256 (owner
    confirmed: link existing words only); the deterministic name
    nightly-<kind>-<sha256(kind, sorted pages)[:12]>; exit codes 0, 1, 2,
    3/4, 6, 10 with precedence 10, then 6, then the first draft failure,
    an OutputWriteError from an existing directory meaning "already
    proposed"; a person approves a nightly-* draft and on an auto-approving
    wiki the agent stops at propose. The #104 reviewer's two notes on D9: an
    unwritable report always exits 6 whatever else failed, reason on
    stderr; a failed proposal write stops drafting as a lock timeout does.
    Release 0.10.0 with a nightly capability and format version in info
    (D15); the build PR's merge closes issue 70 through pr.closes, with the
    D16 fallback if the last-resort cut drops drafting.
---

# Plan: wiki-studio 0.10.0 — a propose-only curation pass

The bet pitch `specs/pitches/70-propose-only-curation-pass/pitch.md` is the
shaping record (reviewed on PR #104 in two rounds, merged 51114b5; owner
decisions D1-D16 and D21 on 15-16 November 2026; bet and cycle 07 start
PR #107 at 22803c6). Its "Findings from the code" were re-checked against
`main` cfe1ebe (0.9.2 released) on 16 November 2026. Most hold with current
line numbers (spec, design references): `findings.findings` 187, `api.propose`
596 with the exclusive create at 676-682, `api.lint` 1223, `lint.py` 433,
`health_lint.py` 110, 158 and 236, `_VERBS` 990, `prepare_backend` 252,
`INDEX_LOG_ACTION_RULE` 64, the test backend's dispatch 59, `.applied` at
`paths.py` 74, "Manual-only in v1" 82-88, the frozen eval pin at
`tests/test_frozen_runs.py` 222. Issue #70's body was not re-fetched while
this bundle was written (no shell or network in the writing session); its
words are taken from the pitch, and the origin-alignment record at approval
reads the issue itself. Facts found while re-checking that shape the spec:

1. **`missing-cross-link` names every unlinked page, not five.**
   `_check_missing_cross_links` builds `pages=[canonical_rel] + unlinked`
   with all unlinked pages (`health_lint.py` 305); only the description
   names the first five (311). The pitch says the finding names "up to five
   pages". Owner, 2026-11-17: one draft shows and edits all of the
   finding's unlinked pages (FR-014, FR-019); the name is keyed on all of
   the finding's pages (FR-015, D6).
2. **`findings` keeps a health finding's pages in order and drops the root
   index and log.** The scope filter at `findings.py` 205-210 keeps in-scope
   pages in their order; `pages[0]` is the canonical page of a
   `missing-cross-link` (FR-014 also checks the description names it).
   A weak orphan's finding names only the orphan; whether its single inbound
   link comes from `index.md` is computed from the index's links with
   `health_lint._intra_wiki_links_from` (already imported by `findings.py`
   at 33), not by parsing the description.
3. **The CLI renderer is not fully generic over `task`.** Finding 6 says a
   new task needs no renderer change. `_render_plain_text_prompt`'s
   wiki-state intro (`copilot_cli.py` 204-212; the block runs to 237) tells the model to
   "integrate the new source", to add an index link "whenever you create a
   new page", and calls the candidate pages "selected by lexical overlap
   with the source", which is wrong for a finding whose bounds forbid a
   create. The spec adds one branch keyed on the `curate` task, leaving
   every other task's output byte-identical (FR-017).
4. **`api.propose` turns any `FileExistsError` into "already exists".**
   At 681-682 a `FileExistsError` from `write_patch_set_dir` becomes
   `OutputWriteError("proposal dir already exists")` with no clean-up.
   `_create_patch_set_dir` uses `mkdir(parents=True, exist_ok=False)` under
   `COLLISION_ERROR` (`ingestor_multi.py` 195-197), which also raises `FileExistsError` when the
   proposals path or a parent is a regular file, and then no proposal
   directory exists. D9(a)'s "cause is `FileExistsError`, or after which the
   directory exists" would read that as "already proposed" and exit 0. The
   spec classifies by the directory's existence after the error (FR-026).
5. **An `OSError` can escape `api.propose` raw.** `WikiLock.acquire`
   opens the lock file (`wikilock.py` 173-179) inside `with WikiLock(...)`
   at `api.py` 676, outside the try at 677, so a lock file that cannot be
   created raises `OSError`, which `cli.main` does not catch. The pass
   treats it as a write failure (FR-021).
6. **`lint` resolves a backend only when one is given; `prepare_backend`
   auto-detects on None.** `api.lint` guards with `backend is not None`
   (1246); `prepare_backend(None)` falls to `resolve_backend(None)`, which
   reads `WIKI_STUDIO_BACKEND` and then auto-detects (`backends/__init__.py`
   137-144). The pass therefore calls `prepare_backend` only with a given
   name (FR-013), and its help does not use `_BACKEND_HELP_SUFFIX` (71).
7. **A proposals directory inside the wiki is not refused today.**
   `WikiPaths.resolve` refuses a search cache inside the wiki (144-146) but
   not a proposals directory; with one inside the wiki, `api.propose` would
   write there, which the circuit breaker's never-list forbids for the
   pass. The spec refuses it when drafting is on (FR-013).
8. **The single-writer test is a grep.** `TestE2ESingleWriterInvariant`
   (`tests/test_e2e.py` 1054-1093) flags write calls on lines that name
   `wiki_dir`; it would not see a report written into the wiki through
   another variable. The spec's real guard is the byte-identical snapshot
   of every file under the wiki in each phase's tests (FR-007), plus the
   report-path refusal (FR-005).
9. **The install-line resolver reads `bash` blocks only.**
   `pip_install_commands` (`tests/helpers/quickstart_blocks.py` 212-225)
   skips a `yaml` block, and the job's `PAGES` (`ci.yml` 274) lists four
   pages. The recipe shows its install line in a `bash` block, joins
   `PAGES`, and the workflow's install step is checked equal to it
   (FR-028, FR-029).
10. **Persona positions.** The 0.9.2 checks find the loop's first promote
    and approve commands and require the "Who approves" markers before them
    (`tests/test_maintainer_persona.py` 328-379). A paragraph placed after
    the loop with no command span keeps those checks unchanged (FR-030).
11. **`ingest-rules.md` is a prompt document whose packaged copy is not
    fingerprinted**; only project overrides are hashed
    (`contract.py` 401-416), and the eval copy pinned at
    `tests/test_frozen_runs.py` 222 is a separate file (FR-031).

## Departures from the pitch

Each is recorded so the origin-alignment record at approval can cite it.

1. **Docs and contract claims move to US6.** The pitch's S2 puts the README
   section, the exit-code table, `docs/knowledge-contract.md` and the
   `info` capability in S2. The gating reviewer reviews each phase on its
   own diff, and 0.9.0's first phase was blocked three rounds for a doc that
   described later-phase code; S2's verb gains `--backend` and its drafting
   codes only in S3, and cut 1 decides whether the JSON format ships. These
   surfaces therefore land in US6 (FR-032, FR-033); each phase's own
   `--help` text is its documentation until then (FR-009).
2. **`--backend`, `--max-proposals` and `--by` land in US3**, not US2: the
   pitch's own rule "no flag for an unbuilt feature" (cut 3) applied per
   phase (FR-009, FR-013).
3. **The precedence tests move to US3.** The pitch's S2 tests a lock timeout
   after a failed draft, a write failure after a failed draft and the 3/4
   order; none can run before drafting exists (FR-023(i)). US2 tests the
   cases it can: lint 1, report 6, and report 6 over lint 1 (FR-012).
4. **The name rule is owned by US3.** The pitch builds S4's naming rule
   before S3; the spec puts it in US3, the first phase that writes a
   proposal (FR-015), and keeps "already proposed" in US4 (FR-025, FR-026).
   Between the two phases a rerun's exclusive create fails and the run
   exits 6; no duplicate is ever created.
5. **Reviewer note 1 extends D9's precedence.** An unwritable report exits 6
   whatever else failed, a lock timeout and a lint failure included, so 6
   precedes 10 and 1 in that case (FR-010). D9's "1 never combines" holds
   for drafting outcomes only.
6. **"Already proposed" needs the directory** (fact 4; FR-026). D9(a)'s
   "cause is `FileExistsError`" alone would read a proposals path that is a
   regular file as already proposed and exit 0. Owner, 2026-11-17: the
   directory must exist after the error; any other `FileExistsError` is a
   write failure, exit 6, and drafting stops (FR-021).
7. **Reviewer note 2: a failed proposal write stops drafting** (the pitch's
   S3 recorded it and went on); the remaining draftable findings are
   recorded `drafting stopped: write failed` with no backend call (FR-021).
8. **The renderer gains a `curate` branch** (fact 3; FR-017).
9. **A proposals directory inside the wiki is refused with drafting on**
   (fact 7; FR-013). Owner, 2026-11-17: refused with exit 1, symlinks
   resolved, before any backend call.
10. **One draft shows and edits every unlinked page** (fact 1; FR-014,
    FR-019). The pitch's finding 4 says a `missing-cross-link` "names the
    canonical page and up to five pages", and S3 shows "the unlinked pages
    from the finding". The code lists every unlinked page
    (`health_lint.py` 305). Owner, 2026-11-17: the prompt shows the
    canonical page and all unlinked pages, the draft must update each of
    them, the link-only check applies to each update independently and one
    failing update refuses the whole draft, and each update carries the
    `base_sha256` of its own `api.read_page`. No page cap and no flag; a
    finding is still one backend call (one attempt of FR-016).
11. **Over-reaching drafts come from stub backends.** The pitch says "an
    over-reaching draft from the test backend"; the test backend stays
    deterministic and valid, and stub backends (or the test backend
    patched behind `--backend test`) supply the refused shapes (FR-023).
12. **D7 changed: two bounds instead of one.** D7 set `--max-proposals 5`,
    "one proposal per finding, in `findings` order", with the reason "five
    backend calls bound a run". Owner, 2026-11-17, against D7's wording:
    `--max-proposals N` counts proposals actually created, and a derived
    bound of `2 × N` backend calls (attempts) limits cost; it is a named
    constant (`ATTEMPTS_PER_PROPOSAL = 2`), not a flag. A refused or failed
    draft uses an attempt but no proposal slot, so findings later in the
    fixed order still get drafted; no state is kept between runs; each
    refused or failed finding is listed with its reason; `--max-proposals 0`
    makes no attempt (FR-016, FR-022). Already-proposed and overlapping
    findings use neither bound.
13. **A read error from `api.lint` or `api.findings` writes no report.** The
    pitch does not say; the spec ends the run with that error's code, as
    `findings` itself does (FR-001).
14. **The recipe's install line is unpinned** (`pip install wiki-studio`, as
    README's), so it resolves at every phase and needs no seventh version
    place (FR-028).
15. **Links inside code are refused; aliases are linked as they stand.**
    The pitch's link-only check does not mention code. A link added inside a
    fenced block or an inline code span breaks the code or renders as
    literal text, so FR-019 refuses it, reading code regions with
    `prose_lint.open_fence` and `closes_fence` (`prose_lint.py` 76-105) and
    same-line backtick spans; the prompt asks for the first mention outside
    code (FR-017). With every unlinked page required (FR-014), a page whose
    only mentions are inside code makes every draft for that finding
    refused, listed under Failed each run. `missing-cross-link` counts a
    glossary avoid term as a mention (`health_lint.py` 256); linking it is
    allowed and the page keeps the avoided term, since the check forbids
    changing words (FR-019; reviewer's notes, 2026-11-17).

After the external review of this spec's PR #108 (head db1a904), the owner
decided four points on 17 November 2026:

16. **The link-only check stays as is (owner, against the reviewer's
    recommendation).** The reviewer showed three shapes that pass FR-019:
    an empty-text link `[](<canonical>)`, an arbitrary existing word linked
    ("We set a [retry](<canonical>) budget"), and a link nested inside an
    existing link (`[[the policy](<canonical>)](other.md)`), and recommended
    constraining the link text to the slug, the spaced slug or a glossary
    avoid term. The owner declined: the check does not constrain the added
    link's text or nesting, the three shapes are accepted, and the person
    who approves every `nightly-*` proposal (D21) reviews them. FR-019 says
    so in one sentence; no stricter rule and no fixture for one (risk
    below). After the re-review of 822bc69 the owner took the reviewer's
    smallest tightening: an added link whose text is empty or only
    whitespace is refused (`empty link text`, one fixture), because it is
    the one shape a person cannot see on the rendered page. The other two
    shapes stay accepted.
17. **The weak-orphan index line has a fixed form.** The pitch says the
    line "links that page and nothing else"; owner: it is exactly
    `- [<title>](<orphan path>)`, the title from the orphan's frontmatter
    `title:`, the path as the index links pages; any other line is refused,
    exit 4 (FR-019(b)). The test backend emits that form (FR-017).
18. **The log line's form is checked.** The pitch only says the
    `append-log` line holds no link; owner: it must be
    `- <run's UTC date> — <verb> <slug> (<page-type>): <why>`, the verb from
    `NIGHTLY_LOG_VERBS = ("link",)`, the slug and type of a page the draft
    edits (the orphan for a weak orphan), the why free text with no link.
    Structural lint does not read log lines (the reviewer verified;
    `lint.py` names `log.md` only for reachability, 22 and 61), so FR-019
    is their only check.
19. **FR-030's wording.** A `nightly-*` proposal already exists when the
    agent sees it, so the persona says the agent does not promote it on an
    auto-approving wiki, instead of "stops at propose"; the rest of D21
    stands.

The origin block above is unchanged: these are decisions on the derived
artifacts, recorded here, not a change to the origin.

Close target: issue 70, by the build PR's merge (`pr.closes: [70]`), with
D16's fallback (FR-038). No other issue is closed; the pitch PR (#104), the
bet PR (#107) and this spec PR use no closing keyword.

## Architecture decisions

- **ADR-1: One module, one entry.** `nightly.py` holds the pass, the result,
  the rendering, the name, the link-only check and the report writer;
  `api.nightly` is a thin additive entry; `cli.py` parses, refuses the
  report path, calls, renders, writes and maps the code. `nightly.py`
  imports `api` lazily (inside functions) because `api.py` imports
  `nightly`.
- **ADR-2: Existing write path only.** Proposals are written by
  `api.propose`, whose exclusive create is the dedup's race guard and whose
  lock is the only lock the pass takes. No new state file, no format change.
- **ADR-3: The link-only check is syntactic and fails closed.** Anything the
  link pattern does not recognise as a link to the canonical page stays in
  both texts, so it can only make the comparison fail (a titled link, an
  image, a reference link), never pass a rewrite. It guards the words, not
  the link's text or nesting (departure 16); the index and log lines have
  fixed forms (departures 17, 18).
- **ADR-4: Precedence is computed once.** Outcomes are recorded as they
  happen; `NightlyResult.exit_code` applies FR-010 (2)-(6) and the CLI
  applies (1) after writing the report.
- **ADR-5: Each phase is true on its own diff.** The report grows a section
  per phase (Proposals in US3), flags land with their feature, and every
  claim about the released contract lands in US6.

## Files

| File | Phase | Change |
|---|---|---|
| `src/wiki_studio/nightly.py` (new) | US1, US3, US4 | The pass, `NightlyResult`, rendering, `check_report_path`, `write_report`, pending listing (US1); drafting, name, link-only check (US3); already-proposed (US4) |
| `src/wiki_studio/api.py` | US1, US3 | `nightly(paths)` (US1); its `backend`, `max_proposals`, `by` keywords (US3); `__all__` |
| `src/wiki_studio/contract.py` | US1, US6 | `NIGHTLY_FORMAT_VERSION = 1` (US1); `FORMATS["nightly"]`, `CAPABILITY_NIGHTLY` (US6) |
| `src/wiki_studio/cli.py` | US2, US3 | The verb, `--report`, `--json` (US2); `--backend`, `--max-proposals`, `--by`, help (US3) |
| `src/wiki_studio/prompt.py` | US3 | `CURATE_TASK`, `compose_curate_prompt` |
| `src/wiki_studio/backends/copilot_cli.py` | US3 | The `curate` branch of the wiki-state lead-in |
| `src/wiki_studio/backends/test.py` | US3 | The `curate` branch |
| `src/wiki_studio/schema/WIKI_MAINTAINER.md` | US5 | The `nightly-*` paragraph |
| `src/wiki_studio/schema/ingest-rules.md` | US5 | The "Manual-only in v1" sentence |
| `src/wiki_studio/__init__.py`, `pyproject.toml` | US6 | Version |
| `tests/test_nightly.py` (new) | US1 | FR-008 |
| `tests/test_nightly_cli.py` (new) | US2 | FR-011, FR-012 |
| `tests/test_nightly_drafting.py` (new) | US3, US4 | FR-023, FR-027 |
| `tests/test_nightly_recipe.py` (new) | US5 | FR-029 |
| `tests/test_maintainer_persona.py` | US5 | FR-030's test |
| `tests/test_cli_contract.py` | US2, US6 | `_VERBS` (US2); version (US6) |
| `tests/test_info_contract.py` | US6 | Formats, capabilities, resolver |
| `tests/integration/test_quickstart_memkernel.py` | US6 | Pins |
| `docs/nightly.md` (new) | US5 | The recipe |
| `.github/workflows/ci.yml` | US5 | `docs/nightly.md` in `PAGES` (274) |
| `README.md` | US6 | Section, exit table, version comment |
| `docs/knowledge-contract.md` | US6 | `info` rows, `## Nightly` |
| `docs/quickstart-memkernel.md` | US6 | Two pins |
| `CHANGELOG.md` | US6 | `[0.10.0]` |
| `CLAUDE.md` | US1, US2 | `nightly.py` layout line (US1); `cli.py` line gains `nightly` (US2) |

## Interfaces

```python
# src/wiki_studio/nightly.py
NIGHTLY_PROPOSAL_PREFIX = "nightly-"
NIGHTLY_KEY_LENGTH = 12
DEFAULT_MAX_PROPOSALS = 5
ATTEMPTS_PER_PROPOSAL = 2          # FR-016: backend calls per run are bounded at 2 × max_proposals

def proposal_name(kind: str, pages: Sequence[str]) -> str: ...
def code_regions(text: str) -> list[tuple[int, int]]: ...              # FR-019: fenced blocks and inline spans, as offsets
def check_report_path(report: Path, paths: WikiPaths) -> Path: ...   # ValueError inside the wiki
def write_report(text: str, path: Path) -> None: ...                  # temp file + os.replace; OSError re-raised
def strip_links_to(text: str, page: str, target: str) -> str: ...
def count_links_to(text: str, page: str, target: str) -> int: ...
def link_only_problems(...) -> list[str]: ...                          # FR-019; empty = within bounds
def run(paths: WikiPaths, *, backend: Backend | None, backend_name: str | None,
        max_proposals: int, by: str | None) -> NightlyResult: ...

@dataclass(frozen=True)
class NightlyResult:
    run_at: str; package_version: str; wiki_dir: Path; proposals_dir: Path
    lint: LintResult; findings: FindingsResult
    needs_curator: tuple[Finding, ...]; pending: tuple[PendingProposal, ...]
    warnings: tuple[str, ...]
    # US3/US4: drafting: DraftingState; created, already_proposed, not_drafted, failed
    @property
    def exit_code(self) -> int: ...      # FR-010 (2)-(6)
    def as_dict(self) -> dict[str, Any]: ...
    def render_markdown(self) -> str: ...

# src/wiki_studio/api.py
def nightly(paths: WikiPaths, *, backend: str | Backend | None = None,
            max_proposals: int = DEFAULT_MAX_PROPOSALS, by: str | None = None) -> NightlyResult: ...

# src/wiki_studio/prompt.py
CURATE_TASK = "curate"
def compose_curate_prompt(*, finding: Finding, shown: Mapping[str, str], editable: Sequence[str],
                          index_md: str, run_date: str, schema_files: Mapping[str, str]) -> dict[str, Any]: ...
```

CLI: `wiki-studio nightly [--report PATH] [--json] [--backend NAME] [--max-proposals N] [--by NAME]`
plus the common path options and `--lock-timeout`.

## Phases (one auto-build phase per `## US<n>:` group of tasks.md)

| Phase | Pitch scope | What | Main files |
|---|---|---|---|
| US1 | S1 | The model-free pass, result, markdown, JSON object, report path and writer, pending listing, no-write snapshot | `nightly.py`, `api.py`, `contract.py`, `tests/test_nightly.py`, `CLAUDE.md` |
| US2 | S2 | The verb with `--report` and `--json`; codes 0, 1, 6; the no-promote guarantee | `cli.py`, `tests/test_nightly_cli.py`, `tests/test_cli_contract.py`, `CLAUDE.md` |
| US3 | S3 | Explicit backend, name, order and cap, `curate` prompt, edits, link-only check, writing, failures, Proposals section, precedence | `nightly.py`, `api.py`, `cli.py`, `prompt.py`, `backends/copilot_cli.py`, `backends/test.py`, `tests/test_nightly_drafting.py`, `tests/test_nightly_cli.py` |
| US4 | S4 | Already proposed: pending check and the race | `nightly.py`, `tests/test_nightly_drafting.py` |
| US5 | S5 | Recipe and its checks; persona paragraph; `ingest-rules.md` | `docs/nightly.md`, `tests/test_nightly_recipe.py`, `.github/workflows/ci.yml`, `WIKI_MAINTAINER.md`, `tests/test_maintainer_persona.py`, `ingest-rules.md` |
| US6 | S6 | README, contract docs, `info` capability and format, CHANGELOG, version, audit | `README.md`, `docs/knowledge-contract.md`, `contract.py`, `tests/test_info_contract.py`, `CHANGELOG.md`, version places |

Order follows the pitch: S1 first; S2 needs S1's result; S3 then S4 (never
S3 without S4 in the release; between the phases a rerun fails closed,
departure 4); S5 and S6 need the others. Cuts follow FR-037.

## Owner-run steps

1. Before the driver: review and approve this bundle; write
   `automation.json` (`pr.closes: [70]`) and the origin-alignment record in
   the approval commit.
2. After US3 lands, or on the build PR: the manual real-backend check
   (FR-024) if the build session could not run it; attach the report and
   drafts to the PR; any prompt revision is a follow-up commit, re-reviewed.
3. Check the build PR is open on the branch tip, that its body carries the
   closing line from `pr.closes`, then review and label it.
4. If cut 3 was taken: remove 70 from `pr.closes` (or the PR body's closing
   line) before merge and file the drafting follow-up issue (FR-038).
5. After the merge: the release PR (CHANGELOG date, `docs/compatibility.md`
   0.10.0 row naming the green `main` run, FR-036), then tag and release by
   `release.yml`'s header steps. Hill chart by hand.

## Unattended run

The parent session writes `specs/wiki-studio-0-10-0/automation.json` at
approval. This plan assumes 0.9.2's shape: profile `pr`, branch
`feature/wiki-studio-0-10-0` off `main`, six phases (`max_phases: 6`), the
DeepSeek correctness reviewer gating (max 3 rounds per phase), the test
command of `specs/wiki-studio-0-9-2/automation.json`, `pr.closes: [70]`.
After the run, re-run the gate on the branch head before trusting `landed`,
and check no phase was bypassed without a per-phase record (the known
driver defects).

## Test strategy

- **Byte-identical wiki.** Every run in every phase's tests is wrapped by a
  snapshot of every file under the wiki (path and sha256), `.audit/`
  included; no lock file after a model-free run (FR-007).
- **No model without `--backend`.** `resolve_backend`, `auto_detect` and
  `WIKI_STUDIO_BACKEND` patched or set to prove they are never reached
  (FR-008(h), FR-023(g)).
- **The link-only check by fixture.** One fixture per refused shape the
  reviewer named (a reworded sentence, a "See also" line, a changed
  frontmatter line, a second index link) plus the bounds cases, links
  inside a fenced block and an inline span, a page mentioning the entity
  only inside code, a linked glossary alias, the index line's fixed form
  (extra prose, a different title, a second link), the log line's form (a
  wrong date, a slug not edited, a link in the why), and unit tests of the
  link and code-region helpers (FR-023(c), (d)). No fixture for link text
  or nesting (departure 16).
- **The two bounds.** A finding that always fails does not block later
  ones; the attempt bound stops at `2 × N`; `--max-proposals 0` makes no
  backend call; a second run behaves the same (FR-023(f)).
- **End to end.** Created proposals promote cleanly and clear their finding
  (FR-023(b)); the issue's three acceptance lines are named tests.
- **Precedence and stopping.** One case per FR-010 ordering and per note
  (FR-012, FR-023(i), (j)); a counting backend proves no call after a stop
  and on rerun (FR-027).
- **Shown commands.** Every `wiki-studio nightly` line in `docs/nightly.md`
  parses with the CLI's parser and runs in-process; the wrapper runs once;
  the workflow's structure is asserted; the persona's existing command
  checks cover the new bare verb mention (FR-029, FR-030).
- **Regression.** `tests/test_findings.py`, the renderer tests and
  `ingest_multi`'s tests unedited; coverage at or above 92 percent.

## Risks

- **Real models reproduce a page imperfectly** (a dropped trailing newline,
  a normalised quote), so the link-only check refuses many drafts.
  Mitigation: refusal is safe (a failed draft, exit 4); the manual check
  (FR-024) tunes the prompt; FR-016's attempt bound (2 × N backend calls)
  bounds the cost, and a refusal uses no proposal slot.
- **Link text and nesting are unconstrained (owner, 2026-11-17; departure
  16), except empty link text, which is refused.** Two shapes pass FR-019:
  an arbitrary existing word linked ("We set a [retry](<canonical>)
  budget"), and a link nested inside an existing link
  (`[[the policy](<canonical>)](other.md)`). Consequence: a draft can link
  words that are not a real mention of the entity, or produce nested-link
  markdown that renderers treat
  inconsistently; the finding may even clear on such a link. Mitigation:
  D21, a person approves every `nightly-*` proposal and reviews its diff
  before promote (FR-030), and every update stays bound to its base hash.
  The PR #108 reviewer recommended constraining the link text to the slug,
  the spaced slug or a glossary avoid term; the owner declined, so the
  build adds no such rule.
- **Findings that fail every night** (a page whose only mentions are inside
  code, a page a model cannot reproduce, owner, 2026-11-17). Each such
  finding uses one attempt per run and no slot, so later findings in the
  fixed order still get drafted while attempts remain; no state is kept
  between runs, so the same findings are tried, and listed under Failed
  with their reason, every night until a curator fixes the page. If more
  than `2 × N` findings at the head of the order always fail, they use all
  the attempts and later findings are never reached; the report shows them
  as `cap: attempts`, and the curator's remedy is to fix the failing pages
  or raise `--max-proposals` (FR-016, FR-022). Cost per run stays bounded at
  `2 × N` backend calls.
- **Prompt size grows with the unlinked pages.** One draft shows the
  canonical page and every unlinked page, and must reproduce each updated
  page in full (owner, 2026-11-17), so a finding with many unlinked pages
  makes a long prompt and a long reply, and more chances for one page to
  fail the check and refuse the whole draft. When a prompt exceeds the
  backend's input, the CLI's refusal, non-zero exit or timeout is a
  `BackendInvocationError`, recorded as a failed draft `backend error`
  (exit 3); a truncated or partial reply fails parsing, the link-only check
  or validation, recorded as a failed draft (exit 4) (FR-021). Never a
  crash, and no new cap or flag; the next finding is still drafted, and the
  finding recurs on the next run. Mitigation: the manual check (FR-024)
  looks at a large finding; a page cap would be a later owner decision.
- **A third review round on a scope.** Escalation to the owner, per the
  pitch's circuit breaker; the spec pins the grammar and the precedence so
  rounds argue wording, not behaviour.
- **Concurrent writers.** The pass reads without the lock; base hashes make
  a draft from a half-applied page fail promote (exit 9), as the pitch
  accepts.
- **Overlapping pending proposals** when a finding's page set changes (D6,
  accepted): the second fails promote with exit 9.
- **Declined drafts return nightly** (D6, accepted); FR-016's proposal cap
  bounds it.
- **Lock tests in one process.** A held `WikiLock` in the test process may
  not conflict with the pass's lock on every platform's lock primitive;
  the tests patch `api.propose` to raise `PromoteApplyError(reason="lock_timeout")`
  or hold the lock from a helper process.

## Success criteria

1. `wiki-studio nightly` writes one report (markdown or JSON), drafts only
   with an explicit `--backend`, at most five proposals and ten backend
   calls per run by default, only link additions outside code the check
   accepts, each bound to the bytes it was drafted from.
2. The wiki directory is byte-identical after every run; nothing reaches
   promote or approve; a rerun creates no duplicate and calls no backend.
3. Exit codes follow FR-010, both reviewer notes included.
4. The recipe's commands and wrapper are checked; the persona and
   `ingest-rules.md` say what the pass does and who approves its drafts.
5. Version 0.10.0 in the six places; `info` lists `nightly`; gate green at
   92 percent; `docs/compatibility.md` untouched by the build.

## Open items for the spec review

Each is a build detail the pitch leaves open; the default is in the spec.
Items 1-3 were decided by the owner on 2026-11-17.

1. **"Already proposed" needs the directory after the error** (departure 6,
   FR-026). Owner, 2026-11-17: yes; any other `FileExistsError` exits 6 and
   stops drafting.
2. **Editable pages per `missing-cross-link` draft** (departure 10,
   FR-014). Owner, 2026-11-17: all the finding's unlinked pages, not the
   first five.
3. **A proposals directory inside the wiki refused with drafting on**
   (departure 9, FR-013). Owner, 2026-11-17: yes, exit 1, symlinks
   resolved, before any backend call.
4. **The proposal cap and the attempt bound** (departure 12, FR-016).
   Owner, 2026-11-17: `--max-proposals` counts proposals created; backend
   calls are bounded at twice that, derived, not a flag.
5. **`--report` with `--json`** writes the markdown file and prints the
   JSON (FR-005).
6. **The `curate` renderer branch** (departure 8, FR-017).
7. **The report heading and section names** (FR-003): `# wiki-studio
   nightly report`, `## Lint`, `## Findings`, `## Proposals`,
   `## Needs a curator`.
8. **The persona paragraph's place**: after the loop's last paragraph
   (fact 10, FR-030).
