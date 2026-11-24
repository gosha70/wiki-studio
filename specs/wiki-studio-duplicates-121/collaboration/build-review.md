---
feature_id: wiki-studio-duplicates-121
phase: 3
status: bypassed
bypass: true
breaker_type: reconstructed
approved_by: gosha70
date: 2026-11-24
---

# Build review — phase 3 (US3), bypassed by the owner

DeepSeek blocked all three review rounds of phase 3 with one finding: the
labels hold 7 true pairs, below the minimum of 8 (D4). The build session
disputed it in rounds 1 and 2 and changed nothing.

The external reviewer judged the finding inapplicable to this phase. FR-016(a)
handles a shortfall at the pause after US3: the main session extracts the
next family by FR-003's order, and a fresh session labels it, repeating until
`true_pairs` is at least 8 or the order is used up (then the verdict is "not
testable"). The minimum of 8 is a condition of the verdict, checked after the
freeze, not of this phase. The README records "True pairs: 7, against the
minimum of 8" as open, and a test checks it. No label was changed to reach 8.

The owner approved the bypass with `/review-decide approve` on 2026-11-24.
