---
cooldown_after_cycle: "03"
started: 2026-10-29
ended: 2026-10-30
duration: 2d
---

<!-- Generated at the end of a cooldown by the cooldown-report agent. -->
<!-- Summarizes bug fixes + lists pitches ready for the next betting table. -->

# Cooldown after Cycle 03

## Summary

Cycle 03 (`38-release-c-discovery-portability`, bet 2026-10-27) shipped as
wiki-studio 0.8.0, tag `v0.8.0` on `aa2362d`, 2026-10-29; Release C closed
with that tag. The cooldown landed one test fix (issue #53), the 0.8.0 doc
follow-ups and the CI pins that closed Release B. No pitch was shaped in the
cooldown, so the betting table has no shaped candidate.

**Cycle 02 closed in this cooldown.** `38-release-b-governed-curation`
shipped the wiki-studio half as 0.7.0 on 2026-10-27 and stayed open under its
circuit breaker until memkernel's counterpart shipped. memkernel 0.6.0 shipped
it. The Release B loop CI job went green against it, and Release B closed on
2026-10-30: PR #63 (pin memkernel `main` past memkernel #48, loop job
blocking), PR #64 (pin memkernel 0.6.0 from PyPI) and PR #65 (docs, open on
`docs/release-b-closed`, commit `8c99e34`). No separate report is written for
cycle 02.

## Bug fixes shipped

| Commit | Pitch / area | One-line description |
|--------|--------------|----------------------|
| `f09b652` (PR #63) | 38-release-b-governed-curation / tests | Closes #53: `test_release_b_loop` compared a non-existent `Memory.id`; it now compares `ref_id` |

## Polish & follow-ups

Window: `v0.8.0..main` plus open PR #65. These commits are docs and CI pins, not bug fixes.

- `219fdbc`, `3fce1f0` (PR #61): the 0.8.0 upgrade note states the default-ranker change, including for `api` calls without a ranker. The Added line now matches the cache-marker rule. Area: 38-release-c-discovery-portability.
- `93718ca` (PR #62): `docs/roadmap.md` records Release C as shipped in 0.8.0. Area: 38-release-c-discovery-portability.
- `16725d3` (PR #63): CI keeps Release B open until a memkernel release and asserts the snapshot is gone. Area: 38-release-b-governed-curation.
- `cb706ab` (PR #64): pins memkernel 0.6.0 from PyPI in both clean-install jobs. Area: 38-release-b-governed-curation.
- `8c99e34` (PR #65, open): docs record that wiki-studio 0.8.0 was tested with memkernel 0.6.0 and that Release B is closed. Area: 38-release-b-governed-curation.

## Pitches shaped during cooldown

| pitch_id | Title | Appetite | Status |
|----------|-------|----------|--------|

No pitch has `bet_status: shaped`. The only pitch not yet shipped is
`28-plain-technical-english` (2w, shaped 2026-10-20) shipped in 0.5.0 on
2026-10-20 (closes #28); its pitch file still read `bet_status: bet` for
cycle "01" and was corrected to `shipped` in this cooldown. It was not
shaped in this cooldown.

## Recommended bets for next cycle

No shaped pitches exist, so no bet is recommended. Candidates to shape, from
`docs/roadmap.md`, CHANGELOG `[0.8.0]` Limitations and the open issues:

1. **The Release B launch items and the integration measurement.** The roadmap's Launch sequence step 2 names two quickstarts, a compatibility matrix and an obsolete-decision correction demo. The Evidence section names the integration measurement: memkernel alone, memkernel with governed Wiki Studio, and files plus grep. Both were waiting on memkernel #48, which is now shipped. Related issue: #10 (wiki cheaper to consult than raw sources). <!-- author note: priority vs. the other candidates -->
2. **Issue #54.** Govern reusable engineering patterns and assess duplicate knowledge. <!-- author note: not yet scoped -->

Smaller open items that are not cycles on their own:

- The discovery evidence is small: 21 development and 53 held-out gold questions.
- The Kiro host run is documented but was not release-blocking.
- The memkernel.dev project page still describes 0.5.0. That page is outside this repo.

### Next-bet recommendation

**Next-bet recommendation:** `/shape <topic>`: no shaped pitches are available. Draft the next bet before the betting table meets.

## Carryover

- [ ] PR #65 (`docs/release-b-closed`) is still open.
- [ ] memkernel quickstart and the integration measurement (roadmap Evidence and Launch sequence step 2).
- [ ] Issue #10: evidence that the wiki is cheaper to consult than raw sources.
- [ ] Issue #54: reusable engineering patterns and duplicate knowledge.
- [ ] Kiro host run (not release-blocking).
- [ ] Larger discovery evidence set (now 21 development and 53 held-out questions).
- [ ] Update the memkernel.dev project page from 0.5.0 (outside this repo).
