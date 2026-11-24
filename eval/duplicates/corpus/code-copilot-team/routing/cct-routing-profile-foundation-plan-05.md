---
page_type: decision
slug: cct-routing-profile-foundation-plan-05
title: 'Normalized backend result — cause-oriented, action-free'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-profile-foundation/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

A
closed JSON Schema at `shared/schemas/routing-result.schema.json`:
`schema_version`, `outcome` (`success|failure`), `failure_class`
(null on success; the frozen cause taxonomy below), then normalized
METADATA beside the enum, never encoded in it: `backend`,
`provider`, `profile`, `requested_model`, `effective_model` (null
when unverifiable — never silently equal to requested),
`quota_pool`, `exit_code`, `retry_after_sec`/`reset_at` (nullable),
`upstream_origin` (sanitized), `evidence` (`{method:
structured|regex, confidence, pattern?, source_artifact?}`),
`artifacts`. The taxonomy classifies CAUSE, never provider wording
and never routing action:

`quota_exhausted` — a shared allowance is spent (subscription
session/weekly limits); scoped to the quota pool, typically
hours-long. NOT the same as:
`rate_limited` — short-horizon throttling (429/Retry-After); the
two must not poison the same routing state.
`unavailable` — provider-side outage/overload/5xx.
`transport` — network/connection/DNS/proxy failure reaching the
provider.
`auth` — credential or billing-configuration rejection; never
looks like "try another profile".
`invalid_request` — the request itself was malformed or exceeds
THIS profile's declared capabilities (context window, tool
protocol); scoped to profile×task, not provider health.
`denied` — policy/compliance/protected-path refusal; carried so
B can enforce the umbrella's hard rule that a denial is never
rerouted around. (Kept as a cause class beyond the reviewer's
core eight because Scenario 8 makes it load-bearing.)
`execution` — the backend ran and the agent/task failed (tests,
lint, review); NOT a provider event; disposition belongs to
#190.
`unknown` — unmatched output; FAILS CLOSED: no retry, no
failover semantics may ever attach to it by default.

B owns the mapping failure_class -> routing action; A normalizes
cause only. The classifier (`scripts/lib/routing-result.sh`) maps
exit code + captured output to this contract. Fixtures are CAPTURED
real output (seeded from the cooldown supervisor's usage-limit
corpus); each fixture pins raw output -> exactly ONE classification,
and the mutation set includes weakening an identifying pattern so
the wrong class (or non-fail-closed `unknown` handling) is caught.
Regex-derived classifications always record method and confidence.
Increment A wires NOTHING into the driver — B consumes this
contract.
