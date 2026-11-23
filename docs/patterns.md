# Patterns: decision pages that carry reusable engineering guidance

A pattern page records a choice another person can reuse: why it was made,
where its canonical implementation and tests are, what was rejected, and when
to look again. It is an ordinary `decision` page — no new page type, no new
frontmatter key and no new section — with an optional convention inside its
four existing H2 sections.

The convention was written and tested by the issue 54 study on fourteen
decision pages — twelve real records and two successors — and every page
passed structural lint and prose lint; the lifecycle ran through the existing
verbs with no package change. The
[study's report](../eval/patterns/report.md) carries the evidence and the
limits.

Install wiki-studio as the [README's install section](../README.md#install)
describes.

## The template

```markdown
---
page_type: decision
slug: <slug>
title: <title>
status: stable
last_reviewed: <YYYY-MM-DD>
sources:
  - path: <the canonical implementation or its spec>
    sha: <the commit it was read at>
  - issue: <owner>/<repo>#<n>
---

## Decision

In the context of <situation>, we chose <choice>. We chose it over
<alternative>. The reason: <why>.

Chosen: <the canonical implementation, named>.

## Context

Requirement: <what the choice must satisfy>

Applies when: <the preconditions under which the pattern holds>

Does not apply when: <the look-alike case that is not this pattern>

## Alternatives considered

- <option>: <why it was rejected>

## Consequences

Revisit when: <the trigger that sends the page back for review>

Tests: <the test or verification outcome>

Confidence: <high, medium or low>: <why>
```

The first paragraph of `## Decision` is the Y-statement. Write it in three
sentences — "In the context of <X>, we chose <Y>." / "We chose it over <Z>." /
"The reason: <W>." — so that each sentence stays within prose lint's 25-word
limit; a statement of 25 words or fewer in total can stay one sentence, as
both successor pages in the study do. The study's records all needed the
three-sentence form.

`Applies when:` and `Does not apply when:` are what keep a pattern from being
reused out of scope, and `Revisit when:` is what a curator checks when a
source moves. `status:` is frontmatter and never approves a page: approval is
a separate record bound to the page's bytes (the README's `wiki-studio
approve` entry and the [standalone quickstart](quickstart.md) show the
propose, promote and approve flow).

Check a new page's prose before proposing it:

```
wiki-studio lint --prose
```

A pattern page enters the wiki the way every page does: propose it, promote
it through the lint gate, then have a curator approve the revision they read.
Nothing in lint or `findings` checks the convention itself; a missing
`Applies when:` or `Revisit when:` line passes every check, so review is where
the convention is enforced.

## The evidence checklist

Before a curator promotes a pattern proposal, the candidate should carry five
items:

1. the canonical implementation as a `sources:` entry with `path:` and `sha:`;
2. at least one test or verification outcome;
3. the originating spec, issue or PR;
4. the rejected options with their reasons;
5. a revisit trigger.

A missing item is a reason to send the proposal back; nothing in code reads
the five. In the study's five example pages the canonical implementation and
the rejected options were present five times, the originating spec four
times, the revisit trigger three times and a test or verification outcome
twice — so expect to send real proposals back.

## Finding, checking and citing a pattern

```
wiki-studio find "<the task, in plain words>" --json
wiki-studio findings --json
wiki-studio read <page> --json
```

The first lists the pages `query` would load for the task. The second keeps
only pages whose review state is `approved` — an `unapproved`,
`approval-stale` or `approval-policy-changed` page is a reason to stop — and
the MCP `review_state` tool answers the same question. The third returns the
page's text and the sha256 of exactly those bytes, which is what an approval
binds and what an agent should record when it cites the page.

Then read the page's `Applies when:` and `Does not apply when:` lines against
the task. A `find` result is a candidate list, and an approval is evidence
that a curator saw those bytes, not that the pattern applies.

## Revisiting and superseding

- Cite what the pattern relies on as `sources:` entries with `path:` and
  `sha:`. `stale-claim` checks that a cited path exists; `findings` also
  compares the `sha:` with git, read-only, in the root's repository and then
  the source roots. `source-not-at-revision` means the citation itself is
  wrong: the path is absent at that commit, no repository has the commit, or
  the `sha:` is malformed; correct the `sha:` or the path.
  `source-revision-changed` means the cited file changed since its `sha:` on
  a line that names one of the page's backticked identifiers or `file:line`
  references, or under a heading the page names. Read it against the page's
  `Revisit when:` line, which the finding quotes: when the condition has
  arrived, review the pattern; when it has not, update the `sha:` and keep
  the page. The flagged page stays approved and `find` still returns it.
  `revision_check` in `findings --json` says whether the check ran and which
  sources it could not check (no `sha:`, a shallow clone, a commit in no
  usable repository).
- Write `Revisit when:` so a curator can recognise the condition. In the
  study's corpus 13 pages cited a file that had changed since its `sha:` and
  12 of them needed no review under their own `Revisit when:` line — a change
  is a reason to look, not a verdict. Of those 12, one sits on a superseded
  page the check skips and one is a citation error that
  `source-not-at-revision` reports instead; on the other 10, the anchor rule
  of `source-revision-changed` flags 3, and it keeps the one true flag, read
  on a copy of that page as it stood before its successor
  ([revision study](https://github.com/gosha70/wiki-studio/blob/main/eval/revisions/report.md)).
- When a pattern is replaced, write the successor page, give the old page
  `superseded_by: decisions/<successor>.md` and `status: deprecated`, and
  point the successor at the old one's evidence. `find` then lists the old
  page ineligible with reason `superseded`. `findings` reports
  `superseded-still-indexed` while `index.md` still links the old page: drop
  the index line when the history need not be browsed, and keep it, accepting
  the finding, when it should be.
- A failed test or a security finding is not detected by any check. Name the
  test in `## Consequences` or cite its file, cite the finding's issue or
  URL, and review the page when either changes.

## What memkernel keeps

When memkernel points at a pattern, keep:

- the page's `page_id`;
- the wiki path;
- the approved revision's sha256, taken from `read --json`;
- the Y-statement: the first paragraph of `## Decision`;
- `corrects:` on the wiki page naming the runtime record it replaces, as
  memkernel #57's research note says.

The wiki bridge carries a page's title, body, single-line frontmatter scalars
and `sources:`; the approval record does not cross it, which is why the
revision sha256 is kept beside the pointer rather than read from the page.
