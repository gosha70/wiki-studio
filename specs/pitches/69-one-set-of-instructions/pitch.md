---
pitch_id: 69-one-set-of-instructions
title: "One set of instructions: the curator persona describes the propose, promote and approve loop that memkernel's templates now send agents to, and leaves memory tools to memkernel"
appetite: 2w
bet_status: shaped
cycle: ""
circuit_breaker: "Core is S1, S2 and the persona-only checks of S3: the curator loop on the propose, promote and approve path with real wiki-studio commands, the short memory-boundary section that links memkernel's template, and the tests that every wiki-studio command the persona shows is a real verb and that the persona restates no memkernel memory step. They ship alone if the cycle runs out. End of week 1: if S1 is not downhill, S2 shrinks to the link with no steps (D4's alternative, as a cut; S1's approve step with --by and its CLI-first order stays, and so does S2's sentence that an agent can take its own memory to an imported page with no person involved), and the copied memkernel line in S3 is cut in favour of the persona-only checks, stated in the CHANGELOG. End of week 2: S4 ships what is true; if the release cannot be cut, the change waits under [Unreleased] for the next release and #69 stays open until a release carries it. Never, to save time: change behaviour under src/wiki_studio/ other than the persona, a CLI verb, an exit code or an MCP tool; change the page schema (frontmatter keys, page types, directories); add a runtime dependency or a network fetch to a test; edit memkernel, code-copilot-team or the frozen eval copy of the persona; restate memkernel's retain, recall or consolidate steps in the persona; drop --by from the approve step, or add code that refuses, flags or reports self-approval in cycle 06 (D3); weaken or skip a test."
shaped_by: "pitch-shaper (Claude Code) for gosha70"
shaped_date: 2026-11-14
---

<!-- Shape-Up pitch. Origin: https://github.com/gosha70/wiki-studio/issues/69 (no comments on 2026-11-14), counterpart of gosha70/memkernel#86. -->
<!-- specs/retros/cooldown-after-05.md: the owner picked #69 to shape first for cycle 06 (then #70, then #54). This pitch shapes the issue; it does not replace it. -->

# Pitch: One set of instructions

## Problem

An agent in a project that uses memkernel and wiki-studio gets wiki
guidance from two places: wiki-studio's curator persona,
`src/wiki_studio/schema/WIKI_MAINTAINER.md`, and memkernel's agent
templates. Issue #69 asks that each job is described once. Then neither
set quietly overrides the other.

