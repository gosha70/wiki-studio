---
pitch_id: 10-release-b-launch-and-measurement
title: "Release B launch and the integration measurement, wiki-studio side: two quickstarts executed on clean installs, a recorded obsolete-decision correction, a design for a governed-composition measurement that can discriminate, and an honest close of issue #10"
appetite: 2w
bet_status: bet
cycle: "04"
circuit_breaker: "Core is S1, S2 and S3: the two quickstarts and the correction demonstration, each executed on a clean install. They ship alone if the cycle runs out. S4, the measurement design, is the stretch and is cut first. End of week 1: if S1-S3 are not downhill, S4 shrinks to the ceiling analysis and the dependency list, filed as one memkernel issue, with no arm or task drafts. The measurement run itself (memkernel's suite, its preregistration and its budget) is not this cycle's exit evidence and does not start here. Issue #10 closes only by restating what the published 0.5.0 run shows (a ceiling, no claim) and naming a successor issue; otherwise it stays open. It never closes on a claim. Never, to save time: change behaviour under src/ or an exit code, add a dependency, edit the frozen 0.4.1 arm files or a frozen run, hand-edit a recorded run, put a model backend on an executed path, write runner or statistics code, or state a gain without a preregistered run."
shaped_by: "pitch-shaper (Claude Code) for gosha70"
shaped_date: 2026-11-03
---

<!-- Shape-Up pitch. Origin: https://github.com/gosha70/wiki-studio/issues/10 (mirror of gosha70/memkernel#17) -->
<!-- docs/roadmap.md (Evidence; Launch sequence step 2), docs/proposals/2026-10-23-product-proposal.md ("Measure the complete workflow", "Launch sequence", "Two tested quickstarts") and specs/retros/cooldown-after-03.md (candidate 1) are the origin. This pitch shapes them; it does not replace them. -->

# Pitch: Release B launch and the integration measurement

## Problem

Release B closed on 2026-10-30. The correction loop works: a wrong memory
that a reviewed page corrects is not a current answer in the next session.
But only a CI test shows it. Three gaps remain.

1. **No one can follow the loop from the docs.** There is no quickstart.
   README's Install section is four lines. The memkernel composition is
   spread over `docs/consumers.md` as API recipes in three version
   sections. The Claude Code and Kiro host settings are in
   `docs/mcp-adapter.md`. An adopter who wants "propose, review, accept,
   read it back next session" must assemble it from these pages. The
   roadmap's Launch sequence step 2 asks for two tested quickstarts and a
   short demonstration. Neither exists.
2. **The integration measurement exists but tells nothing.** memkernel's
   preregistered 0.5.0 run included a `wiki_studio` arm on the five
   `lc-wiki` tasks. It passed 25 of 25. So did every arm, `bare`
   included. Every pairwise effect in the group is +0.0, and memkernel's
   headline is "no gain claimed". The arm is wiki-studio 0.4.1 alone
   through the CLI. It is not the governed composition the roadmap names
   (memkernel exports through the gate, a curator approves, memkernel
   imports, the next session recalls). None of the roadmap's six evidence
   questions has a measurement.
3. **Issue #10 is open on a condition that is met, and the README is
   stale.** #10 says it "closes when that run's results are published and
   linked here". They are published (memkernel `v0.5.0`). The README still
   says agent-level evidence is "an arm in `agent-memory-bench` ... tracked
   in issue #10", and does not say what the run showed.

The cost is the roadmap's adoption claim ("Can others adopt it": time to
the first accepted revision and corrected recall on a clean install) and
its evidence claim. Today a reader cannot try the loop without reading
tests, and the only agent-level number is a ceiling.

## Findings from the code

wiki-studio was read at main `e1f793f` on 2026-11-03. memkernel was read,
read-only, at main `a1a5b32` (0.7 wiring work) and at tag `v0.6.0`. These
facts drive the scopes and the rabbit holes.

1. **Why `lc-wiki` is at ceiling.** Each `lc-wiki` task's exposure prompt
   tells the agent to record the decision as a page under
   `knowledge/wiki/`. The runner copies that directory into the second
   session for every arm (FR-012). The evaluation prompt says where the
   wiki is. The fixture wiki has an index and no other page, so there is
   one fact, no competing page and no obsolete decision. The wiki is
   therefore the carrier for every arm, `bare` included. Any arm that
   writes a file and reads it back passes. The report's diagnostics agree:
   the other arms wrote under the wiki directly (`fs_grep` 52 of 78
   Write/Edit calls, `memkernel` 38 of 63). The `wiki_studio` arm wrote 0
   of 9 there and made no `ingest` or `query` call in 177 Bash calls.
