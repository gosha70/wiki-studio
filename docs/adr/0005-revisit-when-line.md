# ADR 0005: The `Revisit when:` body line, read by `findings`

- Status: accepted
- Date: 2026-11-23
- Issue: [#120](https://github.com/gosha70/wiki-studio/issues/120)
- Feature: `specs/wiki-studio-0-11-0/` (FR-008, FR-032, FR-035)
- Implementation: 0.11.0. `src/wiki_studio/revisions.py` parses the line
  (`revisit_when`) and decides the kind (`revision_changed`), and
  `findings.py` reports it. `tests/test_revision_findings.py` tests both.
  This record states the decision they implement.

## Context

The page schema is a published contract shared with memkernel's
`WikiExporter` and `WikiImporter` and with code-copilot-team's wiki.
`CLAUDE.md` requires a decision record for any change to it.

0.10.0 documented a `Revisit when:` line as part of the optional pattern
convention for `decision` pages (`page-types.md`, `docs/patterns.md`): the
trigger that sends the page back for review. Until now nothing read it.
0.11.0 adds `source-revision-changed` to `findings`. It reports a cited file
that changed in place since its `sha:` in a way the page's anchor check
flags. A curator reading that finding needs the page's own condition beside
it, so the finding quotes the line. A body line that `findings` reads is
part of the contract, so it gets this record, as ADR-0001 registered the
`Avoid:` line and ADR-0004 the conflict callout.

## Decision

A page MAY carry one `Revisit when:` line in its body. The line is optional.
No frontmatter key, page type, directory or H2 changes, and every existing
page stays valid.

**The parse rule** (FR-008). The line is the first body line outside fenced
code whose text, after leading whitespace and an optional list marker (`-`,
`*`, `+`, or a number followed by `.` or `)`), starts with `Revisit when:`.
It is read to the end of that line. The match is case-sensitive. A second
such line is not read. The frontmatter is never searched.

**What reads it.** Only `findings`, and only to quote it.
A `source-revision-changed` finding's description quotes the line from
`Revisit when:` to the end of the line. When the page has no such line, the
description says the page records none. The line never decides whether a
source is flagged: the shipped check (C2, anchor touch) reads the page's
backticked identifiers, `file:line` references and the headings of a changed
Markdown file, not this line. The measured candidates that used the line's
words (C3, C4) did not win (`eval/revisions/report.md`).

**What does not move.**

- `schema.version` stays 2 and `findings_version` stays 1. The kind is
  additive, and `counts` naming it is how a consumer discovers it. No new
  capability.
- Structural lint, `lint --health`, `lint --health --strict` and `approve`
  have no rule for the line. A page without one, or with one in any wording,
  lints and approves as before.
- The line is not checked for form. A page whose line says "not recorded"
  is quoted as written.

## Why not

- **A frontmatter key** (`revisit_when: …`). memkernel keeps a single-line
  top-level scalar (ADR-0002, ADR-0004), so a key would survive. But the
  convention 0.10.0 published, and the pages already written to it, put the
  condition in the body under `## Consequences`. A key would make two places
  to state one condition.
- **Reading the line to decide the flag.** That was candidate C3 (and C4,
  both C2 and C3). The study measured it and selected C2 by the frozen rule.
- **A `revisit-format` kind** reporting a missing or malformed line. Nothing
  in issue 120 asks for it, and the convention stays optional.

## memkernel round trip

The line is body text, like the conflict callout. ADR-0004 records, from
memkernel's code at tags `v0.6.0` and `v0.7.0`, that governed import keeps
the page body as the memory's content, that export never writes a body back
to an existing page, and that a direct `parse_page` and `render_page` keeps
body text byte for byte. The same holds for this line. No memkernel change is
needed.

## Requirement on memkernel

None new. Any memkernel path that parses and re-renders an existing wiki
page keeps the body unchanged, as ADR-0004 records.

## Known limits of the shipped check

The finding that quotes this line comes from C2 with the anchor rule measured
in the evidence PR's post-hoc block: anchors shorter than 4 characters,
anchors with no letter, and the last dotted component of a backticked path
are ignored. Two limits are recorded, not measured or changed:

- A bare file name such as `config.toml` or `package.json` contains no `/`,
  so its last dotted part (`toml`, `json`) is still an anchor.
- An anchor matches anywhere inside a changed line, so a whole anchor can
  match inside a longer word (`test` in `latest`).

## Consequences

- A curator reading `source-revision-changed` sees the page's own
  condition beside the change and decides whether it has arrived.
- A host reads one more key in `findings`'s `counts`, zero included.
- A page with no `Revisit when:` line is still checked; its finding says it
  records none.
