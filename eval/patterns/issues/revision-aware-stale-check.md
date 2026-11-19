<!-- Drafted by the issue 54 study (eval/patterns/report.md, question 5).
Not filed by the build. The owner files it from this text and replaces
{report_permalink} and {staleness_permalink} with permalinks to
eval/patterns/report.md and eval/patterns/results/staleness.json at the
commit that added them (never a branch path). -->

# Specify a revision-aware check for a pattern's cited sources

## Problem

`stale-claim` checks that a cited `path:` exists; it does not compare the
cited `sha:` with the source. A pattern whose canonical implementation or
spec changed in place stays clean, and the issue 54 study measured the gap:
the one page whose `Revisit when:` condition had arrived — a spec that gained
the correction superseding the page's decision — was not flagged, because the
path still exists. A check that compares commits would have found it, but it
also flags every page whose source moved for an unrelated reason, and the
study does not settle how a curator should read such a flag.

## Evidence

- `results/staleness.json`, as recorded: 24 `path:` + `sha:` sources on 14
  pattern pages; `stale-claim` flagged 0 and missed the one page that needed
  review; the study's revision check reported 15 changed and 9 unchanged
  sources across 13 pages — 1 true review and 12 false flags under the pages'
  own `Revisit when:` lines, 0 pages missed.
- The check surfaced one true citation error among the false review flags:
  the judge-statistics page cites `spearman.py` at a commit that does not
  contain the file.
- "Flag, still return" fits the wiki: a finding never withdraws an approval
  and never changes discovery eligibility, so a flagged page stays approved
  and findable while a finding asks for review (report, question 5).
- Report: {report_permalink}. Results: {staleness_permalink}.

## Proposal

A separately specified enhancement: a model-free finding, for example
`source-revision-changed`, raised when a page's cited `path:` differs between
its `sha:` and a revision the check can read, from a local checkout or a
recorded pin. It would flag and still return, and the `findings` command and
the `nightly` report would carry the new kind without further work. The spec
must fix at least: what a flag means (a changed file is not a review trigger
by itself — the page's `Revisit when:` line is), how the false-flag rate of
the study is reduced or explained, what it costs to run, where it runs
(`findings`, `nightly`, or both), and whether a missing or unknown `sha:` is
a finding of its own.

## Out of scope

No package code in this study and none in this issue's text; no network
fetch and no scheduled job; no automatic approval withdrawal, re-review or
page rewrite; no change to memkernel; a memkernel-side counterpart is not
part of this issue.
