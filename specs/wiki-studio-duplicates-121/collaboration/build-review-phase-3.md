---
feature_id: wiki-studio-duplicates-121
phase: 3
status: bypassed
verdict: BYPASSED
bypass: true
bypass_approved: esc-1
---

# Review record — phase 3

Composed by auto-build-loop from the archived review state; the
runner wrote no build-review.md before the breaker tripped.

## Findings (findings-round-3.json)

- [blocking] f-efcc2cfb: The labels contain only 7 true pairs, below the spec's minimum of 8 (D4). Round 2 flagged this as blocking; the builder disputed but made no change — the count is still 7, the README still documents the shortfall as fact, and no extension family was extracted per FR-016. The gate cannot pass while the substantive requirement fails. (file: eval/duplicates/labels.json)
- [warning] f-a705cc60: `MINIMUM_TRUE_PAIRS` is still used only in the README-string assertion (`against the minimum of 8`), never as a bound on `true_pairs`. A regression to 0 true pairs would still pass this suite. Round 2 flagged this; the builder disputed but the test is unchanged. (file: tests/test_duplicates_labels.py)
- [warning] f-7b9962b5: The routing-05 group still labels several pairs `companion` where the reason describes one page extending another's guard ("E3 extends E2's standing authority-guard test", "E2's guard extends E1's diff guard"). Per the README's own definition, `companion` is for "a decision and the incident behind it, a rule and its application to one case, a decision and the later refinement that names it" — an extension of a guard to new modules is arguably `supersedes` or `redundant`. Round 2 flagged this; the builder disputed but the labels are unchanged. This labelling inconsistency may be the direct cause of the true-pair shortfall. (file: eval/duplicates/labels.json)
- [note] f-fd3040e6: The README now does flag the shortfall as an open gate failure requiring owner action (the Round 2 note f-03b00436 appears addressed by the added "Status: open" paragraph). However, the surrounding text still reads as if the shortfall is an accepted outcome in places, and the builder marked this "fixed" in Round 1 while the substantive count remains unchanged. Confirm the status paragraph is sufficient to prevent a reader mistaking this for an accepted outcome. (file: eval/duplicates/README.md)
- [note] f-10603a82: The review-sample tests skip when `review-sample.json` is absent, so the sample's `labels_sha256` binding to `labels.json` is never verified here. If the sample is drawn from a stale labels file, nothing in this suite catches it. Round 2 flagged this; the builder disputed but the test is unchanged. The docstring now explains the hash is deliberately not compared (FR-016(c)), which is a reasonable design choice, but the skip still means the sample is entirely unverified until the pause. (file: tests/test_duplicates_labels.py)
