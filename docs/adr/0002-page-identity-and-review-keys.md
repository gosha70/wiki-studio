# ADR 0002: Page identity and review keys

- Status: accepted
- Date: 2026-10-26
- Issue: [#38](https://github.com/gosha70/wiki-studio/issues/38) (Release B), memkernel [#48](https://github.com/gosha70/memkernel/issues/48)
- Feature: `specs/wiki-studio-0-7-0/` (FR-014..FR-016, FR-019, FR-029, FR-033..FR-036)

## Context

The page schema is a published contract shared with memkernel's
`WikiExporter` and `WikiImporter` and with code-copilot-team's wiki.
`CLAUDE.md` requires a decision record for any change to it.

Release B makes curation trustworthy: approval is a recorded fact about one
revision of one page under one policy, and replacement is explicit. That
needs a stable name for a page, a rule that keeps approval out of
frontmatter, a key that says a page was replaced, and a place for
memkernel's own correction key. 0.6.0's schema has none of these.

## Decision

Four optional frontmatter keys are registered and four keys are reserved.
No required key, page type or directory changes, and every existing page
stays valid. The packaged schema moves from `schema.version` 1 to 2
(`SCHEMA_VERSION` in `wiki_studio.schema`); a root manifest written by 0.7.0
declares version 2, and a manifest declaring version 1 is still read.

Every key below is one single-line scalar, `key: value`. ADR-0001 found that
this is the only form that both `yaml_lite` and memkernel's frontmatter
parser keep through a parse and render.

### `page_id`

```yaml
page_id: pg-0123456789abcdef0123456789abcdef
```

- **Form.** `pg-` followed by 32 lowercase hex digits, matching
  `^pg-[0-9a-f]{32}$` (`pg-` + `uuid4().hex`).
- **Assignment.** `propose --from` and multi-page `ingest` (CLI and
  `api.ingest`) give every `create` without one a fresh `page_id`, inserted
  as the last frontmatter line before the closing `---`, before the preview
  is written. The preview, the commit and any approval therefore cover the
  same bytes. `api.propose` assigns only with `assign_page_ids=True`; by
  default it writes a caller's bytes unchanged, so memkernel's creates land
  byte for byte until memkernel opts in.
- **Never rewritten.** A caller-supplied `page_id` is kept. `update`,
  `append-index`, `append-log` and the legacy single-source ingest never
  add one. An existing page gains a `page_id` only through an ordinary
  guarded `update`; there is no automatic backfill.
- **Lint.** The structural linter reports a malformed `page_id` and every
  page that shares a `page_id` with another. Because `promote` lints the
  staged tree, a `create` that copies an existing id is refused (exit 9).
- **Page key.** A page's key is its `page_id` when it has a well-formed
  one, else its canonical wiki-relative path (`posixpath.normpath`, forward
  slashes, no leading `./` or `/`). Approval records, `review_state` and
  findings use the key. Lint already ties `slug` to the file stem and the
  page type to the directory, so any rename changes the page's bytes and
  its review state becomes `stale`. What `page_id` adds: after a rename,
  `review_state` reports `stale` with the earlier record instead of
  `unapproved`, and memkernel can keep one memory identity across the move.

### Reserved approval keys

`approved`, `approved_by`, `approval` and `review_state` are reserved for
the gate's own record. `propose` and `promote` refuse a `create` or
`update` whose frontmatter carries any of them (exit 4, naming the key and
the page). Approval is recorded only by `wiki-studio approve` (or
auto-approval on promote) under `<wiki>/.audit/approvals/`. Frontmatter
never makes a page approved. `status: stable` stays allowed as a lifecycle
label and means nothing for approval.

A search on 25 October 2026 found none of these keys in the frontmatter of
`tests/fixtures/` or of code-copilot-team's `knowledge/wiki/`, so the list
is final.

### `superseded_by`

```yaml
superseded_by: decisions/retry-backoff-v2.md
```

- Carried by the **replaced** page. The value is a wiki-relative path, not a
  `page_id`, so it resolves and lints without `page_id`.
- The structural linter reports a target that, once normalised, does not
  exist, is not a page, is the page itself or is itself superseded (no
  chains, so no cycles). An absolute or escaping target is a violation. A
  broken target after a hand rename is a lint violation.
- `review_state` reports such a page `superseded` whatever its approval
  records say, and `approve` refuses it.

### `corrects` (memkernel-owned)

```yaml
corrects: mem-ref-1, mem-ref-2
```

- memkernel's key: the `memkernel_ref` values a page corrects. It is
  **memkernel-interpreted**. wiki-studio preserves it byte for byte through
  `propose` and `promote` and does not interpret it.
- **The value syntax is not final.** The comma-separated single line is the
  starting proposal. The syntax becomes final when memkernel defines a
  restricted reference-token grammar that excludes commas and ambiguous
  quoting, and this ADR records it. Until then wiki-studio checks nothing
  beyond the single-line scalar form every frontmatter key already has.

### Review state and memkernel's tiers

`review_state` (`approved`, `stale`, `policy-changed`, `unapproved`,
`superseded`) describes a revision of the wiki. It is not a memory tier.
memkernel decides how a state maps to its tiers, when a memory is
withdrawn, and how it sets `Memory.superseded_by`. memkernel records its
side in its own ADR. This repository supplies the shared text and does not
write memkernel's file.

## Why not

- **`page_id` in `superseded_by`.** A path resolves and lints on every
  wiki, including one whose pages have no `page_id` yet, and a reader can
  follow it.
- **Approval in frontmatter.** An author can write anything in
  frontmatter, and a later hand edit would keep the claim. A record keyed by
  the page's exact bytes and the policy goes stale by itself.
- **Assigning `page_id` in `api.propose` by default.** The memkernel bridge
  compares the bytes it exported with the bytes it reads back. Changing them
  without its consent would break that comparison.

## Consequences

- Pages created by agents and ingest carry a stable identity from their
  first revision. Existing pages keep working without one.
- A wiki initialised by 0.7.0 declares `schema.version` 2. A manifest that
  declares version 1 is still accepted, because version 2 only adds optional
  keys.
- code-copilot-team's local `page-types.md` copy does not describe these
  keys until it syncs from the packaged copy.
