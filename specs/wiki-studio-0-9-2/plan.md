---
spec_mode: full
feature_id: wiki-studio-0-9-2
risk_category: feature
justification: "Guidance text an agent loads to curate a wiki shared with memkernel, where the open question is who approves (a cross-repository contract memkernel's governed import depends on), an approve step that must yield to the host in a fixed order, one test module whose checks must fail on a wrong flag and not only a wrong verb, two doc sentences that tell hosts how to keep approval with a person, and a release; a full spec pins the persona's required elements and the markers the checks read, the check grammar, the invariants that must not move, the per-phase truth rule and the cut order before an unattended build."
status: draft
date: 2026-11-15
collaboration_mode: single
origin:
  issue: 69
  urls:
    - https://github.com/gosha70/wiki-studio/blob/main/specs/pitches/69-one-set-of-instructions/pitch.md
    - https://github.com/gosha70/wiki-studio/issues/69
    - https://github.com/gosha70/wiki-studio/pull/99
    - https://github.com/gosha70/wiki-studio/pull/100
    - https://github.com/gosha70/memkernel/issues/86
    - https://github.com/gosha70/memkernel/pull/104
    - https://github.com/gosha70/memkernel/pull/109
    - https://github.com/gosha70/memkernel/blob/v0.8.0/templates/claude-memory-instructions.md
    - https://github.com/gosha70/wiki-studio/blob/main/specs/retros/cooldown-after-05.md
  origin_claim: |
    Issue #69 (no comments on 2026-11-14), the persona-side counterpart of
    gosha70/memkernel#86 (closed 2026-11-08 by memkernel 0.8.0, PRs #104 and
    #109), shaped by the bet pitch specs/pitches/69-one-set-of-instructions/
    pitch.md (cycle 06, building; reviewed in PR #99, merged 558e0fd; bet and
    cycle start PR #100, merged 204d568) from specs/retros/cooldown-after-05.md
    (the owner's first pick for cycle 06). Problem, as the pitch states it:
    "An agent in a project that uses memkernel and wiki-studio gets wiki
    guidance from two places: wiki-studio's curator persona ... and memkernel's
    agent templates. Issue #69 asks that each job is described once. Then
    neither set quietly overrides the other." memkernel's half is done: its
    templates "send the agent to the persona: 'page types, citations, writing
    and linking a page, linting, and the propose, promote and approve loop.
    Follow it for those steps; this file does not restate them.'" "The persona
    does not hold what memkernel now sends agents to find": no propose,
    promote or approve; a lint command that is not shipped; no boundary with
    memory. The issue's words the pitch carries: memory steps belong to
    memkernel, and the persona "links there instead of restating them"; a
    mention of export and import is allowed "if it uses the same steps"; at
    closure "each names the other's resolving PR". Solution shape: "A text
    change to one packaged document, one test module, and two doc lines. No
    new verb, flag, exit code, MCP tool, frontmatter key or dependency." Owner
    decisions D1-D10 (2026-11-14) and the settled D11-D14 carried into the
    FRs; D3 as revised after the PR #99 review: the agent approves its own
    page with `wiki-studio approve <page> --by <its own name>` unless the
    project's instructions reserve approval for a person or the host runs it
    propose-only (`--disable-tool promote`), then it stops and reports; one
    agent name with --by on propose, promote and approve; the CLI-first order
    for an MCP agent only where approval is not reserved; the plain sentence
    that an agent can take its own memory to an imported page with no person
    involved, where approval is not reserved; no self-approval code in cycle
    06. One 2w bet released as 0.9.2 (D8); the build PR closes #69 (D9). The
    PR #99 reviewer's three notes (a copyable reservation line for hosts; the
    v0.8.0 link is instructions, not a compatibility claim; parse each shown
    command with the CLI's own parser) carried into FR-004, FR-008, FR-020,
    FR-021 and FR-014.
---

# Plan: wiki-studio 0.9.2 — one set of instructions

The bet pitch `specs/pitches/69-one-set-of-instructions/pitch.md` is the
shaping record (reviewed on PR #99 with one revision after review, D3's
yield to the host; owner decisions D1-D10 on 14 November 2026; bet and
cycle 06 started the same day, PR #100). Its "Findings from the code" were
re-checked against `main` at 204d568 on 15 November 2026. They hold:
the persona's loop is 30-72 with step 9 naming `lint-wiki.sh` at 68 and
"Bypass the linter" at 83; no code reads the persona and only
`tests/test_schema.py` (presence, 25-27) and the frozen pin of the eval copy
(`tests/test_frozen_runs.py` 218) mention it; `load_schema` reads only the
three prompt documents from a project copy (`contract.py` 375-398);
`api.approve` takes `by` as attribution and refuses a draft, a superseded
page, a structural violation, a changed revision and a missing approver,
and nothing refuses self-approval (779-811); the MCP adapter exposes no
`approve` (`docs/mcp-adapter.md` 155); `docs/mcp-adapter.md` 178-180 still
says "Use `--disable-tool promote`, or a wiki without the policy, when a
person must approve"; memkernel's tag `v0.8.0` is tag object `fe1e11a` in
the local checkout. Issue #69's body was not re-fetched while this bundle
was written (no shell in the writing session); its words are taken from the
pitch, and the origin-alignment record at approval reads the issue itself.
Seven facts found while re-checking shape the spec:

1. **The pitch states memkernel's `promote` twice, in two ways.** S2 writes
   "memkernel's `promote(ref_id=…)` moves a memory between tiers"; S3
   forbids `promote(ref_id` in the persona. The spec keeps one rule: the
   persona names memkernel's `promote` tool without call syntax (FR-011),
   and FR-012 owns the forbidden tokens, which FR-017 checks.
2. **"First mention in the section" would fail on the section's own first
   sentence.** S2's opening names `wiki_export` and `wiki_import` before
   any `wiki-studio approve`, so the order check of S3 as written reads
   import before approve. The spec scopes the check to the first paragraph
   of "Memory tools" that names all three markers, and has the opening
   paragraph name no `wiki-studio approve` (FR-008, FR-009, FR-018).
3. **"Promote" has a third use at line 77.** "Promote session ephemera"
   uses the word for adding a lesson; finding 8 lists 32 and 85 only. D14
   covers it, so FR-006 rewords all three.
4. **argparse accepts abbreviations.** `_build_arg_parser()` uses the
   default `allow_abbrev=True`, so a parse alone accepts `--b` for `--by`.
   Reviewer note 3 asks that a wrong flag fails; FR-014 adds the
   full-spelling rule and self-tests that prove the checker fails on a
   wrong verb, a wrong flag, an abbreviated flag, a missing required flag
   and an unknown tool. `mcp_adapter/config.py`'s `build_parser` loads
   without the `mcp` extra, so the one MCP option the persona names
   (`--disable-tool promote`) gets the same check against the server's own
   parser and `TOOL_NAMES`.
5. **README's "Schema" sentence is wrong in two ways.** It says a project
   schema directory replaces all six documents, and that the directory as a
   whole replaces them; `load_schema` reads each of the three prompt
   documents individually, when that file exists (FR-020).
6. **The pitch's S4 compatibility row cannot be filled by the build.** The
   row names the green `main` run, which exists only after the build PR
   merges. 0.9.0's build added a Pending row and drew a review note; 0.9.1's
   row came in the evidence PR #98 after the version PR #97 merged. The
   spec moves the row to the release PR (FR-024).
7. **memkernel has moved on, and the pin does not.** memkernel 0.9.0
   (2026-11-08) is out and its `main` carries unreleased template
   additions; the one-line workflow reads identically there (at line 58).
   The persona links `v0.8.0` (D6) and the test pins the line at `v0.8.0`
   (D5); the tag's line number (46) is the pitch's and the build verifies
   it (FR-018). memkernel 0.9.0 also moves to `mcp>=2.3,<3`, which changes
   the "extra cannot share an environment" note on `docs/compatibility.md`
   for that memkernel release only; that is outside this bet (D13 keeps CI
   on 0.6.0) and is not touched.

Close target: issue #69, by the build PR's merge (`pr.closes: [69]`). No
other issue closes; the pitch PR (#99), the bet PR (#100) and this spec PR
use no closing keyword.

## Architecture decisions

- **ADR-1: The rule lives once, in the persona's approve step.** FR-003 is
  the only statement of who approves and when approval is reserved. The
  memory section (FR-009, FR-010), the docs (FR-021) and the checks
  (FR-016) refer to it. The example line R is defined once (FR-004) and
  copied verbatim, with each copy checked in the phase that writes it.
- **ADR-2: Checks read markers and positions, not sentences.** The approve
  step is found by its bold label, the self-approval command by parse, and
  the reservation by two literals and R; the CLI-first order by the MCP
  sub-bullet's label and `without a shell`. Wording rounds do not break the
  test; dropping or reordering a required element does (the pitch's rabbit
  hole on prose order).
- **ADR-3: The CLI's own parser is the oracle.** Each shown command is
  parsed by `wiki_studio.cli._build_arg_parser()` in process, after a fixed
  placeholder substitution, plus a full-spelling rule for flags. The test
  imports two private names (`_build_arg_parser`, argparse's
  `_SubParsersAction`), as `tests/test_info_contract.py` already imports
  `_VERBS`; changing `cli.py` to expose a public builder would be a code
  change the no-gos exclude.
- **ADR-4: The memkernel evidence is a pinned copy, cut first.** One
  copied line at `v0.8.0` with a header naming file, line and tag, like the
  copied parser of 0.9.0. No network, no memkernel import, no CI job
  change (D5).
- **ADR-5: Each phase is true on its own diff.** The driver reviews each
  phase alone (0.9.0's phase 1 was blocked three rounds for a document that
  described later phases' code). So the persona changes in US1 and US2
  without forward references, the checks land in US3 against what exists,
  and every cross-phase claim (README, `docs/mcp-adapter.md`, CHANGELOG,
  version) lands in US4, which makes them true.
- **ADR-6: No compatibility row in the build.** FR-024; the release PR adds
  it with the run it names.

## Phases (one auto-build phase per `## US<n>:` group of tasks.md)

| Phase | Pitch scope | What | Main files |
|---|---|---|---|
| US1 | S1 | The loop's steps 6-13 on the governed path; one agent name; the approve step with the reservation, R, auto-approval, the self-approval command, refusals and the MCP order; the lint bullet; "promote" wording | `src/wiki_studio/schema/WIKI_MAINTAINER.md` |
| US2 | S2 | "Memory tools": the link and the not-a-compatibility-claim sentence, the export and import paragraph, the consequence sentence, memkernel's `promote` | `src/wiki_studio/schema/WIKI_MAINTAINER.md` |
| US3 | S3 | The persona test module: command parse with self-tests, `--by`, reservation and CLI-first positions, R in the persona, no restatement, the section's links, the copied memkernel line (cut first) | `tests/test_maintainer_persona.py` (new) |
| US4 | S4 | README "Schema" and MCP sentence, `docs/mcp-adapter.md` 178-180, R in both docs with its assertion, CHANGELOG `[0.9.2]`, version 0.9.2 in six places, the invariant and cut audit | `README.md`, `docs/mcp-adapter.md`, `tests/test_maintainer_persona.py`, `CHANGELOG.md`, `pyproject.toml`, `src/wiki_studio/__init__.py`, `docs/quickstart-memkernel.md`, `tests/integration/test_quickstart_memkernel.py`, `tests/test_cli_contract.py` |

Order follows the pitch: S1 and S2 touch one file and go first; S3 checks
what they wrote; S4 needs the other three. The circuit breaker cuts from the
end: if FR-018 is cut, US3 keeps FR-013 to FR-017 and FR-019, and the
CHANGELOG names the cut; if FR-009 shrinks to the link (week 1), FR-018 goes
with it and FR-008, FR-010 and FR-011 stay.

## Owner-run steps

1. Before the driver: review and approve this bundle; write
   `automation.json` and the origin-alignment record in the approval
   commit.
2. After the driver opens the build PR: check it is open on the branch tip
   (`gh pr list --head feature/wiki-studio-0-9-2`), that its body carries
   `Closes #69` and names memkernel #104 and #109 (add the two names by
   hand if the driver's body lacks them), then review and label it.
3. After the merge: the release PR, as #98 did for 0.9.1, in two commits:
   the CHANGELOG `[0.9.2]` heading dated with the tag's UTC date, and the
   `docs/compatibility.md` 0.9.2 row naming the green `main` run on the
   build merge commit (FR-024). Then tag and release by `release.yml`'s
   header steps.
4. Comment on memkernel #86 with the build PR's number (D9).
5. Hill chart scopes by hand (the driver does not update it,
   code-copilot-team #405). The optional D7 follow-up issue is the owner's
   call and is not filed by the build.

## Unattended run

The parent session writes `specs/wiki-studio-0-9-2/automation.json` at
approval. This plan assumes 0.9.0's shape: profile `pr`, branch
`feature/wiki-studio-0-9-2` off `main`, four phases with no milestone pause,
the DeepSeek correctness reviewer gating (max 3 rounds per phase), the test
command of `specs/wiki-studio-0-9-0/automation.json` (which checks
`conformance/` and `examples/`), `pr.closes: [69]`, title
`feat: wiki-studio 0.9.2 — one set of instructions: the curator persona's
propose, promote and approve loop and the memory boundary`. The bundle is a
draft; the origin-alignment record is written at approval, before the
build. After the run, re-run the gate on the branch head before trusting
`landed`, and check no phase was bypassed without a per-phase record (the
known driver defects in code-copilot-team #403 and #404).

## Test strategy

- **The packaged bytes.** The module reads the persona through
  `importlib.resources`, the path memkernel's template prints.
- **The CLI's parser decides.** Every shown command parses in process; the
  full-spelling rule closes argparse's abbreviation gap; self-tests prove
  the checker fails on each wrong shape (FR-014e).
- **Markers, not sentences.** Positions of the reservation literals, R and
  the self-approval command; the CLI-first order inside the MCP sub-bullet;
  the export, approve, import order in one paragraph (FR-016, FR-018).
- **Forbidden tokens and scoped words** for the memory boundary (FR-017).
- **Copies of R** checked in the phase that writes each: the persona in
  US3, README and `docs/mcp-adapter.md` in US4 (FR-016, FR-021).
- **Regression.** `test_schema.py`, `test_frozen_runs.py` and
  `test_package_boundaries.py` unedited and green (FR-019); the CLI
  contract and quickstart tests green with the version moved; coverage
  (measured on `src/`, where only markdown and a version string change)
  stays at or above 92 percent.
- **No network, no memkernel.** The memkernel line is a constant; the
  `memkernel-compat`, `memkernel-loop`, `quickstart-memkernel`,
  `demo-correction-loop` and `quickstart` jobs run on the PR unchanged.

## Risks

- **Wording rounds on guidance text.** Mitigation: the spec pins the
  required elements and markers (FR-001 to FR-012) and leaves wording free;
  a third round on one scope escalates to the owner (the pitch's circuit
  breaker).
- **A phase reviewed alone reads as incomplete.** US1 changes the persona
  with no test in its diff. Mitigation: the tasks header and the US1
  checkpoint say the checks are US3's (pitch S3), and the checkpoint
  parses each shown command by hand; no file in US1 or US2 claims later
  work.
- **The markers are too strict for a natural sentence.** Mitigation: three
  literals (`project's instructions`, `` `--disable-tool promote` ``,
  `without a shell`), R and two bold labels; anything else is free.
- **Private argparse names.** `_SubParsersAction` and
  `_option_string_actions` are standard-library internals stable since
  Python 3.2; the alternative, a public builder in `cli.py`, is excluded by
  the no-gos.
- **memkernel's template moves.** The pin is `v0.8.0` by D5 and D6; a
  re-pin is a deliberate later change. The line already reads the same on
  memkernel `main`.
- **The name is attribution, not authentication.** An agent can still pass
  a wrong name; the persona says so (FR-002), and the code stays as it is
  (D3).
- **A reserving host on an auto-approving wiki.** The project's
  instructions do not stop the policy from approving on promote; the docs
  say only propose-only keeps approval with a person there (FR-021,
  default to confirm; open question 1 in the hand-off).

## Success criteria

1. The persona's loop runs propose, promote, lint and approve with real `wiki-studio` commands, `--by <agent-name>` on each writing verb, and an approve step that names the reservation (project's instructions with R, and propose-only) before the self-approval command and the CLI before the no-shell fallback; no `lint-wiki` remains; "promote" means `wiki-studio promote` only.
2. "Memory tools" links memkernel's template at `v0.8.0`, says the link is not a compatibility claim, states export, approve, import in memkernel's order with the consequence sentence, and restates no memory step.
3. `tests/test_maintainer_persona.py` passes and its self-tests show it fails on a wrong verb, flag, abbreviation, missing required flag and unknown tool.
4. README and `docs/mcp-adapter.md` say how a host reserves approval, with R verbatim, and no longer offer a wiki without the policy for that; README "Schema" matches `load_schema`.
5. Version 0.9.2 in the six places; `src/` changes only the persona and the version line; `docs/compatibility.md` and `eval/` untouched; gate green at 92 percent.

## Open items for the spec review

Each is a build detail the pitch leaves open; the default chosen is in the
spec and is what the build does unless the review changes it.

1. **The placeholder form.** Default: `<agent-name>`, `<dir>`, `<path>`, `<proposal-dir>`, `<page>`; the check replaces any `<…>` with one token (FR-001, FR-014). The pitch's `<its own name>` also parses, but reads worse in a command.
2. **Self-promotion when the instructions are silent.** Default: the agent promotes unless the project's instructions or propose-only mode leave promotion to a person (FR-001 step 10); it follows from D3's self-approval default, since approval needs a live page.
3. **R's wording.** Default: the PR #99 reviewer's example, verbatim (FR-004).
4. **Where the memkernel version appears.** Default: the persona names none besides the tag in the URL and links `docs/compatibility.md`; README names memkernel 0.6.0 (FR-008, FR-020), so the packaged file never carries a pin that can go stale.
5. **The full-spelling rule and the MCP launch check.** Default: both in (FR-014b, c), from reviewer note 3.
6. **The order paragraph.** Default: the first paragraph of "Memory tools" naming all three markers (fact 2, FR-018).
7. **The compatibility row.** Default: none in the build; the release PR adds it (fact 6, FR-024).
8. **The CHANGELOG heading.** Default: `## [0.9.2]` undated in the build, dated in the release PR (FR-022), as 0.9.0 and 0.9.1 did.
9. **A reserving host on an auto-approving wiki.** Default, to confirm with the owner: docs say only propose-only keeps approval with a person on such a wiki; the persona keeps D3's "stops after propose or promote" (FR-021).
