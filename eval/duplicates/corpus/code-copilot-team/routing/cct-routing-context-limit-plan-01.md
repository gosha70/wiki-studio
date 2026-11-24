---
page_type: decision
slug: cct-routing-context-limit-plan-01
title: 'the executable-identity tuple is a KEY, not a carrier'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-context-limit/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

`rc_profile_tuple` is documented as the complete executable identity
and backs a monotonic subset invariant. Adding `context_limit` to it
would make two profiles differing only in a declared window
non-identical, which is wrong: a window is a capability attribute, not
part of what a profile executes as.

The same tuple is, however, exactly the right KEY for rule 6. Hashing
the canonical tuple gives an identity digest that changes the moment
provider, model, endpoint reference, credential reference, backend,
tier, pool, roles, tool profile or data policy change — so an
observation expires by construction rather than by a rule someone has
to remember to write. The limit therefore rides beside the tuple in the
effective document, and the tuple's digest keys the observation.
