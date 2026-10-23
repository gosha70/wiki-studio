---
spec_mode: full
feature_id: wiki-studio-0-6-0
risk_category: feature
status: approved
date: 2026-10-23
---

# Spec: wiki-studio 0.6.0 — safe changes (Release A)

<!-- Project constitution: shared/skills/ — copilot-conventions, coding-standards, safety -->

Design references (read before building): `CLAUDE.md`; the owner's product
proposal of 23 October 2026 (Release A, "Safe changes") and its review of the
same date (revision 3), which reproduced every defect below on `main` at
41cfe54; in this repository `src/wiki_studio/promoter.py` (`_stage_wiki`,
`_apply_edit`, `_validate_before_staging`, `_commit_stage_to_wiki`,
`_archive_proposals_dir`, `promote`), `audit.py` (the ingest-log append),
`proposal.py` (`PageEdit`, `WikiPatchSet`, `Citation`, `QueryAnswer`),
`ingestor_multi.py` (`write_patch_set_dir`), `ingestor.py`, `prompt.py`
(candidate pages in `wiki_state`), `querier.py` (`_extract_index_links`,
`_select_query_candidates`, the citation check in `DefaultQuerier.query`),
`lint.py` (`_link_resolves`, `lint_wiki`), `paths.py` (`WikiPaths`),
`api.py` (`propose`, `promote`, `find`, `PromoteResult`), `cli.py`,
`errors.py`, `docs/patch-set-format.md`, `README.md`, `SECURITY.md`.

## Why

Five defects on `main` break promises the README makes. Two promotes that
start together revert each other's pages, because commit writes back every
staged page that differs from the live one. A replacement carries no record
of the page it was drafted from, so a stale draft overwrites a newer page.
A symlinked page is written through to its target, a page may link to a file
outside the project, and `find` follows such a link. The query answer check
accepts a fabricated quotation and an answer with no evidence. "Atomic
promotion" means rollback on exception, not crash safety. This release fixes
the first four, states the fifth honestly, and makes each reproduction a
regression test. It ships before any new contract or promotion campaign.

The claim this release earns is bounded: Wiki Studio writers that cooperate
through its API or CLI on one machine do not lose each other's changes and do
not apply stale replacements. Safety across the memkernel stack additionally
depends on memkernel's outer rollback, which is not changed here.

## User Scenarios

### US1: Two writers, no lost update (Priority: HIGH)

**Given** two proposals that each update a different page, promoted by two processes that start together
**When** both `wiki-studio promote` calls return
**Then** both pages carry their change, each promote wrote only the paths its patch-set named, the second waited on the wiki lock before staging, and each has its own archive and receipt

### US2: A stale replacement is refused (Priority: HIGH)

**Given** an agent that read page A, another writer that then committed page A′, and a proposal that replaces A with content drafted from A
**When** the proposal is promoted
**Then** promote exits 9 naming the page and writes nothing; a proposal whose replacement carries no base revision is refused the same way unless the caller passes the compatibility option, in which case the receipt records the page as unguarded; creates and appends from older proposals promote unchanged

### US3: The wiki stays inside the wiki (Priority: HIGH)

**Given** a wiki with a symlinked page, a page that links to an absolute path, an index entry that points outside the wiki, and a proposal whose preview pointer escapes the proposal directory
**When** lint, promote and `find` run
**Then** lint reports the links, promote refuses the symlink and the escaping pointer before reading or writing anything, and `find` never lists a file outside the wiki; `../` source references inside the configured root stay legal

### US4: An answer carries real evidence (Priority: HIGH)

**Given** a backend reply whose citation quotes text that is not in the cited page, or that answers with no citation
**When** `query` validates the reply
**Then** it exits 4 naming the page; a fragment is checked against the page content that was in the prompt, not a file reread afterwards; the abstention form (empty answer, one citation to the index) still passes

### US5: The guarantees are stated as they are (Priority: HIGH)

**Given** the README, SECURITY.md and the promoter docstrings
**When** 0.6.0 is released
**Then** no document says "atomic" without qualification, the fact and stale-source checks are described as heuristics, the per-operation upgrade policy is in the CHANGELOG, memkernel's outer rollback is listed as a limitation, and the version is 0.6.0

## Requirements