2. **The token totals do not compare.** The report gives `wiki_studio`
   4,309,745 receipt tokens against about 19-20 million for each other
   arm. `wiki_studio` ran on `lc-wiki` only (25 trials). The others ran
   all four groups (100 trials). The report has no per-group token table,
   so no cost result follows for the wiki.
3. **The frozen arm is pinned by hash.** memkernel's
   `arms/wiki_studio/config.frozen.json` records `v0.4.1`, commit
   `8b5c8af`, and the sha256 of `docs/agent-arm/instruction.md` and
   `config.frozen.json` from this repository. `requirements.txt` pins
   `wiki-studio==0.4.1` with PyPI hashes. The proposal says to keep that
   run as the historical run and to version the composition as a separate
   experiment. So the files in `docs/agent-arm/` are a historical source.
   They are not re-pinned.
4. **The demo's skeleton exists.** `tests/integration/test_release_b_loop.py`
   case 4 retains a wrong convention, exports it, corrects it through a
   guarded update carrying `corrects: <ref>`, approves it, imports it, and
   asserts that the wrong text is not current while its record is kept.
   It runs in one process with an in-process Chroma and a deterministic
   embedding, and prints nothing. Its module docstring still says the
   loop job "stays non-blocking until memkernel #48"; `ci.yml` says the
   job is blocking since the 0.6.0 pin.
5. **"Revision and receipt beside the answer" needs no new code.**
   memkernel 0.6.0 tags an imported memory `page_sha:<sha256>`
   (`PAGE_SHA_TAG`, `wiki/sync.py`) with the page path as its source.
   `recall` leaves out records with `superseded_by`; `list_memories(...,
   include_superseded=True)` still returns them. On this side,
   `review_state` gives `approved_sha256`, the receipt gives
   `submission_digest`, `actor`, `started_at` and `committed_at`, and the
   approval record gives the approver and `timestamp`.
6. **memkernel 0.6.0 covers replacement only.** Correction by `corrects`
   is in 0.6.0. Withdrawal on deprecation, deletion and `superseded_by`
   is memkernel 0.7 (`specs/memkernel-0-7/`, on main, not released). The
   roadmap's obsolete-answer rate covers all three, so two of them depend
   on memkernel 0.7.
7. **memkernel downloads an embedding model.** Its server loads
   `all-MiniLM-L6-v2` (about 90 MB) at first start. The integration tests
   avoid it with a deterministic embedding port.
8. **Curation cost is in records already.** Queue age is the time from a
   receipt's `committed_at` to the approval record's `timestamp`.
   Proposer, promoter and approver are recorded. Model calls and tokens
   are in memkernel's receipts. No wiki-studio code is needed to count
   them.
9. **The compatibility matrix is done for the pair.** `docs/compatibility.md`
   lists 0.8.0 with memkernel 0.6.0 as tested (run 41065605919). The
   launch item only needs the quickstart and demo jobs added as evidence.
10. **The standalone path is model-free.** `init`, `propose --from DIR
    --promote`, `approve`, `find`, `read`, `review_state` and `findings`
    call no model. `ingest` needs a backend CLI. The MCP server's launch
    line can be exercised in CI through the conformance runner's
    `--server-cmd`; `claude mcp add` cannot.

## Appetite

**2w** (D1, confirmed), one bet. For an LLM executor the work content is
about 16-24 hours across five scopes:

| Scope | Estimate |
|-------|----------|
| S1 Standalone quickstart, executed | 3-4h |
| S2 memkernel composition quickstart, executed | 3-5h |
| S3 The obsolete-decision demonstration | 4-6h |
| S4 The measurement design (stretch) | 4-6h |
| S5 Closing issue #10 and the launch docs | 2-3h |

The work content is small. The wall-clock budget is set by three things:

- **Review rounds.** The external reviewer reviews the pitch, the spec
  and the build. Each earlier cycle drew several rounds.
- **The memkernel issue.** S4's design goes to memkernel's owner. The
  task set, the arm and the run are memkernel's. This cycle waits for no
  answer, but the text needs one review.
- **The release.** 0.8.1 (D5, confirmed) is cut by the owner.

