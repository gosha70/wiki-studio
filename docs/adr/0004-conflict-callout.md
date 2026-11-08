# ADR 0004: Conflict callout

- Status: accepted
- Date: 2026-11-07
- Issue: [#71](https://github.com/gosha70/wiki-studio/issues/71)
- Feature: `specs/wiki-studio-0-9-0/` (FR-001, FR-002, FR-004, FR-007, FR-020)
- Implementation: 0.9.0. The three `findings` kinds are built by
  `src/wiki_studio/conflicts.py` and `findings.py`, and the parse and render
  round trip is tested by `tests/test_conflict_memkernel_roundtrip.py`. This
  record states the decision they implement.

## Context

The page schema is a published contract shared with memkernel's
`WikiExporter` and `WikiImporter` and with code-copilot-team's wiki.
`CLAUDE.md` requires a decision record for any change to it.

Issue #71: when two sources disagree, the claim on a wiki page is
uncertain, and nothing on the page or in any report says so.
`WIKI_MAINTAINER.md` sends the curator to `open-questions/`, so the affected
pages carry no mark. The only check for disagreement, `contradiction`, needs
a backend, so `findings`, the model-free report a host runs at session start,
never reports one. A recorded disagreement has no fixed form, and nothing
deterministic says which disagreements are open, which were marked on one
page only, and which name a page that is gone.

Two facts constrain the form:

- **memkernel keeps top-level scalars and `sources:` only.** Its
  `_parse_frontmatter` (`src/memkernel/wiki/pages.py` lines 52-86 at tag
  `v0.6.0`) drops the items of any other list. A page with `disputes:` and
  one list item parses to `extra == {"disputes": ""}` and renders back as
  `disputes: ""`. ADR-0002 found the same: a single-line scalar is the only
  frontmatter form both parsers keep.
- **ADR-0001 is the precedent for a body convention.** It registered an
  optional `Avoid:` body line in `glossary/index.md`, reported a refused form
  through `findings` (`avoid-format`) rather than refusing it in lint, and
  did not bump `schema.version`.

## Decision

A page MAY mark a disagreement with another page by a body callout. The
callout is optional. No frontmatter key, page type or directory changes, and
every existing page stays valid.

**The form** (`citation-rules.md`, "When sources disagree"). Both pages
carry a blockquote callout naming the other:

```markdown
> [!conflict] Disagrees with [Retry policy](../decisions/retry-policy.md)
> This page: issue: 12. That page: pr: 22.
```

- The marker is `[!conflict]`, case-insensitive, optionally followed with
  no space by Obsidian's fold sign `+` or `-`. It starts a line after at most three
  spaces and the `>`.
- The first `.md` link on the marker line names the other page. It is a
  relative wiki-page link resolved from the page's directory, as every
  intra-wiki link is. A link on a later line is never the other page.
- The sources lines (`> This page: … That page: …`) name the entries each
  side's `sources:` cites. They are for the reader and are not parsed.
- One callout per other page. The callout pointing back goes on the other
  page in the same patch-set.

**The resolution rule.** Every callout present is an open disagreement;
there is no resolved mark. Resolving is one promoted patch-set that removes
the callout from both pages, adds the deciding source to `sources:` of the
page that keeps the claim, and appends one `log.md` line:
`- YYYY-MM-DD — resolve <slug> (<page-type>): conflict with <other-slug>, decided by <source>`.
The receipt, the archived plan and `log.md` keep the history.

**The report.** `findings` gains three model-free kinds, all `warning`:

- `open-conflict`: two pages each carry a callout naming the other; one
  finding per pair.
- `conflict-one-sided`: a callout names a content page that carries no
  callout naming it back.
- `conflict-dangling`: a callout names no wiki page, a page outside the
  wiki, a missing page, a page that is not a content page (as defined in
  `citation-rules.md`, "When sources disagree"), the page itself, or a page
  that carries `superseded_by`. A superseded page's own callouts are not
  read.

**What does not move.**

- `schema.version` stays 2 and `findings_version` stays 1. The kinds are
  additive, and `counts` naming them is how a consumer discovers them. No
  new capability.
- The kinds run in `findings` only. `lint --health` and
  `lint --health --strict` do not report them.
- Structural lint and `approve` have no callout rule. A page with an open
  conflict approves. A broken `.md` link inside a callout stays fatal
  through the existing link rule, unchanged.
- No prompt code changes. The form reaches the ingest prompts through the
  packaged `citation-rules.md` excerpt.

## Why not

- **A frontmatter list** (`disputes: [b.md]` or a block list). memkernel's
  parser drops the items and renders `disputes: ""`.
- **A single-line scalar key.** It survives memkernel, but one scalar names
  one page and no sources.
- **A dedicated `## Disagreements` section.** It adds an H2 the page-type
  templates do not list, and renderers do not show it as a warning.
- **A `> [!conflict-resolved]` mark.** It adds state the check must parse,
  and it duplicates the receipt and `log.md`.
- **A fourth `conflict-format` kind checking the sources lines.** Matching
  free text against YAML entries is a parser this feature does not need.
  The marker line and its link are the only parts checked.

## memkernel round trip, as observed

From memkernel's code (`memkernel/wiki/pages.py` and `memkernel/wiki/sync.py`
at tag `v0.6.0`; `memkernel/wiki/curation.py` at tag `v0.7.0`):

- **Import keeps the callout.** Governed import retains
  `f"{page.title}\n\n{page.body}"` as the memory's content (`_retain_page`),
  so the callout travels with the claim into recall.
- **Export never writes a callout back.** The exporter skips memories tagged
  `wiki` and any target file that already exists.
- **A direct `parse_page` and `render_page` keeps the callout byte for
  byte.** It is body text. The parse adds no frontmatter key. The only
  difference after a re-render is the blank line after the closing `---`,
  which memkernel adds with or without a callout.
- **The curation report tolerates the new kinds.** memkernel 0.7.0's
  session-start curation report ranks a kind missing from
  `CURATION_KIND_ORDER` after the known ones (`_rank`) and does not refuse
  it. memkernel 0.6.0 does not call `findings`.

These observations come from reading that code. The parse and render
observation also has a test in this repository:
`tests/test_conflict_memkernel_roundtrip.py` (FR-020). It copies memkernel's
`pages.py` functions at tag `v0.6.0` as fixtures, citing their source lines.

## Requirement on memkernel

None new. ADR-0001's requirement covers it: any memkernel path that parses
and re-renders an existing wiki page passes the body through unchanged.

## Follow-up for memkernel

Open a memkernel issue to decide where `open-conflict`, `conflict-one-sided`
and `conflict-dangling` rank in the curation report's `CURATION_KIND_ORDER`.
Until then they rank after the known kinds. This is not assumed done in this
cycle. Tracking: no memkernel issue is open yet. The owner opens it, because
the build does not file issues in other repositories, and links it here.

## Consequences

- Curators write and remove callouts through reviewed proposals. Ingest is
  not asked to write them; a model may still propose one, and it is
  reviewed like any content.
- A host reads three more keys in `findings`'s `counts`, zero included.
- A wiki with a project override of `citation-rules.md`, such as
  code-copilot-team's, does not describe the form until it syncs from the
  packaged copy.
- `open-questions/` stays the form for a gap across more than two pages or
  with no sources yet. A callout may link such an entry on a sources line.
  An entry linked first on the marker line is read as the other page, like
  any content page, and is usually reported `conflict-one-sided`.
