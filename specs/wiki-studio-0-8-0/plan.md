---
spec_mode: full
feature_id: wiki-studio-0-8-0
risk_category: feature
justification: "Adds a second ranker (FTS5 with bm25) behind the index-first workflow with a byte budget, a rebuildable SQLite cache beside the lock file with recovery rules, a preregistered held-out measurement that decides the default ranker, a structural rule that is an upgrade break (every page must be valid UTF-8), the first optional dependency (the official MCP SDK behind an extra) with an eight-tool agent surface, a conformance suite and a recorded host run; a full spec pins each behaviour, the preregistration order, the floors, the tool contract, the cache recovery rules and the cut order before an unattended build."
status: draft
date: 2026-10-27
collaboration_mode: single
origin:
  issue: 38
  urls:
    - https://github.com/gosha70/wiki-studio/blob/main/specs/pitches/38-release-c-discovery-portability/pitch.md
    - https://github.com/gosha70/wiki-studio/issues/38
    - https://github.com/gosha70/wiki-studio/issues/51
    - https://github.com/gosha70/wiki-studio/blob/main/docs/roadmap.md#release-c-standalone-usefulness-and-broader-adoption
    - https://github.com/gosha70/wiki-studio/blob/main/docs/proposals/2026-10-23-product-proposal.md
  origin_claim: |
    Issue #38 (Release C) and its close target #51, shaped by the bet pitch
    specs/pitches/38-release-c-discovery-portability/pitch.md (cycle 03,
    building) from the Release C and Evidence sections of docs/roadmap.md and
    the 2026-10-23 product proposal. Problem, as the pitch states it: "0.7.0
    made the curation loop governable. Two things still limit who can use
    wiki-studio on its own." "Discovery is weak and unbounded": the selector
    "puts the gold page first for 3 of 21 questions (14.3%) and within the top
    five for 10 of 21 (47.6%)", "Five questions select nothing beyond the
    index", and "The five-page cap bounds the page count, not the size".
    "Only shell-capable agents can use it": an MCP host "has to wrap the CLI
    itself, and nothing tells it which operations are safe to give an agent."
    Solution shape: "Two halves that share no code. Both are additive to the
    0.7.0 API and formats. No new exit code, no page schema change, and
    promoter.py stays the only module that writes into the wiki directory."
    Discovery (S1-S3): "A second ranker, FTS5 with bm25 over the same
    candidate set the index-first selector uses", index.md "still read first
    and always loaded, the cap stays five pages, and a byte budget limits what
    is loaded", "The FTS5 table is a cache outside the wiki", every call
    rereads and hashes the eligible pages, a missing FTS5 falls back "and
    never fails", the 21 published questions become the development set, "A
    fresh held-out corpus is ingested through the real pipeline under a
    frozen protocol", frozen before tuning, and "the single held-out run
    decides whether FTS5 becomes the default." Portability (S4-S5): "A
    wiki-studio[mcp] extra on the official SDK and a wiki-studio-mcp stdio
    server", bound at launch to the same roots the CLI resolves, "Its eight
    tools are each one call into the existing api", "approve and every
    model-spawning verb are not on the surface", a conformance suite that
    drives any server command through the SDK's client, "and a Claude Code
    run, checked by the same suite, is the non-memkernel runtime evidence."
    One 6w bet released as 0.8.0 (owner decision: all of Release C in one
    release); core S1-S3 never cut; S4-S5 shelve first; owner decisions D5,
    D8, D8a, D8b, D8c, D9, D14 and D16 carried into the FRs.
---

# Plan: wiki-studio 0.8.0 — discovery and portability (Release C)

The bet pitch `specs/pitches/38-release-c-discovery-portability/pitch.md` is
the shaping record (four review passes on PR #50; owner decisions D5, D9,
D14 and D16 on 26 October 2026, D8 overruled the same day, D8a and D8b
approved and D8c decided on 27 October 2026; bet and cycle 03 started on 27
October). Its "Findings from the code" were re-checked against the current
tree on 27 October 2026 (`specs/release-c-bet` at d0d71c9, on `main`
0f64c3b): every citation holds at or within a few lines of the cited
numbers (`contract.CAPABILITIES` is at 106-116, the constants from 97;
`build-check` is at `ci.yml:158-182`; `lock_path_for` at
`wikilock.py:127-130`), and the FTS5 probe passes locally on CPython 3.13.2
with SQLite 3.48.0. Three facts found while re-checking shape the spec:

