---
pitch_id: 71-conflict-callouts
title: "Conflict callouts: a fixed on-page form for a disagreement between sources, and a model-free finding that reports open, one-sided and dangling ones"
appetite: 2w
bet_status: bet
cycle: "05"
circuit_breaker: "Core is S1, S2 and the wiki-studio half of S4: the documented callout form with ADR-0004, the model-free findings for matched, one-sided and dangling callouts, and the tests that an open conflict still approves and that memkernel's page parser keeps the callout. They ship alone if the cycle runs out. End of week 1: if S2 is not downhill, D6 shrinks to the cases structural lint does not catch and that need no read of the target's frontmatter (a callout that names no wiki page, a non-page target, the page itself), dropping the superseded case, and the live memkernel import case in S4 is cut in favour of the copied-parser test, stated in the CHANGELOG. End of week 2: S3's docs ship as far as they are true; nothing ships that describes an unbuilt kind. Never, to save time: put a model or a backend on any path from findings, approve or review_state; add a structural-lint or approve rule that refuses a page because it carries a callout; add a frontmatter key, a runtime dependency, an exit code or a new MCP tool; bump schema.version or findings_version without a decision record; edit memkernel; weaken or skip a test."
shaped_by: "pitch-shaper (Claude Code) for gosha70"
shaped_date: 2026-11-05
---

<!-- Shape-Up pitch. Origin: https://github.com/gosha70/wiki-studio/issues/71 (no comments on 2026-11-05). -->
<!-- specs/retros/cooldown-after-04.md (candidate 3) lists #71 as a possible small-batch pitch. This pitch shapes the issue; it does not replace it. -->

# Pitch: Conflict callouts

## Problem

When two sources disagree, the claim on a wiki page is uncertain. Nothing
on the page says so, and nothing reports it later. Three places in the
package touch the case, and none gives it a form:

1. `src/wiki_studio/schema/WIKI_MAINTAINER.md` lines 117-123 tell the
   curator to open an `open-questions/` entry "describing the
   contradiction and what would resolve it". The affected pages carry no
   mark, so a reader of either page does not see the disagreement.
2. The only check for disagreement is `contradiction` in
   `health_lint._check_contradictions` (lines 318-368). It sends page
   pairs to a backend. Without one it returns nothing, so `findings`
   says it "never appears" (`findings.py` lines 7-9;
   `docs/knowledge-contract.md`, Findings).
3. `schema/lint-rules.md` lines 161-162 list "cross-page contradictions"
   as something the linter does not check.

So a recorded disagreement has no fixed form. Nothing deterministic tells
a curator, or memkernel's session-start curation report, which
disagreements are still open, which were marked on one page only, or which
name a page that is gone.

## Findings from the code

wiki-studio was read at main `7f931b9` on 2026-11-05. memkernel was read,
read-only, at tag `v0.6.0` and main `61639e5` (0.7.0). These facts drive
the decisions and the rabbit holes.

1. **A frontmatter list does not survive memkernel.** memkernel's
   `_parse_frontmatter` (`src/memkernel/wiki/pages.py` lines 52-86, the
   same at `v0.6.0` and main) keeps top-level scalars and the `sources:`
   list only. Run on a page with `disputes:` and one list item, both
   versions return `extra == {'disputes': ''}` and render
   `disputes: ""`. The item is lost. ADR-0002 already found that a
   single-line scalar is the only form both parsers keep, and one scalar
   cannot name several pages and their sources.
2. **A body callout passes through memkernel as text.** Governed import
   retains `f"{page.title}\n\n{page.body}"` as the memory's content
   (`sync.py` `_retain_page`, main line 885), so the callout travels with
   the claim into recall. Export skips every memory tagged `wiki` (main
   line 262; `v0.6.0` line 178) and never overwrites an existing page,
   so memkernel never writes a callout back. memkernel's parse and render
   of a page with a callout keep it byte for byte. The one difference
   after re-render is the blank line after the closing `---`, which
   happens with or without a callout.
3. **memkernel 0.7.0 tolerates a new finding kind.** Its session-start
   curation report (`wiki/curation.py`) keeps only kinds with a non-zero
   count. It ranks a kind missing from `CURATION_KIND_ORDER` (lines
   52-59) after the known ones (`_rank`, lines 218-220). It does not
   refuse the kind. memkernel 0.6.0 does not call `findings`.
