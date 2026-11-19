<!-- Drafted by the issue 54 study (eval/patterns/report.md, question 1).
Not filed by the build. The owner files it from this text and replaces
{report_permalink}, {trace_permalink} and {docs_permalink} with permalinks
to eval/patterns/report.md, eval/patterns/results/trace.json and
docs/patterns.md at the commit that added them (never a branch path). -->

# Carry the pattern template into the packaged page-types.md

## Problem

A pattern convention now works: the issue 54 study wrote fourteen decision
pages — twelve real records and two successors — using only existing
frontmatter keys and the four existing H2 sections, and the pages pass
structural lint and prose lint with no package change. `docs/patterns.md`
states the convention, and it is live on GitHub at merge. The packaged
`page-types.md` — what users and ingest prompts read offline, and what
reaches them only through a release — carries the `decision` template
without the pattern convention. A user who never opens `docs/` gets no
pattern guidance.

## Evidence

- The study wrote 14 pages (12 memkernel #57 records and 2 successors); they
  lint clean and pass prose lint, six of issue 54's seven fields have an
  existing slot, and the seventh (owner and status) splits between the
  approval record and the frontmatter's `status:` (report, question 1).
- The Y-statement form the study tested is three sentences within prose
  lint's 25-word limit, recorded per page in `manifest.json` (3 sentences for
  a record page, 1 for a successor).
- The convention adopted no new frontmatter key, page type, directory, H2 or
  lint rule; it lives in body lines of the existing four sections.
- The study's lifecycle trace shows the same pages moving through propose,
  promote, approve, read, find and supersession with no package change
  (results/trace.json).
- Report: {report_permalink}. Trace: {trace_permalink}. Docs page:
  {docs_permalink}.

## Proposal

Add the optional pattern convention to the `decision` section of
`src/wiki_studio/schema/page-types.md`, matching `docs/patterns.md`: the
three-sentence Y-statement as the first paragraph of `## Decision`, the
`Applies when:` / `Does not apply when:` lines in `## Context`, the
`Revisit when:` line and evidence in `## Consequences`, and `sources:` with
`path:` + `sha:` for the canonical implementation. It is guidance, not a
lint rule: nothing new parses it and no frontmatter key is added. One
changelog line under the release that carries it; no version bump of its own
beyond that release.

## Out of scope

No new frontmatter key, page type, directory or H2; no lint, `findings` or
MCP change; no change to approval, discovery or the page schema version; no
change to memkernel; no automatic check that a page follows the convention.
