---
spec_mode: full
feature_id: wiki-studio-0-3-0-path-frame
risk_category: bugfix
status: approved
date: 2026-10-16
---

# Spec: wiki-studio 0.3.0 — one path frame for the ingest prompt, and `info` (issue #11)

<!-- Project constitution: shared/skills/ — copilot-conventions, coding-standards, safety -->

Design references (read before building): issue
[#11](https://github.com/gosha70/wiki-studio/issues/11) with the stderr under
`eval/navigation/ingest-logs/`; `src/wiki_studio/backends/copilot_cli.py`
(`_render_plain_text_prompt`: the `--- {wiki_label}/index.md ---` and
`--- {wiki_label}/{rel_path} ---` headings, the response instructions),
`src/wiki_studio/prompt.py` (`_PATCH_SET_RESPONSE_SCHEMA`),
`src/wiki_studio/ingestor_multi.py` (step 6, building `PageEdit`s),
`src/wiki_studio/proposal.py` (`validate_page_edit_semantics`, `validate_patch_set`),
`src/wiki_studio/paths.py` (`WikiPaths.wiki_label`, `resolve`), `src/wiki_studio/cli.py`.

## Why

Run 1 of the navigation evaluation, with the wiki at a directory whose
root-relative name is one word (`wiki`), lost eight of ten ingests: the
model answered with `wiki/decisions/…` because the prompt shows every wiki
file under a `<label>/` heading and never says that edit paths are
wiki-relative. The defect is present since 0.1.0 for any custom wiki
location. The owner will not release 0.3.0 with it open.

## User Scenarios

### US1: Ingest works at any wiki location (Priority: HIGH)

**Given** a wiki at `<root>/wiki`, `<root>/knowledge/wiki` or outside the root
**When** `wiki-studio ingest <source> --backend claude` runs and the model copies the heading label into an edit path
**Then** the prompt has told the model not to, the one exact `<label>/` prefix is removed before validation, every existing path-safety check still runs, and the patch-set is written

### US2: The resolved layout is visible before anything runs (Priority: MEDIUM)

**Given** any combination of flags, `WIKI_STUDIO_*` variables and defaults
**When** the user runs `wiki-studio info`
**Then** it prints whether the layout is default or custom, every resolved location, where each came from (flag, variable or default), whether the wiki and proposals directories exist, and which schema copy applies; `--json` prints the same as one object; `--version` is unchanged

## Requirements

- **FR-001 (prompt states the frame)**: In multi-page mode (a `wiki_state` in the prompt), the response instructions MUST say that every edit `path` is relative to the wiki directory the headings show as `<label>/`, give the three shapes (`<dir>/<slug>.md`, `index.md`, `log.md`) and say never to start a path with `<label>/`. `_PATCH_SET_RESPONSE_SCHEMA`'s `path` property MUST carry the same rule as its `description`. The legacy single-source prompt is unchanged.
- **FR-002 (strip exactly the configured label)**: `WikiPaths.strip_wiki_label(path)` MUST remove one leading `<wiki_label>/` and nothing else (`wikis/x.md` with label `wiki` is untouched; `wiki/wiki/x.md` becomes `wiki/x.md`). `DefaultMultiIngestor` MUST apply it to every edit path before `validate_page_edit_semantics` and `validate_patch_set`, which run unchanged; `query --file-back` therefore gets the same treatment since it uses the multi-ingestor.
- **FR-003 (`info` verb)**: A sixth verb `info` MUST print the resolved layout: `layout: default|custom` (custom when the wiki or proposals directory came from a flag or variable), `root`, `wiki-dir` (with its label and whether it exists), `proposals-dir` (exists or not), `query-log`, `audit-log`, `schema` (project copy at `<wiki>/schema/` or packaged), each location with its source: `flag`, `env <NAME>` or `default`. `--json` prints one JSON object with the same facts. Exit 0; no file is written. `--version` keeps printing only the version. The verb is additive: the five existing verbs, their flags, help and exit codes do not change; the legacy no-verb shim treats `info` as a verb.
- **FR-004 (tests)**: Tests MUST cover the stripping rule's cases; a stub backend returning `wiki/concepts/x.md` with the wiki at `<root>/wiki` and `knowledge/wiki/concepts/x.md` with the default layout, both ending in a valid patch-set, and `wiki/wiki/concepts/x.md` still failing with the existing message; the rendered multi-page prompt containing the instruction with the configured label and the legacy prompt not; `api.ingest` end to end with a one-word label; `info` in default and custom layouts, text and JSON. The CLI contract tests gain `info`.
- **FR-005 (docs)**: README lists `info` under Verbs and the layout rule under Schema or Environment variables; the Evidence paragraph says the gap is fixed in this release and that run 1 was measured on 0.2.0; CHANGELOG `[0.3.0]` moves the entry from "Known issues" to "Fixed" (keeping the run 1 note) and lists `info` under "Added"; `docs/consumers.md` unchanged.

## Constraints / What NOT to Build

- No normalisation beyond the exact configured label: no stripping of arbitrary directory prefixes, no guessing.
- No change to page types, directories, exit codes, existing flags or help text beyond the new verb.
- No second evaluation run in this feature; it follows under its own protocol.

## Success Criteria

1. The stub-backend tests pass for `wiki`, `knowledge/wiki` and the double-prefix case; `api.ingest` with a one-word label writes a patch-set.
2. `wiki-studio info` in a fresh layout prints `layout: default`; with `WIKI_STUDIO_WIKI_DIR` set prints `layout: custom` and `env WIKI_STUDIO_WIKI_DIR`; `--json` parses.
3. Full gate green; CLI contract tests unchanged except for the added verb; CI green on 3.11–3.13.