4. **The structural link rule already covers a broken callout link.** A
   `[text](other.md)` inside a callout is an ordinary local link. A
   missing target is fatal (`lint._link_violation`: "broken intra-wiki
   link"), and `promote` lints the staged tree. The patch-set format has
   no delete action (`create`, `update`, `append-log`, `append-index`;
   `docs/patch-set-format.md` line 76). Through the gate, then, the
   reachable "dangling" cases are a target that carries `superseded_by`
   (the page stays on disk, ADR-0002) and a callout that names no wiki
   page at all. A deleted or renamed target appears only after an edit
   outside the gate.
5. **`approve` gates on structural lint only.** `_lint_for_approval`
   calls `lint_wiki` (`promoter.py` line 2143). A finding never refuses
   an approval. So "a page with an open conflict can still be approved"
   holds as long as no callout rule enters structural lint.
6. **Callouts do not disturb the other checks.** The prose scanner skips
   lines that start with `>` (`lint-rules.md` lines 118-120). A callout's
   link counts as an inbound edge for `weak-orphan` and
   `missing-cross-link`, and for reachability, as any link does.
   `prose_lint.open_fence` and `closes_fence` (lines 76 and 93) already
   give a line-based, fence-aware scan, so an example callout inside a
   code fence can be ignored.
7. **The findings contract is built to grow.** `counts` "names every kind
   this build reports, zero included" and consumers "read keys by name"
   (`docs/knowledge-contract.md`, Findings). `FINDINGS_FORMAT_VERSION` is
   1 (`contract.py` line 87). `tests/test_findings.py` asserts that a
   fixture produces every kind in `FINDING_KINDS` (line 56). A new kind
   therefore needs a fixture case, not a new test shape.
8. **The MCP tool needs no change.** The `findings` tool returns
   `api.findings(...).as_dict()` (`mcp_adapter/tools.py` lines 281-283),
   and `docs/mcp-adapter.md` documents its result as "`findings --json`'s
   object". It lists no kind by name.
9. **Packaged schema edits cause no drift.** The fingerprint hashes only
   project overrides of `citation-rules.md`, `ingest-rules.md` and
   `page-types.md`, never packaged copies (`docs/knowledge-contract.md`,
   "The schema documents and the fingerprint"). Those three documents are
   the schema excerpts in the ingest prompts (`prompt.py` lines 154-156,
   228-230). A form documented in packaged `citation-rules.md` therefore
   reaches the prompts with no drift and no prompt code change. A wiki
   with its own override, such as code-copilot-team's, sees the form only
   after it syncs.
10. **ADR-0001 is the precedent for a body convention.** It registered
    an optional `Avoid:` body line in `glossary/index.md`, reported a
    refused form as the `avoid-format` finding rather than a lint
    violation, and did not bump `schema.version`. Version 2 came later,
    with ADR-0002's frontmatter keys.
11. **No page uses callout syntax today.** At `7f931b9`,
    `git grep '> \[!'` finds nothing in this repository. code-copilot-team's `knowledge/wiki/`
    has none either. The form starts with no existing uses to migrate.

## Appetite

**2w** (D1, decided by the owner), one bet. 2w is the smallest appetite the
pitch format allows, and the work fits it with room. For an LLM executor
the work content is about 11-16 hours across five scopes:

| Scope | Estimate |
|-------|----------|
| S1 The form, documented, and ADR-0004 | 2-3h |
| S2 The model-free check in `findings` | 4-6h |
| S3 Surfaces and the reference docs | 1.5-2h |
| S4 Approval and memkernel import unaffected | 2-3h |
| S5 Release | 1-2h |

The wall-clock budget is set by review, not by code:

- **Review rounds.** The external reviewer reviews the pitch PR, the spec
  and the build. A merge needs the `reviewed` label on the reviewed head
  (`.github/workflows/review-gate.yml`), and each new commit removes it.
- **ADR-0004.** It touches the page contract shared with memkernel, so
  the reviewer reads it against memkernel's parser.
- **The release.** The owner cuts it by the steps in the header of
  `.github/workflows/release.yml`.

Why not 4w: nothing here needs memkernel to change, there is no new verb
or schema key, and the check is one read-only pass over page bytes.

Planned order:

- **Week 1:** S1 and S2 together, since the documented example is a test
  input for S2. Then S4's wiki-studio tests.
- **Week 2:** S3, S4's memkernel import case, review, S5.

## Solution shape

A body convention, one read-only check and the docs. No frontmatter key,
no new verb, flag, exit code, MCP tool or dependency. No change to
structural lint, `approve`, `review_state` or the prompts' code.

```
two pages whose sources disagree
  concepts/a.md:  > [!conflict] Disagrees with [B](b.md)          ─┐
                  > This page: issue 12 (3 retries). That page: PR 22 (5).   │ promoted together,
  concepts/b.md:  > [!conflict] Disagrees with [A](a.md)          ─┘ one patch-set
                  > This page: PR 22 (5 retries). That page: issue 12 (3).

findings (no backend, no lock, reads bytes)
  open-conflict        a.md, b.md   one per matched pair
  conflict-one-sided   a.md, c.md   a.md names c.md; c.md names nothing back
  conflict-dangling    a.md         names a missing, superseded or non-page target, or no page

resolution: one patch-set removes both callouts, adds the deciding source
to `sources:` of the page that keeps the claim, and appends a log line
```

**The form (S1).** A blockquote callout, `> [!conflict]`, on **both**
pages. Its first wiki-page link names the other page. Its text names the
sources each side cites, by the entries in each page's `sources:`. It may
sit anywhere in the body outside fenced code. Obsidian renders it as a
callout. GitHub and other renderers show a plain blockquote. The form is
documented once in `citation-rules.md` and used by the curator loop in
`WIKI_MAINTAINER.md`. ADR-0004 records it as an optional body convention.

**The check (S2).** `findings` scans each content page in scope line by
line, outside fenced code. It reads each callout's other page, resolves
it as the link rule does, and pairs the callouts. The result is three
kinds (D5). Each uses the existing `Finding` shape, `severity: warning`
and the existing `--paths` scoping: a finding touching the scope is kept
and lists only its in-scope pages.

**What "open" means (D4).** A callout on a page is an open disagreement.
There is no "resolved" mark on the page. Resolving removes both callouts
in one promoted patch-set, with the deciding source cited, so the
receipt, the archived plan and `log.md` keep the history.

## Scopes

Build order: S1 and S2 start together. S3 and S4 need S2's kind names.
S5 needs the others.

### S1: The form, documented, and ADR-0004, ~2-3h

- **ADR-0004, "Conflict callout".** Context: issue #71, finding 1
  (memkernel drops list keys), finding 10 (the ADR-0001 precedent).
  Decision: the optional callout form of D2 and D3, the resolution rule
  of D4, no frontmatter key, `schema.version` stays 2 and
  `findings_version` stays 1 (D11). Why not: a frontmatter list (finding
  1), a scalar key (one page only), a dedicated H2 section (D2), a
  "resolved" mark on the page (D4). Consequences: wikis with project
  schema overrides see the form after they sync (finding 9).
- **`citation-rules.md`.** A new section, "When sources disagree": the
  form with one example pair, what each line holds, where it may sit, and
  the resolution rule.
- **`WIKI_MAINTAINER.md`.** The curator loop marks a disagreement between
  two pages with the callout pair in one patch-set and resolves it by D4.
  The Escalation section keeps `open-questions/` for a gap that spans more
  than two pages or has no sources yet (D16).
- **`lint-rules.md`.** The "cross-page contradictions" bullet (lines
  161-162) says the linter still does not detect them, and that a marked
  disagreement is reported by `findings` (S2).

### S2: The model-free check in `findings`, ~4-6h

- **Scan.** A small function, in `findings.py` or a sibling module
  imported only by it, reads each page in scope through the existing
  wiki boundary (`read_live_page`). It matches the marker line
  case-insensitively, with an optional Obsidian fold sign (`+` or `-`),
  and skips fenced code with `prose_lint.open_fence` / `closes_fence`.
  The callout runs over the following `>` lines. Its first `.md` link
  names the other page and is resolved as `health_lint` resolves
  intra-wiki links.
- **Pairing and kinds (D5, D6).** One `open-conflict` per unordered pair
  of pages that name each other. One `conflict-one-sided` per callout
  whose target is a page with no callout naming it back. One
  `conflict-dangling` per callout whose target is missing, is not a wiki
  page, is the page itself or carries `superseded_by`, or that names no
  wiki page. The description names the other page and, for a dangling
  callout, the reason.
- **Constants.** The kinds join `FINDING_KINDS` (so `counts` names them,
  zero included). The marker is a named constant, not a repeated string.
- **Tests (fixtures in `tests/fixtures/`).** The issue's acceptance one
  by one: a matched pair gives exactly one `open-conflict`; a one-sided
  and a dangling callout each give their kind; no callout gives no
  finding. Also: a superseded target; a callout inside a code fence (not
  counted); `--paths` scoping of a pair; the CLI text and `--json` output;
  and the existing stand-in test that `findings` is handed no backend.
  The example pair in `citation-rules.md` is extracted and run through the
  scan, so the documented form and the check cannot drift (the retro rule
  that every shown example gets a real check).
- **The resolution rule (D4), one check per part.** (a) *Both pages in
  one patch-set:* the documented resolution patch-set (two `update` edits
  and one `append-log`) is promoted and `findings` then reports nothing
  for the pair; a patch-set that removes only one callout leaves
  `conflict-one-sided`, which is why the rule asks for both. (b) *The
  deciding source is cited:* the promoted page that keeps the claim has
  the deciding source in `sources:` (asserted on the fixture; the rule
  itself is a `citation-rules.md` line, since `findings` reads no
  history). (c) *The log line's fixed form:* `citation-rules.md` gives
  it, and the test asserts `log.md` ends with exactly that line.
  `fact_warnings` on a resolution are expected: `propose` and `ingest`
  record in `plan.json` the backticked identifiers and numbers the
  removed callout text drops (`ingestor_multi.write_patch_set_dir`).
  They are advisory, never an exit code, and the test asserts the
  resolution still promotes.

### S3: Surfaces and the reference docs, ~1.5-2h

- `api.findings` docstring and the `findings` CLI help list the new kinds.
- `docs/knowledge-contract.md`, Findings: three table rows, and a
  sentence that kinds may be added within `findings_version: 1` and are
  read by name. The "`contradiction` never appears" note stays and points
  to the callout for a recorded disagreement.
- README, `wiki-studio findings`: the kinds sentence.
- `docs/mcp-adapter.md` needs no change (finding 8). One adapter test
  asserts that the `findings` tool's `counts` names the new kinds.
- `CHANGELOG.md` `[Unreleased]`, Added: the form, ADR-0004 and the three
  kinds.

### S4: Approval and memkernel import unaffected, ~2-3h

- **Approval (wiki-studio side, core).** A page in a matched pair
  promotes, `approve` records it, and `review_state` reads `approved`.
  `lint` and `lint --health --strict` pass on that wiki, since D7 keeps
  the kinds out of health lint. This is the issue's acceptance line
  "a page with an open conflict can still be approved".
- **memkernel's parser (core).** A test copies memkernel's
  `_parse_frontmatter`, `parse_page` and `render_page` with a citation,
  as `tests/test_avoid_roundtrip.py` does. The copy's header names the
  source exactly: `src/memkernel/wiki/pages.py` at tag `v0.6.0`, lines
  20 (`_FRONTMATTER_RE`), 45-110 (`_unquote`, `_parse_frontmatter`,
  `parse_page`) and 113-142 (`_quote`, `render_page`). It stays pinned
  to that tag even if the circuit breaker cuts the live import case,
  because the claim it backs is about memkernel 0.6.0. It asserts that the callout
  stays in the body, the frontmatter is unchanged and the parse adds no
  extra key.
- **Governed import (cut first).** One case in the existing
  `tests/integration/` job, against the memkernel release that job pins.
  An approved page with a callout is imported by governed `wiki_import`,
  and the memory's content holds the callout.

### S5: Release, ~1-2h

- The version in `pyproject.toml` and `src/wiki_studio/__init__.py`
  moves to the number D14 settles, and so do the `==X.Y.Z` pins on
  `docs/quickstart-memkernel.md`. The CHANGELOG heading gets the tag
  date. The steps are those in the header of `release.yml`.
- `docs/compatibility.md` gets a row only if the S4 import case ran
  against a pinned memkernel. It names the green run.
- Issue #71 is closed by the build PR's merge, not by the pitch PR. The
  pitch PR body does not use a closing keyword.

## Rabbit holes

- **A Markdown parser.** CommonMark blockquotes, lazy continuation lines,
  nested quotes and callouts inside lists could each take a day.
  *Workaround:* a line-based scan, like the prose scanner. The marker
  must start a line (after up to three spaces and `>`). The documented
  form is the one form checked. Every other shape gives a
  `conflict-dangling` finding ("names no wiki page") or no callout at
  all, and its known limits are listed in `citation-rules.md`.
- **Checking the sources text.** Parsing "This page: … That page: …"
  against each page's `sources:` entries means matching free text to
  YAML. *Workaround:* D3. The sources lines are a documented convention
  for the reader. Only the marker and the link are checked.
- **Proving a resolution was cited.** "Removed with the resolution cited"
  is a fact about history, and `findings` reads the current bytes only.
  *Workaround:* D4. The curator rule and the review state it. The receipt
  and `log.md` record it. No check reads history.
- **Three-way and many-way disagreements.** One page that disagrees with
  two pages, or a disagreement across five. *Workaround:* one callout per
  other page, each paired on its own. Five or more pages go to
  `open-questions/` (D16).
- **Turning the backend `contradiction` check into something it is not.**
  It is tempting to have the backend write callouts, or to let `findings`
  trust its output. *Workaround:* untouched. The backend check stays in
  `lint --health --backend`, and model output reaches a page only through
  a reviewed proposal (D9).

## No-gos

- No frontmatter key, page type or directory. No `schema.version` bump.
- No rule in structural lint or `approve` that refuses a page because it
  carries a callout. A broken link inside one stays fatal through the
  existing link rule, unchanged.
- No model, backend or lock on any path from `findings`, `approve` or
  `review_state`. No change to `_check_contradictions`.
- No new verb, flag, MCP tool, capability or exit code. 0 and 2..11 keep
  their meaning, and 1 stays fatal lint. `promoter.py` stays the single
  writer into the wiki.
- No runtime dependency. The package stays standard-library only.
- No prompt code change. The form reaches the prompts through packaged
  `citation-rules.md`.
- No automatic insertion or removal of callouts. They are written and
  removed by a curator or an agent through a reviewed proposal.
- No memkernel code or doc edits from this repository, and no change to
  code-copilot-team's schema overrides.
- No history check of resolutions and no "resolved" mark.
- Coverage stays at or above 92 percent, and every executable artifact
  is run at least once before commit.

## Decisions

D1-D7, D9, D11 and D14 were **decided by the owner** on 2026-11-05, each
the recommended default. The others are settled by the issue or by the code and are listed
so the spec does not reopen them.

- **D1. Appetite (decided by the owner, 2026-11-05: the default).** Default **2w**, the smallest the
  format allows; the work content is about 11-16 hours. Alternative: none
  smaller exists; 4w is not justified (see Appetite).
- **D2. The marker's form (decided by the owner, 2026-11-05: the default).** Default **a
  `> [!conflict]` callout in the body of both pages**, as the issue
  proposes. Alternatives: (a) a frontmatter list such as `disputes:`,
  which memkernel 0.6.0 and 0.7.0 flatten to `disputes: ""` (finding 1);
  (b) a single-line scalar key, which survives but names one page and no
  sources; (c) a dedicated `## Disagreements` H2 section, which adds a
  section the page-type templates do not list and that renderers do not
  show as a warning.
- **D3. What is machine-checked (decided by the owner, 2026-11-05: the default).** Default **the
  marker line and the callout's first wiki-page link**. The sources each
  side cites are written in the callout's text, in a documented shape
  ("This page: … That page: …"), and are not parsed. Alternative: also
  require the two sources lines, reporting a missing one as a fourth kind,
  `conflict-format`, the way ADR-0001 reports `avoid-format`.
- **D4. Unresolved and resolved (decided by the owner, 2026-11-05: the default).** Default **every
  callout present is open. Resolving removes both callouts in one
  promoted patch-set, adds the deciding source to `sources:` of the page
  that keeps the claim, and appends a `log.md` line**
  (`- YYYY-MM-DD — resolve <slug> (<page-type>): conflict with <other>, decided by <source>`).
  This follows the issue. Alternative: keep a `> [!conflict-resolved]`
  mark on the page, which adds state the check must parse and duplicates
  the receipt and the log.
- **D5. Kind names and severity (decided by the owner, 2026-11-05: the default).** Default
  **three kinds, `open-conflict` (one per matched pair, both pages),
  `conflict-one-sided` and `conflict-dangling`, all `warning`**. The
  issue asks that the one-sided and dangling cases are "each reported
  with their kind". Alternatives: (a) one kind, `open-conflict`, with the
  case in the description (the issue's "for example"), which a host
  cannot count by case; (b) a new `info` severity for the matched pair,
  which adds a second severity value to a contract that has one.
- **D6. What "dangling" covers (decided by the owner, 2026-11-05: the default).** Default **a
  target that is missing, is not a wiki page, is the page itself or
  carries `superseded_by`, or a callout that names no wiki page**. The
  superseded case is the one the gate can produce (finding 4).
  Alternative: a missing target only, as the issue words it. Through the
  gate, that case appears only after an edit outside it.
  *Overlap with lint, stated:* a missing `.md` target inside the wiki is
  already a fatal structural violation (`lint.py` line 253, "broken
  intra-wiki link"), so `promote` refuses it and the finding can only
  see it on a wiki edited outside the gate, where `lint` fails too. The
  finding keeps it because it says what lint's message does not: the
  disagreement has lost its other side. The cases lint passes, and the
  reason the kind exists, are a non-page target (a `.md` link outside the
  wiki or a non-`.md` target is a source reference to lint), the page
  itself, a superseded target, and no page link.
- **D7. Where the kinds run (decided by the owner, 2026-11-05: the default).** Default **`findings`
  only**, like `superseded-still-indexed` and `no-page-id`. Then
  `lint --health --strict`, the CI gate, does not fail a wiki for
  recording a disagreement, and `approve` is untouched. Alternative:
  `conflict-one-sided` and `conflict-dangling` also in `lint --health`,
  so a strict CI gate fails on a half-recorded disagreement; the matched
  pair stays findings-only.
- **D8. Structural lint enforces no callout structure (settled).** The
  issue's acceptance requires that an open conflict can be approved, and
  `approve` gates on structural lint (finding 5). A broken link stays
  fatal through the existing link rule.
- **D9. Prompts (decided by the owner, 2026-11-05: the default).** Default **no prompt code
  change**. Stated plainly: a model ingest is not asked to write
  callouts; curators write them, following the curator loop in
  `WIKI_MAINTAINER.md` that S1 updates. This is a scope choice, not a
  gap. The form documented in packaged `citation-rules.md` is
  already in the ingest prompt's schema excerpts (finding 9), so a model
  may propose a callout. That proposal is reviewed like any content, and
  `findings` reads only promoted bytes. Alternative: an explicit
  instruction in the ingest prompt to emit callouts when its sources
  disagree, with a test-backend fixture.
- **D10. Where the form is documented (settled).** `citation-rules.md`
  (a disagreement is between sources), referenced from
  `WIKI_MAINTAINER.md` and `lint-rules.md`. `page-types.md` is unchanged,
  because the form applies to every page type.
- **D11. Contract versions (decided by the owner, 2026-11-05: the default).** Default
  **`schema.version` stays 2 and `findings_version` stays 1, with no new
  capability**. The convention is optional and body-only (ADR-0001
  precedent, finding 10). The kinds are additive, and `counts` naming
  them is the discovery (finding 7). Alternative: bump `findings_version`
  to 2 and add a `conflict-callout` capability, which tells a strict
  consumer outright, at the cost of a version a host must accept.
- **D12. MCP (settled).** No adapter change (finding 8). One test asserts
  that the tool reports the kinds.
- **D13. memkernel (settled).** No memkernel change is needed: import
  carries the callout as memory text, and export never writes it back
  (finding 2). Evidence: S4's copied-parser test (core) and the governed
  import case (cut first).
- **D14. Release number (decided by the owner, 2026-11-05: the default).** Default **0.9.0**: new
  user-visible output (three `findings` kinds that a host's `counts`
  now carries) and a new ADR-recorded page convention. Alternative:
  **0.8.2**, since no schema key, verb or API signature changes. 0.3.1
  shipped an Added section as a patch release. The `[Unreleased]` Fixed
  entry (the composition quickstart's install line) ships with either.
- **D15. Scope of the scan (settled).** Content pages in the default
  review set; the root `index.md` and `log.md` are not scanned. A
  callout's target is resolved against the whole wiki even under
  `--paths`, so a scoped run still sees the page that answers back.
- **D16. Open questions stay (settled).** The callout pair marks a
  disagreement between two pages whose sources conflict. An
  `open-questions/` entry stays the form for a gap with no sources or
  across more than two pages. A callout may link one.

## Circuit breaker

Core is S1, S2 and the wiki-studio half of S4. That covers the documented
form with ADR-0004, the three model-free kinds, and the tests that an
open conflict still approves and that memkernel's parser keeps the
callout. They ship alone if the cycle runs out. The triggers, in order:

1. **End of week 1.** If S2 is not downhill, D6 drops the superseded
   case and keeps the cases structural lint does not catch (no page
   link, a non-page target, the page itself); S4's live memkernel
   import case is cut. The
   copied-parser test is the evidence, and the CHANGELOG says so.
2. **End of week 2.** S3's docs ship as far as they are true. Nothing
   ships that describes a kind the build does not report.
3. **Never, to save time:** put a model or backend on any path from
   `findings`, `approve` or `review_state`; add a structural-lint or
   `approve` rule that refuses a page because it carries a callout; add a
   frontmatter key, a runtime dependency, an exit code or an MCP tool;
   bump `schema.version` or `findings_version` without a decision record;
   edit memkernel; weaken or skip a test.

"Exhausted" means two working weeks have passed. A third review round on
one scope is not exhaustion. It is an escalation to the owner, who
chooses a fix session, a cut from the list above, or a hold.

## Questions for the owner

Asked by the main session on 2026-11-05; the owner chose the default for
all ten: D1 2w; D2 a `> [!conflict]` body callout on both pages, linking
the other page with a markdown link; D3 the marker line and its first
page link only; D4 resolving removes both callouts in one patch-set,
cites the deciding source in `sources:` and appends a log line; D5 three
kinds (`open-conflict`, `conflict-one-sided`, `conflict-dangling`), all
`warning`; D6 dangling covers a missing target, a non-page, the page
itself, a superseded target and a callout with no page link; D7
`findings` only; D9 no prompt change; D11 `schema.version` 2,
`findings_version` 1, no new capability; D14 release 0.9.0.

## Bet log

| Date | bet_status | Note |
|------|------------|------|
| 2026-11-05 | shaping | Pitch drafted from wiki-studio #71 (no comments) and cooldown-after-04 (candidate 3). wiki-studio read at main 7f931b9; memkernel read at tag v0.6.0 and main 61639e5. memkernel's page parser was run on a list-key page and a callout page in its own virtualenv to confirm findings 1 and 2. |
| 2026-11-05 | shaping → shaped | 5 scopes, 2w. Core: S1 (form, ADR-0004), S2 (three model-free kinds), S4's wiki-studio half. Cut first: S4's live memkernel import case, then D6's superseded case. 16 decisions; D1-D7, D9, D11 and D14 open for the owner with defaults, not yet asked (AskUserQuestion was unavailable to the shaping agent). |
| 2026-11-05 | shaped (decided) | Owner answered D1-D7, D9, D11, D14 in the main session: every default. memkernel's parser at v0.6.0 (`src/memkernel/wiki/pages.py:52`) rechecked: only `sources:` is read as a list, so a list key is lost and the body callout passes through. |
| 2026-11-05 | shaped (revised before the PR) | The four points the reviewer named ahead of review, settled in the text: `conflict-dangling`'s overlap with lint's fatal broken-link rule stated (D6) and the circuit-breaker fallback moved to the cases lint passes; the copied memkernel parser pinned by file, line ranges and tag `v0.6.0` (S4); "curators write callouts, ingest is not asked to" (D9); one check per part of the resolution rule, with `fact_warnings` expected (S2). |
| 2026-11-05 | bet | Bet for cycle 05. |