Why not 4w: nothing here changes runtime behaviour or the API under
`src/` (only the version constant moves), and the measurement run is
excluded by the circuit breaker. 4w would only fit if the owner wants the
composition arm and task drafts built to a level memkernel can adopt
without changes, as `docs/agent-arm/` was for 0.4.0. That is S4 grown into
a scope of its own.

Planned order:

- **Week 1:** S1 and S2 written and executed in CI. S3's script and CI
  job. S4's ceiling analysis and the six-question map.
- **Week 2:** S3's recorded run and its page. S4's design and the
  memkernel issue text. S5: the README, the roadmap, the CHANGELOG, the
  #10 comment and the successor issue. Review and 0.8.1.

## Solution shape

Docs, tests, CI jobs and one example script. No runtime behaviour or API
change under `src/` (the version constant in `src/wiki_studio/__init__.py`
changes with the release, as every release does), no new exit code, no
dependency. memkernel stays out of the
package and the default dev group; it is installed only in clean-install
CI jobs, as today.

```
docs/quickstart.md ───────────── fenced blocks marked "run" ──▶ CI: fresh venv, wheel[mcp], run in order
docs/quickstart-memkernel.md ─── fenced blocks marked "run" ──▶ CI: fresh venv, wheel + memkernel==0.6.0
examples/correction-loop/demo.py ─ session 1 │ curator │ session 2 ─▶ CI job (blocking) + one recorded run
docs/demo-correction-loop.md ◀── the recorded run's transcript, versions, revision and receipt
eval/composition/design.md ──── ceiling analysis, requirements, task sketches, arm draft ──▶ memkernel issue
README Evidence + #10 comment ── what 0.5.0 shows, what remains, successor issue
```

**Quickstarts (S1, S2).** Each is one page with one path through it.
Every executed command sits in a fenced block that a test extracts and
runs in order, so the page and the check cannot drift. Steps that need a
model or a host (`ingest` with a backend, `claude mcp add`, Kiro) are
shown, marked "not executed in CI", and link to the evidence that covers
them (the recorded Claude Code host run of 0.8.0).

**Demonstration (S3).** One script plays the roadmap's story on a clean
install: session 1 retains a wrong decision and recalls it; it is
exported through the gate; a curator corrects it through a reviewed
proposal that carries `corrects`, promotes it and approves it; session 2,
a new process on the same persisted store, imports and recalls. The old
answer is absent. The new one is printed with its page, revision
(`page_sha` equals `approved_sha256`), receipt and approval. The old
record is still readable as superseded.

**Measurement design (S4).** A document, not a run. It explains the
ceiling, states what a task set and a governed-composition arm need so
that `bare` fails and the arms can differ, maps each of the roadmap's six
questions to a measurement or to existing evidence, and lists memkernel's
changes as dependencies.

## Scopes

Build order: S1, S3 and S4 start at once. S2 shares S1's extraction test.
S5 needs the others for the release; its #10 part does not.

### S1: Standalone quickstart, executed, ~3-4h

- **Page.** `docs/quickstart.md` (D3): install (`pip install
  'wiki-studio[mcp]'`), `init`, write a draft directory, `propose --from
  DIR --promote --by you`, the review state read with an executed Python
  block calling `api.review_state` (there is no CLI verb; the MCP tool
  and the API are the surfaces), showing `unapproved`, then `approve --by
  you` and the same block showing `approved`, `find`, `read --json`, a guarded
  update with `.base.json` and the stale-update refusal (exit 9), `lint`,
  `findings`. Then the MCP server: the `wiki-studio-mcp` launch line, the
  `claude mcp add` line, propose-only mode, and links to Kiro's settings
  in `docs/mcp-adapter.md`. `ingest` is an aside with a backend, not
  executed.
- **Check.** A test extracts the blocks marked to run (D8) and runs them
  in a temporary directory against the installed CLI, asserting each exit
  code. It runs in a clean-install CI job on the built wheel with the
  `mcp` extra. The server's launch line from the page is passed to the
  conformance runner as `--server-cmd`.
- **Link.** README Install points to the page.

### S2: memkernel composition quickstart, executed, ~3-5h

