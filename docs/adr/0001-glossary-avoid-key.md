# ADR 0001: Optional `avoid` key on glossary entries

- Status: accepted
- Date: 2026-10-20
- Issue: [#28](https://github.com/gosha70/wiki-studio/issues/28)
- Feature: `specs/wiki-studio-0-5-0/` (FR-004, FR-005, FR-008, FR-009)

## Context

The page schema is a published contract shared with memkernel's
`WikiExporter` and `WikiImporter` and with code-copilot-team's wiki.
`CLAUDE.md` requires a decision record for any change to it.

Issue #28 asks for a list of synonyms on each glossary entry, so a check can
flag a page that uses a synonym instead of the glossary term, and so the
missing-cross-links check counts a synonym as a mention. The issue's example
is a flow list, `avoid: [alignment check, origin check]`.

## Decision

A glossary entry MAY name the terms to avoid. The key is optional. No
existing key, page type or directory changes, and every existing page stays
valid.

**Per-file glossary page.** A page with `page_type: glossary` may carry one
frontmatter line:

```yaml
avoid: alignment check, origin check
```

**`glossary/index.md` entry.** The first non-blank line after `### <term>`
may read:

```markdown
Avoid: alignment check, origin check
```

**The one accepted form.** The value is one line of comma-separated terms.
It is unquoted or wrapped in one pair of double quotes. A term cannot contain
a comma, a double quote (`"`) or a backslash (`\`). Terms are split on commas
and stripped.

**Every other form is an `avoid-format` finding** and contributes no terms:

- a block list (`avoid:` followed by `  - term` lines) or an empty `avoid:`;
- a value that starts with `[` (the flow list);
- a single-quoted value;
- a term that contains `"` or `\`, raw or escaped;
- an empty term after splitting (`a,,b`);
- an index `Avoid:` line that is not the entry's first line, is bulleted, or
  is followed by bullet items;
- one avoid term listed under two canonical terms.

`avoid:` on a page whose `page_type` is not `glossary` is ignored.
`yaml_lite` does not change; the reader reads the raw frontmatter line.

Avoid terms of per-file glossary pages count as mentions of the page in the
missing-cross-links check. Index-entry terms feed only the term lock, because
index entries are not entities.

## Why not the issue's flow list

- `yaml_lite` has no flow sequences. It reads `[a, b]` as one string.
- A block list parses in `yaml_lite`, but memkernel's frontmatter parser
  ignores indented lines outside `sources:`. After a memkernel parse and
  render it becomes `avoid: ""`.
- A single-line scalar is the only form that both parsers keep.

## memkernel round trip, as observed

From memkernel's code (`memkernel/wiki/pages.py` and `memkernel/wiki/sync.py`):

- **Export never rewrites a glossary page.** The exporter has no glossary
  mapping. It skips memories imported from the wiki and any target file that
  already exists.
- **Import drops `avoid:`.** The importer maps `glossary` to a fact memory and
  passes only title, body, tags, source and importance to `retain`, never the
  page's extra keys.
- **A direct `parse_page` and `render_page` call keeps a single-line scalar
  only within the accepted syntax.** memkernel keeps unknown keys in
  `WikiPage.extra` and writes them back. Its `_unquote` strips one pair of
  matching outer `"` or `'` and decodes nothing. Its `_quote` wraps a value in
  `"` when it has any of `:#"'[]{}` or edge whitespace, escaping `\` and `"`.
  So a term with `"` or `\` changes on every round trip (`the "old" gate`
  returns as `the \"old\" gate`). A single-quoted value changes too:
  `yaml_lite` decodes `''` to `'` and memkernel does not, so `'it''s, ok'`
  returns as `it''s, ok`. The accepted syntax excludes these forms, and the
  round trip is claimed only for that syntax.
- **Not determined:** whether memkernel's Memory model could store frontmatter
  extras elsewhere.

`tests/test_avoid_roundtrip.py` checks the complete sequence in this
repository. It copies memkernel's `_unquote` and `_quote` as fixtures, citing
their source lines. Accepted values read back as the same terms. Unsupported
values are refused on the first read, and nothing is asserted about them
after memkernel.

## Requirement on memkernel

Any memkernel path that parses and re-renders an existing wiki page MUST keep
unknown top-level scalar keys unchanged. It does so today for values in the
accepted syntax.

## Follow-up for memkernel

Open a memkernel issue to:

- add the same round-trip test for `avoid:` on memkernel's side;
- decide whether imported glossary memories should carry the avoid terms.

Neither is assumed done in this cycle.

## Consequences

- Authors write one line of terms. A term cannot contain `,`, `"` or `\`.
- A malformed list is reported, never silently changed or dropped.
- code-copilot-team's local `page-types.md` copy does not describe the key
  until it syncs from the packaged copy.
