# Tasks: wiki-studio 0.6.0 — safe changes (Release A)

<!-- One `## US<n>:` group = one auto-build phase. [US#]/FR tags trace to spec.md. -->
<!-- Read first: CLAUDE.md, spec.md, plan.md. The 22 October reproductions in the review are the acceptance tests. -->
<!-- Run per phase: poetry run ruff check src/ tests/ eval/ && poetry run ruff format --check src/ tests/ eval/ && poetry run mypy src/ && poetry run pytest -q -p no:cacheprovider --cov=wiki_studio --cov-fail-under=80 -->
<!-- Every new source file starts with the two-line EGOGE / Apache-2.0 header. Standard library only. Never rewrite an archived plan.json or preview. No production code may pause promotion on an environment variable. -->

## US1: Commit scope, the wiki lock, receipts

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 1 | | Scope `_commit_stage_to_wiki` to the patch-set's edit paths plus this proposal's archive directory; scope both collectors (`*.md` and `.audit/proposals/*/plan.json`) (FR-001) | `src/wiki_studio/promoter.py` | build | [ ] |
| 2 | | `wikilock.py`: `WikiLock(wiki_dir, timeout)` context manager; path `<resolved-wiki-parent>/.<wiki-dir-name>.wiki-studio.lock`; `fcntl.flock` backend on POSIX, `msvcrt.locking` on Windows; diagnostics (PID, host, start time) written into the file, never used for ownership; no delete or recreate; timeout → `PromoteApplyError(reason="lock_timeout")` exit 10 (FR-002) | `src/wiki_studio/wikilock.py`, `src/wiki_studio/errors.py` | build | [ ] |
| 3 | | Hold the lock in `promote` from before staging to after the archive move; take it in `propose --promote` and in the ingest-log append; add `--lock-timeout` and `WIKI_STUDIO_LOCK_TIMEOUT`; remove the "single-process" comment (FR-002) | `src/wiki_studio/promoter.py`, `src/wiki_studio/audit.py`, `src/wiki_studio/cli.py`, `src/wiki_studio/api.py` | build | [ ] |
| 4 | | Receipts: archive dir `<name>-<sha256(plan.json)[:12]>`; copy `plan.json` and `preview/` byte-identical; write `receipt.json` (outcome, written paths, `unguarded_paths`, lock wait, timestamps, plan and preview digests, `promoter` = package name, version, entry point); committed outcomes only (FR-003) | `src/wiki_studio/promoter.py`, `docs/patch-set-format.md` | build | [ ] |
| 5 | | Retry: a proposal already under `.applied/` returns the receipt's outcome with no writes; a committed-but-unmoved proposal is detected by plan digest and only moved (FR-004) | `src/wiki_studio/promoter.py` | build | [ ] |
| 6 | [P] | CI: one Windows job running `tests/test_wikilock.py`; or narrow the `Operating System` classifier to POSIX in this release (FR-002) | `.github/workflows/ci.yml` or `pyproject.toml` | build | [ ] |
| 7 | | Tests: focused commit-scope (stage both, commit sequentially); subprocess interleaving via `tests/helpers/promote_bootstrap.py` that patches the post-stage step then calls `cli.main` (first held after staging, second waits, both land); public operations serialise before staging; aliased wiki dirs share one lock; failure during commit releases the lock; two concurrent ingest-log appends; separate proposal dirs; same-named proposals archive separately; retry semantics; lock backends parametrised (FR-001..FR-004) | `tests/test_promote_concurrency.py`, `tests/test_wikilock.py`, `tests/helpers/promote_bootstrap.py` | build | [ ] |

**Checkpoint US1** — verify before continuing:
- [ ] The 22 October interleaving reproduction now keeps both pages
- [ ] Lock file is outside the wiki; `lint` and staging never see it
- [ ] Full gate green

---

## US2: Revision preconditions

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 8 | | `PageEdit.base_sha256: str \| None = None` (last, default); `plan.json` `edits[].base_sha256` written when present and read back; document the optional key (FR-005) | `src/wiki_studio/proposal.py`, `src/wiki_studio/ingestor_multi.py`, `src/wiki_studio/promoter.py`, `docs/patch-set-format.md` | build | [ ] |
| 9 | | `api.read_page(path, paths)` → bytes, text, sha256 from one read; `wiki-studio read <path> [--json]`; `find` unchanged except it does not hash; document the read-draft-record procedure (FR-006) | `src/wiki_studio/api.py`, `src/wiki_studio/cli.py`, `README.md` | build | [ ] |
| 10 | | Hash capture: ingest attaches sha256 to each captured candidate page in `wiki_state` and carries it into the edits it writes, ignoring anything the backend returns for it; `propose --from` reads `<draft>/.base.json` and never the live page for hashes; `api.propose` passes caller-supplied hashes through (FR-007) | `src/wiki_studio/prompt.py`, `src/wiki_studio/ingestor_multi.py`, `src/wiki_studio/ingestor.py`, `src/wiki_studio/api.py`, `src/wiki_studio/cli.py` | build | [ ] |
| 11 | | Preconditions under the lock, after staging and before commit: create requires absence; appends apply to current content; hashed update requires equality; mismatch → `PromoteValidationError` exit 9, nothing written (FR-008) | `src/wiki_studio/promoter.py` | build | [ ] |
| 12 | | Unhashed update: exit 9 with the two remedies; `--allow-unguarded-updates` / `allow_unguarded_updates=True` applies it and records it; `PromoteResult.unguarded_paths` and `.warnings`; help and docs say "compatibility mode with incomplete conflict protection" (FR-009, FR-010) | `src/wiki_studio/promoter.py`, `src/wiki_studio/api.py`, `src/wiki_studio/cli.py`, `README.md` | build | [ ] |
| 13 | | Dry run: lock, stage, check preconditions under the lock, release, validate the snapshot; no wiki content, receipt or proposal change; help text says point-in-time (FR-011) | `src/wiki_studio/promoter.py`, `src/wiki_studio/cli.py` | build | [ ] |
| 14 | | Tests: early interval (read A, other writer commits A′, replacement from A exits 9); late interval (change between propose and promote); conflicting edits to one page; concurrent create of one path; appends from two legacy proposals both land; legacy create lands; legacy update exits 9, lands under the option and is recorded; stale `.base.json` exits 9, missing manifest is unguarded; backend cannot set hashes; dry run holds the lock only for the check and writes nothing (FR-005..FR-011) | `tests/test_promote_preconditions.py`, `tests/test_api.py`, `tests/test_propose.py` | build | [ ] |

**Checkpoint US2** — verify before continuing:
- [ ] `wiki-studio read index.md --json` prints content and sha256 from one read
- [ ] A stale replacement exits 9 through both `promote` and `api.promote`
- [ ] Full gate green

---

## US3: Containment

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 15 | | Staging refuses any symlink inside the wiki; commit re-checks with `os.lstat` under the lock; write targets checked with `resolve()` against the resolved wiki dir (FR-012) | `src/wiki_studio/promoter.py` | build | [ ] |
| 16 | | Preview pointers in `plan.json` rejected before reading when absolute or resolving outside the proposal dir (FR-012) | `src/wiki_studio/promoter.py` | build | [ ] |
| 17 | | Link classification in `lint_wiki`: web URLs excluded; wiki-page targets must resolve inside the wiki; other local targets inside the root or an allowed source root; absolute and root-escaping targets are violations; `../` inside the root legal; index entries outside the wiki are violations (FR-013) | `src/wiki_studio/lint.py`, `src/wiki_studio/paths.py` | build | [ ] |
| 18 | | `_extract_index_links` applies the same rule as a defence, shared by `find`, `query` and the eval selector; both evaluation runs byte-identical (FR-013) | `src/wiki_studio/querier.py`, `src/wiki_studio/api.py` | build | [ ] |
| 19 | | Tests: symlinked page; symlinked parent dir; absolute link in a page; absolute index entry (lint and promote reject); `../` leaving the root; `../` inside the root allowed; source reference outside the wiki inside the root allowed; web URL ignored; escaping preview pointer rejected before any read (FR-012, FR-013) | `tests/test_containment.py`, `tests/test_lint.py` | build | [ ] |

**Checkpoint US3** — verify before continuing:
- [ ] `find` on a wiki whose index links outside it: lint fails first; `find` lists nothing outside the wiki
- [ ] `python -m eval.navigation.run` and the run-2 invocation reproduce both `results.json`
- [ ] Full gate green

---

## US4: Citation evidence

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 20 | | Validate each fragment against the captured `index_md` and `pages_content` after whitespace normalisation; non-empty answer requires a citation; abstention form kept; error names the page (FR-014) | `src/wiki_studio/querier.py` | build | [ ] |
| 21 | [P] | Docs: the check verifies quotation against the prompt snapshot, not logical support (FR-014) | `README.md` | build | [ ] |
| 22 | | Tests: forged fragment rejected; verbatim accepted; whitespace variant accepted; no citations rejected; abstention accepted; live page changed during the backend call — original-prompt fragment still validates, new-file-only fragment is rejected; test backend fixture satisfies the rule (FR-014) | `tests/test_query_evidence.py` | build | [ ] |

**Checkpoint US4** — verify before continuing:
- [ ] A backend reply quoting text absent from the prompt exits 4
- [ ] Full gate green

---

## US5: Honest guarantees and release 0.6.0

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 23 | | Replace "atomically" (README line 79 and promote section, SECURITY line 32, promoter docstrings) with the validated / serialised on one machine / rolled back on failure / not crash-safe wording; document the lock's scope; describe the fact and stale-source checks as heuristics (FR-015) | `README.md`, `SECURITY.md`, `src/wiki_studio/promoter.py`, `src/wiki_studio/fact_diff.py`, `src/wiki_studio/health_lint.py` | build | [ ] |
| 24 | | CHANGELOG `[0.6.0]`: Added, Changed, Security (credited), Upgrade notes per operation, Limitations (memkernel outer rollback); no statement about memkernel's next release (FR-016) | `CHANGELOG.md` | build | [ ] |
| 25 | | Version 0.6.0 in `pyproject.toml`, `__init__.py`, the contract test; banner pinned to `v0.6.0`; SECURITY supported versions; agent arm stays at 0.4.1 (FR-016) | `pyproject.toml`, `src/wiki_studio/__init__.py`, `tests/test_cli_contract.py`, `README.md`, `SECURITY.md` | build | [ ] |

**Checkpoint US5** — verify before continuing:
- [ ] `grep -rn "atomic" README.md SECURITY.md src/wiki_studio/promoter.py` shows only qualified uses
- [ ] `poetry run wiki-studio --version` prints 0.6.0; `poetry build` succeeds
- [ ] Full gate green

---

## Final Verification

- [ ] Type checker: 0 errors; linter and formatter: 0 errors
- [ ] Full suite green with coverage at or above 92 percent; Windows lock job green or classifier narrowed
- [ ] Single-writer test, CLI contract tests, `tests/test_schema.py` and both evaluation runs' determinism tests green
- [ ] Exit codes unchanged (0, 2..11); 9 for revision conflicts, 10 with `reason="lock_timeout"`
- [ ] No archived `plan.json` or preview is ever rewritten; receipts exist only for committed promotes
- [ ] Every 22 October reproduction is a passing regression test through both `promote` and `api.promote`