- **Page.** `docs/quickstart-memkernel.md` (D3): install
  `memkernel[wiki]==0.6.0` and `wiki-studio==0.8.x` in one environment;
  register both MCP servers in Claude Code (memkernel's settings block,
  `wiki-studio-mcp` with `--disable-tool promote` if promotion stays
  human), Kiro by link; `api.init` once; then the loop: `retain`,
  `wiki_export` (a draft through the gate), the curator's review with the
  wiki-studio CLI (`read --json`, edit, `propose --from` with
  `.base.json`, `--promote`, `approve`), `wiki_import` (governed,
  approved revisions only), `recall`. The commit policy, stated per path:
  commit the wiki manifest, the pages, `index.md`, `log.md` and the whole
  `<wiki>/.audit/` tree (the ingest log and `approvals/`: governed import
  reads the approval records, so a clone without them sees every page
  `unapproved`); commit the proposals' `.applied/` archive (plan, preview,
  receipt: the evidence the demo quotes) or state why it is ignored; ignore
  only the lock file beside the wiki and the rebuildable search cache. The
  handoff is executed: the committed tree is copied to a fresh directory
  and `wiki_import` there imports the same approved revisions.
- **Check.** memkernel's MCP tools are shown as tool calls. The executed
  blocks use the Python calls those tools make, as the loop test does
  (D9). They run in a clean-install job pinned to memkernel 0.6.0 from
  PyPI (D10).
- **Link.** README Install and `docs/consumers.md`'s memkernel section
  point to it. The consumer recipes stay as reference.

### S3: The obsolete-decision demonstration, ~4-6h

- **Script.** `examples/correction-loop/demo.py` (with the copyright
  header). Three steps, each a separate process on one persisted
  memkernel store and one wiki (D9):
  1. *Session 1.* Retain a wrong decision. Recall it: the wrong answer is
     current. Export it through the gate (a draft page).
  2. *Curator.* `wiki-studio read --json`; write the corrected page with
     `status: stable` and `corrects: <ref>`; `propose --from --promote
     --by curator`; `approve --by curator`. Print the receipt and the
     approval record.
  3. *Session 2.* `wiki_import`. Recall the same question. Print the
     answer, its page, its `page_sha` beside `review_state`'s
     `approved_sha256`, the receipt's `submission_digest` and
     `committed_at`, and the approver. Assert that the wrong text is in
     no current answer. Print the old record with `include_superseded`,
     its `superseded_by` set.
- **CI.** A blocking clean-install job (memkernel 0.6.0, the built
  wheel) runs the script. The script exits non-zero if any assertion
  fails.
- **Recorded run (D2).** One run committed under
  `examples/correction-loop/runs/<date>-wiki-studio-<v>-memkernel-0.6.0/`,
  bound to the bytes it executed, in this order: (1) the script and its
  execution protocol are committed first; (2) the run starts from a clean
  tree at that commit, recorded; (3) the wiki-studio wheel is built from
  that commit and its sha256 recorded, and the memkernel 0.6.0
  distribution's sha256 recorded against PyPI; (4) the embedding model's
  Hugging Face revision is pinned and verified, by default the
  `1110a243…` revision memkernel's 0.5.0 run disclosed; (5) the run happens
  once and the transcript and manifest are committed in a separate commit
  after it. The manifest holds those hashes, the versions, Python, the
  script sha256 and an end-state hash over the canonical exported state
  (the wiki tree and the receipts), never over raw Chroma files, whose
  storage metadata is not deterministic. Wall times from install to the
  first approved revision and to corrected recall are recorded. These times are labelled
  machine time on a scripted path, not a measure of human adoption (D15).
  A failed attempt is kept, as with host runs.
- **Page.** `docs/demo-correction-loop.md` tells the story in about one
  screen, quoting the recorded run. Correction by replacement only;
  deprecation and deletion wait for memkernel 0.7 (D11).
- **Small fix in passing.** The loop test's stale docstring (finding 4).

### S4: The measurement design, ~4-6h (stretch, cut first)

`eval/composition/design.md` (D14). A design that memkernel can adopt
into its own preregistration. It does not preregister or run anything.

- **The ceiling, explained** (findings 1 and 2), with the report's
  numbers. What the published run supports, no more: the two diagnostics
  it records (0 `ingest` or `query` calls; 0 direct `Write` or `Edit`
  calls under the wiki) and no outcome or cost difference. Those
  diagnostics do not prove the arm stayed inside the gate: Bash can write
  files, and the receipts keep payload hashes, not commands or gate
  records. A gate claim needs the gate's own records checked, which S4
  lists as a requirement for the composition arm.