1. **A rejected flag value is exit 1, not 2.** `cli.py:_report` (974-983)
   maps a `ValueError` to exit 1, which is how `--lock-timeout -1` fails
   today, and the README lists "a rejected flag combination" under 1 and
   argparse's own usage errors under 2. A `--search-cache` path inside the
   wiki therefore raises `ValueError` from `WikiPaths.resolve` and exits 1
   (FR-012), not the pitch's exit 2. The code wins.
2. **D7 and finding 2 conflict unless the selector is wrapped, not edited.**
   D7 excludes superseded pages from both rankers; finding 2 says the body of
   `_select_query_candidates` is not edited. The spec resolves it by calling
   the selector with `max_pages` equal to the candidate count and letting
   `discovery.py` drop ineligible paths, apply the budget and the cap over
   the ranked list (FR-004, FR-007). The frozen runs call the selector
   directly, so no number moves.
3. **Two MCP result shapes are new.** `lint` has no `--json` and
   `review_state` has no CLI verb (`cli.py:_VERBS` 915-928), so the `lint`
   and `review_state` tools define their JSON (FR-035); `read_page` already
   refuses a non-UTF-8 page with exit 4 (`api.py:886-887`), so `read` needs
   no change for the UTF-8 rule (FR-003).

Close target: `automation.json` has `pr.closes: [51]`, the Release C
tracking issue for the wiki-studio side ("Release C, wiki-studio side: 0.8.0
(discovery and portability)", opened 2026-10-27). Issue #38 tracks Release B
and Release C together and must not be closed by 0.8.0.

## Architecture decisions

- **ADR-1: The selector is wrapped, never edited.** `_select_query_candidates`
  keeps its name, signature, body and return value and becomes the
  `index-first` ranker; `discovery.py` calls it for the whole ranked list and
  applies eligibility, the budget and the cap on top (FR-001, FR-004). The
  one change near it is in `_read_text_or_empty` (FR-003), which reaches all
  four callers at once. `tests/test_navigation_eval.py` is the proof that
  the frozen numbers do not move.
- **ADR-2: A non-UTF-8 page is a structural violation, not a silent empty
  read.** The helper fix alone would make such a page invisible everywhere;
  the lint rule reports it once with its path, fatal like every structural
  rule, so `promote` refuses until the page is fixed. It is an upgrade break
  and the CHANGELOG says so with the remedy (FR-003).
- **ADR-3: One read per eligible page per call, hashed, outside the cache.**
  Discovery reads bytes, hashes them, and decodes for the prompt; the cache
  stores text only for ranking and never supplies it to a prompt (FR-004,
  FR-013, FR-014). D2 (hash every call) makes same-second edits, restored
  mtimes and checkouts correct at no extra I/O.
- **ADR-4: The cache is beside the lock file and `search_index.py` is its
  only writer.** Keyed to the resolved wiki like the lock, outside the wiki
  boundary, one `.gitignore` pattern for both; `WikiPaths` gains the path
  with the usual flag, variable, default precedence and refuses a path
  inside the wiki (FR-012). `promoter.py`'s single-writer rule needs no
  exception, and FR-016 adds the behaviour test the syntactic scans cannot
  give.
- **ADR-5: A cache that cannot be used is a warning, never an error.** Drop
  and rebuild on a mismatched `meta`; remove and rebuild on a corrupt regular
  file; fall back to memory on a symlink, a read-only directory or a held
  busy timeout. `find` and `query` work today without any cache and keep
  working (FR-015).
- **ADR-6: The preregistration order is enforced by the tools, not only by
  the protocol document.** `heldout_protocol.py` carries the manifest's
  state machine and refuses to run out of order; `discovery.py tune` refuses
  before the held-out freeze; `discovery.py run` refuses before the
  configuration hash is frozen and never overwrites `heldout/results.json`
  (FR-021, FR-028, FR-030). The owner's steps (questions by a separate
  session, the probe, the ingest, gold review) are the only ones a person
  performs.
- **ADR-7: The default ranker is `index-first` until the evidence says
  otherwise.** `DEFAULT_RANKER` ships as `index-first` from US1 and is
  flipped only by FR-029's rule on the held-out result with both floors;
  the CHANGELOG states the basis either way. Nothing user-visible changes
  before the measurement exists.
