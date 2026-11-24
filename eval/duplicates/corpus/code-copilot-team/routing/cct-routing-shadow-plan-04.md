---
page_type: decision
slug: cct-routing-shadow-plan-04
title: 'Evidence-set identity, discovery, and binding validation'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-shadow/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

An
evidence set is a directory containing the three artifacts (plus
the ledger-relative evidence files records reference). Discovery
walks operator-configured evidence roots (settings-owned, like the
existing source roots; no default machine scan).
*Identity*: a fourth, EXTERNAL artifact — `manifest.json`
(`benchmarks/schema/evidence-manifest.schema.json`), written
LAST in staging — carries the full fingerprint, the sha256 of
the canonical bytes of ALL THREE artifacts (report included —
a schema-valid edit to report selections or figures must change
the identity, since E2 deliberately recomputes nothing), and an
`evidence_files` map (relative path → sha256) covering every
evidence file the records reference. The set id is the sha256
of the manifest's canonical bytes. Repeated runs with different
outcomes get different ids; byte-identical republication is the
same evidence and correctly the same id. Set ids, never
filesystem paths, are what the API and every evidence reference
speak; serving a referenced evidence file verifies its manifest
hash before returning content.
*Binding validation*, pairwise and exact (routing-run records
deliberately carry only the four shared fingerprint components —
execution_identity is matrix-only by E1's design): the
manifest's THREE artifact hashes against the actual bytes (read
once, hash and parse the SAME bytes); the manifest's stored
fingerprint EQUAL to the report's AND the matrix's full
five-component fingerprint, and its shared four components
equal to EVERY routing-run record's (a manifest whose
fingerprint metadata is fabricated over genuine artifact bytes
is `fingerprint_mismatch` — the pinned mutation); report ↔
matrix on the FULL five-component fingerprint; runs ↔ report
(and runs ↔ matrix) on the four shared components; the report's
`source_artifacts` hashes as a redundant cross-check; every
artifact against its schema (routing_eval.record_check,
fail-closed). The discovered/served set id is ALWAYS
recomputed as sha256(canonical manifest bytes) — the directory
name is a convenience, never trusted.
*Failure vocabulary*, closed and SANITIZED: `missing_artifact`,
`unreadable_artifact`, `schema_invalid`, `hash_mismatch`,
`fingerprint_mismatch`, `path_escape` — each carrying the
artifact enum and a sanitized detail (validator output stripped
of filesystem paths; raw exceptions never serialized). Any
failure makes the set `invalid_evidence`: SET-level, rendered
with its code, never skipped, NO recommendation records derived.
A regression runs the loader against a deliberately sensitive
root pathname across all failure modes (missing, unreadable,
malformed, hash-mismatched, escaping) and asserts no payload
carries any path fragment.