- **Requirements for a task set that can discriminate:**
  - a calibration that shows `bare` fails before any measured run;
  - an obsolete decision in each chain (record X, correct to Y, evaluate),
    with a checker that tells X (obsolete answer) from Y (pass) and from
    anything else (fail), so the obsolete-answer rate is executable;
  - the correction travels only through the arm's own workflow, not
    through a file every arm receives;
  - competing pages in the fixture wiki, so reading one page is not
    enough.
  Five to ten task sketches in prose (prompts per session, the obsolete
  and the informed reference). No task code.
- **The arms**, held to the roadmap's comparison: memkernel alone,
  memkernel with governed wiki-studio, files plus grep, and the negative
  control. The composition arm is a new, versioned arm; the 0.4.1 arm
  stays frozen (D7). The arm needs a curator between sessions; the design
  lists the options (a scripted curator with a preregistered policy, the
  `auto_approve_on_promote` policy, an oracle curator as an upper bound),
  what each measures, and a recommendation.
- **The six questions, mapped:**

  | Question | Where it is answered |
  |---|---|
  | Does governance improve task outcomes | the paired design above, in memkernel's suite |
  | Do corrections reach the agent | the obsolete-answer rate from the checker; deprecation and deletion need memkernel 0.7 |
  | Can changes be explained | counted from the end state with `review_state` and `findings` (records, receipts, citations); no new code |
  | Does failure recovery work | the loop test's retry property and the Release A regression tests (controlled faults in CI), not an agent run |
  | What does curation cost | memkernel's token receipts; receipts and approval records for queue age and actors (finding 8) |
  | Can others adopt it | S3's machine times now; a pilot (Launch step 3) for people |

- **Dependencies on memkernel** (listed, not built): the arm and its
  curator step, the task set and its calibration, a per-group token
  table, the preregistration, the budget, memkernel 0.7 for withdrawal.
  Filed as one memkernel issue by the build session (D4), linked from
  #10's successor.

### S5: Closing issue #10 and the launch docs, ~2-3h

- **README Evidence.** Replace the stale `agent-memory-bench` sentence
  with what the 0.5.0 run shows, with a link: the arm ran on `lc-wiki`,
  25 of 25 like every arm, a ceiling, no claim, tokens not comparable.
  Point to the demo and to S4's design. No efficiency or superiority
  wording.
- **Roadmap.** Launch sequence step 2: the quickstarts, the matrix and
  the demonstration, each with its evidence. The Evidence section points
  to the design and says that the published 0.5.0 run is at ceiling and
  that no governed-composition measurement able to discriminate the arms
  has been run.
- **Compatibility.** The 0.8.x and 0.6.0 row names the quickstart and
  demo jobs beside the loop jobs.
- **Issue #10 (D6).** A closing comment: the condition in the issue is
  met; what the run shows and does not show; what remains, in a
  successor issue for the composition measurement that links the
  memkernel issue. If the owner chooses to keep #10 open, the same
  comment is posted and the issue stays open.
- **Release.** CHANGELOG `[0.8.1]` (D5) and the version bump in
  `pyproject.toml` and `src/wiki_studio/__init__.py` together.

## Exit evidence

| Roadmap item | Where it lands |
|---|---|
| Two tested quickstarts, standalone and memkernel composition, with Claude Code and Kiro instructions | S1 and S2: the pages and their clean-install CI jobs, named by run in `docs/compatibility.md` |
| The compatibility matrix | exists for 0.8.0 with memkernel 0.6.0; S5 adds the new jobs to the row |
| A short demonstration of an obsolete decision corrected through a reviewed proposal and absent from the next session, with the revision and receipt beside the answer | S3: the CI job and the recorded run, quoted in `docs/demo-correction-loop.md` |
| Issue #10 | S5: closed by restatement with a successor issue (D6), or left open with the same comment |

Not exit evidence: the integration measurement. S4 is its design only.

## Decisions

