---
spec_mode: full
feature_id: wiki-studio-0-9-0
risk_category: feature
justification: "A new body convention on the page contract shared with memkernel (decision record required by CLAUDE.md), three new kinds in the model-free findings contract a host reads at session start, a line-based scan whose edge cases (dangling reasons, repeats, the marker-line link, fenced code, superseded targets, scoping) each need a pinned behaviour and a fixture, a resolution rule checked part by part through the promote gate, a copied memkernel parser pinned to a tag, and a release; a full spec pins the form, the kinds, the descriptions, the order, the invariants that must not move and the cut order before an unattended build."
status: draft
date: 2026-11-06
collaboration_mode: single
origin:
  issue: 71
  urls:
    - https://github.com/gosha70/wiki-studio/blob/main/specs/pitches/71-conflict-callouts/pitch.md
    - https://github.com/gosha70/wiki-studio/issues/71
    - https://github.com/gosha70/wiki-studio/pull/85
    - https://github.com/gosha70/wiki-studio/blob/main/specs/retros/cooldown-after-04.md
    - https://github.com/gosha70/wiki-studio/blob/main/docs/adr/0001-glossary-avoid-key.md
  origin_claim: |
    Issue #71 (no comments on 2026-11-05), shaped by the bet pitch
    specs/pitches/71-conflict-callouts/pitch.md (cycle 05, building; approved
    in PR #85 at 462e679 with two points deferred to the spec) from
    specs/retros/cooldown-after-04.md (candidate 3). Problem, as the pitch
    states it: "When two sources disagree, the claim on a wiki page is
    uncertain. Nothing on the page says so, and nothing reports it later."
    "So a recorded disagreement has no fixed form. Nothing deterministic tells
    a curator, or memkernel's session-start curation report, which
    disagreements are still open, which were marked on one page only, or
    which name a page that is gone." Solution shape: "A body convention, one
    read-only check and the docs. No frontmatter key, no new verb, flag, exit
    code, MCP tool or dependency. No change to structural lint, approve,
    review_state or the prompts' code." The form: "A blockquote callout,
    > [!conflict], on both pages. Its first wiki-page link names the other
    page. Its text names the sources each side cites." The check: "findings
    scans each content page in scope line by line, outside fenced code. It
    reads each callout's other page, resolves it as the link rule does, and
    pairs the callouts. The result is three kinds (D5)." What "open" means:
    "A callout on a page is an open disagreement. There is no 'resolved' mark
    on the page. Resolving removes both callouts in one promoted patch-set,
    with the deciding source cited." One 2w bet released as 0.9.0 (D14);
    core S1, S2 and the wiki-studio half of S4, never cut; S4's live import
    case cut first, then D6's superseded case; owner decisions D1-D7, D9,
    D11 and D14 (2026-11-05, every default) and the settled D8, D10, D12,
    D13, D15, D16 carried into the FRs; the PR #85 review's two points (the
    link on the marker line; repeats count once) carried into FR-010.
---

# Plan: wiki-studio 0.9.0 — conflict callouts

