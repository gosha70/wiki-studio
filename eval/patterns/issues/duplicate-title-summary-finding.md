<!-- Drafted by the issue 54 study (eval/patterns/report.md, question 4), at the
owner's request on 2026-11-19. Not filed by the build. The owner files it from
this text and replaces {report_permalink} and {duplicates_permalink} with
permalinks to eval/patterns/report.md and eval/patterns/results/duplicates.json
at the commit that added them (never a branch path). -->

# Specify a near-duplicate finding based on titles and summaries

## Problem

Two pattern pages can describe the same decision in different words, and
nothing in wiki-studio tells a curator so. The issue 54 study measured three
model-free signals for near-duplicates against labels frozen before any signal
ran. Signal (b), which compares page titles and the opening summary
(Y-statement), came closest to its bar.

**This draft rests on a disputed label, not on the study's frozen verdict.**
The recorded verdict for (b) is "fail". It turns into a pass only if one
disputed label (a decision page and the incident record behind it, labelled
`redundant`) is read as `unrelated`. The owner asked for this draft anyway, so
the question is on record.

## Evidence

- `results/duplicates.json`, as recorded: (b) found 2 of the 3 eligible true
  pairs with 1 false candidate. The pair it missed is the disputed one. Read as
  `unrelated`, (b) finds 2 of 2 with 2 true against 1 false.
- Of those two pairs, one is the conflicting pair that `findings` already
  reports as `open-conflict`. (b)'s only new find is the
  never-archive-raw-JSONL / trace-archive pair.
- (b) reads titles and Y-statements, not cited files, so its finds don't
  depend on the labeller's reasoning about shared sources.
- The bar rests on very few pairs, so no precision or recall is estimated with
  any confidence.
- Report: {report_permalink}. Results: {duplicates_permalink}.

## Proposal

A separately specified investigation before any code: re-run (b) on a larger,
independently labelled corpus with the labels frozen first, settle how a
decision page and its incident record should be labelled, and only then
decide whether a model-free `findings` kind (for example
`possible-duplicate`) is worth its false positives. The spec must fix at
least: the corpus and who labels it, the bar, what a curator does with a
flag, and how the kind relates to `open-conflict` so the same pair isn't
reported twice.

## Out of scope

No package code in this issue's text; no automatic merge, deletion or
approval change; no model on the `findings` path; no change to memkernel.
