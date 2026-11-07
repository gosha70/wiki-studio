# Tasks: wiki-studio 0.9.0 — conflict callouts

<!-- One `## US<n>:` group = one auto-build phase. [US#]/FR tags trace to spec.md. US<n> is pitch scope S<n>. -->
<!-- Read first: CLAUDE.md, spec.md, plan.md, specs/pitches/71-conflict-callouts/pitch.md, docs/adr/0001-glossary-avoid-key.md. -->
<!-- Run per phase: poetry run ruff check src/ tests/ eval/ examples/ conformance/ && poetry run ruff format --check src/ tests/ eval/ examples/ conformance/ && poetry run mypy src/ && poetry run pytest -q -p no:cacheprovider --cov=wiki_studio --cov-fail-under=92 -->
<!-- Every new .py file starts with the two-line EGOGE / Apache-2.0 header. Standard library only. No frontmatter key, page type or directory; schema.version stays 2, findings_version stays 1, no new capability. No new verb, flag, exit code, MCP tool or dependency. No model, backend or lock on any path from findings, approve or review_state; _check_contradictions untouched. No structural-lint or approve rule about callouts. lint.py, promoter.py, review.py, prompt.py, health_lint.py, contract.py, schema/__init__.py and mcp_adapter/ are never edited. No memkernel code or doc edits. No commit, push or branch change inside the session; the driver owns git. Never weaken or skip a test. -->

## US1: The form, documented, and ADR-0004

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 1 | | ADR-0004 "Conflict callout" in ADR-0001's form: Status accepted, Date, Issue #71, Feature `specs/wiki-studio-0-9-0/` (FR-001, FR-002, FR-004, FR-007, FR-020); Context (issue #71; memkernel's `_parse_frontmatter` keeps scalars and `sources:` only, a list key renders back empty; ADR-0001 precedent); Decision (the optional form with the marker-line link, both pages, the resolution rule, no key, `schema.version` 2, `findings_version` 1, no capability, kinds in `findings` only, no lint or `approve` rule); Why not (frontmatter list, scalar key, `## Disagreements` section, resolved mark, `conflict-format` kind); memkernel round trip as observed (import retains title + body; export never writes back; 0.7.0's curation report ranks an unknown kind last); Requirement on memkernel (none new); Consequences (override wikis see the form after sync; curators write callouts) (FR-001) | `docs/adr/0004-conflict-callout.md` | build | [ ] |
| 2 | | `citation-rules.md` section `## When sources disagree` between "When a source disappears" and "Inline pointers in prose": the marker line (`> [!conflict] Disagrees with [<title>](<path>.md)`, case-insensitive marker, optional `+`/`-` fold sign, the first `.md` link on that line is the other page), the sources lines (`> This page: … That page: …`, not parsed), placement (body, outside fenced code; one callout per other page; the same callout back on the other page in the same patch-set), rendering, what is checked, the example pair as two fenced `markdown` blocks each introduced by a line ending in the backticked wiki-relative path (two complete pages citing different sources for one claim, each naming the other), the resolution rule (two `update` edits removing both callouts, the deciding source added to `sources:` of the page that keeps the claim, one `log.md` line `- YYYY-MM-DD — resolve <slug> (<page-type>): conflict with <other-slug>, decided by <source>`; `fact_warnings` expected and advisory; no resolved mark; receipt, archived plan and `log.md` keep the history), known limits (line-based; marker starts the line after ≤3 spaces and `>`; list items, lazy continuation, nested quotes, HTML blocks not recognised; a link off the marker line is not the other page) (FR-002, FR-004) | `src/wiki_studio/schema/citation-rules.md` | build | [ ] |
| 3 | [P] | `WIKI_MAINTAINER.md`: the two-page case in the curator loop at step 5 (mark both pages with the callout pair in one patch-set; resolve by the rule); Escalation keeps `open-questions/` for more than two pages or no sources, and says a callout may link such an entry. `lint-rules.md` 161-162: the linter still does not detect contradictions; a disagreement marked with the callout pair is reported by `wiki-studio findings` as `open-conflict`, `conflict-one-sided` or `conflict-dangling`. `page-types.md` untouched (FR-003) | `src/wiki_studio/schema/WIKI_MAINTAINER.md`, `src/wiki_studio/schema/lint-rules.md` | build | [ ] |

**Checkpoint US1** — verify before continuing:
- [ ] `docs/adr/0004-conflict-callout.md` has the eight sections of ADR-0001 and names FR-001, FR-002, FR-004, FR-007 and FR-020
- [ ] The `## When sources disagree` section holds exactly two fenced `markdown` blocks before any other fence, each introduced by a line ending in a backticked `.md` path; the two pages written to a temporary wiki with an `index.md` pass `poetry run wiki-studio lint` (manual check; FR-013 automates it in US2)
- [ ] `git diff main -- src/wiki_studio/schema/page-types.md src/wiki_studio/schema/ingest-rules.md` is empty and `poetry run pytest -q tests/test_schema_fingerprint.py` passes unchanged
- [ ] Full gate green

---

## US2: The model-free check in `findings`

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 4 | | `conflicts.py`: `CONFLICT_MARKER = "[!conflict]"`, the marker regex built from it (`^ {0,3}>[ \t]*\[!conflict\][+-]?(?=[ \t]\|$)`, case-insensitive), a `Callout` record (`page`, `line`, `raw_target`, `resolved`), `scan_callouts(paths) -> dict[str, list[Callout]]` over `default_review_pages` minus pages carrying `superseded_by`, each read once through `read_live_page`, body after the frontmatter, fenced code skipped with `open_fence`/`closes_fence`, the first `health_lint._MD_LINK_RE` match on the marker line only (targets ending in `.md`; fragment dropped), resolved from the page's directory inside the resolved wiki or `None` for an escape or a URL-scheme target; whole review set read regardless of scope; no lock, no backend, no write (FR-005, FR-006, FR-010a) | `src/wiki_studio/conflicts.py` | build | [ ] |
| 5 | | Pairing in `conflicts.py` (`conflict_findings(paths) -> list[Finding]`): per page the deduplicated target set (repeats once, FR-010b); dangling when no `.md` link, outside the wiki, not a file, not in the review set, the page itself, or `superseded_by` on the target, with the six reason phrases of FR-007 and the line number in the description, `pages == (P,)`; matched when `Q` targets `P` back → one `open-conflict` with `pages == (min, max)` naming the resolution rule; else `conflict-one-sided` with `pages == (P, Q)`; a dangling callout never pairs; order `open-conflict` (by pages), `conflict-one-sided` (by pages), `conflict-dangling` (by page, line) (FR-007) | `src/wiki_studio/conflicts.py` | build | [ ] |
| 6 | | `findings.py`: `KIND_OPEN_CONFLICT`, `KIND_CONFLICT_ONE_SIDED`, `KIND_CONFLICT_DANGLING` appended to `FINDING_KINDS` in that order; `findings()` extends `found` with `conflict_findings(paths)` after `_page_findings`, before the existing scope filter and `counts`; the scope rule at 192-199 applied to the new kinds unchanged (FR-005, FR-008, FR-009); module docstring lists the kinds (FR-015) | `src/wiki_studio/findings.py` | build | [ ] |
| 7 | | Fixture wiki `tests/fixtures/conflicts/` (manifest, `index.md` linking every page, `log.md`): matched pair; one-sided; missing target; root `index.md` target; self target; superseded target that carries a callout back; fenced callout; marker line with no `.md` link; FR-010a both cases (link on the next line only; sources line linking `../../docs/x.md` after the marker-line page link; a non-`.md` web link before the page link; a web `.md` link first, dangling as outside the wiki); FR-010b three cases (repeat with a callout back; repeat without; `A`↔`B`, `A`↔`C`); `[!CONFLICT]+`; a page with no callout (FR-011) | `tests/fixtures/conflicts/` | build | [ ] |
| 8 | | Tests: the fixture's expected findings as one literal compared whole (`kind`, `pages`, reason words); the acceptance cases on `ApprovalCase` wikis (matched → exactly one `open-conflict`; one-sided → `(P, Q)`; each dangling reason; no callout → none; fenced → none); FR-010 cases; `--paths` on a pair → `pages == (in-scope,)`, `pages_checked == 1`; `cli.main(["findings"])` text with `[open-conflict / warning]` and `findings --json` with `counts` naming the three kinds and `findings_version == 1`; order; `conflicts` imported only by `findings.py` (an `ast` scan of `src/wiki_studio/`); `lint --health --strict` exit 0 on the fixture minus the missing-target page; `TestNoBackend` green on a callout fixture (FR-009, FR-011, FR-012) | `tests/test_conflict_callouts.py`, `tests/test_findings.py` | build | [ ] |
| 9 | | `tests/test_findings.py::build_fixture_wiki` gains a matched pair, a one-sided callout and a dangling callout; `test_every_kind_is_produced_on_a_fixture_wiki` and the `counts` equality stay as written and pass (FR-012) | `tests/test_findings.py` | build | [ ] |
| 10 | | The documented example as input: read the packaged `citation-rules.md`, take `## When sources disagree`, extract the first two `markdown` fences and the backticked `.md` path on each introducing line, write them into a fresh wiki with an `index.md`, assert exactly one `open-conflict` naming both and no other conflict kind, and `lint` exit 0; fail naming what is missing (FR-013) | `tests/test_conflict_callouts.py` | build | [ ] |
| 11 | | The resolution rule through the gate: build a matched pair with `api.propose`/`api.promote`; (a) a patch-set of two `update` edits with `base_sha256` removing both callouts plus one `append-log` promotes with exit 0 through the CLI and the three kinds report nothing for the pair; a one-callout patch-set promotes and leaves exactly one `conflict-one-sided`; (b) the page that keeps the claim carries the deciding source in `sources:`; (c) `log.md` ends with exactly the FR-004 line; `plan.json` carries `fact_warnings` on the updates, the CLI prints them to stderr, exit stays 0 (FR-014) | `tests/test_conflict_callouts.py` | build | [ ] |

**Checkpoint US2** — verify before continuing:
- [ ] `poetry run wiki-studio findings --json --wiki-dir tests/fixtures/conflicts/wiki` (or the fixture's layout flags) prints `counts` with `open-conflict`, `conflict-one-sided` and `conflict-dangling` and exits 0 with no backend installed
- [ ] `git diff main -- src/wiki_studio/lint.py src/wiki_studio/promoter.py src/wiki_studio/review.py src/wiki_studio/prompt.py src/wiki_studio/health_lint.py src/wiki_studio/contract.py src/wiki_studio/schema/__init__.py src/wiki_studio/mcp_adapter/` is empty
- [ ] `grep -rn '\[!conflict\]' src/wiki_studio/*.py` finds only `conflicts.py`'s constant and regex
- [ ] `poetry run wiki-studio findings --help` shows no new flag; `tests/test_package_boundaries.py` passes
- [ ] Full gate green

---

## US3: Surfaces and the reference docs

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 12 | [P] | `api.findings` docstring (833-846) and the `findings` parser help (416-420) list the three kinds with one clause each (FR-015) | `src/wiki_studio/api.py`, `src/wiki_studio/cli.py` | build | [ ] |
| 13 | [P] | `docs/knowledge-contract.md` Findings: three table rows (FR-016's wording); the sentence that kinds may be added within `findings_version: 1` and are read by name, an unknown kind being a warning the consumer does not classify; the note at 413 keeps "`contradiction` never appears" and adds that a recorded disagreement is reported by the three conflict kinds; no `info`, format or capability change (FR-016) | `docs/knowledge-contract.md` | build | [ ] |
| 14 | [P] | README `wiki-studio findings` (248-262): the kinds sentence names the three and links the `citation-rules.md` section (FR-017) | `README.md` | build | [ ] |
| 15 | | `tests/test_mcp_adapter.py`: beside `test_findings_and_review_state_shapes`, assert the `findings` tool's `counts` has the three keys; `docs/mcp-adapter.md` unchanged (FR-017) | `tests/test_mcp_adapter.py` | build | [ ] |
| 16 | [P] | CHANGELOG `[Unreleased]` Added: the form (marker-line shape), ADR-0004, the three kinds with severity; Notes: no frontmatter key, `schema.version` 2 and `findings_version` 1 unchanged, no new verb, flag, exit code, MCP tool, capability or dependency, no lint or `approve` rule, no prompt code change; the Fixed entry stays (FR-018) | `CHANGELOG.md` | build | [ ] |

**Checkpoint US3** — verify before continuing:
- [ ] `git diff main -- docs/mcp-adapter.md src/wiki_studio/mcp_adapter/` is empty
- [ ] `poetry run wiki-studio findings --help` names `open-conflict`, `conflict-one-sided` and `conflict-dangling`
- [ ] Every kind named in `docs/knowledge-contract.md`'s Findings table is in `FINDING_KINDS` and vice versa (manual check against `findings.py`)
- [ ] Full gate green

---

## US4: Approval and memkernel import unaffected

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 17 | | Approval: a matched pair through `api.propose`/`api.promote`, `api.approve` both, `review_state` reads `approved` for each; `lint` exit 0 and `lint --health --strict` exit 0 on that wiki; `findings` reports the one `open-conflict`. A page whose marker line has no `.md` link promotes (no structural rule) and `findings` reports `conflict-dangling` (FR-019) | `tests/test_conflict_callouts.py` | build | [ ] |
| 18 | | The copied `v0.6.0` parser: `_FRONTMATTER_RE` (20), `_unquote` (45-49), `_parse_frontmatter` (52-86), `parse_page` (89-110), `_quote` (113-117), `render_page` (120-142) from `gosha70/memkernel` `src/memkernel/wiki/pages.py` at tag `v0.6.0`, each with the header "Copied from … at tag v0.6.0, `<name>` lines <a>-<b> (citation verified <date>, see the spec FR-020). Test fixture only."; `WikiPage` as a dataclass stand-in named as the one departure; asserts on the FR-013 pages and a mid-body callout: `body` holds the callout byte for byte, `extra` adds no key, `sources` equal, `render_page` keeps every frontmatter line (blank line after `---` the only difference), parse→render→parse same `body` (FR-020) | `tests/test_conflict_memkernel_roundtrip.py` | build | [ ] |
| 19 | | Governed import (cut first): in `test_memkernel_clean_install.py`, skipped without memkernel, an approved page carrying a callout pair is imported by `WikiImporter(service, wiki).import_pages()` and the memory's `content` holds the marker line; the `memkernel-compat` job unchanged (FR-021) | `tests/integration/test_memkernel_clean_install.py` | build | [ ] |

**Checkpoint US4** — verify before continuing:
- [ ] `git diff main -- src/wiki_studio/lint.py src/wiki_studio/promoter.py src/wiki_studio/review.py src/wiki_studio/prompt.py src/wiki_studio/health_lint.py src/wiki_studio/contract.py src/wiki_studio/schema/__init__.py src/wiki_studio/mcp_adapter/` is empty
- [ ] `poetry run pytest -q tests/test_conflict_memkernel_roundtrip.py` passes with the six copied functions' line ranges matching `git show v0.6.0:src/memkernel/wiki/pages.py` in a memkernel checkout (or the session reports plainly that it could not read the tag and the ranges are the spec's)
- [ ] In a venv with the wheel and `memkernel==0.6.0`, `python -m pytest -q -p no:cacheprovider -rs tests/integration/test_memkernel_clean_install.py` passes (or the session reports plainly that it could not install memkernel, and the `memkernel-compat` job on the PR is the first run)
- [ ] Full gate green

---

## US5: Release 0.9.0

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 20 | | Version 0.9.0 in `pyproject.toml` (6), `src/wiki_studio/__init__.py` (5), README's version comment (26) and the `==` pins on `docs/quickstart-memkernel.md` (27, 38); CHANGELOG `[Unreleased]` entries move under `[0.9.0]` (undated); any cut named there (FR-022, FR-024) | `pyproject.toml`, `src/wiki_studio/__init__.py`, `README.md`, `docs/quickstart-memkernel.md`, `CHANGELOG.md` | build | [ ] |
| 21 | [P] | Compatibility: a 0.9.0 with memkernel 0.6.0 row naming `memkernel-compat` and the import case, pending until the owner names a green `main` run, only if task 19 landed; otherwise no row (FR-023) | `docs/compatibility.md` | build | [ ] |
| 22 | | Invariant and cut audit: `git diff main -- pyproject.toml` is the version line; the untouched-modules diff is empty; `_check_contradictions` byte-identical; `findings --help` and `wiki-studio --help` show no new flag; exit codes 0, 2..11 unchanged and 1 fatal lint (`tests/test_cli_contract.py`); the single-writer and standard-library scans pass; if FR-021 or the superseded case was cut, the CHANGELOG and the contract table say so and no doc describes an unreported case (FR-024) | `CHANGELOG.md`, `docs/knowledge-contract.md` | build | [ ] |

**Checkpoint US5** — verify before continuing:
- [ ] `poetry run wiki-studio --version` prints 0.9.0; `poetry build` succeeds; `pip install --dry-run` resolves the two `docs/quickstart-memkernel.md` install lines against the built wheel (the `quickstart-memkernel` job's check)
- [ ] `git diff main -- src/` touches only `findings.py`, `conflicts.py`, `api.py` (docstring), `cli.py` (help), `__init__.py` (version) and the three schema markdown files
- [ ] `grep -n "open-conflict\|conflict-one-sided\|conflict-dangling" CHANGELOG.md docs/knowledge-contract.md README.md` names only kinds the build reports
- [ ] Full gate green

---

## Final Verification

- [ ] Type checker: 0 errors; linter and formatter: 0 errors on `src/ tests/ eval/ examples/ conformance/`
- [ ] Full suite green with coverage at or above 92 percent
- [ ] `memkernel-compat`, `memkernel-loop`, `mcp-min`, `mcp-latest`, `quickstart`, `quickstart-memkernel`, `demo-correction-loop` and `build-check` green on the PR
- [ ] No frontmatter key, page type or directory added; `SCHEMA_VERSION` is 2 and `FINDINGS_FORMAT_VERSION` is 1; `CAPABILITIES` unchanged
- [ ] No new verb, flag, exit code (0, 2..11; 1 fatal lint), MCP tool or dependency
- [ ] No model, backend or lock on any path from `findings`, `approve` or `review_state`; `_check_contradictions` and `prompt.py` byte-identical to `main`
- [ ] `lint.py`, `promoter.py`, `review.py`, `health_lint.py`, `contract.py`, `schema/__init__.py` and `mcp_adapter/` byte-identical to `main`; `promoter.py` is the only writer into the wiki
- [ ] `conflicts.py` is imported by `findings.py` only and carries the only occurrences of the marker text in the package
- [ ] The documented example pair and the documented log line are test inputs and pass
- [ ] No memkernel code or doc edited; the copied functions are pinned to tag `v0.6.0`
- [ ] #71 is not closed by the session; the PR body carries `Closes #71`
