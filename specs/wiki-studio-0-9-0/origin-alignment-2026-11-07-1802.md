# Origin alignment check — wiki-studio-0-9-0 (amendment)

Gate: the driver parked after phase 1 (US1) on escalation `esc-1` (review
breaker). The owner's review of PR #88 at head `d9da1c0` found one spec
ambiguity, and on 2026-11-07 the owner chose its resolution. This record
covers that amendment only. The origin, working claim and mismatches of
`origin-alignment-2026-11-07-0134.md` stand unchanged.

The amendment:
- **Which link names the other page.** FR-006 said "the first `_MD_LINK_RE`
  match", and `lint._MD_LINK_RE` matches every link, while FR-002, FR-010
  and plan.md mean `health_lint._MD_LINK_RE`, which matches `.md` targets
  only. The owner chose the `.md` rule: a link whose target does not end in
  `.md` is skipped, and a target with a URL scheme (`https://…/b.md`) is
  "outside the wiki", so its callout is `conflict-dangling`. FR-006 first
  named `health_lint._MD_LINK_RE` and the URL-scheme case; FR-010(a) gains
  the two web-link cases (four fixture cases); FR-011 and tasks.md rows 4
  and 7 follow.

- **A link title is dropped.** The reviewer's follow-up found that
  `health_lint._MD_LINK_RE` misses `[B](b.md "Title")`, which lint reads as
  `b.md`. The owner chose to drop the title the way `lint.py` does, so lint
  and `findings` agree. FR-006 now describes the link reading in those
  terms; FR-010(a) gains the titled case (five fixture cases); FR-011 and
  tasks.md rows 4 and 7 follow.

This narrows the existing mismatch "the other page is the first `.md` link
on the marker line" and adds no scope: no new kind, reason phrase, flag or
file beyond the fixture cases.

Verdict: aligned
Confidence: high
