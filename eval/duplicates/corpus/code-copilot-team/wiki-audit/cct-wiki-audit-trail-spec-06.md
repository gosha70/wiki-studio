---
page_type: decision
slug: cct-wiki-audit-trail-spec-06
title: '6 — PII / redaction'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-audit-trail/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The
`.audit/` archive holds the same proposal bodies the curator already
reviews before promote, so the human gate that protects the canonical
wiki equally protects the archive. The codebase has no precedent for
redacting *stored* content — only `--debug-unsafe-output` toggles
*stderr* redaction. Introducing an automated PII/secret scrubber would
be unbudgeted machinery with its own failure modes, contradicting the
cheap-footprint appetite. Decision: `.audit/` content is held to the
**same discipline as any wiki page** (citation-rules + curator
accountability; no new scrubber). The 240-char `reason` field is the
only audit content not subject to curator review; this is acceptable
given its size, and the NDJSON line-length validation in `wiki lint`
provides structural protection against accidentally large reasons
leaking through. **Resolved (user, 2026-05-17): confirmed — same
discipline, no scrubber.**
