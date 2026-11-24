---
page_type: decision
slug: cct-pi-project-config-spec-04
title: 'Fallback'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/pi-project-config/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

Through 2.1.x, removed in 2.2, with the user-home
fallback: the last tag is `v2.0.0` and #411 sits in Unreleased, so if
#460 ships in the same 2.1.0 release both legacy names disappear
together in 2.2. If #460 misses the 2.1.0 release, the old location is read through
the release after the one #460 ships in. Projects always get at least
one full minor release to migrate, and the CHANGELOG states the
removal version. **Ruled 2026-11-18 by the owner.**
