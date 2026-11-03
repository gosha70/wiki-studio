---
spec_mode: full
feature_id: wiki-studio-0-8-1
risk_category: feature
justification: "No runtime code changes, but the release is the roadmap's Launch sequence step 2 and closes issue #10: two quickstarts whose commands are extracted from the pages and executed on clean installs (one against memkernel 0.6.0 from PyPI with a pinned embedding model), a stated and executed commit policy, an example script with a recorder that binds a recorded run to the exact bytes it executed, three new blocking CI jobs, a measurement design filed to memkernel, and GitHub issue actions taken by the build session; a full spec pins the run-block grammar, the commit policy path by path, the recorded run's binding order, the claim wording, the frozen files and the cut order before an unattended build."
status: draft
date: 2026-11-03
collaboration_mode: single
origin:
  issue: 10
  urls:
    - https://github.com/gosha70/wiki-studio/blob/main/specs/pitches/10-release-b-launch-and-measurement/pitch.md
    - https://github.com/gosha70/wiki-studio/issues/10
    - https://github.com/gosha70/memkernel/issues/17
    - https://github.com/gosha70/wiki-studio/blob/main/docs/roadmap.md#evidence
    - https://github.com/gosha70/wiki-studio/blob/main/docs/roadmap.md#launch-sequence
    - https://github.com/gosha70/wiki-studio/blob/main/docs/proposals/2026-10-23-product-proposal.md
    - https://github.com/gosha70/wiki-studio/blob/main/specs/retros/cooldown-after-03.md
  origin_claim: |
    Issue #10 (mirror of gosha70/memkernel#17), which "closes when that run's
    results are published and linked here", shaped by the bet pitch
    specs/pitches/10-release-b-launch-and-measurement/pitch.md (cycle 04,
    building, approved in PR #68) from docs/roadmap.md, the 2026-10-23 product
    proposal and specs/retros/cooldown-after-03.md (candidate 1, "The Release B
    launch items and the integration measurement."). Roadmap, Launch sequence
    step 2: "After B: the two quickstarts, the compatibility matrix, and a short
    demonstration of an obsolete decision corrected through a reviewed proposal
    and absent from the next session." Roadmap, Evidence: "Integration
    measurement starts with Release B. The primary comparison holds agent,
    model, task set and memkernel retrieval constant and varies the curation
    workflow: memkernel alone, memkernel with governed Wiki Studio, files plus
    grep." and "The frozen 0.4.1 agent arm stays as the historical run; the
    hardened composition is a separately versioned experiment." Proposal, "Two
    tested quickstarts": "Publish a standalone shell-agent example and a
    MemKernel composition, each with Claude Code and Kiro instructions where
    applicable. Both should demonstrate proposal, validation, review, promotion
    and reading. The composition adds retain, export, governed import,
    correction and next-session recall." Proposal, "Launch sequence": "After
    Release B, publish the two quickstarts, a compatibility matrix and a short
    demonstration: an obsolete decision is recalled, corrected through a
    reviewed proposal, imported, and absent from the next session's current
    knowledge. Show the revision and receipt alongside the answer." Problem, as
    the pitch states it: "Release B closed on 2026-10-30. The correction loop
    works: a wrong memory that a reviewed page corrects is not a current answer
    in the next session. But only a CI test shows it." "No one can follow the
    loop from the docs." "The integration measurement exists but tells
    nothing." "Issue #10 is open on a condition that is met, and the README is
    stale." Solution shape: "Docs, tests, CI jobs and one example script. No
    runtime behaviour or API change under src/ (the version constant in
    src/wiki_studio/__init__.py changes with the release, as every release
    does), no new exit code, no dependency." One 2w bet released as 0.8.1;
    core S1-S3 never cut; S4 stretch, cut first; owner decisions D1-D6
    (2026-11-03) and D7-D16 carried into the FRs.
---

# Plan: wiki-studio 0.8.1 — Release B launch and the integration measurement (wiki-studio side)

The bet pitch `specs/pitches/10-release-b-launch-and-measurement/pitch.md` is
the shaping record (reviewed on PR #68 with three revisions: the
`api.review_state` block, the per-path commit policy and the executed
handoff, the recorded run's binding order, the two diagnostics with no gate
claim, and the "no runtime behaviour or API change" wording; owner decisions
D1-D6 on 3 November 2026; bet and cycle 04 started the same day). Its
"Findings from the code" were re-checked against `main` at 07ef1b9 on 3
November 2026 and hold: the loop test's case 4 is the demo's skeleton and its
docstring is stale (`tests/integration/test_release_b_loop.py:11-15` against
`ci.yml:122-130`); README Evidence still points to #10 as pending
(`README.md:654-656`); the compatibility matrix lists 0.8.0 with memkernel
0.6.0 as tested (`docs/compatibility.md:12`); the standalone path's verbs call
no model. memkernel was read in its working tree, which is on `main` (0.7
work), not at the `v0.6.0` tag (no shell was available to check the tag out);
see FR-007. Eight facts found while re-checking shape the spec:

1. **A `--by` in the quickstart's launch line would fail the conformance
   runner.** The runner sets the actor through `WIKI_STUDIO_ACTOR`
   (`conformance/mcp/run.py:452`) and case 10 requires the approval record's
   approver to be `conformance-agent` (140, 730-731); a `--by` flag beats the
   variable. A line with `--disable-tool promote` would fail cases 2, 6, 7
   and 10. So the page's tested launch line is `wiki-studio-mcp --root
   "$PWD"`, the actor is named through the host's environment, and
   propose-only mode is shown, not passed to the runner (FR-004).
2. **`approve` refuses a draft.** `api.approve` refuses `status: draft`
   (`api.py:799-800`), so the standalone page's draft directory writes a page
   with `status: stable`; the 0.4.1 arm's instruction writes `status: draft`
   (`docs/agent-arm/instruction.md:22`), which the design notes (FR-020).
3. **memkernel names the page after the memory's first line.** The exporter
   takes the title from the first line and the slug from the title
   (memkernel v0.6.0 `sync.py:278-279`), and the imported memory is the title
   plus the body (v0.6.0 `sync.py:427`). A one-line wrong rule would put the wrong claim in the page path
   and the title beside the right answer. The demo and the composition
   quickstart retain the wrong decision under a neutral first line naming the
   topic, and the curator rewrites the title, heading and body (FR-006,
   FR-012).
4. **The receipt lives only in the proposals archive.** `receipt.json` is
   written beside the proposal and archived under `.applied/<name>/`
   (`promoter.py:159`); the `.audit/proposals/<name>/` copy holds `plan.json`,
   `proposal.md` and `curator-delta.md`, not the receipt (762-767). memkernel's
   README says to ignore its default proposals directory
   `.memkernel/wiki-proposals/` (README 338 at `v0.6.0`). So both tools are pointed at
   wiki-studio's proposals directory and its `.applied/` is committed
   (FR-007, FR-008).
5. **memkernel has no setting for the embedding revision.** It passes
   `MEMKERNEL_EMBEDDING_MODEL` to `SentenceTransformer` with no revision
   (`embeddings.py:20`). The pin is a snapshot downloaded at revision
   `1110a243…`, checked, and given to memkernel as a local path with
   `HF_HUB_OFFLINE=1` (FR-007, FR-014).
6. **The driver owns git.** The recorded run's order needs the script
   committed first, a clean tree, and the run committed separately after it;
   an auto-build session does not commit (`CLAUDE.md`, Working rules). So the
   build commits the script, recorder and protocol, CI runs the same recorder
   on every push, and the one recorded run is an owner-run step in an
   evidence PR, as 0.8.0's held-out run and host run were (FR-028).
7. **`review_state` has no CLI verb.** `cli.py:984-997`; the quickstart reads
   it through an executed Python block (FR-003), as the pitch's review
   required.
8. **The lint job does not cover `eval/` or `examples/`.** CI's `lint` job
   checks `src/ tests/ conformance/` (`ci.yml:30-33`) and the 0.8.0 gate adds
   `eval/`; FR-017 adds `eval/` and `examples/` to the job (the project gate in
   `CLAUDE.md` already includes `eval/`). The gate is the parent's to extend
   (see Open items).

Close target: issue #10, by the build PR's merge after the build session's
restating comment names the successor issue (FR-025). No other issue closes.

## Architecture decisions

- **ADR-1: One source per quickstart (D8).** Executed commands live only in
  fenced blocks marked `run` in the page; `tests/helpers/quickstart_blocks.py`
  extracts and runs them in order, each in its own process, and asserts each
  declared exit code. The page and the check cannot drift. The same helper
  serves both quickstarts (FR-002).
- **ADR-2: A session is a process; memkernel is driven through the Python
  calls its tools make (D9).** No MCP client, no host simulation in CI; the
  host settings are documented and the 0.8.0 Claude Code host run covers
  wiki-studio's adapter. The curator always uses the wiki-studio CLI.
- **ADR-3: The commit policy is executed, not only stated.** The setup block
  writes the `.gitignore` that encodes the policy, and the handoff commits,
  clones and imports in the clone with a fresh store (FR-008, FR-009). A
  policy that drops the approval records would show every page `unapproved`
  there and fail.
- **ADR-4: One recorder for CI and the recorded run.** `record.py` builds the
  wheel from `git archive HEAD`, verifies the memkernel distribution against
  PyPI, pins and verifies the embedding revision, runs the demo once and
  writes the manifest. CI runs it on every push into a temporary directory,
  so the recorded run executes exactly what CI executed, and "every
  executable artifact is run at least once" holds before the recorded run
  (FR-014, FR-015).
- **ADR-5: The end-state hash is over exported state, with the existing
  tool.** The run directory keeps `end-state/` (the wiki tree and the
  proposals directory with its receipts) and hashes it with
  `python -m conformance.mcp.run tree-hash`, the hash host runs use; Chroma
  files are never copied or hashed. The hash binds the committed files to the
  manifest; it is not claimed to reproduce across runs.
- **ADR-6: The design is a document; the 0.4.1 arm stays frozen (D7, D14).**
  `eval/composition/design.md` states requirements, options and a
  recommendation; memkernel decides and builds. The arm's two hashed files
  are untouched; its README gains one pointer.
- **ADR-7: #10 closes by restatement with a successor (D4, D6).** The build
  writes the texts and files nothing. After the build and before the PR
  merges, one interactive step files the memkernel issue (body: the
  committed design, linked by a permalink at its commit), opens the
  successor, and comments on #10; the PR's merge closes #10. It never
  closes on a claim.
- **ADR-8: Evidence review stays apart from code review.** The build PR
  merges once its review passes; the recorded run, the demo page's quotes and
  the compatibility run ids land in one evidence PR before the `v0.8.1` tag
  (FR-028), one commit per step.

## Phases (one auto-build phase per `## US<n>:` group of tasks.md)

| Phase | Pitch scope | What | Main files |
|---|---|---|---|
| US1 | S1 | The run-block helper, the standalone quickstart, its test with the conformance check, the `quickstart` CI job, README Install link | `tests/helpers/quickstart_blocks.py` (new), `docs/quickstart.md` (new), `tests/test_quickstart.py` (new), `.github/workflows/ci.yml`, `README.md` |
| US2 | S2 | The composition quickstart (settings, loop, commit policy, handoff), its test, the `quickstart-memkernel` job with the pinned model, links | `docs/quickstart-memkernel.md` (new), `tests/integration/test_quickstart_memkernel.py` (new), `.github/workflows/ci.yml`, `README.md`, `docs/consumers.md` |
| US3 | S3 | `demo.py`, `record.py` and the protocol, the `demo-correction-loop` job, the demo page, the loop test docstring, `examples/` in the lint job | `examples/correction-loop/demo.py` (new), `examples/correction-loop/record.py` (new), `examples/correction-loop/README.md` (new), `docs/demo-correction-loop.md` (new), `.github/workflows/ci.yml`, `tests/integration/test_release_b_loop.py` (docstring), `CLAUDE.md` |
| US4 | S4 (stretch) | The measurement design and the agent-arm README pointer | `eval/composition/design.md` (new), `docs/agent-arm/README.md` |
| US5 | S5 + release | The memkernel issue, the successor issue, the #10 comment; README Evidence, the roadmap, the compatibility row; release 0.8.1; the invariant audit | `README.md`, `docs/roadmap.md`, `docs/compatibility.md`, `CHANGELOG.md`, `pyproject.toml`, `src/wiki_studio/__init__.py`, `tests/test_cli_contract.py`, `CLAUDE.md` |

Order follows the pitch: S2 shares S1's extraction helper; S3 shares S2's
settings and story; S5's issue texts need S4's committed design. S1, S3 and
S4 could start at once, but the driver runs one phase at a time. If S4 is
cut (FR-028), US4 keeps only FR-018 and FR-021's dependency list and US5
files that.

## Owner-run steps: the evidence PR

The recorded run needs a clean tree at a commit carrying the merged script,
network access to PyPI and Hugging Face, and commits in a fixed order, so the
build never performs it (FR-028). The build PR merges once its review passes;
`main` then carries the script, the recorder, the protocol and three green
blocking jobs. The owner then opens `evidence/wiki-studio-0-8-1` from that
`main`, one commit per step, never squashed:

1. **The recorded run.** From a clean checkout: `python
   examples/correction-loop/record.py --out
   examples/correction-loop/runs/<YYYY-MM-DD>-wiki-studio-0.8.1-memkernel-0.6.0`;
   commit the run directory alone, as written. A failed attempt is committed
   as it is, and a second attempt is a new directory.
2. **The demo page's quotes** from the committed transcript and manifest
   (`docs/demo-correction-loop.md`, FR-016).
3. **The compatibility row's run ids**: the first green run on `main` of
   `quickstart`, `quickstart-memkernel`, `demo-correction-loop`,
   `memkernel-compat` and `memkernel-loop` (FR-024).

The evidence PR is reviewed on its own and merged before the owner tags
`v0.8.1` and dates the CHANGELOG heading (D5). The owner's memkernel README
edit linking the composition quickstart is outside this repository (D3).

## Unattended run

The parent session writes `specs/wiki-studio-0-8-1/automation.json` and
`verification.yaml` at approval. This plan assumes 0.8.0's shape: profile
`pr`, branch `feature/wiki-studio-0-8-1` off `main`, five phases with no
milestone pause (`milestone_every` above the phase count), the DeepSeek
correctness reviewer gating (max 3 rounds per phase), the test command of
`specs/wiki-studio-0-8-0/automation.json` (see Open items for `examples/`),
`pr.closes: [10]`. The three new CI jobs, `memkernel-compat` and
`memkernel-loop` run on the PR, not in the driver's gate. The US5 GitHub
actions (FR-025) need the session to reach GitHub with `gh`; if it cannot,
the phase stops at that task and reports. The bundle is a draft: an
origin-alignment record is written only after approval, before the build.

## Test strategy

- **Extraction, not duplication.** Both quickstarts are tested only by
  running their own `run` blocks (FR-002); the parser has unit tests in
  `tests/test_quickstart.py` (grammar, `exit=`, `contains=`, non-run blocks
  skipped, the empty-page and `ingest`/`query`/`--backend` refusals).
- **Clean installs.** `quickstart` (wheel with `[mcp]`), `quickstart-memkernel`
  (wheel with `memkernel==0.6.0`) and `demo-correction-loop` (the recorder's
  own fresh environment) each install into a fresh virtual environment and
  import-check before running, so nothing is skipped there; locally, the
  memkernel test is skipped without memkernel and the conformance check
  without `mcp`, each with its reason.
- **The demo checks itself.** `demo.py` exits 1 on any failed check; the CI
  job's exit code is the recorder's. No `assert` statements.
- **Regression.** No `src/` behaviour changes, so the existing suite,
  `tests/test_mcp_conformance.py`, the single-writer scans, the CLI contract
  tests, the frozen-run pins and the two memkernel jobs stay green unchanged;
  coverage stays at or above 92%.
- **Wording.** A checkpoint greps the new pages, README Evidence and the
  roadmap for "cheaper", "better", "faster", "prevents" and "guarantee".

## Risks

- **The embedding model in CI.** About 90 MB from Hugging Face; the download
  can be slow or blocked. Mitigation: the snapshot is pinned and cached keyed
  on the revision; if the jobs stay unreliable, the deterministic embedding
  is a spec-review decision, labelled in the job, and the recorded run keeps
  the real model.
- **memkernel 0.6.0 differs from `main`.** The planning session read memkernel
  `main` (0.7 work). Mitigation: FR-007 requires the build to call memkernel
  as 0.6.0 accepts it, verified against the installed wheel; the existing
  loop test (`WikiImporter(service, wiki)`) shows the 0.6.0 form.
- **Approval records may not survive a clone.** If record verification
  depended on absolute paths, the clone would read `unapproved`. Mitigation:
  that is exactly what FR-009's handoff tests; a failure is a `src/` defect
  handled under D13, not worked around in the page.
- **Network in the build session.** `demo.py` and `record.py` need PyPI and
  Hugging Face. Mitigation: the session runs them where it can; otherwise it
  reports the skipped run plainly and CI on the PR is the first execution,
  which must be green before merge.
- **Public actions from an unattended build.** Filing issues and
  commenting are public and outside the driver's git ownership.
  Mitigation: the build only writes the texts; the filing is one
  interactive step after the build (memkernel issue, successor, #10
  comment, in that order), before the PR merges.
- **A claim slipping into the docs.** Mitigation: FR-016's word list, the
  wording checkpoint, and the reviewer.
- **Review depth.** Each earlier cycle drew several review rounds; a third
  round on one scope escalates to the owner.

## Success criteria

1. `docs/quickstart.md`'s run blocks pass on a clean install of the wheel with `[mcp]`, including the `api.review_state` block before and after `approve` and the exit-9 stale update, and the conformance suite passes against the page's launch line.
2. `docs/quickstart-memkernel.md`'s run blocks pass against memkernel 0.6.0 from PyPI; the commit policy is stated per path and executed; a clone with a fresh store imports exactly the approved revisions.
3. `demo.py` passes in the blocking `demo-correction-loop` job through `record.py`; the protocol binds a recorded run to the commit, the wheel, the PyPI-checked memkernel distribution and the embedding revision; `docs/demo-correction-loop.md` tells the story in about one screen.
4. `eval/composition/design.md` exists (or its cut form is filed), reports the two diagnostics with no gate claim, and the frozen 0.4.1 arm files are unchanged.
5. README Evidence and the roadmap restate the 0.5.0 ceiling; the memkernel issue and the successor exist; #10 carries the restating comment and closes with the build PR.
6. Version 0.8.1; `git diff main -- src/` is the version line only; exit codes unchanged; gate green at 92%.

## Open items for the spec review

Each is a build detail the pitch leaves open; the default chosen is in the
spec and is what the build does unless the review changes it.

1. **The run-block grammar.** Default: info strings `bash run` / `python run` with optional `exit=<N>` and `contains=<token>`, and `bash server-cmd` for the launch line (FR-002, FR-004).
2. **The actor in the tested launch line.** Default: `WIKI_STUDIO_ACTOR` through the host's environment (`claude mcp add --env WIKI_STUDIO_ACTOR=you …`), because the runner's case 10 fails with `--by` (finding 1). Rejected: editing the conformance runner (scope) or stripping `--by` in the test (the tested line would not be the page's). The `--env` spelling is checked against Claude Code's documentation at build time; the line is not executed.
3. **One proposals directory for both tools.** Default: `MEMKERNEL_WIKI_PROPOSALS_DIR` set to wiki-studio's `doc_internal/proposals`, whose `.applied/` is committed (finding 4).
4. **memkernel's local files.** Default: `.memkernel/` and `.env` are ignored as memkernel's own files, outside wiki-studio's "ignore only the lock and the cache" rule, which covers wiki-studio's paths (FR-008).
5. **The wrong decision's text.** Default: a neutral first line naming the topic, then the wrong rule; the curator rewrites title, heading and body (finding 3).
6. **The model in CI.** Settled at review: the real model at the pinned revision, cached; a failed download exits 2, never 1; switching to the deterministic embedding is a spec decision, never a silent fallback (FR-007).
7. **The recorder.** Default: one standard-library `record.py` used by CI and the recorded run; wheel from `git archive HEAD` with `poetry build`; memkernel via `pip download` checked against PyPI's JSON; wall times measured from the start of the install (FR-014).
8. **Who performs the recorded run.** Settled at review: the owner, in the evidence PR (finding 6, FR-028).
9. **The end-state hash.** Default: `conformance.mcp.run tree-hash` over a committed `end-state/` holding the wiki and the proposals directory (ADR-5).
10. **CI layout.** Default: three new blocking jobs on Python 3.11 (`quickstart`, `quickstart-memkernel`, `demo-correction-loop`); `tests/test_quickstart.py` also runs in the default suite.
11. **The compatibility matrix.** Default: a new 0.8.1 with 0.6.0 row, "pending" until the evidence PR names green run ids; the 0.8.0 row stays as recorded (FR-024).
12. **How #10 closes.** Settled at review: the build writes the comment's text; the interactive step after the build posts it (after the memkernel and successor issues); the build PR's merge closes #10 (`pr.closes: [10]` in `automation.json`).
13. **The memkernel issue body.** Settled at review: the committed design text, linked by a permalink at its commit, filed in the interactive step after the build, not by US5.
14. **The gate and `examples/`.** Default: the 0.8.0 gate unchanged; `examples/` is checked by the CI `lint` job and each phase checkpoint. Recommendation for the parent: add `examples/` to the ruff check and format paths of `automation.json`'s test command.
15. **The CHANGELOG date.** Default: `[0.8.1]` dated when the owner cuts the release.
