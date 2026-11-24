---
page_type: decision
slug: cct-wiki-audit-trail-spec-03
title: '3 — Ingest-log schema'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/wiki-audit-trail/spec.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The file is `knowledge/wiki/.audit/ingest-log.md` (the issue's named
path). Line 1 is the literal marker `<!-- ingest-log schema v1 -->`;
then one NDJSON object per line, append-only. NDJSON (not TSV, not a
bespoke format) is chosen because it is greppable, unambiguous to parse,
and trivially extensible. The per-line `v` lets the format evolve
without rewriting history (lint format-checks each line against the
version it declares). `source_sha` is the SHA-256 lowercase-hex of the
source file's raw bytes — verified: `wiki ingest` accepts only a single
file path today (no directory/stdin/URL); if future ingest gains those
modes, `source_sha` extends using the `proposal_hash` framing recipe
below, which is out of scope here. **External sources are a supported
mode** (`--allow-out-of-repo`, `_path_within_repo` in `__main__.py`), so
`source_path` cannot always be repo-relative: it is recorded as the path
*as used by the run* — `Path.relative_to(repo_root)` POSIX when within
the repo, the supplied path verbatim otherwise — and the boolean
`source_repo_relative` disambiguates the two (no lying about relativity,
no rejecting a supported ingest mode). `reason` is truncated to **240
Unicode codepoints** measured on the gate string *before* JSON escaping,
after collapsing newlines to spaces; if cut, codepoint 240 is replaced
by `…` (U+2026) (i.e. 239 codepoints + ellipsis). `proposal_hash` /
**canonicalization recipe** (recorded verbatim in `audit-rules.md` so
the future cross-referential lint can verify it): sort included files by
repo-relative POSIX path under `LC_ALL=C`; for each emit
`<rel_path>\n` (UTF-8) + raw file bytes + `\n--\n`; concatenate in
order; SHA-256; lowercase hex. Included: `plan.json` + every file under
`preview/` recursively. Excluded: `.ingest-snapshot/` and any path
component beginning with `.`. `wiki lint` validates **format only** in
v1 (marker, JSON parse, keys/types/enums, `ts`, `reason` length); it
does **not** verify that `source_sha` resolves to a real object or that
`proposal_hash` matches an archive — semantic cross-checks need git
object access, would slow every promote, and are deferred to keep lint
cheap, deterministic, and offline.