- **ADR-8: The ranker configuration is one hash.** Tokenizer, weights,
  minimum match and the cap are hashed canonically; the hash keys the cache,
  is carried in every result, and is what "frozen configuration" means
  (FR-006, FR-028).
- **ADR-9: The adapter is a thin extra: one `api` call per tool, stdio
  only, launch-time binding.** `mcp>=2.3,<3` behind `wiki-studio[mcp]`,
  `MCPServer` and the stdio transport only, no hand-written JSON-RPC; roots,
  actor and ranker resolved once at launch through the same functions the
  CLI uses; no tool takes a root, backend, actor or escape hatch;
  `--disable-tool` only narrows (FR-031, FR-034..FR-037). ADR-0003 records
  the dependency and the tool contract; the page schema and ADR-0002 are
  untouched.
- **ADR-10: Auto-approval is honoured and reported, not refused (D14).** The
  `promote` tool carries `approved_paths` and a warning naming the policy and
  the server's fixed actor; the docs say that on such a wiki an agent's
  promote approves its own proposal (FR-038).
- **ADR-11: The standard-library core is proved twice.** An `ast` test in
  the repository and a clean-install check in CI's `build-check` over the
  wheel's `Requires-Dist` and `sys.modules` (FR-033), so the extra can never
  leak into the core unnoticed.
- **ADR-12: The conformance suite is adapter-agnostic and checks the host
  run from its trace and end state.** `conformance/mcp/run.py` takes any
  `--server-cmd` and imports nothing from `wiki_studio`; `check-host-run`
  applies the same cases to a trace the suite did not drive (FR-041,
  FR-043, FR-045). The host run needs the owner's account and is not in CI.
- **ADR-13: Capabilities are added by the phase that ships them.** US1 adds
  `ranked-discovery` and `context-budget` with resolvers; the adapter is not
  a core capability and reports itself through its own `info` tool (D19).

## Phases (one auto-build phase per `## US<n>:` group of tasks.md)

| Phase | Pitch scope | What | Main files |
|---|---|---|---|
| US1 | S1 | `discovery.py` and `search_index.py` (in memory), the probe, eligibility, FTS5 documents and query, bm25 with ties by index order, the configuration hash, the byte budget, `api.find`/`api.query`/`DefaultQuerier` additions, `--ranker`/`--max-bytes`/`WIKI_STUDIO_RANKER`, the `_read_text_or_empty` fix and the UTF-8 lint rule, `info.discovery`, two capabilities, docs | `discovery.py` (new), `search_index.py` (new), `querier.py`, `wiki_state.py`, `lint.py`, `api.py`, `cli.py`, `contract.py`, `docs/knowledge-contract.md`, `README.md` |
| US2 | S2 | The on-disk cache beside the lock, `WikiPaths.search_cache`, `--search-cache`/`WIKI_STUDIO_SEARCH_CACHE`, the content manifest and `meta`, refresh on every call, recovery and fallback, the recovery suite and the byte-identity test, `.gitignore` docs | `search_index.py`, `paths.py`, `cli.py`, `contract.py`, `README.md`, `docs/consumers.md`, `SECURITY.md` |
| US3 | S3 (build-able part) | The sha256 pins of the frozen runs, the runner `eval/navigation/discovery.py` with `run`, `tune` and `decide`, `run3/results-untuned.json`, the held-out sources and corpus (D8a), `heldout_protocol.py` with its state machine, `heldout/protocol.md`; the owner's steps are documented, not performed | `eval/navigation/discovery.py` (new), `eval/navigation/heldout_protocol.py` (new), `eval/navigation/run3/`, `eval/navigation/heldout/`, `NOTICE`, `tests/test_frozen_runs.py`, `tests/test_discovery_eval.py` |
| US4 | S4 | The `mcp` extra and `wiki-studio-mcp`, ADR-0003, the standard-library proof (test and CI), the server with launch binding and `--disable-tool`, the eight tools, errors and clean stdout, the trace file, `entry_point: "mcp"`, adapter docs | `pyproject.toml`, `src/wiki_studio/mcp_adapter/` (new), `promoter.py`, `tests/test_package_boundaries.py`, `tests/test_mcp_adapter.py`, `.github/workflows/ci.yml`, `docs/adr/0003-...md` (new), `docs/mcp-adapter.md` (new), `docs/patch-set-format.md`, `SECURITY.md`, `README.md` |
| US5 | S5 + release | The conformance suite and its fixtures, `mcp-min` and `mcp-latest`, the host-run scenario and `check-host-run`, the compatibility MCP table; release 0.8.0 (version, CHANGELOG with the UTF-8 upgrade note and the basis of the default, README Evidence, `CLAUDE.md`), the circuit-breaker audit | `conformance/mcp/` (new), `tests/test_mcp_conformance.py`, `.github/workflows/ci.yml`, `docs/compatibility.md`, `CHANGELOG.md`, `pyproject.toml`, `__init__.py`, `README.md`, `SECURITY.md`, `CLAUDE.md` |