The bet pitch `specs/pitches/71-conflict-callouts/pitch.md` is the shaping
record (reviewed on PR #85 with one revision before the PR, the four points
settled in its bet log; owner decisions D1-D7, D9, D11 and D14 on 5 November
2026; bet and cycle 05 started the same day, PR #86). Its "Findings from the
code" were re-checked against `main` at c909e2b on 6 November 2026 and hold:
`findings.py`'s docstring still says `contradiction` never appears (7-9);
`_check_contradictions` returns `[]` without a backend (332-333); `promote`
lints the staged tree and the patch-set format has no delete action
(`docs/patch-set-format.md` 76); the prose scanner skips `>` lines
(`lint-rules.md` 118-120); `open_fence` and `closes_fence` are at
`prose_lint.py` 76-105; `FINDINGS_FORMAT_VERSION` is 1 (`contract.py` 87);
`tests/test_findings.py` asserts every kind in `FINDING_KINDS` at 56; the MCP
`findings` tool returns `as_dict()` (`tools.py` 281-283); the fingerprint
hashes project overrides only; `git grep '> \[!'` still finds nothing.
memkernel was read at tag `v0.6.0` (the `pages.py` lines the pitch pinned,
20, 45-110 and 113-142, hold at the tag; `sync.py` `_retain_page` 413 with
the content line at 427) and at main fbc28a4 (0.7 work; `curation.py`
`CURATION_KIND_ORDER` 52, `_rank` 218). Four facts found while re-checking
shape the spec:

1. **The link must be on the marker line, and the scan must not read the
   rest of the callout.** The pitch's "first `.md` link" of the whole callout
   misreads a sources line that links a document as the other page (the PR
   #85 review's first point). `_MD_LINK_RE` (`health_lint.py` 57) matches a
   `.md` target with an optional fragment, so applying it to the marker line
   alone is one regex call and the sources lines are never parsed, which is
   also D3 (FR-006, FR-010).
2. **A superseded page should not be scanned, only targeted.** D6 makes a
   superseded target dangling. If the superseded page's own callout were
   also read, the pair would report one dangling and one one-sided finding
   for one stale disagreement. `review_states` already treats a superseded
   page as replaced; the scan reads the same `superseded_by` and skips the
   page (FR-006, FR-007).
3. **`findings`'s scope rule already does what D15 asks.** `findings`
   (192-199) keeps a finding that touches the scope and lists only its
   in-scope pages. The scan reads the whole review set regardless of scope,
   as the graph health checks do, and the three kinds pass through the
   existing filter unchanged (FR-008).
4. **The fixture wiki cannot be promoted.** A callout naming a missing page
   is a fatal structural violation (`lint.py` 253), so the FR-011 fixture is
   read in place by `findings`, never through `propose`/`promote`; the
   promote-path cases (FR-014, FR-019) build their wikis through
   `ApprovalCase` instead. This is the overlap D6 states, made concrete.

Close target: issue #71, by the build PR's merge (`pr.closes: [71]`). No
other issue closes; the pitch PR (#85), the bet PR (#86) and this spec PR
use no closing keyword.

## Architecture decisions

- **ADR-1: A sibling module, imported by `findings.py` only.** The scan is
  `src/wiki_studio/conflicts.py`; `findings.py` calls it and owns the kind
  constants and `FINDING_KINDS`. `health_lint.py`, `lint.py`, `review.py`,
  `promoter.py`, `prompt.py`, `contract.py`, `schema/__init__.py` and the
  adapter are not edited (FR-005, FR-019's diff check). The one shared
  helper the scan needs, link resolution, is reimplemented in three lines
  with the same rule as `_intra_wiki_links_from` rather than exported from
  `health_lint.py`, so that module stays byte-identical.
- **ADR-2: One regex for the marker, one for the link, on one line.** The
  marker regex is built from `CONFLICT_MARKER`; the link is
  `_MD_LINK_RE`'s first match on the marker line. No blockquote parsing, no
  continuation handling, no reading of the sources lines (D3, FR-010).
- **ADR-3: Reasons are words in the description, not a new field.** The
  `Finding` shape is a contract memkernel's `HealthItem` mirrors; the
  dangling reasons are fixed phrases the tests assert (FR-007), so a host
  can grep them without a schema change.
- **ADR-4: The documented example is executed (FR-013).** The retro rule
  that every shown example gets a real check: the example pair in
  `citation-rules.md` is extracted by a fixed grammar and run through
  `findings` and `lint`.
- **ADR-5: The resolution rule is tested through the gate, part by part
  (FR-014).** `propose` and `promote` build and resolve the pair; the test
  asserts the finding clears only when both callouts go, that the deciding
  source is in `sources:`, and the exact log line; `fact_warnings` are
  asserted present and advisory.
- **ADR-6: The memkernel evidence is a pinned copy first, a live import
  second.** The copied `v0.6.0` functions (FR-020) are the core evidence
  and stay pinned to the tag; the governed import case (FR-021) is the
  live evidence and is cut first (D13).
- **ADR-7: No version bump of any contract (D11).** `findings_version` 1
  with new keys in `counts` is the discovery mechanism the contract already
  promises ("names every kind this build reports, zero included"); the
  contract gains the sentence that says so (FR-016).

## Phases (one auto-build phase per `## US<n>:` group of tasks.md)

| Phase | Pitch scope | What | Main files |
|---|---|---|---|
| US1 | S1 | ADR-0004; the `When sources disagree` section with the example pair and the resolution rule; the curator loop and Escalation; the lint-rules bullet | `docs/adr/0004-conflict-callout.md` (new), `src/wiki_studio/schema/citation-rules.md`, `src/wiki_studio/schema/WIKI_MAINTAINER.md`, `src/wiki_studio/schema/lint-rules.md` |
| US2 | S2 | `conflicts.py`; the three kinds in `findings.py`; the fixture wiki; the tests (acceptance, FR-010, scoping, CLI, order, example extraction, resolution rule) | `src/wiki_studio/conflicts.py` (new), `src/wiki_studio/findings.py`, `tests/fixtures/conflicts/` (new), `tests/test_conflict_callouts.py` (new), `tests/test_findings.py` |
| US3 | S3 | Docstring and CLI help; the contract's Findings rows and sentence; README; the adapter test; CHANGELOG | `src/wiki_studio/api.py`, `src/wiki_studio/cli.py`, `src/wiki_studio/findings.py`, `docs/knowledge-contract.md`, `README.md`, `tests/test_mcp_adapter.py`, `CHANGELOG.md` |
| US4 | S4 | The approval tests and the untouched-modules check; the copied `v0.6.0` parser test; the governed import case (cut first) | `tests/test_conflict_callouts.py`, `tests/test_conflict_memkernel_roundtrip.py` (new), `tests/integration/test_memkernel_clean_install.py` |
| US5 | S5 | Version 0.9.0 in the four places; CHANGELOG `[0.9.0]`; the compatibility row if earned; the invariant audit | `pyproject.toml`, `src/wiki_studio/__init__.py`, `README.md`, `docs/quickstart-memkernel.md`, `CHANGELOG.md`, `docs/compatibility.md` |

Order follows the pitch: US1 first because its example is US2's test input
(FR-013); US3 and US4 need US2's kind names; US5 needs the others. The
driver runs one phase at a time. The circuit breaker cuts from the end: if
FR-021 is cut, US4 keeps FR-019 and FR-020 and US5 adds no compatibility
row; if D6's superseded case is cut, FR-007 and FR-011 lose that case and
FR-016's row and the CHANGELOG say so.

## Owner-run steps

None before the release. The owner cuts 0.9.0 by `release.yml`'s header
steps after the build PR merges with the `reviewed` label, and names the
green `memkernel-compat` run in `docs/compatibility.md`'s 0.9.0 row (if
FR-021 landed) in the release commit or a docs PR after it, as the 0.8.1 row
was filled. There is no recorded run, evidence PR or GitHub action in this
cycle.

## Unattended run

The parent session writes `specs/wiki-studio-0-9-0/automation.json` at
approval. This plan assumes 0.8.1's shape: profile `pr`, branch
`feature/wiki-studio-0-9-0` off `main`, five phases with no milestone pause,
the DeepSeek correctness reviewer gating (max 3 rounds per phase), the test
command of `specs/wiki-studio-0-8-1/automation.json` (which checks
`examples/`), `pr.closes: [71]`. `memkernel-compat` runs on the PR, not in
the driver's gate; the FR-021 case is first executed there if the session
cannot install memkernel. The bundle is a draft: the origin-alignment record
is written at approval, before the build.

## Test strategy

- **The fixture lists its findings whole.** One literal for the FR-011
  wiki, compared as a whole, so an extra, missing or re-ordered finding
  fails the test, not only a count.
- **Promote-path cases through the gate.** FR-014 and FR-019 use
  `ApprovalCase` and `api.propose`/`api.promote`, so structural lint runs on
  every page they create and the approval records are real.
- **No backend, proved as today.** `TestNoBackend`'s patches
  (`resolve_backend`, `prepare_backend` raising; `_check_contradictions`
  replaced by the stand-in) stay and run on a fixture with callouts
  (FR-009).
- **The untouched modules are a diff check** (FR-019), run at the US4 and
  US5 checkpoints, not an assertion in the suite.
- **The documented example and the documented log line are inputs**
  (FR-013, FR-014c): the page is parsed, the line is compared exactly.
- **memkernel.** The copied functions are run in every build; the live
  import runs in `memkernel-compat` on the PR and locally when memkernel is
  installed (skipped with the reason otherwise).
- **Regression.** `tests/test_findings.py`, `test_mcp_adapter.py`'s shapes,
  the single-writer scans, the standard-library scan, the CLI contract
  tests and the frozen-run pins stay green; coverage stays at or above 92%.

## Risks

- **A CommonMark edge case reads as a callout, or a real callout is
  missed.** Mitigation: the one form is documented with its limits
  (FR-002); every other shape is a dangling finding or nothing; the
  fixture covers the fence, the fold sign, case and the no-link line; no
  parser is written.
- **The review-set rule surprises a curator.** A callout naming a section
  `index.md` (a page the linter lists) is a content-page target; one naming
  the root `index.md` is dangling. Mitigation: the reason words say which
  (FR-007), and `citation-rules.md` says a callout names a content page.
- **The example pair drifts from the form.** Mitigation: FR-013 extracts and
  runs it; FR-002 fixes the grammar the extraction relies on.
- **`fact_warnings` noise on resolutions.** Mitigation: FR-004 says they are
  expected; FR-014 asserts they are advisory and the promote succeeds.
- **memkernel 0.6.0 differs from `main`.** Mitigation: the copied functions
  are read at the tag (verified 2026-11-06) and pinned; the live case runs
  against the release the job pins.
- **Review depth.** ADR-0004 touches the shared page contract, so the
  reviewer reads it against memkernel's parser; a third round on one scope
  escalates to the owner (the pitch's circuit breaker).

## Success criteria

1. `citation-rules.md` documents one callout form with an executable example pair, the resolution rule and the scan's limits; ADR-0004 exists in ADR-0001's form; the curator loop and `lint-rules.md` point to it.
2. `wiki-studio findings` reports `open-conflict`, `conflict-one-sided` and `conflict-dangling` on the fixture exactly as the literal lists them, with no backend, under `findings_version: 1`, and `counts` names the three kinds; the FR-010 cases hold.
3. The documented resolution patch-set clears the pair; removing one callout leaves one-sided; the log line is exact; `fact_warnings` are advisory.
4. A page in a matched pair approves and `lint --health --strict` passes; the copied `v0.6.0` parser keeps the callout byte for byte; the governed import case holds the callout in the memory (or its cut is named).
5. The contract, README, docstring and CLI help list the kinds; `docs/mcp-adapter.md` is unchanged and the adapter test passes.
6. Version 0.9.0 in the four places; `lint.py`, `promoter.py`, `review.py`, `prompt.py`, `health_lint.py`, `contract.py`, `schema/__init__.py` and the adapter are byte-identical to `main`; exit codes unchanged; gate green at 92%.

## Open items for the spec review

Each is a build detail the pitch leaves open; the default chosen is in the
spec and is what the build does unless the review changes it.

1. **The marker regex.** Default: `^ {0,3}>[ \t]*\[!conflict\][+-]?(?=[ \t]|$)`, case-insensitive (FR-005). Rejected: allowing a nested `> >` or a list-item prefix.
2. **Which link is the other page.** Settled by the PR #85 review: the first `.md` link on the marker line (FR-010a).
3. **Repeats.** Settled by the PR #85 review: a repeated target on one page counts once (FR-010b).
4. **Superseded pages are not scanned.** Default: a page carrying `superseded_by` is skipped by the scan and is a dangling target (finding 2, FR-006). Alternative: scan it too, giving a second finding per stale pair.
5. **What "content page" means for a target.** Default: a page in `default_review_pages` (every page the linter lists except the root `index.md` and `log.md`), so a section `index.md` is a valid target and the root one is not (FR-007).
6. **The dangling reason words.** Default: the six phrases in FR-007, in the description, no new field (ADR-3).
7. **`pages` of a one-sided finding.** Default: `(P, Q)`, the pitch's diagram; under `--paths` the existing filter trims it (FR-008). Alternative: `(P,)` only.
8. **Order of the new findings.** Default: after the existing kinds; `open-conflict`, then `conflict-one-sided`, then `conflict-dangling`, each sorted (FR-007).
9. **Where the example pair is extracted from.** Default: the first two fenced `markdown` blocks of the `## When sources disagree` section, each introduced by a line ending in the backticked page path (FR-002, FR-013).
10. **The log line's `<source>`.** Default: the deciding `sources:` entry as written (`issue: 12`), not a URL (FR-004).
11. **The fixture wiki is read in place.** Default: `tests/fixtures/conflicts/` is never promoted, since its missing-target page fails structural lint (finding 4, FR-011).
12. **`WikiPage` in the copied parser.** Default: a dataclass stand-in with the same fields, named as the one departure, because pydantic is not a dependency (FR-020).
13. **Where the governed import case lives.** Default: `tests/integration/test_memkernel_clean_install.py`, the `memkernel-compat` job's file (FR-021). Alternative: `test_release_b_loop.py` and the `memkernel-loop` job.
14. **The compatibility row.** Default: a 0.9.0 row only if FR-021 landed, pending until the owner names a green `main` run (FR-023).
15. **The CHANGELOG date.** Default: `[0.9.0]` dated when the owner tags (FR-022).
