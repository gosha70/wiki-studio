# Reusable engineering patterns: a research spike (issue 54)

This is a study for [issue 54](https://github.com/gosha70/wiki-studio/issues/54).
It is a research spike, and its deliverable is a recommendation — docs and a
template, a separately specified enhancement, or no change — not a schema, a
page type or a deduplication service.

The inventory below reads wiki-studio at the build branch's base commit,
`43aab76000ccb7acf8d5cda1ae5cdd929e452f72` (0.10.0 released). Every file and
line it cites is that commit's, and each opens at the line cited.

## What the study measures, and what it does not

It measures what wiki-studio already does with a reusable pattern:

- whether a `decision` page, unchanged, has a slot for each of issue 54's
  seven fields — intent, applicable constraints, canonical implementation
  link, rejected alternatives, validation evidence, owner and status, and
  revisit criteria;
- what the real verbs do while a candidate pattern travels from a pending
  proposal, through a lint-gated promotion, to an approval bound to the bytes
  a reviewer saw, and what a later edit does to that approval;
- whether `find` puts the right pattern page in front of a reader for the
  task the pattern claims to help with, with each of the two rankers;
- whether the existing model-free pair signals expose near-duplicate
  patterns, with no merge and no edit;
- what the existing checks report when a pattern's cited source changes or
  the pattern itself is superseded.

It does **not** measure whether an agent chooses better with patterns in
reach. That needs agent runs at historical commits and is the subject of
issue 75; nothing here measures agent behaviour, and no result depends on a
model — every claim is computed from code and files.

Nothing under `src/wiki_studio/` changes: no verb, flag, exit code, MCP
tool, `findings` kind, lint rule, prompt, persona, packaged schema document,
frontmatter key or page type is added or changed.

## Fit map: issue 54's seven fields against today's `decision` page

A pattern record, as issue 54 defines it, has seven fields. The table maps
each to the existing `decision` template — its four H2 sections and the
universal frontmatter (`page-types.md` 104-121 and 11-25) — and says what
checks the field, if anything, and what a round trip through memkernel's
wiki bridge carries. The bridge keeps a page's title, body, single-line
frontmatter scalars and `sources:`; the approval record is not page text and
does not cross it.

File references are repository-relative; `page-types.md` abbreviates
`src/wiki_studio/schema/page-types.md`.

| Issue 54 field | Where it can live today | What checks it | What reaches memkernel |
|---|---|---|---|
| Intent | `## Decision`, the section's prose (`page-types.md` 109) | No content check. Prose lint advises on sentence length only (`src/wiki_studio/prose_lint.py` 22-27); approval binds the bytes the approver saw but checks nothing about their content (`src/wiki_studio/review.py` 1-21) | Body |
| Applicable constraints | `## Context` (`page-types.md` 110) | Nothing: structural lint has no body-section rule (`src/wiki_studio/lint.py` 5-23) | Body |
| Canonical implementation link | A `sources:` entry with `path:` and `sha:` (`page-types.md` 18-20); a body link where the evidence has no commit | Structural lint requires `sources:` (`lint.py` 372-373); `stale-claim` checks that the path exists, never that `sha:` is current (`src/wiki_studio/health_lint.py` 110-155) | `sources:`; a body link only as body text |
| Rejected alternatives | `## Alternatives considered`, one bullet per option (`page-types.md` 111) | Nothing | Body |
| Validation evidence | `## Consequences` prose — the tests and confidence stated there — and `sources:` entries | Only `sources:` presence (`lint.py` 372-373) and the path-existence check (`health_lint.py` 110-155) | Body and `sources:` |
| Owner and status | Owner: the approver named in the approval record by `--by` (`src/wiki_studio/api.py` 783-789; `src/wiki_studio/cli.py` 322) — there is no maintainer slot. Status: the frontmatter `status:` scalar, `draft`, `stable` or `deprecated` (`page-types.md` 16) | Approval names who approved which bytes, not a maintainer (`review.py` 1-21); `findings` reports the review state (`src/wiki_studio/findings.py` 70-83). `status:` never approves a page (`page-types.md` 46-49) | The `status:` scalar; the approver is not a page field and does not cross |
| Revisit criteria | A `## Consequences` body line (`page-types.md` 112) | Nothing: neither lint nor `findings` reads it | Body |

## Behaviour inventory

One paragraph per behaviour, with file and line at the commit above. The
paragraphs describe what the code does; none quotes it.

**Page types and the `decision` template.** Every page carries exactly one
page type, and the type names the directory the page lives in; the
structural linter checks the placement (`page-types.md` 3-5; `lint.py`
349-370). A `decision` page lives under `decisions/` and has four required
H2 sections — `## Decision`, `## Context`, `## Alternatives considered` and
`## Consequences` — with status and date in the frontmatter rather than in
`## Status` or `## Date` H2s (`page-types.md` 104-121). Those four sections
are the only body slots a pattern convention can use without a schema
change, and no code requires them (see structural lint, below).

**`propose --from` and `promote`.** `propose --from DIR` reads a directory
laid out like the wiki and writes a pending proposal, adding a `page_id` to
every page it creates (`cli.py` 542-568, `--from` at 550; `page-types.md`
36-39); `api.propose` is at `api.py` 600. `promote` (`api.py` 721) validates
a patch-set against a staged copy of the wiki — per-edit semantics and the
structural linter — under the wiki lock, and it is the only code path that
writes into the wiki directory: it commits only the paths the patch-set
names and rolls back on an exception (`src/wiki_studio/promoter.py` 5-14,
22-33). A candidate pattern is therefore a pending proposal first, and it
enters the wiki only when a promotion passes validation.

**Approval and `review_state`.** An approval is one immutable record per
decision under `<wiki>/.audit/approvals/`, keyed by the page key, the sha256
of the reviewed revision and the policy hash (`review.py` 1-21).
`approve --revision` takes the sha256 that `read --json` printed and refuses
a page whose live bytes differ (`api.py` 783-811; `cli.py` 302-322,
`--revision` at 315-320). `review_state` reads the verified records only —
it takes no lock and calls no model — and reports a page approved, stale,
policy-changed, superseded or unapproved from bytes; frontmatter never makes
a page approved (`api.py` 818-834; `review.py` 19-20).

**Citations.** `sources:` is required on every page except `index` and `log`
(`page-types.md` 27). An entry is `path:` with `sha:`, or `issue:`, or
`url:` with `retrieved:` (`page-types.md` 18-23). The structural linter
checks only that the list is present and non-empty (`lint.py` 372-373); the
`path:` entries are what `stale-claim` later looks for on disk, below.

**Structural lint (no section rule) and prose lint (advisory, 25-word
limit).** Structural lint runs six checks — frontmatter present and
well-formed, a known `page_type`, a matching unique slug, directory
placement, `sources:` presence, and link resolution with reachability
(`lint.py` 5-23); the rules page lists the same checks and no
body-section rule (`page-types.md` 196-212), so nothing in code requires a
`## Decision` or any other H2. Prose lint is a separate advisor: checks 1-5
cover sentence length, semicolons, filler phrases, `## Summary` and
`## Key ideas` length, and the glossary avoid-term lock
(`src/wiki_studio/prose_lint.py` 22-27). A sentence is limited to 25 words
(`src/wiki_studio/schema/__init__.py` 119), counted by `count_words`
(`prose_lint.py` 618-620), and check 4 reads only `## Summary` and
`## Key ideas` (`prose_lint.py` 644). Its findings are advisory: a body
convention costs nothing in lint, and nothing enforces it either.

**`stale-claim` checks path existence only.** `_check_stale_claims`
(`health_lint.py` 110-155) resolves each cited `path:` against the project
root (`health_lint.py` 141) and reports a page whose path does not exist. It
says in the code that it does not compare `sha:` with git and does not fetch
URLs (`health_lint.py` 115-119), so a source that changed in place is
reported by nothing.

**`findings`: twelve kinds, none for similarity.** `FINDING_KINDS`
(`findings.py` 70-83) lists twelve: `stale-claim`, `weak-orphan`,
`missing-cross-link`, `avoid-format`, `unapproved`, `approval-stale`,
`approval-policy-changed`, `superseded-still-indexed`, `no-page-id`,
`open-conflict`, `conflict-one-sided` and `conflict-dangling`. None compares
two pages for similarity. `findings` reads only — no lock, no backend, no
model (`findings.py` 188; `api.py` 837-839; `cli.py` 420).

**Discovery: index-linked candidates, two rankers, the FTS5 fallback,
superseded pages ineligible.** `index.md` is read first, and the candidates
are the pages it links (`src/wiki_studio/discovery.py` 4-7, 410-424), so a
page the index does not link is never considered. Two rankers order the
eligible pages, `index-first` and `fts5` (`discovery.py` 49-52); without
FTS5 in this Python's SQLite the `fts5` ranker falls back to `index-first`
and says why (`discovery.py` 12-13; the probe is `Fts5Probe` 150-155 and
`fts5_available` 158-162). A page carrying `superseded_by` is ineligible
with reason `superseded` (`discovery.py` 278, 78). `find` runs the
selection only — no backend, nothing written (`api.py` 1158-1207;
`cli.py` 587-598).

**Supersession.** `superseded_by` is an optional frontmatter key naming the
wiki-relative page that replaces this one; the target must exist and must
not itself be superseded (`page-types.md` 40-42; `lint.py` 268-289, 388).
`review.superseded_by` reads the key (`review.py` 175), discovery drops the
page from every result (`discovery.py` 278), and `findings` reports
`superseded-still-indexed` for a superseded page that `index.md` still links
(`findings.py` 157-184).

**The conflict callout.** A page may mark a disagreement with another page
by a body callout: a blockquote whose marker line names the other page, in
the form `> [!conflict] Disagrees with [<title>](<path>)`, with no new
frontmatter key, page type or directory (`docs/adr/0004-conflict-callout.md`
40-62; the form at 46-52). `findings` has three kinds that read it:
`open-conflict`, `conflict-one-sided` and `conflict-dangling`
(`findings.py` 66-68, 80-82).

## Compatibility

Three coordination issues are closed, and this study changes none of their
contracts. #38 (closed 2026-10-30) and #51 (closed 2026-10-28) are
wiki-studio's release tracks, and memkernel #48 (closed) is the wiki-bridge
side.
Revision preconditions, containment, citations, locking, receipts and the
human gates stay as released: the study adds no package code, no schema
change and no ADR.

memkernel #57 (closed by gosha70/memkernel#117) and memkernel #123 (closed
by gosha70/memkernel#127) are the runtime side. #57 is memkernel's own
research spike on preserving and retrieving implementation decisions; #123
is its revalidation rule, which flags a decision that cites a changed file
and still returns it. The study compares wiki-studio's reporting against
that rule and does not change memkernel.