memkernel has done its half. memkernel 0.8.0 (#104, #109) made its
templates cover memory only. For curation they send the agent to the
persona: "page types, citations, writing and linking a page, linting,
and the propose, promote and approve loop. Follow it for those steps;
this file does not restate them."

The persona does not hold what memkernel now sends agents to find:

1. **No propose, promote or approve.** The curator loop (lines 30-72)
   has the agent write the page, edit `index.md`, append to `log.md`
   and run the linter by hand. It never names `wiki-studio propose`,
   `promote` or `approve`, the path that memkernel's governed import
   depends on.
2. **A lint command that is not shipped.** Step 9 (line 68) and the
   "Bypass the linter" rule (line 83) name
   `bash knowledge/wiki/scripts/lint-wiki.sh`. That is
   code-copilot-team's own bash linter. The wheel does not ship it
   (`tests/test_package_boundaries.py` line 55 asserts that). A
   memkernel user who follows the persona runs a command that does not
   exist.
3. **No boundary with memory.** The persona never names memkernel,
   `retain`, `recall`, `wiki_export` or `wiki_import`. An agent reading
   both files does not learn which file owns which step, or that
   memkernel's `promote(ref_id=…)` is not `wiki-studio promote`.

So the single home that memkernel points to is incomplete. Today an
agent either improvises the loop or falls back on older guidance.

## Findings from the code

wiki-studio was read at main `829e688` (0.9.1) on 2026-11-14. memkernel
was read, read-only, at tag `v0.8.0` (tag object `fe1e11a`, commit
`700d31f`, 2026-11-07). code-copilot-team was read, read-only, at
`00d49c0`. These facts drive the decisions and the rabbit holes.

1. **What memkernel 0.8.0 says.** `templates/claude-memory-instructions.md`
   line 46 and `templates/kiro/steering/memory.md` line 38 carry one
   identical line:
   `wiki_export()  → review the draft pages → (with wiki-studio) wiki-studio approve <page> → wiki_import()`.
   The `### Wiki` section (lines 166-182) says governed import takes
   only approved pages. It sends curation to the persona and prints the
   persona's packaged path with
   `python -c "import importlib.resources as r; print(r.files('wiki_studio') / 'schema' / 'WIKI_MAINTAINER.md')"`
   (run here: it resolves to the packaged file). The steering file
   (lines 40-42) says the same in short form.
2. **memkernel's test keeps curation out of its templates.**
   `tests/unit/test_template_wiki_workflow.py` asserts that every
   paragraph that mentions `wiki_import` names `wiki-studio approve`,
   that the one-line workflow is the same in both templates, and that
   neither template contains `ingest-rules`, `page-types.md`,
   `citation-rules`, `lint-rules`, `lint-wiki` or `wiki-studio propose`.
   memkernel has fixed its vocabulary. The persona is now the only
   place those steps can live.
3. **memkernel's templates are not in its wheel.** Its `pyproject.toml`
   packages `src/memkernel` only. The memkernel release that wiki-studio's
   CI installs (`MK_VERSION: "0.6.0"` in `ci.yml`) therefore cannot
   supply the template text to a test. A live comparison would need a
   network fetch or a memkernel checkout.
4. **No code reads the persona.** The prompts load three schema
   documents (`PROMPT_SCHEMA_DOCUMENTS`, `schema/__init__.py` line 112:
   `ingest-rules`, `page-types`, `citation-rules`). The fingerprint
   hashes project copies of those three only, never packaged files
   (`docs/knowledge-contract.md`, "The schema documents and the
   fingerprint"). The persona ships as package data
   (`pyproject.toml` line 29, wheel and sdist). `tests/test_schema.py`
   line 26 checks only that it is present. Editing it moves no
   fingerprint, no prompt excerpt and no `info` output. It reaches
   users only through a release.
5. **The page schema is not touched.** The work changes guidance text,
   not frontmatter keys, page types or directories. ADR-0001 to
   ADR-0004 stay as they are, and no new ADR is needed.
6. **The governed path the loop must describe.** `propose --from <dir>`
   takes pages laid out like the wiki, plus `<dir>/index.md` and
   `<dir>/log.md` lines to append. An update carries `.base.json` with
   the hash from `wiki-studio read <path> --json`. `promote` lints the
   staged tree and is the only writer into the wiki. `approve` refuses
   a draft, a superseded page or a page with a structural violation, so
   a page needs `status: stable` (README, "approve"). A governed
   `wiki_export()` creates `status: draft` pages through wiki-studio's
   propose and promote (memkernel `sync.py` `_export_gated`). So an
   exported page goes through the same loop as an update before it can
   be approved.
7. **Who may approve.** `api.approve` (`src/wiki_studio/api.py` lines
   786-807) takes `by`, the approver: the `--by` flag, else
   `WIKI_STUDIO_ACTOR`, else none. It is attribution, not
   authentication. Approval is refused for `status: draft`,
   `superseded_by`, a structural-lint violation for the page, a live
   revision that differs from the one reviewed (`--revision`), and a
   policy that requires an approver when none is named. Nothing refuses
   self-approval, so an agent may approve a page it proposed. The MCP
   server does not expose `approve` (`docs/mcp-adapter.md` line 155).
   In propose-only mode, proposals wait for a person to `promote` and
   `approve` (line 165). `auto_approve_on_promote` in the manifest
   policy approves on promote (`docs/knowledge-contract.md` line 36).
8. **"Promote" has three meanings.** In memkernel, `promote(ref_id=…)`
   moves a memory between tiers. In wiki-studio, `promote` applies a
   patch-set. In the persona, "promotion" means moving a lesson into
   the wiki (line 32, "For every promotion or update"; line 85, "Mix
   promotion and curation"). A combined reader can confuse the three.
9. **The README overstates project schema copies.** README "Schema"
   (lines 452-459) lists all six documents and says a project copy
   under `<wiki-dir>/schema/` "is used instead of the packaged one".
   Only the three prompt documents are read from a project copy
   (finding 4). memkernel's template says correctly that wiki-studio
   reads no project copy of the persona. The two pages contradict each
   other on where the persona lives.
10. **There are other copies of the persona. None of them is read.**
    `eval/navigation/wiki/schema/WIKI_MAINTAINER.md` is part of a frozen
    run, hash-pinned in `tests/test_frozen_runs.py` line 218, and is
    never edited. code-copilot-team keeps its own older copy at
    `knowledge/wiki/schema/WIKI_MAINTAINER.md`, without the 0.5.0
    writing-rules link or the 0.9.0 conflict rules, beside its bash
    `lint-wiki.sh`. Its agents follow that copy, not the packaged one.
11. **Other code-copilot-team details remain outside the loop.** "Edit a
    generated artifact" (lines 80-82) names `scripts/generate.sh` and
    `shared/skills/`. "Distribution-claim discipline" (lines 90-126)
    names the same generator, with "or the equivalent". Neither is part
    of the wiki workflow that #69 is about.
12. **The issue's acceptance, as it stands.** memkernel #86 closed on
    2026-11-08. Its closing comment names this issue as the persona-side
    counterpart, but it names no wiki-studio PR, because none exists
    yet. The acceptance line "each names the other's resolving PR"
    therefore needs one action after this build merges (D9).

## Appetite

**2w** (D1, decided by the owner), one bet for cycle 06. 2w is the smallest appetite the format
allows. The work is a small batch: no code under `src/` except package
data, one test module, and a few doc lines. For an LLM executor the work
content is about 4-6 hours:

| Scope | Estimate |
|-------|----------|
| S1 The curator loop on the governed path | 1.5-2h |
| S2 The memory boundary | 0.5-1h |
| S3 The checks | 1-1.5h |
| S4 README, CHANGELOG, release and closure | 1-1.5h |

The wall-clock budget goes to review, not to code:

- **Review rounds.** The external reviewer reviews the pitch PR, the
  spec and the build. A merge needs the `reviewed` label on the
  reviewed head (`.github/workflows/review-gate.yml`). A new commit
  removes it. Guidance text tends to draw wording rounds.
- **The release.** The owner cuts it by the steps in the header of
  `.github/workflows/release.yml`.

The build should land in week 1. Week 2 is for review rounds and the
release, not for new scope. Why not a larger appetite: nothing here
changes code, a contract or memkernel.

## Solution shape

A text change to one packaged document, one test module, and two doc
lines. No new verb, flag, exit code, MCP tool, frontmatter key or
dependency. No change to the prompts, the fingerprint, the linter or
`approve`.

```
memkernel templates (0.8.0, done)          WIKI_MAINTAINER.md (this pitch)
  memory: retain, recall, consolidate,       curation: gate, classify, slug, cite,
          promote(ref_id), checkpoints  ───►           draft, propose, promote, lint,
  wiki:   wiki_export → review →          link           approve --by <agent's own name>
          wiki-studio approve → wiki_import  ◄─── "Memory tools": owned by memkernel,
  "curation: follow WIKI_MAINTAINER.md"              link to its template; export makes
                                                     drafts, approve, import takes approved
```

**The loop (S1).** Steps 1-5 (Listen, Gate, Classify, Slug, Cite,
including the 0.9.0 conflict rule) stay. Steps 6-9 (Write, Link, Log,
Lint) become the governed path. The agent drafts the page in a directory
laid out like the wiki. It puts the index and log lines in that
directory's `index.md` and `log.md`. For an update, it records the base
hash from `wiki-studio read --json` in `.base.json`. Then it runs
`wiki-studio propose --from <dir>`. Promotion is either `--promote` or a
reviewed `wiki-studio promote <proposal-dir>`, and the host decides
which. The agent runs `wiki-studio lint`. Then the agent approves its
own page with `wiki-studio approve <page> --by <its own name>` (D3).
The persona calls the curating agent the curator. Every command shown
is a real wiki-studio verb.

**The boundary (S2).** A short section, "Memory tools", says memkernel
owns `retain`, `recall`, `wiki_export` and `wiki_import`, and links to
memkernel's template. It states the order memkernel's line 46 uses:
export creates draft pages, the curator turns a draft into a stable
page through the loop and approves it, and the governed import takes
approved pages only (D4). It says that memkernel's
`promote(ref_id=…)` is not `wiki-studio promote`.

**The checks (S3).** One test reads the packaged persona. It checks
three things: the commands are real verbs, no memory step is restated,
and the export, approve and import order matches memkernel's line,
copied and pinned to `v0.8.0` (D5).

## Scopes

Build order: S1 and S2 together (one file). S3 is written beside them.
S4 needs the other three.

### S1: The curator loop on the governed path, ~1.5-2h

- **Steps 6-9 of "The canonical curator loop"** are rewritten as the
  governed path of finding 6. *Write* drafts the page in a directory
  laid out like the wiki, with the `page-types.md` template and the
  writing rules (keep both links). *Link* and *Log* become lines in
  `<dir>/index.md` and `<dir>/log.md`. The log line keeps its fixed
  form (`- YYYY-MM-DD — <verb> <slug> (<page-type>): <one-line why>`).
  *Propose* runs `wiki-studio propose --from <dir>`, with `.base.json`
  for an update. *Promote* is `--promote` or `wiki-studio promote`, as
  the host allows. In MCP propose-only mode it is a person's step
  (finding 7). *Lint* runs `wiki-studio lint`. *Stop* is unchanged.
  The numbering may grow. Steps 1-5 and the conflict sub-rule do not
  change.
- **Approve (D3).** After promote and lint, the agent approves its own
  page: `wiki-studio approve <page> --by <its own name>`, or with
  `WIKI_STUDIO_ACTOR` set to that name. It names itself honestly, so
  the approval record shows that an agent approved the page. The step
  says what `approve` refuses (a draft, a superseded page, a page with
  a structural violation, a changed revision, a missing approver when
  the policy requires one). Where the policy sets
  `auto_approve_on_promote`, promote already approved the page and the
  step is skipped. The MCP adapter has no approve tool, so an agent
  that reaches wiki-studio through MCP follows a fixed order. If it
  has a shell, it runs the CLI,
  `wiki-studio approve <page> --by <its own name>`. Only without a
  shell does it stop and report the promoted pages awaiting approval.
  A person may still re-review a page through
  `review_state` or `findings`. The persona defines the curating agent
  as the curator, the word memkernel's template uses (line 172).
- **"Bypass the linter"** (line 83) names `wiki-studio lint` instead of
  `lint-wiki.sh`.
- **Wording for "promote" (finding 8).** "For every promotion or
  update" and "Mix promotion and curation" are reworded so that
  "promote" in the persona means `wiki-studio promote` only. One
  sentence explains how memkernel's `promote` differs (in S2).
- **What stays (D7).** "Edit a generated artifact", "Distribution-claim
  discipline" and "Escalation" do not change, apart from the lint
  command. The `../index.md` and `../log.md` links keep their current
  form.

### S2: The memory boundary, ~0.5-1h

- **A section "Memory tools"**, placed after "Required reading". It
  says that memkernel's `retain`, `recall`, `wiki_export` and
  `wiki_import` are described in memkernel's agent template, not here.
  It links that template at the tag D6 settles.
- **Export and import (D4).** One short paragraph, with no call
  signatures, in the order of memkernel's line 46. `wiki_export()`
  creates draft pages. The curator turns a draft into a stable page
  through the loop above, as an update with its base hash, and approves
  it. The governed `wiki_import()` takes approved pages only. It adds
  nothing memkernel's line contradicts. It adds one fact memkernel's
  line leaves out: `approve` refuses a draft (finding 6).
- **The consequence, in one sentence (D3).** The section says plainly
  that an agent can take its own retained memory all the way to an
  imported page with no person involved: export, make the draft
  stable, approve, import. The sentence uses tool names only, no call
  syntax.
- **`promote`.** One sentence: memkernel's `promote(ref_id=…)` moves a
  memory between tiers and does not touch the wiki.
- **What the section never holds:** `retain(`, `recall(`,
  `consolidate(` or checkpoint steps. Those are memkernel's (the issue,
  "links there instead of restating them").

### S3: The checks, ~1-1.5h

One test module, for example `tests/test_maintainer_persona.py`. It
reads the packaged persona through `importlib.resources`, as memkernel's
template tells users to, so the test reads the bytes that users get.

- **Commands are real (core).** Every `wiki-studio <verb>` in the
  persona names a verb that `wiki_studio.cli` accepts (checked against
  the parser, in process). The persona contains no `lint-wiki`. This is
  the repository rule that a shown command gets the cheapest real check.
  The loop's `wiki-studio approve` line carries `--by`, so the curator
  is told to name itself (D3). The persona names the CLI before the
  stop-and-report fallback for an agent without the approve tool.
- **No memory restatement (core).** The persona contains none of
  `retain(`, `recall(`, `consolidate(`, `checkpoint=` or
  `promote(ref_id`. It names `retain`, `recall`, `wiki_export` and
  `wiki_import` only inside the "Memory tools" section, and that section
  links memkernel's template. The check forbids call syntax, not tool
  names, so the S2 sentence on an agent taking its own memory to an
  imported page passes it.
- **Same order as memkernel (cut first, D5).** A constant holds
  memkernel's one-line workflow, copied from
  `templates/claude-memory-instructions.md` line 46 at tag `v0.8.0`
  (commit `700d31f`). The test's header names the file, the line and
  the tag. The test asserts that the "Memory tools" section mentions
  `wiki_export`, `wiki-studio approve` and `wiki_import` in the same
  relative order as the copied line, at their first mention in the
  section. The S2 consequence sentence names the steps in that same
  order, so it cannot fail the check. The test reads that section
  only, because the loop's own approve step appears elsewhere in the
  file.
  The copy changes only by a deliberate re-pin to a
  newer memkernel tag. The test makes no network call and does not
  depend on memkernel.
- **Unchanged checks.** `tests/test_schema.py` (the six documents
  present) and `tests/test_frozen_runs.py` (the frozen copy's hash)
  pass untouched.

### S4: README, CHANGELOG, release and closure, ~1-1.5h

- **README "Schema" (D10).** One sentence corrected: a project copy
  under `<wiki-dir>/schema/` is read for the three prompt documents
  only. The persona is read by agents from the package (finding 9). One
  sentence says the persona owns curation and memkernel's template owns
  memory, with both links.
- **CHANGELOG `[Unreleased]`, Changed:** the persona's curator loop
  follows propose, promote and approve with `wiki-studio` commands, its
  lint step uses `wiki-studio lint`, and it has a "Memory tools" section
  that links memkernel's template (#69, counterpart of memkernel #86).
- **Release (D8).** The version moves in `pyproject.toml` and
  `src/wiki_studio/__init__.py` together, with the
  `==X.Y.Z` pins in `docs/quickstart-memkernel.md`. The CHANGELOG
  heading gets the tag date. The steps are in the header of
  `release.yml`. `docs/compatibility.md` gets no row, because the
  memkernel pin and the integration jobs do not change.
- **Closure (D9).** The build PR closes #69 and names memkernel #104
  and #109 as the counterpart's resolving PRs. After the merge, the
  owner comments on memkernel #86 with the build PR's number. The pitch
  PR body uses no closing keyword.

## Rabbit holes

- **Rewriting the whole persona.** The code-copilot-team details
  (finding 11) are tempting to generalise while the file is open.
  *Workaround:* D7. Only the loop, the lint command and the "promote"
  wording change. The rest goes to a follow-up issue if the owner wants
  one.
- **A live cross-repo test.** Fetching memkernel's template from GitHub
  in CI, or adding a memkernel checkout to a job, brings network,
  flakiness and a second source of truth for a one-line pin.
  *Workaround:* D5. A copied line pinned to a tag, like the copied
  memkernel parser in `tests/test_avoid_roundtrip.py` and
  `tests/test_conflict_memkernel_roundtrip.py`. memkernel's own test
  (finding 2) keeps its side.
- **Syncing every copy.** The frozen eval copy and code-copilot-team's
  copy (finding 10) diverge from the packaged persona. *Workaround:*
  neither is edited. The frozen copy is evidence. code-copilot-team's
  copy belongs to that repository (D7 names the follow-up).
- **Turning the persona into a manual.** The loop could restate every
  `propose` and `promote` flag, the receipt protocol and the approval
  policy. *Workaround:* the persona names the verb and the one flag
  each step needs. It links the README and `docs/quickstart.md` by
  absolute GitHub URL for the details, as the README links
  `citation-rules.md`. Relative links would not resolve from the
  installed package.
- **Approval under the wrong name.** An agent that follows a quickstart
  copies `--by you` or `--by curator`, and the record names a person
  who never saw the page. *Workaround:* the approve step tells the
  agent to pass its own name (D3), and S3 checks that the step carries
  `--by`. The name is attribution, not authentication, and the persona
  says so.
- **Testing prose order too tightly.** A test that matches whole
  sentences breaks on every wording round. *Workaround:* S3 checks verb
  names, forbidden tokens and the relative order of three markers, not
  sentences.

## No-gos

- No change to `src/wiki_studio/` other than `schema/WIKI_MAINTAINER.md`.
  No verb, flag, exit code, MCP tool, capability, API signature or
  format version. 0 and 2..11 keep their meaning, and 1 stays fatal
  lint.
- No code that refuses, flags or reports self-approval in cycle 06,
  and no change to `approve`, `review_state` or the approval policy
  (D3). The persona states the consequence; the code stays as it is.
  This holds for this pitch only. A `findings` kind for self-approved
  pages can be a separate issue later. None is filed now.
- No change to the page schema (frontmatter keys, page types,
  directories) and no ADR (finding 5). `schema.version` stays 2.
- No change to the three prompt documents, the prompts or the
  fingerprint (finding 4).
- No runtime dependency, no memkernel dependency in any group, and no
  network access in a test.
- No edit to memkernel, to code-copilot-team or to
  `eval/navigation/wiki/schema/WIKI_MAINTAINER.md`.
- No restatement of memkernel's memory steps (`retain`, `recall`,
  `consolidate`, checkpoints) in the persona.
- No edit to `docs/quickstart-memkernel.md` apart from the release pins.
  It is an executed walkthrough of both tools, not an instruction set
  an agent loads.
- Coverage stays at or above 92 percent. Every command the persona or
  the README shows gets a real check (S3 for the persona, the existing
  jobs for the README).

## Decisions

The owner **decided D1-D10** on 2026-11-14 in the main session. D3 went
against the recommended default; the other nine took it. Each item
keeps the default, its reason and the alternative, so the record shows
what was weighed. D-items marked *settled* follow from the issue or the
code, and are listed so the spec does not reopen them.

- **D1. Appetite (decided by the owner, 2026-11-14: the default).**
  Owner, 2026-11-14: 2w, bet for cycle 06, build in week 1. The
  default was **2w, bet for cycle 06**, as the owner's cooldown note
  plans, with week 2 kept for review and the release. The work content
  is 4-6 hours, a small batch, and 2w is the smallest the format
  allows. Alternative not taken: run it outside a cycle as a cooldown
  small batch, as #90 shipped in 0.9.1.
- **D2. Rewrite the loop on the governed path (decided by the owner,
  2026-11-14: the default).** Owner, 2026-11-14: rewrite steps 6-9 as
  propose, promote, lint and approve. The default was **yes**, with
  real wiki-studio commands (S1). memkernel's templates already send
  agents to the persona for "the propose, promote and approve loop",
  and the issue says the persona owns it. Alternative not taken: keep
  the hand-edit loop and add a pointer to the README. memkernel's
  templates would then point at a loop the persona does not contain
  (finding 2).
- **D3. Who runs `approve` (decided by the owner, 2026-11-14: NOT the
  default).** Owner, 2026-11-14: **the agent approves its own page.**
  After propose, promote and lint, the agent runs
  `wiki-studio approve <page> --by <its own name>`, or runs it with
  `WIKI_STUDIO_ACTOR` set to that name. It names itself honestly, so
  the approval record shows that an agent approved the page. A person
  may still re-review it later through `review_state` or `findings`.
  The persona keeps the note that `auto_approve_on_promote` approves
  on promote. The MCP adapter has no approve tool (finding 7).
  Owner, 2026-11-14: an order is set. An agent that reaches
  wiki-studio through MCP uses the CLI
  (`wiki-studio approve <page> --by <its own name>`) when it has a
  shell. Only otherwise does it stop and report the promoted pages
  awaiting approval. The persona defines the curating agent as the
  curator. The code allows this: `api.approve` takes `by` as
  attribution, not authentication, and refuses a draft, a superseded
  page, a structural-lint violation, a changed revision and a missing
  approver when the policy requires one. Nothing refuses
  self-approval (finding 7).
  *The consequence, recorded plainly:* memkernel's governed import then
  takes pages that an agent approved, and each approval record names
  that agent as the approver. Owner, 2026-11-14: say it plainly. An
  agent can take its own retained memory all the way to an imported
  page with no person involved: export, make the draft stable,
  approve, import. The persona's "Memory tools" section carries the
  same sentence (S2).
  *Scope of the no-go:* Owner, 2026-11-14: no code that refuses, flags
  or reports self-approval in cycle 06, for this pitch only. A
  `findings` kind for self-approved pages can be a separate issue
  later; none is filed now.
  *Agreement with memkernel, checked:* memkernel's line 46
  (`wiki_export() → review the draft pages → (with wiki-studio)
  wiki-studio approve <page> → wiki_import()`) gives the order of the
  steps but not who approves, so an agent running `approve` follows
  the same sequence. memkernel's line 172 says only pages "a curator
  approved" are imported. With the curating agent defined as the
  curator, that sentence holds too. No memkernel text needs to change.
  The recommended default was **the reviewer, a person**: the agent
  would stop after promote and approve only when a reviewer told it to.
  That matched the MCP adapter, which leaves approval to a person.
- **D4. How much the persona says about export and import (decided by
  the owner, 2026-11-14: the default).** Owner, 2026-11-14: name the
  four tools, link the template, and give one paragraph in memkernel's
  order with the draft-to-stable rule and no call signatures. In that
  paragraph, export creates drafts, the curator turns a draft into a
  stable page through the loop and approves it (D3), and the governed
  import takes approved pages only. It includes the fact that
  `approve` refuses a draft (S2). The issue allows a mention "if it
  uses the same steps", and the draft-to-stable step is curation, which
  memkernel leaves to the persona. Alternative not taken: link only,
  with no steps.
- **D5. How agreement with memkernel is pinned (decided by the owner,
  2026-11-14: the default).** Owner, 2026-11-14: a copied memkernel
  line pinned to `v0.8.0`, plus the persona-only checks (S3). This
  needs no network and no memkernel dependency, and follows the
  copied-parser precedent. Alternatives not taken: (a) a CI job that
  fetches memkernel's template from GitHub at a tag, which adds network
  and a new job, because the template is not in memkernel's wheel
  (finding 3); (b) persona-only checks, with no cross-repo pin; (c) a
  memkernel-side test that reads the installed persona, which would be
  a memkernel change.
- **D6. Which memkernel URL the persona links (decided by the owner,
  2026-11-14: the default).** Owner, 2026-11-14: the template at tag
  `v0.8.0`,
  `https://github.com/gosha70/memkernel/blob/v0.8.0/templates/claude-memory-instructions.md`.
  This is the tag D5 pins, so the link cannot drift from the copy.
  Alternative not taken: `main`.
- **D7. The code-copilot-team details outside the loop (decided by the
  owner, 2026-11-14: the default).** Owner, 2026-11-14: leave them
  unchanged; one follow-up issue is optional. It would cover
  generalising "Edit a generated artifact" and "Distribution-claim
  discipline", and code-copilot-team syncing its own persona copy
  (findings 10, 11). Only the lint command changes, because it is a
  step of the loop. Alternative not taken: generalise the whole persona
  in this pitch.
- **D8. Release vehicle (decided by the owner, 2026-11-14: the
  default).** Owner, 2026-11-14: release as **0.9.2**, a patch. The
  persona ships inside the wheel (finding 4), and memkernel 0.8.0
  already sends users to it. No API, verb or contract changes.
  Alternatives not taken: 0.10.0; no release of its own.
- **D9. How #69 closes (decided by the owner, 2026-11-14: the
  default).** Owner, 2026-11-14: the build PR closes #69 with a closing
  keyword, and its body names memkernel #104 and #109. After the merge,
  the owner comments on memkernel #86 with the build PR's number. That
  meets "each names the other's resolving PR" (finding 12). The pitch
  PR and the spec PR use no closing keyword. Alternative not taken:
  close #69 only when the release ships.
- **D10. The README "Schema" sentence (decided by the owner,
  2026-11-14: the default).** Owner, 2026-11-14: fix it in S4
  (finding 9). Otherwise the README and memkernel's template would
  contradict each other on where the persona is read from.
  Alternative not taken: a later docs pass.
- **D11. No ADR, no fingerprint move (settled).** The persona is not a
  prompt document and is not hashed (finding 4). The page schema does
  not change (finding 5).
- **D12. The frozen eval copy stays (settled).** It is hash-pinned
  evidence of a past run (finding 10).
- **D13. No memkernel change (settled).** memkernel #86 is closed. Its
  template and test already describe and guard its side (findings 1,
  2). The memkernel pin in CI (0.6.0) and `docs/compatibility.md` do not
  change.
- **D14. "Promote" means `wiki-studio promote` in the persona
  (settled).** Finding 8. The wording changes in S1, and the one-line
  explanation of memkernel's `promote` is in S2.

## Circuit breaker

Core is S1, S2 and the persona-only checks of S3: the loop on the
governed path with real commands, the memory boundary with its link,
and the tests that every command is real and that no memory step is
restated. They ship alone if the cycle runs out. The triggers, in
order:

1. **End of week 1.** If S1 is not downhill, S2 shrinks to the link with
   no steps (D4's alternative, as a cut). The approve step of S1, with
   `--by` and the CLI-first order for an agent without the approve
   tool, stays in either case. So does S2's sentence that an agent can
   take its own memory to an imported page with no person involved. The copied memkernel line in S3 is cut,
   and the persona-only checks are the evidence. The CHANGELOG says so.
2. **End of week 2.** S4 ships what is true. If the release cannot be
   cut, the change waits under `[Unreleased]`, and #69 stays open
   until a release carries it.
3. **Never, to save time:** change behaviour under `src/wiki_studio/`
   other than the persona, or a verb, exit code or MCP tool; change
   the page schema; add a runtime dependency or a network fetch in a
   test; edit memkernel, code-copilot-team or the frozen eval copy;
   restate memkernel's memory steps in the persona; drop `--by` from
   the approve step, or add code that refuses, flags or reports
   self-approval in cycle 06 (D3); weaken or skip a test.

"Exhausted" means two working weeks have passed. A third review round
on one scope is not exhaustion. It is an escalation to the owner, who
chooses a fix session, a cut from the list above, or a hold.

## Questions for the owner

Asked by the main session on 2026-11-14. The owner chose the default for
nine of the ten and decided D3 against it. D1 2w, cycle 06, build in
week 1; D2 rewrite steps 6-9 as propose, promote, lint and approve; D3
**the agent approves its own page** with
`wiki-studio approve <page> --by <its own name>`. On the three D3
follow-up points (same day): an agent reaching wiki-studio through MCP
uses the CLI when it has a shell, and only otherwise stops and reports;
the persona and D3 each say plainly that an agent can take its own
memory to an imported page with no person involved; and the
self-approval no-go holds for cycle 06 only, with a possible separate
issue later, not filed. D4 name the four
tools, link the template, one paragraph in memkernel's order with the
draft-to-stable rule; D5 a copied memkernel line pinned to `v0.8.0`
plus the persona-only checks; D6 link the template at tag `v0.8.0`; D7
the code-copilot-team details stay, with one optional follow-up issue;
D8 release 0.9.2; D9 the build PR closes #69 and names memkernel #104
and #109, then the owner comments on memkernel #86; D10 fix the README
"Schema" sentence in S4.

## Bet log

| Date | bet_status | Note |
|------|------------|------|
| 2026-11-14 | shaping | Pitch drafted from wiki-studio #69 (no comments) and cooldown-after-05 (the owner's next pick). wiki-studio read at main 829e688 (0.9.1); memkernel read at tag v0.8.0 (tag fe1e11a, commit 700d31f), including its templates, `test_template_wiki_workflow.py` and `sync.py` export; code-copilot-team read at 00d49c0. The packaged persona path command from memkernel's template was run here and resolves. |
| 2026-11-14 | shaping → shaped | 4 scopes, 2w, work content 4-6h (a small batch). Core: S1 (the loop on propose, promote and approve), S2 (memory boundary), S3's persona-only checks. Cut first: the copied memkernel line, then S2's steps. 14 decisions; D1-D10 open for the owner with defaults, not yet asked (AskUserQuestion was unavailable to the shaping agent). |
| 2026-11-14 | shaped (decided) | Owner answered D1-D10 in the main session. Nine defaults; D3 against the default: the agent approves its own page with `wiki-studio approve <page> --by <its own name>` (or `WIKI_STUDIO_ACTOR`), an MCP-only agent stops and reports or uses the CLI, and the persona defines the curating agent as the curator. `api.approve` (`src/wiki_studio/api.py` 786-807) rechecked: `by` is attribution, and nothing refuses self-approval. memkernel v0.8.0 rechecked: line 46 gives the order but not who approves, and line 172 ("a curator approved") holds with the agent as curator. Updated: finding 7, Appetite, Solution shape, S1 (approve step), S2, S3 (`--by` check; order check scoped to "Memory tools"), a rabbit hole, a no-go, the circuit breaker. Same day, the owner settled three D3 follow-ups: an agent reaching wiki-studio through MCP uses the CLI approve when it has a shell, and only otherwise stops and reports; the persona's "Memory tools" section and D3 each say plainly that an agent can take its own retained memory to an imported page with no person involved; the self-approval no-go holds for cycle 06 only, and a self-approval findings kind may be a separate issue later (not filed). Updated: D3, S1, S2, S3 (the restatement and order checks allow that sentence; CLI-first order), the no-go, the circuit breaker, the questions section. |
