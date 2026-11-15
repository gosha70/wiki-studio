---
spec_mode: full
feature_id: wiki-studio-0-9-2
risk_category: feature
status: approved
date: 2026-11-15
---

# Spec: wiki-studio 0.9.2 — one set of instructions

<!-- Project constitution: shared/skills/ — copilot-conventions, coding-standards, safety -->

Design references (read before building): `CLAUDE.md`; the bet pitch
`specs/pitches/69-one-set-of-instructions/pitch.md` (cycle 06, building;
reviewed in PR #99, merged 558e0fd, with three reviewer notes carried into
this spec: note 1 in FR-004 and FR-021, note 2 in FR-008 and FR-020, note 3
in FR-014; bet and cycle start PR #100, merged 204d568). The pitch is the shaping record and carries the owner's decisions
D1-D10 (2026-11-14; D3 against the default and revised after review the same
day) and the settled D11-D14. Its origin: wiki-studio issue #69, the
counterpart of gosha70/memkernel#86 (closed; memkernel PRs #104 and #109,
merged 2026-11-07), and `specs/retros/cooldown-after-05.md` (the owner's pick
for cycle 06). The origin block is in `plan.md`'s frontmatter. The 0.9.0
bundle (`specs/wiki-studio-0-9-0/`) for this bundle's form.

