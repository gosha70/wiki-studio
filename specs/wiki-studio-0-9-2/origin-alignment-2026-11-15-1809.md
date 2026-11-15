# Origin alignment check — wiki-studio-0-9-2 (amendment)

Gate: the auto-build ran 2026-11-15 and opened build PR #103 (head
4fd532b). The external review of that head asked for two fixes to the
persona's approve step. The owner decided the second on 2026-11-15. This
record covers that amendment only. The origin, working claim and mismatches
of `origin-alignment-2026-11-15-1427.md` stand unchanged.

The amendment (spec FR-003(d) and (f), the tasks.md task 2 text, plan.md
departure 10, and the persona's step 13):
- **Pages `approve` always refuses are skipped.** A changed page that is
  `status: draft` (for example, left by a memkernel export) or carries
  `superseded_by` (a patch-set that supersedes a page updates the old one)
  is skipped and reported, not approved. The agent never edits frontmatter
  to get an approval through. The reviewer had asked for this in the #101
  review; it did not reach the approval commit (#102).
- **A changed revision is not approved.** When `approve --revision`
  refuses because another writer replaced the page after promote, the
  agent does not approve it, and reports the page and stops. The earlier
  text both allowed approving the new revision "if it still holds" and
  forbade approving content the agent did not author. The owner chose the
  narrower rule, because an approval under the agent's name would vouch for
  bytes another writer produced.

- **Auto-approval is checked, not assumed (outcome 4).** The re-review of
  9481865 found that outcome (4) skipped approval entirely on an
  auto-approving wiki. But auto-approval runs after the promotion commits,
  under a second lock, and is best effort. A lock timeout, a failed record
  write or another writer can leave a page unapproved while promote still
  succeeds; promote says so in a warning, and `approved_paths` omits the
  page. The owner chose "report and stop" (2026-11-15). Every eligible
  page must appear in promote's approved list: an eligible page is a
  changed content page that is not `status: draft` and carries no
  `superseded_by`. If one is missing, the agent reports it with promote's
  warning and stops, and never approves it itself. Self-approval stays on
  outcome (5) only.
- **The plan's stale direction is replaced.** Departure 2 in plan.md no
  longer says "re-read and re-inspect" after a changed revision.
- **The three rules are pinned.** `tests/test_maintainer_persona.py` gains
  `TestTheApprovalSafeguards`. Against the persona at 4fd532b, all three
  tests fail.

This narrows the approval step and adds no scope: no new verb, flag, test
module, page schema or doc page (the new tests extend the existing
persona module).

Verdict: aligned
Confidence: high
