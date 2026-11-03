<!-- Successor issue body (FR-025). Not filed by the build. One interactive
step after the build files, in this order: the memkernel issue whose body is
eval/composition/design.md, this issue, then the comment in
issue-10-comment.md on #10. Replace {design_permalink} with the permalink to
eval/composition/design.md at the commit that added it (never a branch path),
and {memkernel_issue} with the URL of the memkernel issue. -->

# Measure the governed composition with a task set that can discriminate the arms

Issue #10 closes by restatement: memkernel's published 0.5.0 run shows a
ceiling on `lc-wiki`, not a result, and no measurement able to tell the arms
apart has been made. This issue tracks the measurement that would.

The measurement belongs to memkernel's lifecycle suite: memkernel designs,
preregisters, budgets and runs it. This repository's side is the governed
composition under test.

## The design

[`eval/composition/design.md`]({design_permalink}) states, from memkernel's
published numbers:

- why `lc-wiki` is at ceiling — each task's exposure prompt tells the agent
  to record its decision under `knowledge/wiki/`, the runner copies that
  directory into the second session for every arm, and the fixture wiki holds
  only `index.md`, so any arm that writes a file and reads it back passes;
  every arm passed 25 of 25, `bare` included, and every pairwise effect was
  +0.0;
- what a task set needs so the arms can differ — a calibration showing `bare`
  fails before any measured run, an obsolete decision in each chain with a
  checker that separates the obsolete answer (X) from the informed one (Y)
  and from anything else, the correction travelling only through the arm's
  own workflow, and competing pages in the fixture wiki;
- the four arms — memkernel alone, memkernel with governed wiki-studio, files
  plus grep, and the negative control — with the composition as a new,
  versioned arm and the 0.4.1 arm left frozen;
- the curator options and a recommendation — a scripted curator with a
  preregistered policy as the primary arm, an oracle curator as the upper
  bound, `auto_approve_on_promote` at most as a named sensitivity check;
- the gate's own records (receipts, approval records, `.audit/`,
  `review_state`) checked for every landed page, not tool-call diagnostics,
  as a requirement of the composition arm;
- the roadmap's six questions mapped to a measurement or to existing
  evidence, and memkernel's dependencies listed.

It is design only: it preregisters, runs and budgets nothing, and it is not
evidence for or against any arm.

## What remains to be built

The memkernel issue carrying the design is {memkernel_issue}. Its dependency
list is the work:

1. the versioned composition arm and its curator step;
2. the task set with its calibration, and the runner change that stops
   copying the correction into every arm's second session;
3. a per-group token table;
4. the preregistration, including checkers, exclusions and analysis;
5. the budget;
6. memkernel 0.7 for withdrawal (replacement only until it lands).

On this repository's side the governed loop is executable today and needs no
new code: `docs/quickstart-memkernel.md` runs it in the
`quickstart-memkernel` CI job, and `docs/demo-correction-loop.md` tells its
story, run by the `demo-correction-loop` job and once as a recorded run. No
runner, statistics, event-schema or task code is written here, and the frozen
0.4.1 arm files are not edited.

## When this can close

When a preregistered measured run on a calibrated task set has been run and
its results are published, with the arms separated in the report or the
report saying they are not. Until then the published 0.5.0 run stays a
ceiling result and no claim follows from it.

Related: issue #10 (closed by restatement), the memkernel issue
{memkernel_issue}, and the committed #10 comment
(`eval/composition/issue-10-comment.md`).