In this repository: `src/wiki_studio/schema/WIKI_MAINTAINER.md` (142 lines;
Role 5-15, which already names the agent "the wiki curator" at 7; "Required
reading on every invocation" 17-28; "The canonical curator loop" 30-72 with
"For every promotion or update" at 32, steps 1-5 at 34-58 including the
0.9.0 conflict sub-rule 48-58, Write 59-62, Link 63-65 and Log 66-67 (links
`../index.md`, `../log.md`), Lint 68-69 naming
`bash knowledge/wiki/scripts/lint-wiki.sh`, Stop 70-72; "What you must never
do" 74-88 with "Promote session ephemera" 77-79, "Edit a generated artifact"
80-82, "Bypass the linter" 83-84 naming `lint-wiki.sh`, "Mix promotion and
curation" 85-86; "Distribution-claim discipline" 90-126; "Escalation"
128-142), `src/wiki_studio/schema/page-types.md` (`status: <draft | stable |
deprecated>` 16; "Approval is recorded by `wiki-studio approve`, never by
frontmatter" 46-49), `src/wiki_studio/cli.py` (`_build_arg_parser` 176-539:
the subparsers at 202, `promote --by` 298, `approve` 301-321 with
`--revision` 314-320 and `--by` 321, `propose` 481-507 with `--from` required
at 489, `--promote` 492 and `--by` 502-507, `read` 510-523 with `--json`
printing `{"path", "sha256", "content"}` at 519-523, `info` 453-461 with
`--json` at 461; `_do_promote` prints each applied path as
`  + <wiki-label>/<path>` and each policy-approved one as
`  approved <wiki-label>/<path>` at 645-655; `_do_approve` refuses
`--revision` with more than one page (exit 4) at 660-664; `_do_propose`
prints the proposal directory, then one `  <action> <path>` line per edit
(wiki-relative) at 943-945, and with `--promote` only a count of applied
edits at 960; `_do_info` merges the contract's keys into `info --json` at
849-850; `_VERBS` 990-1003; the legacy shim 1009-1043, not used by the
check; `main` 1062-1091), `src/wiki_studio/mcp_adapter/config.py`
(`TOOL_NAMES` 39-48; `describe_launch` 88: with `auto_approve_on_promote`,
"promote approves the pages it writes"; `build_parser` 97-154 with
`--disable-tool` 139-146; the module imports only
the standard library and `wiki_studio`, and `mcp_adapter/__init__.py` imports
only `sys`, so it loads without the `mcp` extra, as
`tests/test_mcp_adapter.py` 37 already does), `src/wiki_studio/api.py`
(`approve` 779-811: `by` is the approver, flag, else `WIKI_STUDIO_ACTOR`,
else none, "attribution, not authentication"; refusals in the docstring at
797-801; nothing refuses self-approval), `src/wiki_studio/contract.py`
(`load_schema` 375-398: each of the three prompt documents is read from
`<wiki>/schema/<name>.md` when that file exists, else from the package;
`POLICY_AUTO_APPROVE_ON_PROMOTE` and `POLICY_KEYS` 65-66; `ManifestInfo`
484-504, whose `as_dict` gives a present manifest's `policy` and a missing
one's `state`, `mode` and `instruction` only, so a legacy wiki has no
policy; the contract's `as_dict` puts it under `manifest` at 558),
`src/wiki_studio/mcp_adapter/tools.py` (`info` 264-279 returns the same
object plus `adapter`; `promote` 203-234 lists policy-approved pages in
`approved_paths`), `src/wiki_studio/schema/__init__.py` (`PROMPT_SCHEMA_DOCUMENTS` 112),
`docs/mcp-adapter.md` ("The boundary" 153-186: "Not exposed" 155-157 names
`approve`; propose-only mode 164-167; the fixed actor 168-172; auto-approval
by policy 173-180, the sentences to correct at 178-180), `README.md`
(`# 0.9.1` at 26; `wiki-studio approve` 230-246; `propose --from` 319-355;
"Attribution" 357-366; `WIKI_STUDIO_ACTOR` 447; "Schema" 452-466 with the
overstated sentence at 456-458; "MCP" 551-572 with the propose-only sentence
at 565-566, which the pitch cites as 566), `docs/quickstart-memkernel.md`
(`==0.9.1` pins at 27 and 38), `docs/compatibility.md` ("A pair that is not
listed here is not claimed as compatible" 5; tested pairs 9-15 with the 0.9.1
row at 15; "A row moves to 'tested' only when a green run … is named" 27-28),
`.github/workflows/ci.yml` (`MK_VERSION: "0.6.0"` at 102, 135 and 249),
`.github/workflows/release.yml` (the release steps in its header 9-25),
`CHANGELOG.md` (`[Unreleased]` empty at 7; `[0.9.1] — 2026-11-15` at 9),
`pyproject.toml` (version 6; the schema package data 28-29),
`src/wiki_studio/__init__.py` (version 5), `tests/test_schema.py`
(`SCHEMA_DOCUMENTS` 25-27, presence only), `tests/test_frozen_runs.py`
(`FROZEN_PINS` 51-225 pins `eval/navigation/wiki/schema/WIKI_MAINTAINER.md`
by sha256 at 218; `test_every_pinned_file_is_unchanged` 451),
`tests/test_package_boundaries.py` (`test_bash_linter_is_not_shipped` 55-61
asserts that no file named `lint-wiki.sh` is in the package and that
`lint.py` and `promoter.py` do not name it; it reads no markdown, and
`TestNoForeignLayoutStrings` 43-53 scans `*.py` only), `tests/test_cli_contract.py`
(`self.assertEqual(__version__, "0.9.1")` at 148),
`tests/integration/test_quickstart_memkernel.py` (`EXPECTED_INSTALL_COMMANDS`
pins at 58-59), `tests/test_info_contract.py` (imports the private
`wiki_studio.cli._VERBS` at 16, the precedent for a test reading a private
CLI name), `tests/test_avoid_roundtrip.py` and
`tests/test_conflict_memkernel_roundtrip.py` (the copied-from-memkernel
header form). In memkernel, read-only, tag `v0.8.0` (tag object `fe1e11a`,
confirmed in the local checkout's `.git/refs/tags/v0.8.0`; commit `700d31f`):
`templates/claude-memory-instructions.md` line 46, the one-line workflow
`wiki_export()  → review the draft pages → (with wiki-studio) wiki-studio approve <page> → wiki_import()`,
and its `### Wiki` section 166-182 (line 172: only pages "a curator approved"
are imported). Those tag line numbers are the pitch's; the local checkout is
at memkernel `main` (version 0.9.0 plus unreleased template additions), where
the same line reads identically at 58 and `### Wiki` is 210-226. Every
wiki-studio citation above was checked against `main` at 204d568 on 15
November 2026; where the pitch's numbers differ, the numbers here are the
current ones.

## Why

memkernel 0.8.0 made its agent templates cover memory only and sends agents
to wiki-studio's curator persona, `WIKI_MAINTAINER.md`, for "page types,
citations, writing and linking a page, linting, and the propose, promote and
approve loop". The persona does not hold that loop. Its steps 6-9 have the
agent write the page, edit `index.md`, append to `log.md` and run
code-copilot-team's bash linter by hand; it never names `wiki-studio
propose`, `promote` or `approve`, and the lint command it names is not in the
wheel. It never draws the line between memory and curation, so an agent
reading both files cannot tell which file owns a step, or that memkernel's
`promote` is not `wiki-studio promote`. Issue #69 asks that each job is
described once.

This release rewrites the persona's loop on the governed path (draft,
propose, promote, lint, approve), with one agent name on every record and an
approval rule that yields to the host: the agent approves each page it
changed, at the revision it read and inspected, unless the project's
instructions reserve approval for a person or the host runs it propose-only
(D3). Where the instructions reserve approval and the wiki's policy approves
on promote, the agent stops after propose, so the reservation holds on every
wiki (owner, 2026-11-15, after the PR #101 review). It adds a short "Memory tools" section that leaves memory
to memkernel's template and states the export, approve, import order. One
test module checks the persona as users receive it: every command it shows
parses with the CLI's own parser, the approval rule and its policy check
come before any promote or approve command, the approve command carries
`--revision` after a `read --json`, no memory step is restated, and the order
matches memkernel's line copied at `v0.8.0`. Two doc sentences that promise
hosts a person approves are corrected, the README's "Schema" overstatement
is fixed, and the change ships as 0.9.2. Nothing else moves: no verb, flag,
exit code, MCP tool, capability, API signature, page-schema key, prompt,
fingerprint or dependency, and no code that refuses, flags or reports
self-approval.

## User Scenarios

### US1: The curator loop on the governed path (Priority: HIGH)

**Given** an agent with a shell in a project that uses wiki-studio, a lesson that passes the ingest gate, and the packaged `WIKI_MAINTAINER.md`
**When** the agent follows the curator loop for a new page, for an update and for a two-page patch-set, once in a project whose instructions say nothing about approval, once in a project whose instructions carry the line "A person approves wiki pages here; do not run `wiki-studio approve`." on a wiki whose policy does not auto-approve and once on a wiki whose policy sets `auto_approve_on_promote`, and once reaching wiki-studio only through the MCP server
**Then** the loop tells it to draft the pages in a directory laid out like the wiki with the index and log lines beside it, record the base hash from `wiki-studio read <path> --json` for an update, decide who approves (the project's instructions, propose-only mode, and the policy `wiki-studio info --json` reports) before it proposes, run `wiki-studio propose --from <dir> --by <agent-name>`, promote with `--promote` or `wiki-studio promote <proposal-dir> --by <agent-name>` when the rule allows, run `wiki-studio lint`, and then, for each changed content page, run `wiki-studio read <page> --json`, inspect the page and run `wiki-studio approve <page> --revision <sha256> --by <agent-name>`; every command names the agent's own name, never a person's; in the reserving project it promotes and stops before approve where the policy does not auto-approve, and stops after propose where it does; on an auto-approving wiki without a reservation promote approves and the approve step is skipped; through MCP it runs the CLI read and approve when it has a shell and otherwise stops and reports; and the persona no longer names `lint-wiki.sh` or uses "promote" for anything but `wiki-studio promote`

### US2: The memory boundary (Priority: HIGH)

**Given** an agent that has read memkernel 0.8.0's template and the packaged persona
**When** it reads the persona's "Memory tools" section
**Then** the section says memkernel's `retain`, `recall`, `wiki_export` and `wiki_import` are described in memkernel's template, links that template at tag `v0.8.0`, says the link is to instructions and not a compatibility claim, gives one paragraph in memkernel's order (export creates draft pages, the curator makes a draft stable through the loop and approves it, the governed import takes approved pages only), says plainly that unless the host reserves approval an agent can take its own retained memory to an imported page with no person involved, says memkernel's `promote` tool moves a memory between tiers and does not touch the wiki, and restates no memory step or call syntax

### US3: The checks (Priority: HIGH for the persona-only checks; the copied memkernel line is cut first)

**Given** the packaged persona read through `importlib.resources`, the CLI's argparse parser and the MCP server's launch parser, with no network and no memkernel installed
**When** `tests/test_maintainer_persona.py` runs
**Then** every `wiki-studio …` command the persona shows parses with `wiki_studio.cli._build_arg_parser()` with every flag spelled in full, every bare `wiki-studio <verb>` names a real verb, the MCP launch option the persona names parses with `mcp_adapter.config.build_parser()` and names a real tool, a wrong verb, a wrong flag, an abbreviated flag, a missing required flag and an unknown tool each fail the checker; every propose, promote and approve command carries `--by` and every approve command `--revision`; the "Who approves" step names both reservation markers, the example line, the `wiki-studio info --json` policy check and the stop-after-propose case before any promote or approve command; the approve step names the each-changed-content-page rule and a `read --json` command before its approve command, and the CLI before the no-shell fallback; no memory step or call syntax appears and memkernel's tool names appear only in "Memory tools"; and that section names export, approve and import in the order of memkernel's line copied at `v0.8.0`

### US4: Docs, release 0.9.2 and closure (Priority: MEDIUM)

**Given** the three phases above landed, or cut by the circuit breaker in the pitch's order
**When** a host reads README and `docs/mcp-adapter.md`, and the version moves to 0.9.2
**Then** README "Schema" says only the three prompt documents are read from a project copy and the persona is read from the package, with the persona owning curation and memkernel's template owning memory; README and `docs/mcp-adapter.md` say a host reserves approval for a person by its project's instructions (with the copyable example line) or by propose-only mode, that under such instructions on a wiki whose policy approves on promote the persona stops after propose, and no longer offer a wiki without the policy as a way to keep approval with a person; the CHANGELOG lists the change under `[0.9.2]`; the version reads 0.9.2 in the six places; `docs/compatibility.md` is untouched by the build (the release PR adds the row); exit codes, the page schema, the dependency list and `promoter.py`'s single-writer rule are unchanged; and #69 closes by the build PR's merge

## Requirements

### US1 — the curator loop on the governed path

- **FR-001 (steps 6 onward, D2)**: In "The canonical curator loop", steps 1-5 and the conflict sub-rule (34-58) MUST stay byte-identical. Steps 6-9 (Write, Link, Log, Lint) are replaced by the governed path, numbered on from 6 in this order: **6. Write** — draft the page in a working directory laid out like the wiki (`concepts/<slug>.md`, `decisions/<slug>.md`, …), outside the wiki directory, with the template from `page-types.md` and the writing rules (both existing links kept); for an update, start from the live text of `wiki-studio read <path> --json` and record its `sha256` for the page in `<dir>/.base.json`; set `status:` per `page-types.md`, and note that a page left `draft` cannot be approved (step Approve, FR-003). **7. Link** — put the line that links the page from the wiki's index in `<dir>/index.md`. **8. Log** — put the log line, in its fixed form `- YYYY-MM-DD — <verb> <slug> (<page-type>): <one-line why>`, in `<dir>/log.md`. **9. Who approves** — FR-003; it comes before the propose command because `--promote` is chosen when proposing. **10. Propose** — run `wiki-studio propose --from <dir> --by <agent-name>`, or, when step 9 allows promotion and the host allows promoting at once, `wiki-studio propose --from <dir> --promote --by <agent-name>`; the first line of output is the proposal directory, followed by one `  <action> <path>` line per edit. **11. Promote** — only when step 9 allows it: `wiki-studio promote <proposal-dir> --by <agent-name>` after review, unless step 10 already promoted with `--promote`; `promote` lints the staged tree and is the only writer into the wiki. **12. Lint** — run `wiki-studio lint`; if it fails, fix the violation, do not silence it. **13. Approve** — FR-003. **14. Stop** — the current step 10's text, unchanged. Through MCP, the `propose` and `promote` tools take the place of the two commands under the same rule. Placeholders are written `<dir>`, `<path>`, `<proposal-dir>`, `<page>`, `<sha256>` and `<agent-name>`. The loop names each verb and the flags each step needs (`--from`, `--promote`, `--by`, `--json`, `--revision`) and no others, and links the README and `docs/quickstart.md` once each for details, by absolute URL under `https://github.com/gosha70/wiki-studio/blob/main/`, because a relative link does not resolve from the installed package (the README's own precedent at 259). No step refers to the "Memory tools" section (US2 adds it).
- **FR-002 (one agent name on every record, D3)**: Every `wiki-studio propose`, `wiki-studio promote` and `wiki-studio approve` command the persona shows MUST carry `--by <agent-name>` (the approve command also carries `--revision`, FR-003). The persona defines `<agent-name>` once, at its first use: the agent's own name, one that identifies it as an agent (for example `claude-code`), never a person's name and never a name copied from a quickstart (`--by you`); setting `WIKI_STUDIO_ACTOR` to that name is the alternative; the same name on propose, promote and approve makes the records show one name; it is attribution, not authentication. Through MCP the tools take no `by`, and the records carry the actor the server was launched with.
- **FR-003 (who approves, and the approve step; D3 as refined by the owner on 2026-11-15; the one place the rule lives)**: Two steps of the loop hold the rule.
  **Step 9 begins with the bold label `**Who approves.**`** and holds, in this order: (a) **the reservation condition**: approval is reserved for a person when the project's instructions say a person approves wiki pages or tell the agent not to run `wiki-studio approve` (for example the line of FR-004, quoted verbatim), or when the host runs the agent propose-only (`--disable-tool promote`, where the `promote` tool is missing); the text contains the literal phrase `project's instructions` (straight apostrophe) and the code span `` `--disable-tool promote` ``; (b) **the policy check**: run `wiki-studio info --json` (through MCP the `info` tool returns the same object) and read `manifest.policy.auto_approve_on_promote`; a wiki with no manifest (`manifest.state` is `missing`) has no policy and never approves on promote; the text contains the code span `` `wiki-studio info --json` `` and `auto_approve_on_promote`; (c) **the outcomes**, each stated once: (1) propose-only mode, or project's instructions that leave promotion to a person: stop after propose and report the proposal directory for a person to promote and approve; (2) approval reserved by the project's instructions and the policy approves on promote: stop after propose and report the proposal directory for a person to promote and approve, because promote would approve the pages at once; the text contains the literal phrase `stop after propose`; (3) approval reserved by the project's instructions and the policy does not approve on promote: promote (step 11) and lint (step 12), then stop before approve and report the promoted pages awaiting a person; (4) approval not reserved and the policy approves on promote: promote and lint; promote approves the pages it writes, under the wiki lock at the bytes it wrote (`wiki-studio promote` and `propose --promote` print `approved <wiki-label>/<path>`, the MCP tool lists them in `approved_paths`); auto-approval is best effort and can leave a page unapproved while promote succeeds, so every eligible page (each changed content page of (d) that is not `status: draft` and carries no `superseded_by`) must appear in that list, and if one is missing the agent does not approve it, reports each missing page with promote's warning, and stops; only when every eligible page appears is the approve step skipped (owner, 2026-11-15, after the #103 review); (5) approval not reserved and the policy does not approve on promote: promote, lint and approve (step 13), the persona's default. No promote or approve command of the loop appears before this step.
  **Step 13 begins with the bold label `**Approve.**`** and applies in outcome (5) only. It holds, in this order: (d) **which pages**: each changed content page, meaning the pages of the patch-set's `create` and `update` edits; `propose` lists them as `  create <path>` and `  update <path>`, and they are the applied paths `wiki-studio promote` prints as `  + <wiki-label>/<path>` (without the label) minus the root `index.md`, `log.md` and anything under `.audit/`; a changed page that is `status: draft` or carries `superseded_by` is skipped and reported, not approved, and the agent never edits frontmatter to get an approval through (amended 2026-11-15 after the #103 review); the text contains the literal phrase `each changed content page`; (e) **per page, in order**: run `wiki-studio read <page> --json` and take its `sha256`; inspect the content (it is the page the agent drafted and promoted, and nothing else changed it); then run `wiki-studio approve <page> --revision <sha256> --by <agent-name>`, naming itself honestly so the record shows that an agent approved; one page per approve, because `--revision` takes exactly one page (exit 4 otherwise); (f) **a changed revision**: if approve refuses because the live page differs from `<sha256>`, another writer replaced it after promote; the agent does not approve it, and reports the page and stops, because an approval under its name would vouch for bytes another writer produced (owner, 2026-11-15, after the #103 review; this narrows the earlier re-read-and-approve rule); it never approves without `--revision`; (g) **what `approve` refuses** (exit 9, nothing written): a `status: draft` page, a page carrying `superseded_by`, a page with a structural-lint violation, a `--revision` that is not the live one, and a missing approver when the policy requires one; on a wiki with no manifest it exits 4 (`wiki-studio init` first, a person's call), and the agent reports the pages instead; (h) a sub-bullet beginning `- **Through MCP.**`: the MCP server has no approve tool, so in outcome (5) an agent that reaches wiki-studio through MCP runs the read and approve commands of (e) through the CLI when it has a shell, and only without a shell stops and reports the promoted pages awaiting approval; the sub-bullet contains the literal phrase `without a shell` after its approve command; (i) a person may still re-review a page later through `review_state` or `findings`.
  Role's existing "You are the **wiki curator**" (7) is the definition of the curator and stays; FR-009 ties memkernel's word to it. Every other FR that mentions who approves, promotes or stops (FR-001, FR-009, FR-010, FR-021, FR-022) refers to this FR and does not restate the condition, the policy check or the outcomes.
- **FR-004 (the reservation example line, reviewer note 1)**: The example a host can copy into its project instructions is exactly this line, called R in this spec: ``A person approves wiki pages here; do not run `wiki-studio approve`.`` R is defined here only. The persona quotes R verbatim in FR-003(a); README and `docs/mcp-adapter.md` quote it verbatim in FR-021; FR-016 and FR-021 check the copies. The span inside R is a bare verb mention (FR-014) and carries no `--revision` or `--by`, so it is never read as an approve command.
- **FR-005 (the lint command)**: "Bypass the linter" (83-84) MUST name `wiki-studio lint` in place of `lint-wiki.sh`, with no other change to the bullet's meaning. After the phase the persona contains no `lint-wiki` anywhere (FR-014 checks it).
- **FR-006 ("promote" means `wiki-studio promote`, D14)**: Every use of "promote" or "promotion" in the persona for adding a lesson to the wiki MUST be reworded so the word names only `wiki-studio promote`, `--promote` or the MCP `promote` tool: "For every promotion or update" (32), "Promote session ephemera" (77, which the pitch's finding 8 does not list but D14 covers) and "Mix promotion and curation in one turn. Promote *or* refactor; not both." (85-86). The meaning of each sentence stays (for example "For every new page or update", "Store session ephemera", "Mix adding a lesson and refactoring in one turn"). The one sentence about memkernel's `promote` is FR-011's.
- **FR-007 (what stays, D7)**: The title and opening blockquote (1-3), Role, "Required reading", steps 1-5, the "What you must never do" bullets other than those FR-005 and FR-006 change, "Edit a generated artifact", "Distribution-claim discipline" and "Escalation" MUST be byte-identical to `main`. The relative links `../index.md`, `../log.md` and `../open-questions/` keep their form wherever they remain; the rewritten steps need not keep them. No new relative link to a file outside `schema/` is added; links out of the package are absolute URLs (FR-001, FR-008).

### US2 — the memory boundary

- **FR-008 (the section and its links, D4, D6, reviewer note 2)**: A section headed exactly `## Memory tools` MUST sit after "Required reading on every invocation" and before "The canonical curator loop". Its opening paragraph says memkernel's `retain`, `recall`, `wiki_export` and `wiki_import` are described in memkernel's agent template, not in this file, and links the template at `https://github.com/gosha70/memkernel/blob/v0.8.0/templates/claude-memory-instructions.md`; it names no `wiki-studio approve`, so FR-009's paragraph is the section's first to name all three order markers (FR-018). The same paragraph says plainly that the link is to memkernel's instructions at that tag and is not a compatibility claim, and that the wiki-studio and memkernel pairs CI tests are listed in `https://github.com/gosha70/wiki-studio/blob/main/docs/compatibility.md`. The persona names no memkernel version other than the tag in the URL, so the release-specific pin (memkernel 0.6.0) lives on README and `docs/compatibility.md` only (FR-020).
- **FR-009 (export and import, D4)**: One paragraph, with no call signatures, in the order of memkernel's line: `wiki_export` creates `status: draft` pages through wiki-studio's propose and promote; the curator turns a draft into a stable page through the loop below, as an update with its base hash, and approves it as the loop's "Who approves" and "Approve" steps say (FR-003); the governed `wiki_import` takes approved pages only. It adds the one fact memkernel's line leaves out, that `approve` refuses a draft, by referring to the approve step's list (FR-003(g)) rather than restating the list. It says that memkernel's template calls the approver "a curator", and that the curator is the agent following this file (Role, FR-003). The paragraph names `wiki_export`, `wiki-studio approve` and `wiki_import`, first mentioned in that order, and is the first paragraph of the section that names all three; `wiki-studio approve` appears there as a bare verb mention, not a command (the command is the approve step's).
- **FR-010 (the consequence, in one sentence, D3)**: The section MUST say plainly, in one sentence after FR-009's opening sentence or in its own paragraph, that unless the host reserves approval for a person (FR-003), an agent can take its own retained memory all the way to an imported page with no person involved: export, make the draft stable, approve, import. The sentence uses tool names only, no call syntax, and names the steps in the same order as FR-009.
- **FR-011 (memkernel's `promote`, D14)**: One sentence: memkernel's `promote` tool moves a memory between memory tiers and does not touch the wiki; it is not `wiki-studio promote`. The sentence names the tool without call syntax. The pitch's S2 wrote `promote(ref_id=…)`, which its own S3 forbids; this spec follows S3 and D4 ("no call signatures").
- **FR-012 (what the persona never holds)**: The persona MUST contain none of `retain(`, `recall(`, `consolidate(`, `checkpoint=`, `promote(ref_id`, `wiki_export(` or `wiki_import(`, and no memory step (retaining, recalling, consolidating, checkpoints); the words `retain`, `recall`, `consolidate`, `wiki_export` and `wiki_import` appear only inside "Memory tools". The rule forbids call syntax and memory steps, not tool names, so FR-009, FR-010 and FR-011 pass it. FR-017 checks it.

### US3 — the checks

- **FR-013 (the module)**: `tests/test_maintainer_persona.py`, unittest style with the two-line EGOGE / Apache-2.0 header, reads the persona through `importlib.resources.files("wiki_studio").joinpath("schema", "WIKI_MAINTAINER.md")`, the bytes users get. It imports only the standard library, `wiki_studio.cli` and `wiki_studio.mcp_adapter.config`; it makes no network call and does not import or need memkernel. The persona-only checks (FR-014 to FR-017) are core; FR-018 is cut first.
- **FR-014 (every shown command parses, reviewer note 3)**: The module extracts every inline code span of the persona (single-backtick spans on one line, outside fenced blocks) and every non-blank line of a fenced block. Before splitting, each placeholder matching `<[^<>\n]+>` is replaced by one token (`PLACEHOLDER`); the span is then split with `shlex.split`. (a) A span whose first token is `wiki-studio` with exactly one more token is a verb mention: that token MUST be a choice of the parser's subparsers action (found by scanning `_build_arg_parser()._actions` for `argparse._SubParsersAction`). (b) A span whose first token is `wiki-studio` with more tokens is a command: `wiki_studio.cli._build_arg_parser().parse_args(tokens[1:])` MUST return, with stderr captured; a `SystemExit` fails the test naming the span and argparse's message. Because argparse accepts unambiguous prefixes, every token starting with `--` (cut at `=`) MUST also be an option string of the verb's subparser or of the top-level parser, so `--b` for `--by` fails. (c) A span whose first token is `wiki-studio-mcp`, or that starts with `--disable-tool`, is an MCP launch: it is parsed with `wiki_studio.mcp_adapter.config.build_parser()` under the same full-spelling rule, and each `--disable-tool` value MUST be in `TOOL_NAMES`. (d) The persona MUST show at least one command for each of `propose`, `promote`, `approve`, `read` with `--json` and `info` with `--json`, and contain no `lint-wiki` (FR-005). (e) Self-tests prove the checker bites: fed `wiki-studio aprove <page>`, `wiki-studio approve <page> --approver x`, `wiki-studio approve <page> --b x`, `wiki-studio approve <page> --rev <sha256> --by x`, `wiki-studio propose --by x` (no `--from`) and `--disable-tool approve`, the checker reports each as a failure, and fed `wiki-studio approve <page> --revision <sha256> --by <agent-name>`, `wiki-studio read <page> --json` and `wiki-studio info --json` it passes.
- **FR-015 (`--by` on the three writing verbs, `--revision` on approve, FR-002, FR-003)**: Every command of FR-014(b) whose verb is `propose`, `promote` or `approve` MUST carry `--by` followed by a value token, and every command whose verb is `approve` MUST also carry `--revision` followed by a value token.
- **FR-016 (the approval rule's markers and positions, FR-003, FR-004)**: A loop step is the numbered item of "The canonical curator loop" whose text starts with its bold label, up to the next line matching `^\d+\. \*\*` or the next `## ` heading. In the loop text, the first promote command P is the first FR-014(b) command whose verb is `promote` or whose verb is `propose` with `--promote`, and the first approve command A is the first FR-014(b) command whose verb is `approve`. (a) **Who approves**: the step labelled `**Who approves.**` contains `project's instructions`, `` `--disable-tool promote` ``, R (FR-004), a span that parses as `info` with `--json`, `auto_approve_on_promote` and `stop after propose`, and the first occurrence of each in the loop comes before both P and A. (b) **Approve**: in the step labelled `**Approve.**`, its first approve command C carries `--revision` and `--by`; `each changed content page` and a span that parses as `read` with `--json` each come before C. (c) **CLI first**: the MCP sub-bullet is the approve step's text from `- **Through MCP.**` to the end of the step; in it the first approve command comes before the first `without a shell`. The check matches these markers and their positions, not sentences.
- **FR-017 (no memory restatement, and the section's links, FR-008, FR-012)**: The persona contains none of FR-012's forbidden tokens. The section "Memory tools" is the text from the line `## Memory tools` to the next `## ` heading; outside it, `\b(retain|recall|consolidate|wiki_export|wiki_import)\b` matches nothing. The section contains the memkernel template URL and the `docs/compatibility.md` URL of FR-008 verbatim.
- **FR-018 (same order as memkernel; cut first, D5)**: A module constant holds memkernel's one-line workflow copied from `templates/claude-memory-instructions.md` line 46 at tag `v0.8.0` (commit `700d31f`), leading indentation stripped: `wiki_export()  → review the draft pages → (with wiki-studio) wiki-studio approve <page> → wiki_import()`. Its comment header reads "Copied from gosha70/memkernel templates/claude-memory-instructions.md at tag v0.8.0, line 46 (citation verified <date>, see the spec FR-018). Test fixture only; it changes only by a deliberate re-pin to a newer memkernel tag." The test derives the expected order of the markers `wiki_export`, `wiki-studio approve` and `wiki_import` from the constant, takes the first paragraph (blank-line-separated block) of "Memory tools" that names all three, and asserts their first mentions there follow that order. The build verifies the line at the tag (`git -C /Users/gosha/dev/repo/memkernel show v0.8.0:templates/claude-memory-instructions.md`) and corrects the header's line number if it differs, or reports plainly that it could not read the tag.
- **FR-019 (unchanged checks)**: `tests/test_schema.py`, `tests/test_frozen_runs.py` and `tests/test_package_boundaries.py` MUST pass unedited: `git diff main -- tests/test_schema.py tests/test_frozen_runs.py tests/test_package_boundaries.py eval/` is empty at the end of every phase.

### US4 — docs, release 0.9.2 and closure

- **FR-020 (README "Schema", D10, reviewer note 2)**: The sentence at 456-458 ("A project may carry its own copy under `<wiki-dir>/schema/`; when that directory exists it is used instead of the packaged one.") MUST be replaced by what `load_schema` does: a project may carry its own copy of any of the three prompt documents (`ingest-rules.md`, `page-types.md`, `citation-rules.md`) under `<wiki-dir>/schema/`; each copy present is used instead of the packaged one and is fingerprinted (`docs/knowledge-contract.md`); wiki-studio reads no project copy of the other three, and agents read the curator persona from the package. One sentence follows: the curator persona owns curation (page types, citations, the propose, promote, lint and approve loop) and memkernel's agent template owns memory, with links to both (the persona by absolute URL under `blob/main/`, the template at `v0.8.0`), and the template link points to instructions, not a compatibility claim: CI tests this release with memkernel 0.6.0 (`docs/compatibility.md`). The Layout table's "schema override … (used when present)" row (52) stays; it is true for the three documents.
- **FR-021 (how a host reserves approval, D3, finding 13, reviewer note 1)**: `docs/mcp-adapter.md` 178-180 keeps its first sentence ("On such a wiki an agent's promote approves its own proposal; that is the host's configured policy.") and replaces the second ("Use `--disable-tool promote`, or a wiki without the policy, when a person must approve.") with: a host reserves approval for a person in one of two ways, and the curator persona (`WIKI_MAINTAINER.md`) respects both: by running the server propose-only (`--disable-tool promote`), or by its project's instructions, for example with the line R (FR-004) quoted verbatim; on a wiki with this policy an agent following the persona under such instructions stops after propose and leaves promote and approve to a person, because its promote would approve. README 565-566 keeps "`--disable-tool promote` is propose-only mode: proposals wait for a person to promote and approve them." and adds: an agent that follows the curator persona approves the pages it changed through the CLI, at the revision it read, unless the host reserves approval for a person, by propose-only mode or by its project's instructions, for example R quoted verbatim; under such instructions, on a wiki whose policy approves on promote, it stops after propose. Neither page offers a wiki without `auto_approve_on_promote` as a way to keep approval with a person, and neither says that only propose-only keeps approval with a person on such a wiki (the owner's decision of 2026-11-15 on the PR #101 review supersedes that wording). Neither restates FR-003 beyond the two signals and the stop-after-propose case. `tests/test_maintainer_persona.py` gains one assertion, in this phase, that R appears verbatim in `README.md` and `docs/mcp-adapter.md` (FR-016 already checks the persona's copy).
- **FR-022 (CHANGELOG)**: `CHANGELOG.md` keeps an empty `## [Unreleased]` and gains `## [0.9.2]` (undated; the release PR adds the tag's UTC date, FR-024) with a one-line summary and a **Changed** section: the curator persona's loop follows propose, promote, lint and approve with `wiki-studio` commands and `--by <agent-name>` on each writing verb; the agent approves each page it changed with `--revision` at the bytes it read and inspected, unless the project's instructions or propose-only mode reserve approval for a person, and under such instructions on a wiki whose policy approves on promote it stops after propose; its lint step and "Bypass the linter" use `wiki-studio lint`; a "Memory tools" section leaves memory to memkernel's template (linked at `v0.8.0`) and states the export, approve, import order (#69, counterpart of memkernel #86, resolved by memkernel #104 and #109); README "Schema" says which documents a project copy replaces; README and `docs/mcp-adapter.md` say how a host reserves approval for a person. A **Notes** line: no API, verb, flag, exit code, MCP tool, capability, page-schema, prompt, fingerprint or dependency change; the frozen eval copy of the persona is unchanged; any cut from FR-025 named by its FR. No line uses a closing keyword (FR-026).
- **FR-023 (version, D8)**: 0.9.2 in `pyproject.toml` (6) and `src/wiki_studio/__init__.py` (5) together, README's `# 0.9.1` comment (26), the two `==0.9.1` pins on `docs/quickstart-memkernel.md` (27, 38), `EXPECTED_INSTALL_COMMANDS` in `tests/integration/test_quickstart_memkernel.py` (58-59) and the version assertion in `tests/test_cli_contract.py` (148), as PR #97 did for 0.9.1. No other line of those files changes.
- **FR-024 (compatibility: no row in the build; owner, 2026-11-15: confirmed over the pitch's S4 wording)**: The build MUST NOT edit `docs/compatibility.md`. The 0.9.2 with memkernel 0.6.0 row is added after the build PR merges, in the release PR that dates the CHANGELOG heading, naming the green `main` run on the build PR's merge commit for the five jobs the 0.9.1 row names (`memkernel-compat`, `memkernel-loop`, `quickstart-memkernel`, `demo-correction-loop`, `quickstart`), as PR #98 did for 0.9.1. Why this and not a Pending row: the build cannot name a run that exists only after its own merge; the page says a row moves to tested only with a named run (27-28); 0.9.0's build added a Pending row and its gating reviewer flagged it (f-fbff906c); a version that is not yet released needs no row, and the release PR merges before the tag, so the released version always has its row. The pitch's S4 placed the row in the build; this departs from it for those reasons.
- **FR-025 (circuit breaker and the invariant audit)**: The build follows the pitch's cut order and never cuts US1, US2's link and FR-010, FR-014 to FR-017, or FR-021's two corrections. End of week 1, if US1 is not downhill: FR-009 shrinks to the link with no steps (D4's alternative, as a cut) while FR-008, FR-010 and FR-011 stay, FR-018 is cut, and the CHANGELOG says so. End of week 2: US4 ships what is true. Never: a change under `src/wiki_studio/` other than `schema/WIKI_MAINTAINER.md` and the version line of `__init__.py`; a page-schema change; a runtime or memkernel dependency or a network fetch in a test; an edit to memkernel, code-copilot-team or anything under `eval/`; a restated memory step; a dropped `--by`, `--revision`, reservation condition or policy check; a weakened or skipped test; code that refuses, flags or reports self-approval. At the end of US4: `git diff main --stat -- src/` lists only `src/wiki_studio/schema/WIKI_MAINTAINER.md` and `src/wiki_studio/__init__.py`; `git diff main -- pyproject.toml` is the version line; `git diff main -- docs/quickstart-memkernel.md` is the two pins; `git diff main -- docs/compatibility.md eval/` is empty; the only changed test files are the new module, `tests/test_cli_contract.py` (148) and `tests/integration/test_quickstart_memkernel.py` (58-59); `wiki-studio --help` and every verb's `--help` are byte-identical to `main`; exit codes 0 and 2..11 unchanged and 1 fatal lint.
- **FR-026 (issue #69, D9)**: `automation.json` (written at approval) carries `pr.closes: [69]`, so the build PR body closes #69; the PR body also names memkernel #104 and #109 as the counterpart's resolving PRs. No other artifact (spec, plan, tasks, CHANGELOG, persona, docs, commit message) uses a closing keyword, and no other issue closes. After the merge the owner comments on memkernel #86 with the build PR's number. If at merge time the owner decides the release cannot be cut (circuit breaker, week 2), the owner drops `Closes #69` before merging, so #69 stays open until a release carries the change.

## Constraints

- **Guidance and tests only.** Under `src/wiki_studio/` only `schema/WIKI_MAINTAINER.md` changes, plus the version line of `__init__.py` in US4. No verb, flag, exit code, MCP tool, capability, API signature, format version, prompt, prompt document, fingerprint, linter rule or `approve` behaviour changes; `review_state` and the approval policy are untouched (D3, D11).
- **The page schema does not change.** No frontmatter key, page type or directory; `schema.version` stays 2; no ADR (D11).
- **No self-approval code in cycle 06** (D3): nothing refuses, flags or reports a page an agent approved; a `findings` kind for it may be a separate issue later and none is filed.
- **Standard library only; no network in tests.** No runtime dependency, no memkernel dependency in any group; the persona check reads package data and in-process parsers; the memkernel line is a pinned copy (D5).
- **Read-only elsewhere.** No edit to memkernel, code-copilot-team, `eval/` (the frozen persona copy is hash-pinned evidence, D12) or `docs/quickstart-memkernel.md` beyond its two pins; `docs/quickstart.md` and the other docs are unchanged except FR-020 and FR-021.
- **No restatement of memory steps** in the persona (FR-012); the persona links memkernel's template instead.
- **Each phase is true on its own diff.** No file written in a phase states later-phase work as done: the persona of US1 does not refer to "Memory tools"; tests land in US3 and check only what US1 and US2 wrote; README, `docs/mcp-adapter.md`, the CHANGELOG and the version move only in US4.
- **Contracts.** CLI exit codes 0 and 2..11 keep their meaning and 1 stays fatal lint; `promoter.py` stays the only writer into the wiki; `WikiLock` untouched.
- **Python 3.11–3.13;** the test module uses only standard-library `argparse`, `shlex`, `re`, `contextlib`, `io`, `importlib.resources` and `unittest`.
- **Gate.** `poetry run ruff check src/ tests/ eval/ examples/ conformance/ && poetry run ruff format --check src/ tests/ eval/ examples/ conformance/ && poetry run mypy src/ && poetry run pytest -q -p no:cacheprovider --cov=wiki_studio --cov-fail-under=92` stays green at every phase; every new source file carries the EGOGE / Apache-2.0 header.
