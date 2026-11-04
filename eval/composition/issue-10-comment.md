<!-- Comment body for gosha70/wiki-studio#10 (FR-025). Not posted by the
build. One interactive step after the build posts it, after the memkernel
issue and the successor issue are opened. Replace {design_permalink} with the
permalink to eval/composition/design.md at the commit that added it, and
{memkernel_issue} and {successor_issue} with their issue URLs. The build PR
carries `Closes #10`; the issue closes when that PR merges. -->

The condition in this issue — that it "closes when that run's results are
published and linked here" — is met. memkernel published the 0.5.0
lifecycle-suite run, and it included a `wiki_studio` arm.

- Report:
  https://github.com/gosha70/memkernel/blob/v0.5.0/eval/lifecycle-suite/report-0.5.0.md
- Preregistration:
  https://github.com/gosha70/memkernel/blob/v0.5.0/eval/lifecycle-suite/preregistration.md
- Arm configuration:
  https://github.com/gosha70/memkernel/blob/v0.5.0/eval/lifecycle-suite/arms/wiki_studio/config.frozen.json

## What the run shows

The `wiki_studio` arm — wiki-studio 0.4.1 through the CLI, with no curator
and no governed import — ran on the five `lc-wiki` tasks. It passed 25 of 25
trials, as every arm did, the negative control `bare` included; every
pairwise effect in the group was +0.0, and the report's headline is "no gain
claimed". The group is at ceiling, and the reason is structural: each task's
exposure prompt tells the agent to record the decision under
`knowledge/wiki/`, the runner copies that directory into the second session
for every arm, and the fixture wiki holds only `index.md`, so any arm that
writes a file and reads it back passes.

The report records two diagnostics for the arm: 0 of 177 Bash calls ran
`wiki-studio ingest` or `wiki-studio query`, and 0 of 9 `Write`/`Edit` calls
were under the wiki (against `fs_grep` at 52 of 78 and `memkernel` at 38 of
63). They do not show that the arm stayed inside the gate: Bash can write
files, and the receipts keep payload hashes, not the commands that produced
them or the gate's records. No gate claim is made.

The token totals do not compare: 4,309,745 receipt tokens on 25 `lc-wiki`
trials against about 19-20 million per other arm over 100 trials in four
groups, with no per-group token table.

## What does not follow

No outcome, cost, efficiency or superiority claim follows from this run, in
either direction. The arm was wiki-studio 0.4.1 alone through the CLI, not
the governed composition the roadmap names (memkernel exports through the
gate, a curator corrects and approves, memkernel imports, the next session
recalls).

## What remains

A governed-composition measurement able to discriminate the arms. The design
is `eval/composition/design.md` ({design_permalink}): it explains the ceiling
from the report's numbers and states what a task set, a new versioned
composition arm and a curator policy need so that `bare` fails and the arms
can differ. The measurement is memkernel's to preregister, budget and run;
the memkernel issue carrying the design is {memkernel_issue}. This
repository's successor issue carries it forward: {successor_issue}.

The build PR carries `Closes #10`. The issue closes when that PR merges, by
this restatement and not by a claim.
