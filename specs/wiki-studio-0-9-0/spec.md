---
spec_mode: full
feature_id: wiki-studio-0-9-0
risk_category: feature
status: approved
date: 2026-11-06
---

# Spec: wiki-studio 0.9.0 — conflict callouts

<!-- Project constitution: shared/skills/ — copilot-conventions, coding-standards, safety -->

Design references (read before building): `CLAUDE.md`; the bet pitch
`specs/pitches/71-conflict-callouts/pitch.md` (cycle 05, building; reviewed
and approved in PR #85 at 462e679 with two points deferred to this spec, see
FR-010), which is the shaping record and carries owner decisions D1-D7, D9,
D11 and D14 (2026-11-05, every default) and the settled D8, D10, D12, D13,
D15 and D16; its origin, wiki-studio issue #71 (no comments on 2026-11-05)
and `specs/retros/cooldown-after-04.md` (candidate 3); ADR-0001 (`docs/adr/`)
for the decision-record form and the body-convention precedent, ADR-0002 for
the memkernel parser finding; the 0.8.0 and 0.8.1 bundles for this bundle's
form. In this repository: `src/wiki_studio/findings.py` (the module
docstring's "`contradiction` never appears" 7-9; the kind constants 52-60;
`FINDING_KINDS` 62-72; `Finding` 84-99; `FindingsResult` 102-118;
`_page_findings` 146-173, which reads each page through `read_live_page` and
`superseded_by`; `findings` 176-210 with the scope rule at 192-199 and
`counts` at 202-204), `health_lint.py` (`_MD_LINK_RE` 57,
`\]\(([^)]+\.md)(?:#[^)]*)?\)`; `_list_wiki_pages` 68-84;
`_intra_wiki_links_from` 86-107, which resolves a target from the page's
directory and drops one that escapes the wiki; `_check_contradictions`
318-370, a no-op without a backend at 332-333), `lint.py` (`list_pages` 90;
`md_links` 189 and `md_page_links` 208-210; `_link_violation` 218-262 with
"broken intra-wiki link" at 253 for a `.md` target inside the wiki and
"broken source reference" at 254 for any other target), `prose_lint.py`
(`_FENCE_RE` 71, `open_fence` 76-90, `closes_fence` 93-105), `review.py`
(`superseded_by` 175-177, `read_live_page` 180, `default_review_pages`
685-688: every page the structural linter lists except the root `index.md`
and `log.md`), `api.py` (`findings` 833-846, whose docstring lists the
kinds), `cli.py` (the `findings` parser 413-430 whose help lists the kinds;
`_do_findings` 774-785, text form `[kind / severity] pages: description`),
`mcp_adapter/tools.py` (`findings` 281-283 returning `as_dict()`),
`contract.py` (`FINDINGS_FORMAT_VERSION = 1` 87; `CAPABILITIES` 108-120),
`schema/__init__.py` (`SCHEMA_VERSION = 2` 96; `SUPERSEDED_BY_KEY` 104;
`PROMPT_SCHEMA_DOCUMENTS` 112: `ingest-rules`, `page-types`,
`citation-rules`), `schema/citation-rules.md` (129 lines; "When a source
disappears" 104-117, "Inline pointers in prose" 119-129),
`schema/WIKI_MAINTAINER.md` ("The canonical curator loop" 30-61, "What you
must never do" 63-77, "Escalation" 117-123), `schema/lint-rules.md` (the
prose scanner skips blockquotes 118-120; "Cross-page contradictions"
161-162), `ingestor_multi.py` (`write_patch_set_dir` 209, `fact_warnings`
231 and 307), `docs/patch-set-format.md` (the four actions at 76, no delete;
`fact_warnings` at 80), `docs/knowledge-contract.md` (Findings 372-414, the
kinds table 401-411, "`contradiction` never appears" 413), `docs/mcp-adapter.md`
(the `findings` tool is documented as `findings --json`'s object, no kind
named), `README.md` (`wiki-studio findings` 248-262; `# 0.8.1` at 26),
`docs/quickstart-memkernel.md` (`==0.8.1` pins at 27 and 38),
`docs/compatibility.md` (tested pairs 7-13), `tests/test_findings.py`
(`_no_model_check` 22-26; `build_fixture_wiki` 30-46;
`test_every_kind_is_produced_on_a_fixture_wiki` 48-66, which asserts the
fixture produces every kind in `FINDING_KINDS` at 56; `TestNoBackend`
137-156), `tests/test_avoid_roundtrip.py` (the copied-function header form
21-22 and 30-31), `tests/test_mcp_adapter.py` (`test_findings_and_review_state_shapes`
349), `tests/integration/test_memkernel_clean_install.py` (`HAS_MEMKERNEL`
30; `WikiImporter(self.service, self.wiki)` 175), `.github/workflows/ci.yml`
(`memkernel-compat` 86-120 with `MK_VERSION: "0.6.0"` at 102),
`.github/workflows/release.yml` (the release steps in its header 9-25),
`CHANGELOG.md` (`[Unreleased]` with one Fixed entry; `[0.8.1] — 2026-11-04`).
In memkernel, read-only, at tag `v0.6.0`: `src/memkernel/wiki/pages.py`
(`_FRONTMATTER_RE` 20, `WikiPage` 24-34 a pydantic model, `_unquote` 45-49,
`_parse_frontmatter` 52-86 reading top-level scalars and the `sources:` list
only, `parse_page` 89-110, `_quote` 113-117, `render_page` 120-142),
`src/memkernel/wiki/sync.py` (`_retain_page` 413, the memory content
`f"{page.title}\n\n{page.body}"` at 427); at main fbc28a4 (0.7 work):
`src/memkernel/wiki/curation.py` (`CURATION_KIND_ORDER` 52, `_rank` 218
ranking an unknown kind after the known ones). Every citation above was
checked against `main` at c909e2b on 6 November 2026 (the bet branch 2ce3c15
adds only the pitch and its hill chart); where the pitch's line numbers
differ, the numbers here are the current ones.

## Why

When two sources disagree, the claim on a wiki page is uncertain, and
nothing on the page or in any report says so. `WIKI_MAINTAINER.md` tells the
curator to open an `open-questions/` entry, so the affected pages carry no
mark and a reader of either page does not see the disagreement. The only
check for disagreement, `contradiction`, needs a backend, so `findings`, the
model-free report a host runs at session start, never reports one. The
structural linter lists cross-page contradictions as something it does not
check. So a recorded disagreement has no fixed form, and nothing
deterministic tells a curator, or memkernel's session-start curation report,
which disagreements are open, which were marked on one page only, and which
name a page that is gone.

This release gives the disagreement a form and a report. The form is a body
convention, a `> [!conflict]` callout on both pages, each linking the other
on its marker line and naming the sources each side cites; it is optional,
documented in the packaged `citation-rules.md`, recorded in ADR-0004, and
reaches the ingest prompts through the schema excerpts with no prompt code
change. The report is three model-free kinds in `findings`: `open-conflict`
(one per matched pair), `conflict-one-sided` and `conflict-dangling`. Nothing
else moves: no frontmatter key, no `schema.version` or `findings_version`
bump, no new verb, flag, exit code, MCP tool, capability or dependency, no
structural-lint or `approve` rule about callouts, and no model on any path
from `findings`. The pitch's eleven findings from the code hold at c909e2b;
the three that shape the requirements are: memkernel's frontmatter parser
keeps top-level scalars and `sources:` only, so a frontmatter list is lost
and a body callout passes through as text (FR-001, FR-020); the structural
link rule already makes a missing `.md` target inside the wiki fatal, so
through the gate a dangling callout is one whose target is superseded, is
not a content page, is the page itself, or that names no page (FR-007); and
`approve` gates on structural lint only, so a page with an open conflict
still approves as long as no callout rule enters structural lint (FR-019).

## User Scenarios

### US1: The form, documented, and ADR-0004 (Priority: HIGH)

**Given** two wiki pages whose cited sources disagree, a curator following `WIKI_MAINTAINER.md`, and a wiki whose project schema override of `citation-rules.md` has not synced
**When** the curator marks the disagreement, resolves it later, and reads the packaged schema documents and ADR-0004
**Then** `citation-rules.md` gives one callout form (the `> [!conflict]` marker line carrying the link to the other page, then the two sources lines), its placement, one complete example pair of pages, the resolution rule (both callouts removed in one patch-set, the deciding source added to `sources:` of the page that keeps the claim, one `log.md` line in a fixed form) and the scan's known limits; the curator loop marks a two-page disagreement with the pair and keeps `open-questions/` for a gap across more than two pages or with no sources yet; `lint-rules.md` says the linter still does not detect contradictions and that a marked disagreement is reported by `findings`; ADR-0004 records the decision, the alternatives and that `schema.version` stays 2 and `findings_version` stays 1; and the overriding wiki sees the form only after it syncs

### US2: The model-free check in `findings` (Priority: HIGH)

**Given** a wiki with a matched callout pair, a one-sided callout, callouts whose targets are missing, not a content page, the page itself or superseded, a marker line with no page link, a callout inside a code fence, two callouts on one page naming the same other page, a callout whose text links a source document before the page link, and a `--paths` scope naming one page of a pair
**When** `wiki-studio findings`, `findings --json`, `api.findings` or the MCP `findings` tool runs, with no backend installed and backend resolution patched to fail
**Then** exactly one `open-conflict` names the matched pair, one `conflict-one-sided` names the one-sided callout and its target, one `conflict-dangling` per dangling callout names the page and the reason, the fenced callout and the repeat count nothing extra, the source-document link does not change which page is "the other page", the scoped run keeps the pair's finding listing only the in-scope page, `counts` names the three kinds (zero included) in `findings_version: 1`, no callout gives no conflict finding, and the documented example pair from `citation-rules.md` produces exactly one `open-conflict`; resolving by the documented patch-set clears the pair while removing only one callout leaves `conflict-one-sided`

### US3: Surfaces and the reference docs (Priority: MEDIUM)

**Given** the `api.findings` docstring, the `findings` CLI help, `docs/knowledge-contract.md`, README, `docs/mcp-adapter.md` and the CHANGELOG
**When** a host, a curator or a reviewer reads what `findings` reports
**Then** each surface lists the three kinds where it lists kinds; the contract's Findings table has three rows and says kinds may be added within `findings_version: 1` and are read by name; its "`contradiction` never appears" note points to the callout for a recorded disagreement; `docs/mcp-adapter.md` is unchanged and one adapter test asserts the tool's `counts` names the kinds; and the CHANGELOG's `[Unreleased]` Added lists the form, ADR-0004 and the kinds

### US4: Approval and memkernel import unaffected (Priority: HIGH for the wiki-studio half; the live import case is cut first)

**Given** a page in a matched pair promoted through the gate, memkernel's page parser at tag `v0.6.0`, and the pinned memkernel release of the `memkernel-compat` job
**When** the page is approved, `lint` and `lint --health --strict` run on that wiki, the page is parsed and rendered by the copied `v0.6.0` functions, and an approved page with a callout is imported by governed `wiki_import`
**Then** `approve` records it and `review_state` reads `approved`; `lint` and `lint --health --strict` exit 0; the callout stays in the body byte for byte, the frontmatter is unchanged and the parse adds no key; and the imported memory's content holds the callout

### US5: Release 0.9.0 (Priority: MEDIUM)

**Given** the four phases above landed, or cut by the circuit breaker in the pitch's order
**When** the version moves to 0.9.0 and the owner cuts the release by `release.yml`'s steps
**Then** `pyproject.toml`, `src/wiki_studio/__init__.py`, README's version comment and the `==` pins on `docs/quickstart-memkernel.md` all say 0.9.0; the CHANGELOG `[0.9.0]` section lists the form, ADR-0004, the three kinds, the carried Fixed entry and any cut by name; `docs/compatibility.md` gains a row only if the governed import case ran against a pinned memkernel; exit codes, the page schema, the dependency list and `promoter.py`'s single-writer rule are unchanged; and issue #71 closes by the build PR's merge

## Requirements

### US1 — the form, documented, and ADR-0004

- **FR-001 (ADR-0004, "Conflict callout")**: `docs/adr/0004-conflict-callout.md`, in ADR-0001's form (Status, Date, Issue #71, Feature `specs/wiki-studio-0-9-0/` with its FR numbers; Context; Decision; Why not; memkernel round trip, as observed; Requirement on memkernel; Consequences). Context: issue #71; memkernel's `_parse_frontmatter` keeps top-level scalars and the `sources:` list only, so a frontmatter list such as `disputes:` renders back as `disputes: ""` (pitch finding 1; ADR-0002); ADR-0001 is the precedent for an optional body convention reported through `findings`, not refused by lint (finding 10). Decision: the optional callout form of FR-002 with the marker-line link rule of FR-010; the resolution rule of FR-004; no frontmatter key, page type or directory; `schema.version` stays 2 and `findings_version` stays 1, no new capability (D11); the three kinds of FR-007 run in `findings` only (D7); structural lint and `approve` have no callout rule (D8). Why not: a frontmatter list (finding 1); a single-line scalar key (names one page and no sources); a dedicated `## Disagreements` section (D2); a `> [!conflict-resolved]` mark (D4); a fourth `conflict-format` kind checking the sources lines (D3). memkernel round trip: governed import retains `title + body`, so the callout travels with the claim into recall; export skips memories tagged `wiki` and never overwrites an existing page, so memkernel never writes a callout back; memkernel 0.7.0's curation report ranks an unknown kind after the known ones and does not refuse it (finding 3); the copied-parser test of FR-020 is the evidence. Requirement on memkernel: none new beyond ADR-0001's (an existing page's body passes through unchanged). Consequences: wikis with a project override of `citation-rules.md` see the form after they sync (finding 9); curators write callouts, ingest is not asked to (D9).
- **FR-002 (the form, in `citation-rules.md`)**: The packaged `src/wiki_studio/schema/citation-rules.md` MUST gain one `## When sources disagree` section between "When a source disappears" and "Inline pointers in prose" that documents exactly one form. **The marker line**: a blockquote line `> [!conflict] Disagrees with [<title>](<relative path to the other page>.md)`, where the marker is `[!conflict]` (case-insensitive, optionally followed by Obsidian's fold sign `+` or `-`, as in `[!conflict]-`) and the first `.md` link on that same line names the other page, as a relative wiki-page link resolved from the page's directory, the way every intra-wiki link is. **The sources lines**: the following `>` lines read `> This page: <the entries this page's sources: cite, as written there>. That page: <the entries the other page cites>.`; they are for the reader and are not parsed (D3). **Placement**: anywhere in the body outside fenced code; one callout per other page, and a page that disagrees with two pages carries two callouts (FR-010); the same callout, pointing back, goes on the other page in the same patch-set. **Both pages**: a callout on one page only is reported as `conflict-one-sided`. **Rendering**: Obsidian shows a callout, GitHub and other renderers a plain blockquote. **What is checked** (D3): the marker line and its first `.md` link, nothing else; a marker line with no `.md` link is reported as `conflict-dangling` ("names no wiki page"). **The example**: one complete pair of pages (frontmatter and body, each citing a different source for the same claim, each carrying the callout naming the other), given as two fenced `markdown` blocks, each introduced by a line that ends with the page's wiki-relative path in backticks (`concepts/retry-budget.md`, `decisions/retry-policy.md` or similar); FR-013 extracts and runs this example, so its shape is fixed. **The resolution rule** (FR-004). **Known limits** (the rabbit hole's workaround): the scan is line-based, not a CommonMark parser; the marker must start a line after at most three spaces and the `>`; a callout inside a list item, a lazy-continuation blockquote, a nested quote or an HTML block is not recognised; a `.md` link that is not on the marker line is not the other page.
- **FR-003 (`WIKI_MAINTAINER.md` and `lint-rules.md`)**: The curator loop MUST gain, after step 5 (Cite) or as a numbered sub-rule of it, the two-page case: when the sources of two pages disagree, mark both pages with the callout pair of `citation-rules.md` in one patch-set, and resolve by its rule; the Escalation section (117-123) MUST keep `open-questions/` for a gap that spans more than two pages or has no sources yet, and say a callout may link such an entry (D16). `lint-rules.md`'s "Cross-page contradictions" bullet (161-162) MUST say the linter still does not detect them, and that a disagreement marked with the callout pair of `citation-rules.md` is reported by `wiki-studio findings` (the three kinds, by name). `page-types.md` is unchanged (D10). No other schema document changes, and the fingerprint does not move (the packaged copies are not hashed; finding 9).
- **FR-004 (the resolution rule, D4)**: `citation-rules.md` MUST state: every callout present is an open disagreement, and there is no resolved mark. Resolving is one promoted patch-set that (a) removes the callout from both pages (two `update` edits), (b) adds the deciding source to `sources:` of the page that keeps the claim (and may rewrite that page's claim), and (c) appends one `log.md` line of exactly the form `- YYYY-MM-DD — resolve <slug> (<page-type>): conflict with <other-slug>, decided by <source>` where `<source>` is the deciding `sources:` entry as written (`issue: 12`, `pr: 22`, `path: ...` or `url: ...`). The section says the receipt, the archived plan and `log.md` keep the history, and that `fact_warnings` on the two updates are expected and advisory (the removed callout text drops backticked identifiers and numbers; `docs/patch-set-format.md` 80). No check reads history (D4's rabbit hole).

### US2 — the model-free check in `findings`

- **FR-005 (module and constants)**: A new module `src/wiki_studio/conflicts.py` holds the scan; `findings.py` is its only importer (a test asserts no other module under `src/wiki_studio/` imports it). It defines `CONFLICT_MARKER = "[!conflict]"` and one compiled marker regex built from it (`^ {0,3}>[ \t]*\[!conflict\][+-]?(?=[ \t]|$)`, case-insensitive), the only places the marker text appears in the package. The three kind constants live beside the others in `findings.py` (`KIND_OPEN_CONFLICT = "open-conflict"`, `KIND_CONFLICT_ONE_SIDED = "conflict-one-sided"`, `KIND_CONFLICT_DANGLING = "conflict-dangling"`) and are appended to `FINDING_KINDS` in that order, so `counts` names them, zero included, and `findings_version` stays 1 (D11). The result shape (`Finding`, `FindingsResult`) does not change; `severity` is `warning` for all three (D5). The module imports only the standard library and `wiki_studio`; `tests/test_package_boundaries.py`'s standard-library scan covers it.
- **FR-006 (the scan)**: For every page in the default review set (`default_review_pages`: every page the structural linter lists except the root `index.md` and `log.md`; D15) that does not carry `superseded_by` (a superseded page's text is replaced, so its callouts are not read), the scan reads the page once through `read_live_page` and walks the body after the frontmatter line by line, skipping fenced code with `prose_lint.open_fence` and `closes_fence` (non-indented form, as the prose scanner). A line the marker regex matches is a callout's marker line. Its target is the first `health_lint._MD_LINK_RE` match on that same line, the first link whose target ends in `.md` (a link that does not end in `.md` is skipped; FR-010), with the fragment dropped, resolved from the page's directory as `_intra_wiki_links_from` resolves (`(page_dir / target).resolve()` relative to the resolved wiki directory; an escape, or a target with a URL scheme such as `https://`, is "outside the wiki"). The callout's remaining `>` lines are not read. The scan records, per page, the ordered list of (line number, raw target, resolved target or None). The whole review set is always read, whatever `pages` scope `findings` was given, so a scoped run still sees the page that answers back (D15). The scan takes no lock, no backend, writes nothing, and runs inside `findings` only: `lint --health`, `lint --health --strict`, `approve` and `review_state` never call it (D7, D8).
- **FR-007 (pairing and the three kinds, D5, D6)**: From the recorded callouts, each page `P` has a set of targets; a raw target that repeats on `P` counts once (FR-010). For each (`P`, target): if the marker line has no `.md` link, the target resolves outside the wiki, the resolved target is not a file, is not in the default review set (the root `index.md`, `log.md`, a page under `schema/`, `scripts/` or `.audit/`), is `P` itself, or carries `superseded_by`, the callout is **dangling**: one `conflict-dangling` with `pages == (P,)` and a description naming the marker line number, the raw target and the reason in these words: `names no wiki page`, `points outside the wiki`, `names a missing page`, `names <rel>, which is not a content page`, `names the page itself`, `names <rel>, which is superseded by <superseded_by value>`. Otherwise the target `Q` is a content page; if `Q`'s own targets include `P`, the unordered pair `{P, Q}` is **matched**: exactly one `open-conflict` with `pages == (min(P, Q), max(P, Q))` (string order) and a description saying both pages mark a conflict with each other and naming the resolution rule; if not, the callout is **one-sided**: one `conflict-one-sided` with `pages == (P, Q)` and a description saying `Q` carries no callout naming `P` back, and that the curator adds the matching callout or removes this one. A dangling callout never pairs, so the superseded `P`'s own callout naming `Q` is not read (FR-006) and `Q`'s callout naming `P` is `conflict-dangling` (`names <P>, which is superseded by …`). Findings are listed after the existing kinds, in the order `open-conflict` (by `pages`), `conflict-one-sided` (by `pages`), `conflict-dangling` (by page, then line), so the output is deterministic.
- **FR-008 (scoping)**: The existing scope rule of `findings` (192-199) applies unchanged to the three kinds: with `pages=None` every finding is reported; with an explicit list a finding is kept when at least one of its `pages` is in scope and lists only its in-scope pages, so `findings --paths concepts/a.md` on a matched pair reports one `open-conflict` with `pages == ("concepts/a.md",)`, and `pages_checked` counts the scope. A finding's description still names both pages.
- **FR-009 (API, CLI and MCP surfaces unchanged)**: `api.findings`'s signature, `findings`'s flags, the `--json` key set, the text form and the MCP tool's result do not change; the new kinds appear through `counts` and `findings` only. No new exit code: a completed run exits 0 whatever it finds, and `--paths` naming a missing page still exits 5. `tests/test_findings.py::TestNoBackend` (backend resolution patched to raise, `_check_contradictions` replaced by `_no_model_check`) MUST still pass with a fixture that carries callouts.
- **FR-010 (the two points from the PR #85 review)**: (a) **The link sits on the marker line.** The other page is the first `.md` link on the `> [!conflict]` marker line itself, never a link on a later `>` line; a callout whose marker line has no `.md` link and whose next line links a page is `conflict-dangling` ("names no wiki page"), and a callout whose marker line links the other page while its sources line links a source document (`[spec](../../docs/spec.md)`) pairs with the other page, not the document. A web link before the page link is skipped unless it ends in `.md`: `> [!conflict] see [x](https://example.com/a) and [B](b.md)` names `B`, and a marker line whose first `.md` link is `https://example.com/b.md` is `conflict-dangling` ("points outside the wiki"). Fixture cases: all four. (b) **Repeats count once.** Two callouts on one page whose marker lines name the same other page are one target: with a callout back on the other page they give exactly one `open-conflict` and no `conflict-one-sided`; without one they give exactly one `conflict-one-sided`. A page in conflict with two pages carries one callout per other page, and each pairs on its own: `A` naming `B` and `C`, with `B` and `C` each naming `A`, gives exactly two `open-conflict` findings and nothing else. Fixture cases: all three.
- **FR-011 (fixture wiki)**: `tests/fixtures/conflicts/` holds a managed wiki (a root manifest, `index.md` linking every page, `log.md`) whose pages cover, each by name: a matched pair; a one-sided callout; a callout naming a missing page (this wiki is read in place by `findings` and never promoted, since structural lint refuses the broken link, which is the overlap D6 states); a callout naming the root `index.md`; a callout naming the page itself; a callout naming a page that carries `superseded_by`, which itself carries a callout back; a callout inside a code fence; a marker line with no `.md` link; the four FR-010(a) cases; the three FR-010(b) cases; a marker with the fold sign and in upper case (`[!CONFLICT]+`); a page with no callout. The test lists the expected findings for this wiki as one literal, compared whole (`kind`, `pages`, and the reason words of FR-007 in each `conflict-dangling` description).
- **FR-012 (tests, the issue's acceptance one by one)**: `tests/test_conflict_callouts.py` MUST assert, on the fixture of FR-011 and on wikis built through `ApprovalCase.create`: a matched pair gives exactly one `open-conflict` naming both pages; a one-sided callout gives exactly one `conflict-one-sided` with `pages == (P, Q)`; each dangling case gives one `conflict-dangling` with its reason words; no callout gives no finding of the three kinds; a fenced callout is not counted; the FR-010 cases; `--paths` scoping of a pair (FR-008); `findings` (text, with `[open-conflict / warning]`) and `findings --json` through `cli.main` with `counts` naming the three kinds and `findings_version == 1`; the deterministic order of FR-007; `conflicts.py` imported only by `findings.py`; and `lint --health --strict` on the FR-011 wiki minus its broken-link page reports no conflict kind (D7). `tests/test_findings.py::build_fixture_wiki` gains a matched pair, a one-sided callout and a dangling callout so `test_every_kind_is_produced_on_a_fixture_wiki` keeps asserting every kind in `FINDING_KINDS` and the `counts` equality at 66 holds.
- **FR-013 (the documented example is a test input)**: A test reads the packaged `citation-rules.md`, takes the `## When sources disagree` section, extracts its first two fenced `markdown` blocks and the backticked `.md` path on the line introducing each, writes them as those pages into a fresh wiki (with an `index.md` linking both), and asserts `api.findings` reports exactly one `open-conflict` naming both and nothing of the other two kinds, and that `lint` passes on that wiki. If the section, the two blocks or the paths are missing the test fails naming what is missing. The documented form and the check cannot drift.
- **FR-014 (the resolution rule, one check per part)**: On a promoted wiki whose matched pair was created through `api.propose` and `api.promote`: (a) **both pages in one patch-set**: a patch-set of two `update` edits (each carrying `base_sha256`) that remove the callouts, plus one `append-log` edit, promotes (exit 0 through the CLI, a receipt written) and `api.findings` then reports no finding of the three kinds for the pair; a patch-set that removes one callout only promotes and leaves exactly one `conflict-one-sided`; (b) **the deciding source is cited**: the promoted page that keeps the claim carries the deciding source in `sources:` (asserted on the fixture text; the rule is a `citation-rules.md` line, since `findings` reads no history); (c) **the log line's fixed form**: `log.md` ends with exactly the FR-004 line for the fixture's slugs and source. The two updates produce `fact_warnings` in `plan.json` (the removed callout text drops backticked identifiers or numbers), which the test asserts are present, advisory, and never an exit code.

### US3 — surfaces and the reference docs

- **FR-015 (docstring and CLI help)**: The `api.findings` docstring (833-846) and the `findings` parser help (416-420) MUST list `open-conflict`, `conflict-one-sided` and `conflict-dangling` beside the other kinds, with one clause saying what they report. The `findings.py` module docstring (3-19) lists them and keeps the sentence that `contradiction` never appears.
- **FR-016 (`docs/knowledge-contract.md`, Findings)**: The kinds table (401-411) MUST gain three rows: `open-conflict`, `warning`, "Two pages each carry a `> [!conflict]` callout naming the other (`citation-rules.md`, When sources disagree); one finding per pair"; `conflict-one-sided`, `warning`, "A callout names a page that carries no callout naming it back"; `conflict-dangling`, `warning`, "A callout names no wiki page, a page outside the wiki, a missing page, a page that is not a content page, the page itself, or a superseded page". One sentence after `counts`'s paragraph: kinds may be added within `findings_version: 1`; `counts` names every kind the build reports, so a consumer reads kinds by name and treats an unknown kind as a warning it does not classify. The note at 413 MUST keep "`contradiction` never appears" and add that a disagreement a curator has recorded is reported by the three conflict kinds. No `info` key, format version or capability changes (D11).
- **FR-017 (README and `docs/mcp-adapter.md`)**: README's `wiki-studio findings` section (248-262) MUST name the three kinds in its kinds sentence and link `citation-rules.md`'s section for the form. `docs/mcp-adapter.md` MUST NOT change (finding 8: the tool returns `findings --json`'s object and names no kind). `tests/test_mcp_adapter.py` gains one assertion, beside `test_findings_and_review_state_shapes` (349), that the `findings` tool's `counts` has the three keys (skipped without `mcp`, as the file's other tests).
- **FR-018 (CHANGELOG)**: `CHANGELOG.md` `[Unreleased]` MUST gain an Added section listing the form (one sentence with the marker line's shape), ADR-0004, and the three kinds with their severities, and a Notes line: no frontmatter key, `schema.version` 2 and `findings_version` 1 unchanged, no new verb, flag, exit code, MCP tool, capability or dependency, no structural-lint or `approve` rule, no prompt code change. The existing Fixed entry stays.

### US4 — approval and memkernel import unaffected

- **FR-019 (approval; the issue's acceptance line)**: A test MUST create a matched pair through `api.propose` and `api.promote` (so structural lint ran on the staged tree), `api.approve` both pages, and assert `review_state` reads `approved` for each; `lint` exits 0 and `lint --health --strict` exits 0 on that wiki (the kinds run in `findings` only, D7); and `api.findings` reports the one `open-conflict`. A second case promotes a page whose callout marker line has no `.md` link and asserts the promote succeeds (no structural rule about callouts, D8) while `findings` reports `conflict-dangling`. `git diff main -- src/wiki_studio/lint.py src/wiki_studio/promoter.py src/wiki_studio/review.py src/wiki_studio/prompt.py src/wiki_studio/health_lint.py src/wiki_studio/contract.py src/wiki_studio/schema/__init__.py src/wiki_studio/mcp_adapter/` MUST be empty at the end of the phase.
- **FR-020 (memkernel's parser, copied and pinned)**: `tests/test_conflict_memkernel_roundtrip.py` MUST copy, as `tests/test_avoid_roundtrip.py` does with a header naming the source, `_FRONTMATTER_RE` (line 20), `_unquote` (45-49), `_parse_frontmatter` (52-86), `parse_page` (89-110), `_quote` (113-117) and `render_page` (120-142) of `gosha70/memkernel` `src/memkernel/wiki/pages.py` at tag `v0.6.0`, each header reading "Copied from gosha70/memkernel src/memkernel/wiki/pages.py at tag v0.6.0, `<name>` lines <a>-<b> (citation verified <date>, see the spec FR-020). Test fixture only." `WikiPage` (a pydantic model at 24-34) is replaced by a standard-library dataclass with the same fields and defaults, named in the header as the one departure; the copied functions are otherwise verbatim. The pin stays `v0.6.0` even if FR-021 is cut, because the claim it backs is about memkernel 0.6.0. It asserts, for the FR-013 example pages and a page whose callout sits mid-body: `parse_page` returns a page whose `body` holds the callout lines byte for byte; `extra` holds no key the page's frontmatter did not carry and `sources` equals the page's entries; `render_page` of the parse keeps every frontmatter line (the only accepted difference is the blank line after the closing `---`, which memkernel adds with or without a callout); and `parse_page(render_page(parse_page(text)))` has the same `body`.
- **FR-021 (governed import; cut first)**: One case in `tests/integration/test_memkernel_clean_install.py` (skipped without memkernel, as the file's others): an approved page carrying a callout pair is imported by `WikiImporter(service, wiki).import_pages()` against the memkernel release the `memkernel-compat` job pins (`MK_VERSION: "0.6.0"`), and the imported memory's `content` holds the callout marker line. The job's install and import check are unchanged. If the circuit breaker cuts this case (end of week 1 with S2 not downhill), the CHANGELOG says the copied-parser test is the evidence and `docs/compatibility.md` gains no 0.9.0 row (FR-023).

### US5 — release 0.9.0

- **FR-022 (version)**: 0.9.0 in `pyproject.toml` (6) and `src/wiki_studio/__init__.py` (5) together (D14); README's `# 0.8.1` comment (26) and the `==0.8.1` pins on `docs/quickstart-memkernel.md` (27, 38) move to 0.9.0 (`release.yml` header step 1; the `quickstart-memkernel` job resolves the lines against the built wheel). `tests/test_cli_contract.py` reads `__version__` and needs no edit. CHANGELOG: the `[Unreleased]` entries (FR-018's Added and Notes, the carried Fixed entry) move under `[0.9.0]`, undated until the owner tags (the heading takes the tag's UTC date at release); any cut from FR-024 is named there.
- **FR-023 (compatibility)**: `docs/compatibility.md` gains a 0.9.0 with memkernel 0.6.0 row only if FR-021's case landed; the row names `memkernel-compat` and the import case, status pending until the owner names a green run on `main` after the build PR merges (as the 0.8.1 row did). Without FR-021 no row is added and the 0.8.1 row stands.
- **FR-024 (circuit breaker and the invariant audit)**: The build follows the pitch's cut order and never cuts US1, US2 or the wiki-studio half of US4 (FR-019, FR-020). End of week 1: if US2 is not downhill, FR-007 drops the superseded case and keeps the cases structural lint does not catch (no page link, outside the wiki, not a content page, the page itself; a missing target stays reported only because lint catches it first), and FR-021 is cut, stated in the CHANGELOG. End of week 2: US3's docs ship as far as they are true; nothing describes a kind the build does not report. Never: a model or backend on any path from `findings`, `approve` or `review_state`; a structural-lint or `approve` rule that refuses a page for carrying a callout; a frontmatter key, runtime dependency, exit code, MCP tool or capability; a `schema.version` or `findings_version` bump without a decision record; a memkernel edit; a weakened or skipped test. At the end of US5: `git diff main -- pyproject.toml` is the version line; `poetry run wiki-studio --help` and `findings --help` show no new flag; exit codes 0 and 2..11 unchanged, 1 fatal lint; the single-writer scans pass; `_check_contradictions` is byte-identical to `main`.
- **FR-025 (issue #71)**: `automation.json` carries `pr.closes: [71]` and the build PR body `Closes #71`; the pitch PR and this spec PR use no closing keyword. No other issue closes.

## Constraints

- **Standard library only.** `conflicts.py` imports `re`, `pathlib` and `wiki_studio`; no dependency is added; the base-install import scan and `build-check` stay green.
- **Contracts.** Exit codes 0 and 2..11 keep their meaning and 1 stays fatal lint; `api.findings`'s signature is unchanged; `findings --json`'s key set is unchanged; `findings_version` stays 1 and `schema.version` stays 2; no new `info` key or capability; the receipt, patch-set, approval and ingest-log formats are untouched.
- **The page schema does not change.** No frontmatter key, page type or directory; the callout is an optional body convention recorded in ADR-0004, as ADR-0001 recorded `Avoid:`.
- **Single writer and no model.** `promoter.py` stays the only module that writes into the wiki; `findings`, `approve` and `review_state` reach no backend; `_check_contradictions` and the prompts' code are unchanged; `WikiLock` stays non-reentrant and `findings` takes no lock.
- **Structural lint and `approve` are untouched.** A broken link inside a callout stays fatal through the existing link rule; no rule refuses or requires a callout.
- **No memkernel edits** from this repository and no change to code-copilot-team's schema overrides; memkernel is read at tag `v0.6.0` for the copied functions and installed only in the `memkernel-compat` job's environment.
- **Python 3.11–3.13;** the scan is line-based and its limits are documented (FR-002), not parsed around.
- **Gate.** `poetry run ruff check src/ tests/ eval/ examples/ conformance/ && poetry run ruff format --check src/ tests/ eval/ examples/ conformance/ && poetry run mypy src/ && poetry run pytest -q -p no:cacheprovider --cov=wiki_studio --cov-fail-under=92` stays green; every new source file carries the EGOGE / Apache-2.0 header; coverage does not fall below 92 percent.
