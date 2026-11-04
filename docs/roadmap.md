# Roadmap

The product direction and the three releases that follow from the October
2026 evaluation of Wiki Studio. This file is the durable record; the
reasoning behind it is in `docs/proposals/2026-10-23-product-proposal.md`
(the owner's proposal), the PR #37 review history, and the Release A spec in
`specs/wiki-studio-0-6-0/`. Later decisions update this file, not the
proposal.

## Product decision

Wiki Studio is an independent, embeddable curation engine for project
knowledge used by AI agents. memkernel is the flagship composition, not the
owner: the Python API, CLI, Markdown format and evaluation suite stay useful
without it, and other runtimes compose through the same contracts.

The claim to earn: an agent proposes a change; policy decides whether it may
land; concurrent changes are preserved; the accepted revision carries
evidence; replacing it keeps the obsolete version from returning as current
knowledge. "Trustworthy" is the outcome of that workflow, not a label.
Public claims name demonstrated guarantees and avoid "best in class",
"rejects all bad pages" and "atomic" without qualification.

Positioning:

- **Wiki Studio:** reviewable project knowledge for AI agents, with validated
  proposals, controlled promotion and revision history.
- **Flagship composition:** memkernel retains and retrieves memory; Wiki
  Studio curates the durable project knowledge it uses.

Investment rule: correctness, integration effort and measured user value
first; the core stays free of runtime dependencies; the safety patch ships
before new contracts and broad integrations.

## Why this order

Three external reviews (two consultant reviews and one code review) agreed
on the pattern and disagreed on sequencing. The code review reproduced five
defects on `main` at 41cfe54: concurrent promotes revert each other's pages;
no revision precondition on replacements; incomplete containment (symlinks,
outside links, `find` following them); citation checks that accept forged
evidence; and "atomic" meaning exception rollback. Those break promises the
README makes, so they come before any feature or promotion push. Retrieval
and distribution follow, measured, not asserted.

## Release A: safe changes (0.6.0) — shipped 2026-10-24

Owner: Wiki Studio. Spec: `specs/wiki-studio-0-6-0/`. Exit evidence: every
reproduced defect is a passing regression test through both entry points.

- Commit only the patch-set's paths; an OS advisory lock on the resolved
  wiki, taken by every cooperating writer; receipts beside byte-identical
  archived proposals with a full-payload submission identity and a pinned
  commit / receipt / archive recovery protocol.
- A base revision per replacement, captured where the author read the page
  (`read` returns content and hash from one read); checked under the lock;
  creates and appends from older proposals stay safe; unguarded replacements
  refused unless an explicit compatibility option is passed and recorded.
- One containment check on every read and write surface across three
  boundaries: wiki, proposal directory, configured source roots; the link
  collector covers every local target.
- Citation fragments validated against the prompt snapshot; evidence
  required for a non-empty answer.
- Guarantees stated as they are. memkernel's outer rollback is a named
  limitation; no combined safety claim until Release B closes it.
- Fallback: a contract-compatible 0.5.1 subset if 0.6.0 slips.

## Release B: governed curation (joint with memkernel)

Status: closed 2026-10-30. Wiki Studio's half shipped in 0.7.0
(2026-10-27); memkernel's counterpart (memkernel #48: snapshot removal in
memkernel PR #55, the governed import in PR #60) shipped in memkernel
0.6.0 (2026-10-30); the `memkernel-compat` and `memkernel-loop` CI jobs,
pinned to that release and blocking, pass the four loop cases and the
retry property on clean installs (`docs/compatibility.md` names the run
on `main`). Tracker #38 is closed.

Depends on A. Exit evidence: one complete correction loop (retain, export,
review, import, correct, next-session recall) passes on clean installs with
compatible versions and survives retries. The loop's acceptance cases are
named here so they are not lost in shaping: a draft page is never imported;
a page that declares itself approved without the gate's record is refused;
an approved page that is edited after approval is re-reviewed before its new
revision is imported; a wrong raw memory that a corrected page supersedes is
not returned as a current answer in the next session, while its provenance
remains readable.

Wiki Studio:
- First item: the combined integration gate deferred from A — memkernel
  bridge compatibility through `api.propose` (creates and appends), receipt
  and `.applied/` layout, lock coordination.
- A versioned knowledge contract: schema identity and version, proposal and
  audit format versions and capabilities through `info`; a root manifest
  written by `init`; a fingerprint for project-local schemas; a compatibility
  matrix of tested package pairs.
- Identity and evidence: stable page identity across renames; asserted actor
  attribution (`--by`) recorded as attribution, not authentication; approver
  recorded separately when required.
- Approval bound to the revision and the policy: an accepted revision records
  the wiki, page identity, content hash, policy and decision; a manual edit
  after approval invalidates it until revalidated; a frontmatter status alone
  does not establish approval, the gate's record does.
- A `superseded_by` key through a decision record on both sides; review
  state kept separate from memory tier.
- Findings exposed without a model call so the host decides when synthesis
  or review is worth a model.

memkernel:
- A governed configuration that requires the gate and refuses the unchecked
  fallback; a clearly identified ungated mode for independent deployments.
- Idempotent import by page identity and revision hash, of approved
  revisions only: the importer today accepts drafts and has no approval
  check, so it must read the gate's approval record and refuse drafts,
  self-declared approval and a revision whose hash is not the approved one;
  withdrawal on supersession, deprecation and explicit deletion; a pending /
  applied / failed synchronisation state with a retry path; no claimed
  transaction across Markdown and the memory store.
- Reconciliation of originating raw memories: when an approved page corrects
  the memory it was curated from, that memory is marked superseded by the
  page so it no longer competes as a current answer, with its provenance
  retained; the page-to-source mapping is explicit, so a multi-source page
  withdraws only the sources it corrects and never every source it cites.
- Curation debt at session start; bounded batches of candidates; source
  content hashes for freshness, with Git revision metadata when available.
- The outer whole-wiki snapshot and rollback coordinated with the wiki lock
  or removed.

Docs: two tested quickstarts, standalone ([`docs/quickstart.md`](quickstart.md))
and memkernel composition
([`docs/quickstart-memkernel.md`](quickstart-memkernel.md)), each with Claude
Code and Kiro instructions, shipped in wiki-studio 0.8.1 and executed in the
`quickstart` and `quickstart-memkernel` CI jobs; the correction-loop
demonstration is [`docs/demo-correction-loop.md`](demo-correction-loop.md).

## Release C: standalone usefulness and broader adoption

Status: shipped in 0.8.0 (2026-10-29) and closed with that tag. The three
exit-evidence items are in the release: the held-out run and the
`decide` record under `eval/navigation/` (`fts5` became the default
ranker), the cache recovery tests, and a recorded Claude Code host run
that passed `check-host-run` (`conformance/runs/`). Kiro is documented
and was not release-blocking.

Depends on a stable shared API. Exit evidence: versioned retrieval results
on declared fixtures, cache recovery tests, and one non-memkernel runtime
passing the adapter conformance suite.

- Discovery: SQLite FTS5 ranking behind the index-first workflow and the
  five-page cap, plus a byte or token budget; the index is a rebuildable
  cache with a content manifest and stale-index recovery; FTS5 availability
  probed at runtime with a documented fallback. The published question set
  is a development set; a held-out corpus with a frozen protocol is added
  before final tuning. Results are versioned beside the frozen runs.
- Portability: an optional MCP adapter exposing discovery, page reading with
  revision hashes, proposals, promotion, lint and information through the
  same validated API; proposal and promotion stay distinct; model-spawning
  verbs off the default surface; shipped as an extra on the official SDK
  with the standard-library core intact.

## Evidence

Correctness tests run on every release. Integration measurement starts with
Release B. The primary comparison holds agent, model, task set and memkernel
retrieval constant and varies the curation workflow: memkernel alone,
memkernel with governed Wiki Studio, files plus grep. A separate standalone
comparison covers Wiki Studio discovery. The frozen 0.4.1 agent arm stays
as the historical run; the hardened composition is a separately versioned
experiment.

| Question | Measurement |
|---|---|
| Does governance improve task outcomes | Paired task success and failure categories across sessions |
| Do corrections reach the agent | Obsolete-answer rate after replacement, deprecation and deletion |
| Can changes be explained | Fraction of accepted revisions with resolvable source and decision evidence |
| Does failure recovery work | Lost updates, duplicates and unreconciled revisions under controlled faults |
| What does curation cost | Model calls, tokens, wall time, review time and queue age |
| Can others adopt it | Time to first accepted revision and corrected recall on a clean install |

Executable checkers where possible; published rubric and blinded review
where not. Evaluation sets, budgets and analysis are frozen before measured
runs. Uncertainty, negative controls, failures and version identifiers are
reported. Safety regressions block releases; accuracy or cost superiority
needs evidence, not a small-fixture percentage.

The published integration evidence so far is memkernel's 0.5.0 run. Its
`wiki_studio` arm (wiki-studio 0.4.1 through the CLI) passed 25 of 25 trials
on the five `lc-wiki` tasks, as every arm did, `bare` included; every
pairwise effect in the group was +0.0. The group is at ceiling — the runner
copies the wiki into the second session for every arm — so it supports no
comparison between the arms, and its token totals do not compare across
groups. [`eval/composition/design.md`](../eval/composition/design.md)
explains the ceiling with the report's numbers and states what a task set, a
versioned composition arm and a curator policy need so that `bare` fails and
the arms can differ. No governed-composition measurement able to discriminate
the arms has been run; that measurement is memkernel's to preregister and
run. The design is filed as [memkernel #90](https://github.com/gosha70/memkernel/issues/90) and this repository's successor issue is
[#75](https://github.com/gosha70/wiki-studio/issues/75); the successor issue's text is committed under `eval/composition/`.

## Launch sequence

1. After A: the patch and its exact guarantees; a credited advisory for the
   escape findings per `SECURITY.md`; one public issue per other defect,
   closed by the release.
2. After B (shipped in 0.8.1): the two tested quickstarts,
   [`docs/quickstart.md`](quickstart.md) and
   [`docs/quickstart-memkernel.md`](quickstart-memkernel.md), whose executed
   blocks run in the `quickstart` and `quickstart-memkernel` CI jobs; the
   compatibility matrix at [`docs/compatibility.md`](compatibility.md); and a
   short demonstration of an obsolete decision corrected through a reviewed
   proposal and absent from the next session,
   [`docs/demo-correction-loop.md`](demo-correction-loop.md), run by the
   `demo-correction-loop` CI job and once as a recorded run, committed at
   `examples/correction-loop/runs/2026-11-04-wiki-studio-0.8.1-memkernel-0.6.0/`.
3. Pilot: three teams, one correction loop each, repeated across sessions.
   A validation target, not evidence of demand.
4. After C: conformance fixtures, measured results, the adapter in
   registries. Further adapters follow repeat use.

## Out of scope, by decision

Hosted collaboration, a new runtime, a vector store as a requirement,
mandatory semantic judges, the STE vocabulary, auto-rewrite of prose, and
crash-safe multi-file transactions unless a deployment need justifies them.

## Record

- 2026-10-22: code review reproduces five defects on 41cfe54.
- 2026-10-23: product proposal adopted with amendments; Release A specified
  (PR #37), reviewed twice and approved; this roadmap written. A plan review
  the same day returned the bundle to draft for revisions to the submission
  identity, recovery and containment requirements; re-approval pending.
