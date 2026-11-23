# The revision-check study: report (issue 120)

This report gives the measurement that `README.md` in this directory defines
and that `protocol.json` freezes. The labels, cases, candidates, bar and
selection rule were committed, reviewed by the owner and pinned by sha256
(`tests/test_revisions_frozen.py`) before any candidate code existed. Every
figure here is copied from `results/candidates.json` as recorded; nothing
is rounded by hand except wall times, shown to three decimals.

## How the results were produced

The record is run once, by hand, against a local code-copilot-team checkout;
the scores are recomputed from it in CI. It was run on 23 November 2026 by the
build session outside the auto-build sandbox, whose sessions could not run
Python (the plan's fallback, owner step 1), against `../code-copilot-team`,
with both commands below exiting 0; the checkout was left unchanged.

```
poetry run python -m eval.revisions.record --checkout ../code-copilot-team
poetry run python -m eval.revisions.candidates --out eval/revisions/results/candidates.json
```

`record.py` clones the checkout locally into a temporary directory (one clone
at the study's pin `00d49c0`, one per case at its read commit), checks every
case's recorded source hashes against the checkout first, and then runs the
call plan p1-p7 with the hardened prefix, a clean environment, argument lists,
no shell and no network. It writes `results/hunks.json`, and each
keyword-quoting case's record to that case's own
`cases/keyword-quoting/<id>/hunks.json`. `candidates.py` reads only the
committed files and runs no git.

How the record reads the protocol, where the protocol leaves room:

- **Repository order.** Each run lists this wiki-studio checkout first (the
  root) and the clone second (the one source root), as D6 orders them. Every
  short `sha:` is therefore probed in wiki-studio's repository before the
  clone. The record shows that no cited `sha:` matched in wiki-studio's
  repository: every checked source names `code-copilot-team` as its
  repository. A match there would be recorded and reported.
- **Superseded pages are not examined.** The study run lists the two
  superseded fixture pages and makes no call for them (structural rule 1), so
  its process count is the one the shipped check would make on the fixture
  wiki.
- **The pre-successor copy is its own run**, against the same pin clone, so
  that the merge page's `a24a00e` source is recorded without adding its calls
  to the study run's count.
- **Every changed cited path gets p5, p6 and, for Markdown, p7**, so each
  candidate is charged only the steps it needs: C0 none, C1 p5, C2 p6 and p7
  (p5 when the page has no anchor), C3 p6 (p5 when the page has no
  Revisit-when tokens), C4 the union of C2's and C3's.
- **A path p4 does not list** is unchanged, or absent at both commits; the
  call plan does not tell the two apart, the record leaves its presence
  `null`, and neither yields a flag.
- **The heading rule** takes ATX headings outside fenced code only, as
  CommonMark defines a heading; a `#` line inside a fenced block is code.
- **Case pages are recorded whole.** A case page that cites more than one
  source has all of them recorded; only the case's own source is scored.

## Results

| Candidate | False pages flagged | False entries flagged | `a24a00e` on the pre-successor copy | Supplementary positives kept | Without the two built pages | Negatives flagged | Git processes, study run | Wall time (s), study run | Bar |
|---|---|---|---|---|---|---|---|---|---|
| C0 | 10 of 10 | 11 of 11 | kept | 5 of 5 | 3 of 3 | 0 of 0 | 37 | 0.349 | fail |
| C1 | 10 of 10 | 11 of 11 | kept | 5 of 5 | 3 of 3 | 0 of 0 | 45 | 0.433 | fail |
| C2 | 5 of 10 | 6 of 11 | kept | 5 of 5 | 3 of 3 | 0 of 0 | 50 | 0.479 | pass |
| C3 | 8 of 10 | 9 of 11 | kept | 5 of 5 | 3 of 3 | 0 of 0 | 47 | 0.453 | fail |
| C4 | 5 of 10 | 6 of 11 | kept | 5 of 5 | 3 of 3 | 0 of 0 | 53 | 0.510 | pass |

Every candidate keeps the merge page's `a24a00e` flag on the pre-successor
copy and all five supplementary positives, so conditions 2 and 3 hold for all
five. Condition 1 decides: C0 and C1 flag all 10 false pages, C3 flags 8, and
C2 and C4 flag 5, exactly the limit. No matched negative was recorded (none
was found, README "The labels"), so that column is 0 of 0.

**The two cases labelled `should_flag: false`** (reported only, not part of
the bar): every candidate flags `run-wiki-ingest-rules`, a real change to a
cited file that called for no review; no candidate flags `vllm-backend-doc`,
whose cited file is absent at its `sha:`, so it gets no revision kind and
belongs to the exact kind.

**Selection.** C2 and C4 pass with 5 false pages each. The tie goes to the
fewer git processes on the study run: C2 with 50 against C4's 53.

Winner: C2

**What the win rests on.** C2 passes condition 1 at the limit, 5 of 10 false
pages, with no margin. Without the two built pages the supplementary set has
3 positives, below the minimum of 4, so that variant of condition 3 is not
testable; it is reported, not a condition. How much of the win rests on
fragment anchors is measured post hoc, below.

**Process counts** (study run, from `process_counts`): the exact kind's plan
(p1-p4) takes 37 git processes in 0.349 s; with each candidate's steps added,
C0 37, C1 45, C2 50, C3 47 and C4 53. The slowest single recorded call is a
p4 of the study run, 0.012 s. FR-022 derives the shipped call cap and the
per-call timeout from these counts.

## Post hoc: fragment anchors (not binding)

Found after the freeze, by the external review of this PR. It changes no
verdict, no condition of the bar and not the winner line; `candidates.py`
computes it in its own `post_hoc` block of `results/candidates.json`, marked
`"binding": false`, and CI checks the figures below against it.

As frozen, C2's anchors include fragments: the last dotted component of every
backticked item (`py`, `sh`, `ts`, `md` from file names, `run` from
`correlate.run`) and short or letterless items (`"`, `0`, `1`, `2`), each
matched anywhere inside a changed line. Some of the winner's flags rest on
nothing else:

- the benchmark-step page (both its entries) and the config-redaction page,
  2 of C2's 5 false pages;
- the `run-wiki-ingest-rules` case.

None of the true flags depends on a fragment: the merge entry and all five
supplementary positives are also caught by whole anchors.

Re-scored with the rule "anchors shorter than 4 characters, anchors with no
letter, and the last dotted component of a backticked path (an identifier
containing '/') are ignored":

| Candidate (post hoc) | False pages flagged | False entries flagged | `a24a00e` on the pre-successor copy | Supplementary positives kept | `run-wiki-ingest-rules` flagged |
|---|---|---|---|---|---|
| C2 | 3 of 10 | 3 of 11 | kept | 5 of 5 | no |
| C4 | 3 of 10 | 3 of 11 | kept | 5 of 5 | no |

The rule was chosen after seeing the data, so these numbers are evidence for
the spec amendment's choice of what ships (FR-032 builds the winner exactly
as FR-008 defines it), not a result of the preregistered study.

## Limits

- **The study has one true case.** One source entry (the merge page's
  `specs/auto-build-loop-merge-profile/spec.md` at `a24a00e`), on a page the
  shipped check skips because it is superseded, read through a derived copy
  (`pre-successor/merge-require-green-ci-was-never-read.md`). Keeping or
  losing that flag is one observation.
- **The supplementary set is small and narrow.** Five positives from one
  repository and one author; three of them are one page at three moments
  (`pre-pr-strict-mode`, `pre-pr-keyword-set`, `pre-pr-doc-audit`), and two
  are pages built for this study from spec text (`provider-config-guarantee`,
  `benchmark-provider-id`). Four of the five are counterfactual: read at the
  commit that both changed the source and corrected the page. Recall is
  therefore a count out of n, not an estimate.
- **The false alarms are measured on 10 pages and 11 entries** from one
  repository, judged by reading each cited file at the pin against the page's
  `Revisit when:` line.
- **The anchor rule is literal.** An identifier also counts by its last
  dotted component, so a backticked file name such as `spec.md` also counts
  as `md`, and an anchor matches any changed line that contains it as a
  substring. Both are the frozen protocol's reading and were not adjusted; how much
  of the result rests on them is measured post hoc, above.
- **No agent behaviour is measured**, and no repository other than
  code-copilot-team.

## Labels the build disputes

None. No label, case or bar condition was changed after the freeze; a
disagreement found later would be reported here, not patched.

## Cuts

None taken. Cut 1 was not invoked at the milestone, so all five candidates
are measured.

## The keyword-quoting cases

Three cases are named here by id and path only:
`pre-pr-strict-mode` (`cases/keyword-quoting/pre-pr-strict-mode/`),
`pre-pr-keyword-set` (`cases/keyword-quoting/pre-pr-keyword-set/`) and
`pre-pr-doc-audit` (`cases/keyword-quoting/pre-pr-doc-audit/`). Their records
stay in those directories; this report, `results/hunks.json` and
`results/candidates.json` carry their ids and counts, never their text.
