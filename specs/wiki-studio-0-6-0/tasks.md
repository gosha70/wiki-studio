# Tasks: wiki-studio 0.6.0 — safe changes (Release A)

<!-- One `## US<n>:` group = one auto-build phase. [US#]/FR tags trace to spec.md. -->
<!-- Read first: CLAUDE.md, spec.md, plan.md. The 22 October reproductions in the review are the acceptance tests. -->
<!-- Run per phase: poetry run ruff check src/ tests/ eval/ && poetry run ruff format --check src/ tests/ eval/ && poetry run mypy src/ && poetry run pytest -q -p no:cacheprovider --cov=wiki_studio --cov-fail-under=92 -->
<!-- Every new source file starts with the two-line EGOGE / Apache-2.0 header. Standard library only. Never rewrite an archived plan.json or preview. No production code may pause promotion on an environment variable. -->

## US1: Commit scope, the wiki lock, receipts

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 1 | | Scope `_commit_stage_to_wiki` to the patch-set's edit paths plus this proposal's archive directory; scope both collectors (`*.md` and `.audit/proposals/*/plan.json`) (FR-001) | `src/wiki_studio/promoter.py` | build | [ ] |
| 2 | | `wikilock.py`: `WikiLock(wiki_dir, timeout)` context manager; path `<resolved-wiki-parent>/.<wiki-dir-name>.wiki-studio.lock`; `fcntl.flock` backend on POSIX, `msvcrt.locking` on Windows; diagnostics (PID, host, start time) written into the file, never used for ownership; no delete or recreate; timeout → `PromoteApplyError(reason="lock_timeout")` exit 10 (FR-002) | `src/wiki_studio/wikilock.py`, `src/wiki_studio/errors.py` | build | [ ] |
| 3 | | Hold the lock in `promote` from before staging to after the archive move; take it in `propose --promote`, in the ingest-log append and in `audit-flush` while it reads and commits the log; add `--lock-timeout` and `WIKI_STUDIO_LOCK_TIMEOUT`; remove the "single-process" comment (FR-002) | `src/wiki_studio/promoter.py`, `src/wiki_studio/audit.py`, `src/wiki_studio/audit_flush.py`, `src/wiki_studio/cli.py`, `src/wiki_studio/api.py` | build | [ ] |
| 4 | | Receipts: `receipt.json` in the proposal dir with `state`, `submission_digest` (recipe 2 `payload_digest` over `plan.json` and every file under `preview/` with no dot-component exclusion, the snapshot outside the identity; used by both the receipt and the ingest log, equal only for an unchanged proposal; recipe 1 `proposal_hash` kept for records before 0.6.0; `digest_recipe: 2` in the receipt, optional `hash_recipe: 2` on new ingest-log records accepted by the audit lint in `v: 1`; recipe 2 documented beside recipe 1 in `audit-rules.md`; a `preview` pointer that is not a regular file under `preview/` exits 4), the payload captured once under the lock and used for parsing, hashing, staging and archiving (archive written from the capture, original removed only when its digest still matches), numbered-suffix directory creation (`<name>`, `-2`, `-3`, `exist_ok=False`, under the lock) in `write_patch_set_dir` with `ingest` feeding its date-and-stem name, `wiki_target` (`st_dev`, `st_ino` by `os.fstat` on the wiki-directory descriptor taken under the lock; zero means unavailable; resolved path as a diagnostic; staging reads relative to that descriptor on POSIX and by path on Windows, documented as the weaker binding), `plan_sha256`, planned paths with expected post-commit sha256, written paths, `unguarded_paths`, lock wait, timestamps, `promoter` = package name, version, entry point; archive dir names unchanged (`<name>`, `-2`, `-3`); plan, previews and snapshot copied byte-identical (FR-003) | `src/wiki_studio/promoter.py`, `src/wiki_studio/audit.py`, `src/wiki_studio/audit_lint.py`, `src/wiki_studio/ingestor_multi.py`, `src/wiki_studio/api.py`, `src/wiki_studio/schema/audit-rules.md`, `docs/patch-set-format.md` | build | [ ] |
| 5 | | Commit protocol: receipt `committing` + fsync → commit → receipt `committed` + fsync → move to `.applied/`; the receipt tracks only actual writes (no-ops excluded, this proposal's audit artifact included) with pre- and post-commit sha256 each; receipt write failure exits 6 before any commit; retry rules: `committed` → archive from the directory's bytes and remove it when the digest matches, else exit 10 `payload_changed` with no archive, the directory left in place and a message naming the tracked post-commit hashes and the remedy; under `.applied/` → recorded outcome, no writes; `committing` → all tracked writes at pre-state: remove receipt, fresh promote allowed; all at post-state: complete; anything else: exit 10 `uncertain_outcome`; digest recomputed and verified before any "already committed" answer; `wiki_target` compared by device and inode with the invoked wiki before any recovery, archival or outcome report, mismatch → exit 10 `wiki_mismatch`, no usable identity → exit 10 `wiki_identity_unavailable`; archive written from the capture first, original removed only if its digest still matches, else exit 10 `payload_changed` naming the leftover directory and the completed archive with the one-line remedy; manual remedy for `wiki_mismatch` on a restored wiki documented (compare tracked writes, finish afresh or discard by hand); missing or corrupt receipt never means committed (FR-004) | `src/wiki_studio/promoter.py`, `src/wiki_studio/errors.py` | build | [ ] |
| 6 | [P] | CI: one Windows job running `tests/test_wikilock.py`; or narrow the `Operating System` classifier to POSIX in this release (FR-002) | `.github/workflows/ci.yml` or `pyproject.toml` | build | [ ] |
| 7 | | Tests: focused commit-scope (stage both, commit sequentially); subprocess interleaving via `tests/helpers/promote_bootstrap.py` that patches the post-stage step then calls `cli.main` (first held after staging, second waits, both land); public operations serialise before staging; aliased wiki dirs share one lock; failure during commit releases the lock; two concurrent ingest-log appends; ingest append overlapping `audit-flush`; separate proposal dirs; two same-named proposals with byte-identical plans and different previews get different identities and both archive; changing a hidden preview file, an unreferenced preview file or a file outside `preview/` changes the digest or is refused; receipt digest equals the ingest-log hash for an unchanged proposal, and after a curator edit the log entry is unchanged while receipt and archive match the edited bytes and the curator delta; an ingest of the same source while a promote of the earlier proposal is held between capture and archive lands in a new directory, receipt and archive identify the captured bytes, the new proposal stays unpromoted; a directory changed after commit leaves a complete archive and exits `payload_changed`; a process killed between the `committed` rewrite and the archive, followed by an edit to the directory, exits `payload_changed` on retry with no archive, the directory in place and the post-commit hashes in the message; a pre-0.6.0 ingest-log record verifies with recipe 1 and a new record carries `hash_recipe: 2` and passes the audit lint; fault injection after the `committing` receipt, during its write, during the `committed` rewrite and during the archive move, each retried without a replayed append; an update identical to the live page is a no-op excluded from tracking and recovers as not committed; missing and corrupt receipts refused; interrupted promotion retried with `--wiki-dir` and with `WIKI_STUDIO_WIKI_DIR` pointing at another wiki exits 10 `wiki_mismatch` with nothing written to either; wiki A renamed and wiki B created at A's old path, retried with `committing` and with `committed` receipts, both `wiki_mismatch`; `run2_protocol.py`'s `.applied/<name>/plan.json` path still resolves; lock backends parametrised (FR-001..FR-004) | `tests/test_promote_concurrency.py`, `tests/test_promote_recovery.py`, `tests/test_wikilock.py`, `tests/helpers/promote_bootstrap.py`, `tests/test_navigation_eval.py` | build | [ ] |

**Checkpoint US1** — verify before continuing:
- [ ] The 22 October interleaving reproduction now keeps both pages
- [ ] Lock file is outside the wiki; `lint` and staging never see it
- [ ] Full gate green

---

## US2: Revision preconditions

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 8 | | `PageEdit.base_sha256: str \| None = None` (last, default); `plan.json` `edits[].base_sha256` written when present and read back; document the optional key (FR-005) | `src/wiki_studio/proposal.py`, `src/wiki_studio/ingestor_multi.py`, `src/wiki_studio/promoter.py`, `docs/patch-set-format.md` | build | [ ] |
| 9 | | `api.read_page(path, paths)` → bytes, UTF-8 text, sha256 from one read, path checked against the wiki boundary first, non-UTF-8 → exit 4; `wiki-studio read <path>` prints text, `--json` prints `{path, sha256, content}`; `find` does not hash; document the read-draft-record procedure (FR-006, FR-012) | `src/wiki_studio/api.py`, `src/wiki_studio/cli.py`, `README.md` | build | [ ] |
| 10 | | Hash capture: `wiki_state.load_wiki_state` reads each selected page once and returns bytes, text and sha256 together; the prompt text and the edit's `base_sha256` come from those same bytes (replace the repeated reads in selection); the backend cannot set or change a hash; `propose --from` reads `<draft>/.base.json` and never the live page for hashes; `api.propose` passes caller-supplied hashes through (FR-007) | `src/wiki_studio/wiki_state.py`, `src/wiki_studio/prompt.py`, `src/wiki_studio/ingestor_multi.py`, `src/wiki_studio/ingestor.py`, `src/wiki_studio/api.py`, `src/wiki_studio/cli.py` | build | [ ] |
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
| 15 | | `paths.contain(candidate, boundary)` (resolve both sides, refuse outside or via symlink) and `WikiPaths.source_roots` from `--source-root` / `WIKI_STUDIO_SOURCE_ROOTS`; staging refuses any symlink inside the wiki; commit re-checks with `os.lstat` under the lock; write targets and `read_page` checked against the wiki boundary (FR-012) | `src/wiki_studio/paths.py`, `src/wiki_studio/promoter.py`, `src/wiki_studio/api.py`, `src/wiki_studio/cli.py` | build | [ ] |
| 16 | | Proposal boundary on every proposal input before it is read: `plan.json`, each `preview` pointer, every file the digest enumeration reads under `preview/` (referenced or not), every `.ingest-snapshot/` file read for `curator-delta.md`, `receipt.json`; absolute, `../` and symlinked targets rejected, and an enumeration refuses any symlink it meets (FR-012) | `src/wiki_studio/promoter.py` | build | [ ] |
| 17 | | Expand `md_links` to return every local target (today it keeps only `.md`), with a separate wiki-page view for reachability; link classification in `lint_wiki` over every target: web URLs excluded; local `.md` inside the wiki is a page link and must exist; local `.md` outside the wiki and any local non-`.md` target is a source reference inside the root or an allowed source root; absolute and root-escaping targets are violations; `../` inside the root legal; index entries outside the wiki are violations; reachability counts page links only (FR-013) | `src/wiki_studio/lint.py`, `src/wiki_studio/paths.py` | build | [ ] |
| 18 | | `_extract_index_links` applies the same rule as a defence, shared by `find`, `query` and the eval selector; both evaluation runs byte-identical (FR-013) | `src/wiki_studio/querier.py`, `src/wiki_studio/api.py` | build | [ ] |
| 19 | | Tests, per surface (page write, staging, `read_page`, `read`, `find`, `query`, `plan.json`, preview pointer, snapshot file, receipt): absolute path, `../` escape, symlink target, each rejected before any read or write; symlinked page and parent dir; an unreferenced symlink under `preview/` and under `.ingest-snapshot/` refused by hashing and by curator-delta generation; absolute index entry (lint and promote reject); `../` leaving the root; `../` inside the root allowed; source reference outside the wiki inside the root allowed; non-`.md` local target classified as a source reference; an image link escaping the permitted source roots (`![d](../../outside/diagram.png)`) is a violation; `--source-root` admits a reference outside the root; web URL ignored (FR-012, FR-013) | `tests/test_containment.py`, `tests/test_lint.py`, `tests/test_paths.py` | build | [ ] |

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
| 24 | | CHANGELOG `[0.6.0]`: Added, Changed (including digest recipe 2, recipe 1 kept for older records), Security (credited), Upgrade notes per operation, Limitations (memkernel outer rollback); no statement about memkernel's next release (FR-016) | `CHANGELOG.md` | build | [ ] |
| 25 | | Version 0.6.0 in `pyproject.toml`, `__init__.py`, the contract test; banner pinned to `v0.6.0`; SECURITY supported versions; agent arm stays at 0.4.1; coverage gate `--cov-fail-under=92` in CI, `CLAUDE.md` and this bundle's `automation.json` (FR-016) | `pyproject.toml`, `src/wiki_studio/__init__.py`, `tests/test_cli_contract.py`, `README.md`, `SECURITY.md`, `.github/workflows/ci.yml`, `CLAUDE.md` | build | [ ] |

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
- [ ] No archived `plan.json`, preview or snapshot is ever rewritten; receipts carry `committing` or `committed` only, never for a failed validation or a dry run
- [ ] Every 22 October reproduction is a passing regression test through both `promote` and `api.promote`
- [ ] Different preview bytes never share a submission identity, hidden and unreferenced files included; the receipt and the archive identify the bytes that were applied, even when the proposal directory changes mid-promotion
- [ ] Receipt digest equals the ingest-log hash only for an unchanged proposal; a curated proposal keeps its log entry
- [ ] A receipt from one wiki, or from a directory recreated at its path, is refused against another before recovery, archival or reporting
- [ ] A commit followed by an archive-move failure never replays an append
- [ ] A missing or corrupt receipt never causes silent reapplication
- [ ] `read_page` and every proposal input reject path escapes and unsafe symlinks
- [ ] `run2_protocol.py` resolves `.applied/<name>/plan.json` unchanged; both evaluation runs byte-identical
- [ ] Ingest hashes the exact bytes placed in its prompt snapshot
- [ ] Concurrent ingest append and `audit-flush` tested
- [ ] The enforced coverage gate is 92 in CI, `CLAUDE.md` and `automation.json`
- [ ] No combined memkernel safety claim anywhere; the cross-product gate is listed as Release B's first item
