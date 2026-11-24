---
page_type: decision
slug: cct-routing-profile-foundation-plan-04
title: 'Trust-asymmetric repo block'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-profile-foundation/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`automation.json` gains a closed
`routing` object: `{enabled: bool, allowed_profiles: [ids],
default_task_route: <route-class name>}` — restriction-only by
CONSTRUCTION (the schema has no field that could define a profile,
credential, endpoint, or route class). `profiles`, `credential*`,
`base_url*`, and `protocol` inside the repo block are additionally
refused by name with pointed messages; `tier2` and `recovery` are
refused by name as owned by increments C/D (C1's
rejected-until-shipped pattern). Effective policy: routing is
enabled only if both layers enable it; the allowed profile set is
the intersection of the registry's profiles with `allowed_profiles`
(absent = all registry profiles); `default_task_route` must name a
registry route class. A repo-listed id missing from the registry is
a NAMED violation, not a silent drop — a typo must not silently
widen or narrow policy. The trust asymmetry is an EXECUTABLE
INVARIANT, not a key list: for every (user, repo) input pair,
`effective_candidates(user, repo) ⊆ candidates(user)` — a repo can
never introduce a profile, provider, model, credential reference,
quota pool, less-restricted tier, or any capability the registry
did not already grant. T4 proves the subset property over a
generated case matrix (narrowing, disjoint, absent, and
would-be-widening repo blocks), not just per-key examples.