- **FR-001 (commit scope)**: `_commit_stage_to_wiki` MUST write only the paths named by the patch-set's edits (including `index.md` and `log.md` appends) plus this proposal's own archive under `.audit/proposals/`. Both staged-tree collectors (`*.md` and `.audit/proposals/*/plan.json`) MUST be scoped this way. A staged file outside that set is never written back.
- **FR-002 (the wiki lock)**: A new module `src/wiki_studio/wikilock.py` MUST provide `WikiLock`, an OS advisory lock held on an open file descriptor: `fcntl.flock(fd, LOCK_EX)` on POSIX and `msvcrt.locking` on Windows, behind one interface. Ownership is the OS lock; no PID-file ownership, no stale-lock reclamation, and the lock file is never deleted or recreated while contenders may hold it. PID, hostname and start time MAY be written into the file as diagnostics only. The lock file is `<resolved-wiki-parent>/.<wiki-dir-name>.wiki-studio.lock`, keyed to `wiki_dir.resolve()`, so two spellings of one directory share it; it lies outside the wiki, so staging and lint never see it. Acquisition waits up to a timeout (default 30 s; `--lock-timeout` and `WIKI_STUDIO_LOCK_TIMEOUT`); on expiry `PromoteApplyError` with `reason="lock_timeout"`, exit 10. The lock is held from before staging to after the archive move, and taken by every cooperating entry point: `promote`, `propose --promote`, the ingest-log append in `audit.py`, `audit-flush` while it reads and commits the log, and `api.promote`. CI MUST run the lock tests on one Windows job; if that job is not added in this release, the "OS Independent" classifier MUST be narrowed to POSIX in the same release.
- **FR-003 (receipts and submission identity)**: The archived `plan.json`, `preview/` and `.ingest-snapshot/` MUST be byte-identical copies of the submitted proposal. Execution metadata MUST go in `receipt.json` in the proposal directory (moved with it into the archive): `state` (FR-004), `submission_digest`, `plan_sha256`, planned paths with the sha256 each live page is expected to hold after commit, written paths, `unguarded_paths`, lock wait, timestamps, and `promoter` as software identity only (package name and version, entry point `cli` or `api`). The submission identity is `submission_digest`: the canonical full-payload digest over the exact bytes used during promotion (`plan.json` plus every file under `preview/`, the same rule as `audit.proposal_hash`), never the plan digest alone, because `plan.json` holds pointers and a curator can change a preview without changing the plan. `plan_sha256` is kept separately for provenance. Archive directory names are unchanged from 0.4.0 (`.applied/<name>/`, then `<name>-2`, `-3` on a name clash), so existing consumers keep resolving; two same-named submissions never share a directory, and never share an identity unless their payload bytes are equal. Failed validation attempts and dry runs persist no receipt.
- **FR-004 (commit, receipt and recovery ordering)**: Under the lock, after validation and the FR-008 checks pass, promote MUST proceed in this order: (1) write `receipt.json` into the proposal directory with `state: "committing"`, the submission digest and, for every path the commit will actually write (no-op paths whose live content already equals the proposed content are excluded, and this proposal's own audit artifact under `.audit/proposals/` is included), both the sha256 of its pre-commit content (or absence) and the sha256 it will hold after commit, and fsync it; if this write fails, nothing is committed and promote exits 6; (2) commit the files; (3) rewrite the receipt with `state: "committed"` and fsync; (4) move the proposal directory into `.applied/`. On a later promote of the same proposal directory: a receipt with `state: "committed"` means finish step 4 only, with no appends; a proposal already under `.applied/` returns the recorded outcome with no writes; a receipt with `state: "committing"` is resolved under the lock by comparing each tracked write's live sha256 (or absence) with the receipt: all tracked writes equal to their recorded pre-state means not committed (the receipt is removed and the proposal may be promoted afresh); all equal to their expected post-state means committed (complete steps 3 and 4); any other combination, including a tracked path that matches neither state, exits 10 with `reason="uncertain_outcome"` and a message naming the paths, with no writes. Excluding no-op paths keeps a page that already held its proposed content from reading as a partial commit; including the proposal's own audit artifact keeps a later cooperative writer's changes to shared pages from making a committed proposal look uncommitted. Before treating a retry as already committed, promote MUST recompute the submission digest from the directory's bytes and require it to equal the receipt's; a missing or corrupt receipt is never treated as committed and never causes silent reapplication. This protocol covers failures between these steps and does not claim recovery from arbitrary process crashes during step 2 beyond the existing exception rollback; the docs say so. Tests inject faults after step 1, during step 1, during step 3 and during step 4, and cover an update whose proposed content is already identical to the live page (a no-op: excluded from tracking, recovery after step 1 reads as not committed).
- **FR-005 (base revision in the edit model)**: `PageEdit` MUST gain `base_sha256: str | None = None`, added last with a default so positional construction keeps working; `plan.json` MUST gain the optional key `edits[].base_sha256`, documented in `docs/patch-set-format.md` under the format's minor-version rule. The hash is sha256 over the page bytes as read.
- **FR-006 (one read gives content and hash)**: `api.read_page(path, paths)` MUST read the page once and return the bytes, the UTF-8 decoded text and the sha256 of those exact bytes; a page that is not valid UTF-8 is a `ContractViolationError` (exit 4) and returns no content. `wiki-studio read <path>` prints the text; `--json` prints `{"path", "sha256", "content"}` with the decoded text, never raw bytes. The path is wiki-relative and MUST pass FR-012's wiki boundary before the read. `find` lists pages and does not hash them; `info` stays configuration and capabilities. The documented agent procedure is: read with `read`, draft from that content, record its hash.
- **FR-007 (the hash is what the author read)**: For `ingest`, `wiki_state.load_wiki_state` MUST read each selected page once, returning bytes, decoded text and sha256 from that one read; the text placed in the prompt and the hash attached to the edit MUST come from the same bytes (today the selection code reads candidate pages more than once; that is replaced). The model never supplies or reconstructs a hash. For `propose --from`, the draft directory MAY carry `<draft>/.base.json` mapping wiki path to sha256; `propose` MUST NOT fill a missing hash from the live page, and an `update` without a manifest entry is unguarded. For `api.propose`, the caller supplies it. No code path upgrades an older proposal by attaching a current hash.
- **FR-008 (preconditions under the lock)**: After staging and while holding the lock, immediately before commit, promote MUST check: `create` requires absence of the live target; `append-index` and `append-log` apply to the current live content; `update` with `base_sha256` requires the live page's sha256 to equal it. A mismatch is `PromoteValidationError` (exit 9) naming the page, with nothing written.
- **FR-009 (unguarded updates)**: An `update` without `base_sha256` MUST be refused with exit 9 and a message naming the page and the two remedies (regenerate from a fresh `read`, or pass the compatibility option). With `--allow-unguarded-updates` (CLI) or `allow_unguarded_updates=True` (`api.promote`) it is applied and listed under `unguarded_paths` in the receipt and in `PromoteResult`. Help text and docs MUST call this "compatibility mode with incomplete conflict protection" and MUST NOT describe it as preventing stale overwrites.
- **FR-010 (structured findings)**: `PromoteResult` MUST gain `unguarded_paths: list[str]` and `warnings: list[str]`, added last with defaults.
- **FR-011 (dry run on a snapshot)**: `promote --dry-run` MUST acquire the lock, stage, check FR-008's preconditions against live while holding the lock, release the lock, then validate the staged copy. It writes no wiki content, no receipt and no proposal change; the lock file itself may be created. Its help text says the result is point-in-time evidence and a real promote checks again.
- **FR-012 (containment boundaries)**: One canonical check, `paths.contain(candidate, boundary)`, resolves both sides and refuses a candidate outside the boundary or reached through a symlink; it is used on every read and write surface, new and existing. Wiki boundary: page writes, staging reads, `read_page` and `wiki-studio read`, and navigation reads (`find`, `query`, the eval selector). Proposal boundary: `plan.json` itself, every `preview` pointer, every file under `.ingest-snapshot/` read for `curator-delta.md`, and `receipt.json`; each is checked before its content is read. Source boundary: a local source reference in page text resolves inside the configured root or an explicitly allowed source root. Allowed source roots are configured by `--source-root PATH` (repeatable) and `WIKI_STUDIO_SOURCE_ROOTS` (path-separator list), default empty, exposed as `WikiPaths.source_roots`. Checks use `resolve()`, never `normpath` alone. Staging MUST refuse any symlink inside the wiki (file or directory) with `PromoteValidationError` naming it, and commit MUST re-check with `os.lstat` under the lock. Tests cover absolute paths, `../` escapes and symlink targets on every surface named here.
- **FR-013 (link rule)**: `md_links` (`lint.py:112-122`) today keeps only targets ending in `.md`, so an image or data link such as `![d](../../outside/diagram.png)` is never checked; US3 MUST expand the collector to return every local target (a non-`.md` local target is part of the security boundary) while keeping a separate wiki-page view for reachability. `lint_wiki` MUST then classify each target: `http`, `https` and `mailto` targets are not filesystem links; a local `.md` target that resolves inside the wiki directory is a wiki-page link and must exist; a local `.md` target outside the wiki, and any local non-`.md` target (images, data files, source files), is a source reference and must resolve inside the root or an allowed source root; the reachability check counts only wiki-page links. Absolute targets and targets that leave the root are violations. `../` targets that stay inside the root remain legal. An index entry whose target resolves outside the wiki directory is a violation, so promote rejects it; `_extract_index_links` MUST apply the same rule as a defence, shared by `find`, `query` and the eval selector. Both evaluation runs MUST remain byte-identical.
- **FR-014 (citation evidence)**: `DefaultQuerier.query` MUST validate each citation's fragment against the captured `index_md` and `pages_content` supplied to the backend, never against files reread after the backend returns; the fragment must occur in that text after whitespace normalisation, else `ContractViolationError` (exit 4) naming the page. A non-empty answer MUST carry at least one citation. The abstention form (empty answer, one citation to `index.md` whose fragment occurs in the captured index) remains valid. Docs state that the check verifies quotation against the prompt snapshot, not logical support.
- **FR-015 (honest guarantees)**: README (the promote section and line 79), SECURITY.md (line 32) and the promoter docstrings MUST describe promotion as "validated, serialised against other wiki-studio writers on the same machine, rolled back on failure; not crash-safe across files, and uncoordinated readers may observe intermediate state." The fact check MUST be described as a heuristic for citations, identifiers and quantities that does not detect changes of meaning; the stale-source check as verifying that cited paths exist, not the recorded revision. The lock's scope (one machine, one filesystem; not distributed; not protection against direct edits; network filesystems out of scope) MUST be documented.
- **FR-016 (release)**: Version 0.6.0 in `pyproject.toml`, `src/wiki_studio/__init__.py` and the CLI contract test; README banner pinned to `v0.6.0`; CHANGELOG `[0.6.0]` with Added (lock, receipts, `read`, preconditions, containment boundaries, citation evidence), Changed (commit scope, link rule, receipt files in archived proposals), Security (symlink and outside-link escapes, credited to the reporter), Upgrade notes stated per operation (creates and appends from older proposals promote unchanged; replacements without a base hash are refused until regenerated from a fresh `read`, or applied under the compatibility option, recorded as incomplete conflict protection), and Limitations (memkernel's outer whole-wiki snapshot and rollback can still undo another writer's committed changes until memkernel holds the same lock across its lifecycle or removes that workaround; mixed-writer safety across the stack is claimed only when both halves ship). The CHANGELOG MUST NOT state what memkernel's next release does. The agent arm stays pinned at 0.4.1 with its note. The enforced coverage threshold MUST match the stated gate: `--cov-fail-under=92` in `.github/workflows/ci.yml`, `CLAUDE.md` and `specs/wiki-studio-0-6-0/automation.json`. `eval/navigation/run2_protocol.py` (which reads `.applied/<proposal_dir>/plan.json`) MUST keep working unchanged, and a test MUST pin that the archive layout it depends on is unchanged.
- **FR-017 (fallback)**: If 0.6.0 slips, the contract-compatible subset MAY ship first as 0.5.1: FR-001, FR-002, FR-012, FR-013, FR-014 and FR-015. Receipts, `read`, `base_sha256`, the compatibility option and `PromoteResult` fields wait for 0.6.0, because each adds to a published format or API.

## Constraints

- **Standard library only.** `fcntl`, `msvcrt`, `hashlib`, `os` and `pathlib` suffice; no new runtime or dev dependency.
- **Contracts.** Exit codes 0 and 2..11 unchanged (9 for revision conflicts, 10 with `reason="lock_timeout"` for the lock); the patch-set format gains optional keys only; `api` changes are additive with defaults; `promoter.py` stays the single writer into the wiki (the single-writer test stays green).
- **Submitted bytes are never rewritten.** No code path edits an archived `plan.json` or preview; execution metadata lives in `receipt.json`.
- **No production pause hook.** Tests force interleavings from a test bootstrap that patches the child process before it calls `cli.main`; no environment variable in shipped code can pause promotion.
- **Cross-product gate.** Mixed-writer safety across the memkernel stack is not claimed by this release. A combined integration gate (memkernel bridge compatibility: creates and appends through `api.propose`, receipt and `.applied/` layout, lock coordination) is tracked as the first item of Release B and must pass before any combined safety claim.
- **Out of scope.** Asserted actor attribution, schema version and root manifest, supersession keys, FTS5, MCP, curation-debt reporting, quickstarts, crash-safe multi-file transactions, distributed or network-filesystem coordination, changes to memkernel.
- **Gate.** `poetry run ruff check src/ tests/ eval/ && poetry run ruff format --check src/ tests/ eval/ && poetry run mypy src/ && poetry run pytest -q -p no:cacheprovider --cov=wiki_studio --cov-fail-under=92` stays green; coverage does not fall below the current level (92%); both evaluation runs' determinism tests stay green.