Order follows the pitch's dependencies: S2 needs S1's index builder; S3
needs S1 and S2 (the latency block measures the cache); S5 needs S4. S1 and
S4 share no code, but the phases run in order because the driver runs one
phase at a time. If S4 is cut (circuit breaker step 3), US4 and US5 keep
only FR-047 and FR-048.

## Owner-run steps outside the automation

Two runs need the owner's account and a model, so the build never performs
them (FR-048; proposed, owner to confirm at spec review):

1. **The held-out set** (after US3 has shipped the tooling; the questions
   may be written earlier from `heldout/corpus/` once US3's task 29 has
   copied it, or by a separate session over the mapatlas files directly):
   questions by a separate agent session (FR-023) → `heldout_protocol.py
   pin` and the probe (FR-024) → `ingest` once (FR-025) → `freeze-wiki`
   (FR-026) → gold, owner review, `freeze` (FR-027) → `python -m
   eval.navigation.discovery tune` on the development set (FR-021) →
   `run3/ranker-config.json` committed → `discovery run --fixture
   eval/navigation/heldout` once (FR-028) → `discovery decide` (FR-029) →
   the default flip (or not), the CHANGELOG basis, the README numbers and
   the sha256 pins, each an owner commit on the feature branch before the
   tag. Until then the build ships `DEFAULT_RANKER = index-first` and the
   CHANGELOG says the basis is pending.
2. **The host run** (after US4 and US5): `claude -p` at a pinned version
   against the fixture with `--trace`, `check-host-run`, the recorded run
   directory and the compatibility row (FR-045, FR-046), an owner commit on
   the feature branch. If it has not passed at release time, the extra ships
   as a preview (FR-048, step 4).

The alternative is a milestone pause after US3 (`milestone_every: 3`), so
the owner performs step 1 before US4 starts and the build itself tunes,
runs the held-out set and decides the default in US5. It costs a resume and
holds the adapter until the ingest is done; the owner chooses at spec
review. `automation.json` is written for the no-pause design.

## Unattended run

`specs/wiki-studio-0-8-0/automation.json`: profile `pr`, branch
`feature/wiki-studio-0-8-0` off `main`, five phases with no milestone pause
(`milestone_every: 7`, above the phase count, so the driver finalises and
opens the PR after phase 5), DeepSeek gating review (max 3 rounds per
phase), the test command of 0.7.0, caps 12 hours and $150, the circuit
breaker's week checkpoints applied by the owner at the build-PR review
(FR-048), `pr.closes: [51]` (see above). The `mcp-min`, `mcp-latest` and
`memkernel-*` jobs run in CI on the PR, not in the driver's gate. The bundle
is a draft: an origin-alignment record is written only after approval,
before the build.

## Test strategy

- Every FR maps to at least one unit or CLI test (CLI in-process through
  `wiki_studio.cli.main(argv)`); new test files per phase are named in
  tasks.md: `tests/test_discovery.py`, `tests/test_utf8_rule.py`,
  `tests/test_search_index.py`, `tests/test_frozen_runs.py`,
  `tests/test_discovery_eval.py`, `tests/test_mcp_adapter.py`,
  `tests/test_mcp_conformance.py`, plus additions to
  `tests/test_package_boundaries.py`, `tests/test_info_contract.py`,
  `tests/test_lint.py` and `tests/test_cli_contract.py`.
- The FTS5 fallback is tested by patching `discovery.fts5_available`, never
  by building a Python without FTS5; the operator questions of FR-005 run
  through both rankers.
- The cache suite (FR-017) compares every cached ranking to
  `search_index.build_in_memory` and hashes the wiki tree before and after
  (FR-016); concurrency and kill-during-refresh use the 0.6.0 pattern
  (subprocess children through a bootstrap that patches a step before
  calling `cli.main`; no production pause hook); the property test is
  seeded and at least 200 steps.