D1-D6 change the build or the evidence. The owner answered them on
2026-11-03 (recorded here; D3 and D4 differ from the pitch's defaults).
The rest follow from the repository's rules and can be overruled at the
spec review.

- **D1 (owner, 2026-11-03: 2w). Appetite.** One 2w bet. S4 delivers the
  ceiling analysis, the design and the dependency list, not adoptable arm
  and task drafts.
- **D2 (owner, 2026-11-03: both). The demo's form.** A script run as a
  blocking CI job against pinned releases, and one committed recorded
  run.
- **D3 (owner, 2026-11-03: this repository and memkernel's README). Where
  the quickstarts live.** `docs/quickstart.md` and
  `docs/quickstart-memkernel.md`, linked from README Install. In the same
  cycle the owner edits memkernel's README to link the composition
  quickstart; that edit is the owner's, in the memkernel repository, not
  the build's.
- **D4 (owner, 2026-11-03: yes, filed by the build). File the memkernel
  issue this cycle.** One issue in gosha70/memkernel with S4's design and
  dependency list, filed by the build session with no approval step; its
  text is S4's committed design document, and its number is recorded in
  #10's successor. The redesign itself is memkernel's decision and work.
- **D5 (owner, 2026-11-03: 0.8.1). Release.** A patch release: docs,
  tests, CI jobs and an example; no API change, so not 0.9.0. It puts
  the quickstart links on the PyPI page.
- **D6 (owner, 2026-11-03: close by restatement with a successor). Issue
  #10.** Its written condition is met. Close it with the restating
  comment and open a successor issue for the discriminating measurement.
- **D7. The 0.4.1 arm stays frozen.** `docs/agent-arm/config.frozen.json`
  and `instruction.md` are not edited; their sha256 are recorded in
  memkernel's frozen arm. Its README gains one note pointing to S4. The
  composition arm is a new, versioned experiment, as the proposal says.
- **D8. One source for each quickstart.** Executed blocks are extracted
  from the markdown. There is no separate script to keep in step.
- **D9. A session is a process.** Each session is a new process on the
  persisted store. memkernel is driven through the Python calls its MCP
  tools make, as in the loop test. The curator uses the wiki-studio CLI.
  A Claude Code session is not simulated in CI.
- **D10. Pin memkernel 0.6.0 from PyPI,** not main (0.7 is in progress).
- **D11. The demo corrects by replacement** (`corrects`). Deprecation and
  deletion are listed for memkernel 0.7.
- **D12. No model backend on any executed path.** Only memkernel's local
  embedding model runs.
- **D13. No runtime behaviour or API change under `src/` is planned; the
  version constant moves with the release.** A defect found by a quickstart is
  fixed as its own change with a regression test, and the scope that
  found it waits for it.
- **D14. S4 is a design, not a harness.** The preregistration, runner,
  statistics, budget and run are memkernel's.
- **D15. Wall times are labelled machine time** on a scripted path, not
  adoption evidence.
- **D16. The example lives in `examples/`,** added to the ruff and format
  checks in CI. Its recorded runs live beside it.

## Rabbit holes

- **The page and the check drift apart.** A quickstart and a separate
  test script diverge after the first edit. *Workaround:* D8, one source.
- **The embedding model in CI.** memkernel downloads about 90 MB at first
  start, and the download can be slow or blocked. *Workaround:* cache the
  model directory in the job. If the job is still unreliable, CI injects
  the loop test's deterministic embedding and says so in the job; the
  recorded run keeps the real model.
- **Driving memkernel through MCP in CI.** It would need a host or the
  SDK client against memkernel's server and its startup cost.
  *Workaround:* D9. The host settings are documented; the 0.8.0 Claude
  Code host run covers wiki-studio's adapter.
- **Designing the benchmark in full.** Task authoring, a simulated
  curator, a calibration and power analysis could fill the cycle.
  *Workaround:* S4 states requirements and options with a recommendation;
  memkernel decides and builds. Timebox 6h, and cut first.
- **A claim slipping into the docs.** "Cheaper", "better" or "prevents
  obsolete answers" in the README or the demo page. *Workaround:* the
  demo page states what one scripted run shows; the README's evidence
  text names the ceiling; the reviewer checks the wording.

## No-gos

- No hosted collaboration, new runtime, LLM-as-judge rubric, or runner,
  event schema or statistics code of our own (memkernel's suite is the
  harness). No memkernel.dev page.
- No measured run of memkernel's suite, no preregistration and no spend
  in this cycle.
- No runtime behaviour or API change under `src/` beyond a separate defect
  fix (D13); the version constant moves to 0.8.1 with the release. No new exit
  code; 0 and 2..11 keep their meaning, 1 stays fatal lint. `promoter.py`
  stays the single writer. No runtime dependency; memkernel stays a
  CI-only install.
- No edit to the frozen 0.4.1 arm files, the frozen navigation runs or a
  recorded run.
- No memkernel code or doc edits from this repository.
- No superiority or efficiency claim without a preregistered run.
- No recorded Kiro run required; Kiro stays documented, not blocking.
- Coverage stays at or above 92 percent; every executable artifact is run
  at least once before commit.

## Circuit breaker

Core is S1, S2 and S3: the two quickstarts and the correction
demonstration, each executed on a clean install. They ship alone as
0.8.1 if the cycle runs out. The triggers, in order:

1. **End of week 1.** If S1-S3 are not downhill, S4 shrinks to the
   ceiling analysis and the dependency list, filed as one memkernel
   issue, with no task sketches and no arm draft.
2. **End of week 2.** S4 not done ships as far as it got, marked a draft;
   it is not exit evidence either way. The measurement run (memkernel's
   suite, its preregistration and its budget) is not this cycle's exit
   evidence and does not start.
3. **Issue #10** closes only by restating what the published 0.5.0 run
   shows, with a successor issue (D6). Otherwise it stays open. It never
   closes on a claim.
4. **Never, to save time:** change behaviour under `src/` or an exit
   code; add a dependency; edit the frozen 0.4.1 arm files or a frozen
   run; hand-edit a recorded run; put a model backend on an executed path;
   write runner or statistics code; weaken or skip a test; state a gain
   without a preregistered run.

"Exhausted" means two working weeks have passed. A third review round on
one scope is not exhaustion: it is an escalation to the owner, who
chooses a fix session, a cut from the list above, or a hold.

## Questions for the owner

Answered 2026-11-03; the answers are recorded in D1-D6. Asked as:

1. **Appetite:** 2w (default) or 4w?
2. **Demo:** a CI job and a recorded run (default), CI only, or recorded
   only?
3. **Quickstarts:** in this repository under `docs/`, linked from the
   README (default), or elsewhere (README sections, memkernel's README)?
4. **memkernel issue:** filed this cycle with the design (default), or
   left for memkernel's own shaping?
5. **Release:** 0.8.1 (default) or 0.9.0?
6. **Issue #10:** close by restatement with a successor issue (default),
   or keep open until a discriminating run?

## Bet log

| Date | bet_status | Note |
|------|------------|------|
| 2026-11-03 | shaping | Pitch drafted from wiki-studio #10, the cooldown report after cycle 03 (candidate 1), docs/roadmap.md (Evidence; Launch sequence step 2) and the 2026-10-23 product proposal. wiki-studio read at main e1f793f; memkernel read at main a1a5b32 and tag v0.6.0, including eval/lifecycle-suite/report-0.5.0.md. |
| 2026-11-03 | shaping → shaped | 5 scopes, 2w, 0.8.1 (both to confirm). Core S1-S3 (quickstarts, demonstration); S4 (measurement design) stretch, cut first; S5 closes #10 and releases. 16 decisions; D1-D6 open for the owner with defaults, not yet asked (AskUserQuestion was unavailable to the shaping agent). |
| 2026-11-03 | shaped (revised) | Owner answered D1-D6: 2w; demo as a blocking CI job plus a recorded run; quickstarts under docs/ linked from the README, and the owner links the composition quickstart from memkernel's README this cycle; the memkernel issue is filed by the build session with S4's design, no approval step; 0.8.1; #10 closed by restatement with a successor issue. |
| 2026-11-03 | shaped (revised, 2) | PR #68 review, five findings folded in: the quickstart reads review state through an executed `api.review_state` block (no CLI verb exists); the composition quickstart states the commit policy per path (`.audit/` with the approval records committed, only the lock and cache ignored) and executes the handoff; the recorded run is bound to the executed bytes (script committed first, clean tree, wheel and memkernel distribution hashes, embedding revision pinned, run then committed separately, end-state hash over canonical state); the ceiling analysis reports the two diagnostics and no gate claim, and the roadmap says no discriminating governed-composition measurement has run; the no-`src/` rule is "no runtime behaviour or API change", the version constant moves with the release. |
| 2026-11-03 | shaped (revised, 3) | PR #68 recheck: the two remaining no-`src/` sentences (appetite rationale, D13) use the same contract as the solution shape and no-gos: no runtime behaviour or API change, the version constant moves with the release. |
| 2026-11-03 | bet | Bet for cycle 04. |
