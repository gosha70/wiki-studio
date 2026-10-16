---
spec_mode: full
feature_id: wiki-studio-0-3-1
risk_category: bugfix
status: approved
date: 2026-10-16
---

# Spec: wiki-studio 0.3.1 — index/log action rule in the ingest prompt (issue #15), py.typed, tag-pinned banner

Design references: issue [#15](https://github.com/gosha70/wiki-studio/issues/15) with run 2's stderr under `eval/navigation/run2/ingest-logs/` (04, 07, 09); `src/wiki_studio/backends/copilot_cli.py` (EXISTING WIKI STATE text, response instructions); `src/wiki_studio/prompt.py` (`_PATCH_SET_RESPONSE_SCHEMA`); `src/wiki_studio/proposal.py` (`validate_page_edit_semantics`, unchanged); `src/wiki_studio/schema/__init__.py` (`PROMOTABLE_PAGE_TYPES`).

## Requirements

- **FR-001 (state the rule)**: One constant `prompt.INDEX_LOG_ACTION_RULE` MUST say that the root `index.md` changes only through a one-line `append-index` edit and `log.md` only through a one-line `append-log` edit, never as a full page and never with frontmatter; that a `<dir>/index.md` which is itself a content page (`glossary/index.md`, `page_type: glossary`) is edited with `create`/`update` like any content page; and that `create`/`update` are only for the promotable page types (listed from `schema.PROMOTABLE_PAGE_TYPES`, not spelled out). The multi-page response instructions MUST include it; the EXISTING WIKI STATE text MUST name the two actions and say the full index and log are shown for reference only. The patch-set schema's `action` description MUST be the constant and `new_content` MUST say one line for appends. The legacy single-source prompt is unchanged.
- **FR-002 (no leniency)**: Validation is unchanged: a full-page `index.md` edit stays `ContractViolationError` (exit 4) with the existing messages. Nothing is rewritten into an append.
- **FR-003 (py.typed)**: `src/wiki_studio/py.typed` ships in wheel and sdist (PEP 561); a test asserts it is package data.
- **FR-004 (banner)**: The README banner points at `raw.githubusercontent.com/gosha70/wiki-studio/v0.3.1/docs/assets/wiki-studio-banner.png` (the release tag), per the review note on PR #14.
- **FR-005 (release)**: Version 0.3.1 in `pyproject.toml`, `__init__.py`, the version test and the README; CHANGELOG `[0.3.1]` (Fixed, Added, Changed).

## Constraints

- No change to validators, page types, exit codes, verbs or flags. No re-run of the evaluation; run 2 stays as measured on 0.3.0, and `eval/` results must still reproduce.

## Success Criteria

1. Tests: the rendered multi-page prompt contains the rule; the schema carries it; the legacy prompt does not; a stub backend returning a full-page index edit still fails with exit 4 and both existing messages; an `append-index` line is accepted; `py.typed` is package data.
2. The built wheel contains `wiki_studio/py.typed`; `wiki-studio --version` prints 0.3.1; both evaluation runs still reproduce.
3. Full gate green; CI green on 3.11–3.13.