- Frozen evidence: `tests/test_navigation_eval.py` unchanged;
  `tests/test_frozen_runs.py` pins sha256 for every frozen file and, once
  they exist, the held-out files; `tests/test_discovery_eval.py` asserts
  `run3/` results and (once present) `heldout/results.json` except the
  latency block, FR-029's decision rule on synthetic results, and that
  `tune` and `run` refuse out of order.
- The adapter: every tool and every error class through a subprocess with
  the SDK's client, stdout checked byte for byte (FR-040); the surface and
  the forbidden argument names (FR-036); `--disable-tool`; the auto-approval
  case on a governed fixture (FR-038); the trace line shape (FR-041).
  Skipped when `mcp` is not importable; CI runs them at the locked, the
  floor and the newest `<3` version.
- Regression: the single-writer scans, the CLI contract tests,
  `tests/test_schema.py`, both evaluation runs' determinism tests and
  `test_every_capability_resolves` stay green; coverage stays at or above
  92%.

## Risks

- **The owner's schedule.** The held-out ingest and the host run are
  outside the automation. Mitigation: FR-048's week-3 and week-5 rules (FTS5
  opt-in untuned; the extra as a preview), the tools' refusal to run out of
  order, and the CHANGELOG stating the basis of the default either way.
- **A thin held-out result.** A one-attempt ingest may promote few of eight
  documents, or produce fewer than ten eligible pages. Mitigation: D8b and
  D8c are floors in FR-029; the result is reported with its counts and the
  random baseline, and FTS5 stays opt-in without a claim of loss.
- **SQLite differences between builds.** FTS5 may be missing, Unicode
  tables differ, bm25 can tie. Mitigation: the probe, ties by index
  position, the SQLite version in every result and `info`, CI asserting on
  its own matrix, and the latency block recording the versions.
- **The check-then-open window on the cache path.** SQLite follows
  symlinks; `lstat` precedes every open and the window touches only derived
  data outside the wiki; `SECURITY.md` says so (FR-015).
- **SDK churn.** Four 2.x minors in ten weeks. Mitigation: the pin below 3,
  `mcp-min` and `mcp-latest`, one `api` call per tool, stdio only, no
  hand-written JSON-RPC; a break in `mcp-latest` is a CI failure to fix,
  never a reason to widen the pin.
- **Review depth.** Two independent halves and a new dependency; 0.7.0's
  build review found six defects. Mitigation: the four reviewer-first areas
  (preregistration order, floors and baselines, the tool contract, cache
  recovery) each have their own FRs and tests; a third review round on one
  scope escalates to the owner.
- **Coverage.** The adapter counts toward the 92% gate only where `mcp` is
  installed (the dev group), and the eval runner is outside `wiki_studio`;
  the core modules carry the gate.

## Success criteria

1. `find`/`query` rank with FTS5 behind the index-first workflow, within five pages and a byte budget, fall back without FTS5 with a notice and exit 0, never select a superseded or non-UTF-8 page, and the frozen runs reproduce unchanged; a non-UTF-8 page is one lint violation that blocks `promote` until fixed.
2. The cache lives beside the lock file, is refreshed by hashing on every call, recovers from every FR-017 case with a ranking equal to an in-memory build, never fails `find` or `query`, and the wiki tree is byte-identical throughout.
3. The frozen runs are pinned by sha256; the runner reports both rankers with the eligible page count and the random baseline beside every hit rate; the held-out protocol's order is enforced by the tools; the default follows FR-029 and the CHANGELOG states its basis.
4. `wiki-studio[mcp]` installs the adapter; the base install imports nothing outside the standard library (proved twice); exactly eight tools with no root, backend, actor or escape-hatch argument; `--disable-tool` only narrows; errors are `{error, exit_code, message}`; stdout is clean; auto-approval is honoured and reported with the fixed actor.
5. The conformance suite passes in CI at the SDK floor and the newest `<3` for each tested protocol version; a recorded Claude Code run passes `check-host-run` or the extra ships as a preview; `docs/compatibility.md` lists what was tested.
6. Version 0.8.0; exit codes unchanged; no page schema change; ADR-0003 exists; gate green at 92%; any cut named in the CHANGELOG.
