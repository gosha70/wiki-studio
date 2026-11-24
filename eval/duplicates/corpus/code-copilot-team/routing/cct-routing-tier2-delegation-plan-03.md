---
page_type: decision
slug: cct-routing-tier2-delegation-plan-03
title: 'Packet envelope — versioned, closed, driver-generated, provenance-bound, IMMUTABLE'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-tier2-delegation/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The packet is the immutable unit C
executes, exactly as B made `result-N.json` the immutable recovery
unit. `scripts/lib/routing-packet.sh` (`rp_*`) builds
`.cct/auto-build/<feature>/routing/packet-<task>-<n>.json`:
`schema_version: 1`, `packet_id`, `packet_digest` (sha256 over the
canonical envelope bytes minus the digest field itself), feature
id, task id + outcome, route class, `allowed_files`,
`forbidden_categories` (effective = floor ∪ declared), `fr_refs`
each with its `statement_sha` and its verifier `test` commands
quoted VERBATIM from `verification.yaml`, `base_commit`,
`current_diff_sha256` (hash and content from the same single
capture), `routing_tasks_sha256` + `verification_spec_sha256`
(digests of the two source artifacts as admitted — the provenance
bindings), prior-evidence refs, `dependencies_complete` (computed,
must be true to build). Envelope validation is closed — unknown
keys refuse (sibling discipline of B's result envelope).
Generation reads only FROZEN inputs (the two artifacts + git
state); regenerating from unchanged inputs is byte-identical. The
Tier-2 model never writes or edits a packet; after build, NOTHING
edits a packet — a changed input means a NEW packet id, never a
mutated envelope.
