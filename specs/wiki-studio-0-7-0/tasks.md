# Tasks: wiki-studio 0.7.0 — governed curation (Release B, wiki-studio side)

<!-- One `## US<n>:` group = one auto-build phase. [US#]/FR tags trace to spec.md. US<n> is pitch scope S<n>. -->
<!-- Read first: CLAUDE.md, spec.md, plan.md, specs/pitches/38-release-b-governed-curation/pitch.md. -->
<!-- Run per phase: poetry run ruff check src/ tests/ eval/ && poetry run ruff format --check src/ tests/ eval/ && poetry run mypy src/ && poetry run pytest -q -p no:cacheprovider --cov=wiki_studio --cov-fail-under=92 -->
<!-- Every new source file starts with the two-line EGOGE / Apache-2.0 header. Standard library only. promoter.py is the only module that writes into the wiki (manifest and approval records included). No new exit code. No model call in findings, approve or review_state. WikiLock stays non-reentrant. memkernel is never imported outside tests/integration/ and never mocked. No production pause hook. -->

## US1: The combined integration gate (test-only)

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 1 | | Bridge-shaped contract tests replaying memkernel `studio.py:151-193` without importing memkernel: memkernel-shaped `create` pages (`status: draft`, `memkernel_ref`, `memory_type`, `memkernel://` source), one `append-index`, one `append-log`, `name="memkernel-export-<ts>-<hex>"`, `source="memkernel wiki_export"`, `backend="memkernel"`, proposals dir `<root>/.memkernel/wiki-proposals`; assert pages and index/log lines land on current content; `.applied/<name>/receipt.json` `committed` with the submission digest, archived `plan.json` and `preview/` byte-identical; a second export proposed after the first landed is refused by `api.propose` (exit 4) and one proposed before it landed is refused at promote (exit 9 via CLI, `PromoteValidationError` via API), nothing written either way; an interrupted post-commit promote resolves from its receipt and re-applies nothing; lock file beside the wiki; wiki lints clean (FR-001) | `tests/test_bridge_contract.py` | build | [ ] |
| 2 | | Combined concurrency test: a CLI `promote` of another proposal in a subprocess (via the bootstrap) while a bridge-shaped export is inside `api.promote`; both land, neither reverted, both archives exist (FR-002) | `tests/test_bridge_contract.py`, `tests/helpers/promote_bootstrap.py` | build | [ ] |
| 3 | | Copy `_WikiSnapshot.take`/`restore` from memkernel `src/memkernel/wiki/sync.py:299-363` with file, lines and revision cited in the header; test: a failing bridge-shaped export wrapped in it, a second writer committing between `take` and `restore`, shows that writer's page rewritten and its `.audit/proposals/<name>/plan.json` deleted; the same failure without the wrapper leaves that work intact (FR-003) | `tests/helpers/memkernel_snapshot.py`, `tests/test_snapshot_hazard.py` | build | [ ] |
| 4 | | Clean-install harness: tests skipped unless `memkernel` is importable, running the real `WikiExporter` and `WikiImporter` against the installed wiki-studio (export, re-export, import) (FR-004) | `tests/integration/__init__.py`, `tests/integration/test_memkernel_clean_install.py` | build | [ ] |
| 5 | [P] | CI job `memkernel-integration`, separate from the coverage job, `continue-on-error: true`: build the wheel, fresh venv, install the wheel, pytest and memkernel at a pinned ref named in an env var, run `tests/integration/`; memkernel stays out of `pyproject.toml` and the default dev group (FR-004) | `.github/workflows/ci.yml` | build | [ ] |
| 6 | [P] | `docs/consumers.md` memkernel section: the gate path, receipt recovery instead of an outer rollback, `api.init` for the scaffold, the lock file in `.gitignore`; CHANGELOG `[Unreleased]` notes the tests; the memkernel Limitation stays (FR-005) | `docs/consumers.md`, `CHANGELOG.md` | build | [ ] |

**Checkpoint US1** — verify before continuing:
- [ ] `git diff --stat main -- src/` is empty (S1 changes no API)
- [ ] The hazard test shows the rewrite and deletion with the wrapper and none without it
- [ ] Full gate green; `tests/integration/` skipped locally without memkernel

---

## US2: The versioned knowledge contract

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 7 | | Constants (`MANIFEST_NAME = ".wiki-studio.json"`, `MANIFEST_VERSION = 1`, `SCHEMA_ID = "wiki-studio/page-schema"`, `SCHEMA_VERSION = 1`, policy key names and defaults); `contract.py`: contained `O_NOFOLLOW` manifest read, malformed manifest → exit 4 naming the key, governed / managed / legacy mode (FR-006) | `src/wiki_studio/contract.py`, `src/wiki_studio/schema/__init__.py`, `src/wiki_studio/paths.py` | build | [ ] |
| 8 | | `init_wiki` writes the manifest after the containment check by `O_CREAT \| O_EXCL \| O_NOFOLLOW`, never overwriting, adding it to a legacy wiki without touching anything else; `InitResult.manifest`; `--update-schema` / `api.init(update_schema=True)` rewrites only `schema_fingerprint` via an exclusive no-follow temporary sibling, fsync and atomic replace under the lock (FR-006, FR-009) | `src/wiki_studio/promoter.py`, `src/wiki_studio/api.py`, `src/wiki_studio/cli.py` | build | [ ] |
| 9 | | One shared loader for `ingest-rules.md`, `page-types.md`, `citation-rules.md` under `<wiki>/schema/`: containment check, `O_NOFOLLOW`, symlinked override or schema dir → exit 4 with the target unread; returns merged texts and the exact override bytes; `prompt.load_schema_files` keeps name, signature and return value and delegates to it; `schema_source` derived (FR-007) | `src/wiki_studio/contract.py`, `src/wiki_studio/prompt.py` | build | [ ] |
| 10 | | Fingerprint: SHA-256 over present overrides sorted by file name, each as UTF-8 name, NUL, raw bytes; no override → SHA-256 of empty input; packaged and unloaded files ignored (FR-008) | `src/wiki_studio/contract.py` | build | [ ] |
| 11 | | Compatibility and drift in `propose` (CLI, `api.propose`) and `promote` (CLI, `api.promote`, dry run included) and `init`: newer `manifest_version` / `schema.version` → exit 4 naming both and the upgrade; drift → exit 4 naming declared and current fingerprint and `init --update-schema` on a governed wiki, stderr warning and `PromoteResult.warnings` on a managed one; legacy wiki unchanged (FR-009, FR-011) | `src/wiki_studio/api.py`, `src/wiki_studio/promoter.py`, `src/wiki_studio/cli.py` | build | [ ] |
| 12 | | `api.info(paths) -> InfoResult` and `info` (text and `--json`): `package_version`, `schema_contract` (`id`, `version`, `source`, `fingerprint`, `declared_fingerprint`, `drift`), `formats` (`patch_set`, `receipt`, `ingest_log`), `capabilities` (`wiki-lock`, `receipts`, `base-revision`, `root-manifest`), `manifest` (`state`, and `manifest_version`, `wiki_id`, `policy`, `mode` or the `init` instruction); every 0.6.0 key unchanged, `schema` string included (FR-010) | `src/wiki_studio/contract.py`, `src/wiki_studio/api.py`, `src/wiki_studio/cli.py` | build | [ ] |
| 13 | [P] | `docs/compatibility.md` (tested pairs, evidence with the CI run, capabilities each side needs, re-creating pre-0.6.0 `update` proposals); `docs/knowledge-contract.md` (manifest keys, vocabulary, fingerprint recipe incl. the line-ending note, drift and its surfaces, `info` keys) (FR-008, FR-012) | `docs/compatibility.md`, `docs/knowledge-contract.md` | build | [ ] |
| 14 | | Tests: manifest created once, never overwritten; `api.propose` on a managed wiki with drift emits `DriftWarning` and still returns the proposal path; symlinked manifest path and symlinked wiki parent refused, targets untouched; fingerprint changes on one byte, order-independent, ignores packaged and unloaded files, empty-input digest without overrides; outside-pointing override symlink refused unread; a changed packaged schema document alone never trips drift; `--update-schema` after the first override added and the last removed, `info` source correct each time; drift exit 4 governed, warning managed, through `propose` and `promote`; newer manifest exit 4; legacy wiki as 0.6.0; `info --json` new and old keys; every advertised capability resolves (FR-006..FR-013) | `tests/test_manifest.py`, `tests/test_schema_fingerprint.py`, `tests/test_info_contract.py`, `tests/test_cli_contract.py` | build | [ ] |

**Checkpoint US2** — verify before continuing:
- [ ] `poetry run wiki-studio init` then `poetry run wiki-studio info --json` shows `manifest.state: present`, `mode: managed`, `drift: false`
- [ ] The CI wheel smoke import of `load_schema_files` still works
- [ ] Full gate green

---

## US3: Identity and attribution

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 15 | | `page_id` constants and pattern `^pg-[0-9a-f]{32}$`; `api.propose(..., assign_page_ids=False)` inserting `page_id: pg-<uuid4 hex>` as the last frontmatter line of a `create` without one, before the preview is written; CLI `propose --from` passes `True`; multi-page `ingest` assigns on creates; caller-supplied ids never rewritten; updates, appends and legacy single-source unchanged (FR-014) | `src/wiki_studio/schema/__init__.py`, `src/wiki_studio/api.py`, `src/wiki_studio/cli.py`, `src/wiki_studio/ingestor_multi.py` | build | [ ] |
| 16 | | Structural lint: malformed `page_id` and duplicated `page_id` are violations (FR-015) | `src/wiki_studio/lint.py` | build | [ ] |
| 17 | | `review.py`: canonical wiki-relative path (`posixpath.normpath`, forward slashes, no leading `./` or `/`) and page key (`page_id` when well formed, else the canonical path) (FR-016) | `src/wiki_studio/review.py` | build | [ ] |
| 18 | | Actor: `ENV_ACTOR = "WIKI_STUDIO_ACTOR"`; resolution `flag` (`--by` or `by=`) → `env` → `none`, never the OS user; `--by` on `propose` and `promote`; `by=` on `api.propose` and `api.promote`; `WikiPatchSet.proposer` (last, default) written to `plan.json` `proposer`; receipt `actor` (receipt version stays 1) (FR-017) | `src/wiki_studio/paths.py`, `src/wiki_studio/proposal.py`, `src/wiki_studio/ingestor_multi.py`, `src/wiki_studio/promoter.py`, `src/wiki_studio/api.py`, `src/wiki_studio/cli.py` | build | [ ] |
| 19 | [P] | Docs: `--by` is attribution, not authentication; the host supplies authority; audit files give traceability, not tamper-proof evidence; `proposer`, `actor` and `page_id` assignment documented (FR-018) | `README.md`, `SECURITY.md`, `docs/patch-set-format.md` | build | [ ] |
| 20 | | ADR-0002 in ADR-0001's form: `page_id`, the reserved approval keys, `superseded_by`, memkernel's `corrects` registered with syntax not final, review state separate from memory tier, schema version 2; `SCHEMA_VERSION = 2` citing it; `page-types.md` documents the optional keys (FR-019) | `docs/adr/0002-page-identity-and-review-keys.md`, `src/wiki_studio/schema/__init__.py`, `src/wiki_studio/schema/page-types.md` | build | [ ] |
| 21 | | Capabilities `page-id` and `attribution` advertised (FR-010) | `src/wiki_studio/contract.py` | build | [ ] |
| 22 | | Tests: CLI `propose --from` and ingest creates carry a fresh `page_id` in the preview and the committed page (same bytes); `api.propose` default leaves bridge-shaped bytes unchanged and `assign_page_ids=True` assigns; caller id kept; malformed and duplicate ids fail lint and a copying `create` exits 9 at promote; actor source `flag`, `env`, `none` in `plan.json` and the receipt; no OS user name anywhere in audit files by default; schema version 2 in a new manifest (FR-014..FR-019) | `tests/test_page_id.py`, `tests/test_attribution.py` | build | [ ] |

**Checkpoint US3** — verify before continuing:
- [ ] `grep -rn "getuser\|getlogin\|USER" src/wiki_studio/` finds no implicit actor capture
- [ ] ADR-0002 exists and the schema version constant cites it
- [ ] Full gate green

---

## US4: Approval bound to the revision and the policy

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 23 | | Policy: three booleans with defaults; `policy_sha256` over canonical JSON (sorted keys, `,`/`:` separators, UTF-8) of `approver_required` only; a test turns a managed wiki governed and asserts every existing approval stays `approved` (FR-020) | `src/wiki_studio/review.py`, `src/wiki_studio/contract.py` | build | [ ] |
| 24 | | Record layout `id/<page_id>/…` and `path/<path-digest>/…/<sha256>/<policy_sha256>/<decision>.json`; path digest = SHA-256 hex of the canonical path in UTF-8; record keys (`approval_version: 1`, `wiki_id`, `page_key`, `path`, `sha256`, `policy_sha256`, `decision`, `proposal`, `proposer`, `approver`, `promoter`, `timestamp`); verification on every read (regular contained file, version, `wiki_id`, `page_key` equals the looked-up key, fields equal the path) with failures skipped and reported (FR-023, FR-024) | `src/wiki_studio/review.py` | build | [ ] |
| 25 | | Publication in the promoter: names contained against `.audit/approvals/` before creation, directories created without following symlinks, `O_NOFOLLOW` opens, symlinked component → exit 4 target untouched; temporary file, fsync, exclusive `os.link` (fallback `O_CREAT \| O_EXCL` on the final name), never `rename`; existing tuple → no-op (FR-025) | `src/wiki_studio/promoter.py` | build | [ ] |
| 26 | | `approve` in `promoter.py` under the lock: read and hash each page once through the wiki boundary (7 outside or symlink, 5 missing); batch preflight → exit 9 naming page and reason (expected revision differs, structural-lint violation for the page, draft, `superseded_by` present, approver required and unnamed); legacy wiki → exit 4 naming `init`; newer manifest and governed drift → exit 4, managed drift → warning; `proposal` from the newest matching committed receipt under `.applied/`; I/O failure after partial publication → exit 6 naming published and unpublished; rerun idempotent. `api.approve(pages, paths, *, by=None, expected=None) -> ApproveResult` and CLI `approve <page>... [--revision SHA] [--by NAME]` (`--revision` with more than one page → exit 4); verb added to the dispatcher (FR-021, FR-022, FR-024) | `src/wiki_studio/promoter.py`, `src/wiki_studio/api.py`, `src/wiki_studio/cli.py` | build | [ ] |
| 27 | | `api.review_state(paths, *, pages=None) -> list[ReviewState]`, no lock: default set = linted pages except root `index.md` and `log.md`; order `manifest_missing` → (`superseded`, US5) → `draft` → `approved` → `policy-changed` → `stale` → `unapproved`; lookup `id/` then `path/`, newest by `timestamp`; returns live and approved sha256, record path, warnings (FR-026, FR-027) | `src/wiki_studio/review.py`, `src/wiki_studio/api.py` | build | [ ] |
| 28 | | Reserved edits, checked by `api.propose` and by `promote` before staging, after the existing escape checks, as `ContractViolationError` (exit 4): a normalised path with a dot-prefixed component or under `schema/`; frontmatter keys `approved`, `approved_by`, `approval`, `review_state` on `create` / `update` (FR-028, FR-029) | `src/wiki_studio/proposal.py`, `src/wiki_studio/api.py`, `src/wiki_studio/promoter.py` | build | [ ] |
| 29 | | Auto-approval after the receipt is `committed` and the archive published: re-acquire the lock once, per content page (creates and updates only) compare live sha256 with the receipt's post-commit hash, apply `approve`'s per-page conditions, publish records for matching pages with the promoter's actor, no record and no attribution for mismatched pages, a warning per skipped, failed or mismatched page, promotion never failed by it; `PromoteResult.approved_paths` (last, default) (FR-030) | `src/wiki_studio/promoter.py`, `src/wiki_studio/api.py`, `src/wiki_studio/cli.py` | build | [ ] |
| 30 | | Audit lint: `approvals/` admitted in `.audit/`'s closed set; tree shape, name formats, record validity against location, no symlinks, stray temporary files reported (FR-031) | `src/wiki_studio/audit_lint.py`, `src/wiki_studio/schema/audit-rules.md` | build | [ ] |
| 31 | [P] | Capability `approval-record`, format `approval: 1`; `docs/knowledge-contract.md`: policy and its hash, record layout, path-digest recipe, verification, review states, partial publication and idempotent rerun, auto-approval guarantee (FR-010, FR-022, FR-023) | `src/wiki_studio/contract.py`, `docs/knowledge-contract.md` | build | [ ] |
| 32 | | Tests: the four acceptance cases (draft refused and skipped; `status: stable` without a record `unapproved` and `approved_by:` refused; hand edit `stale` then re-approved `approved`; policy edit `policy-changed`); `--revision` mismatch and multi-page `--revision`; batch preflight writes nothing; partial publication exit 6 then idempotent rerun; legacy wiki exit 4 naming `init` and `manifest_missing`; collision (`concepts/x.md` vs root `concepts__x.md`, `page_id` equal to a path-derived name) and equivalence (`./concepts/x.md`); stored `page_key` mismatch skipped; symlink planted at each approval-tree level refused, target untouched; existing record never rewritten; deleted page recreated at its path reads `stale` naming the old record, never `approved`; page gaining a `page_id` by update reads `stale` with its `path/` record; reserved manifest, record and override paths refused, raw `./index.md` passes; multi-page auto-approval interleaving (second writer between archive and auto-approval: no record for that revision under the promoter, others approved); `auto_approve_on_promote` toggle never yields `policy-changed`; drift through `approve`: managed drift in `ApproveResult.warnings` and on stderr, governed drift exit 4, a newer manifest exit 4, each through the CLI and `api.approve` (FR-009, FR-011, FR-013, FR-020..FR-032) | `tests/test_approve.py`, `tests/test_review_state.py`, `tests/test_approval_records.py`, `tests/test_reserved_edits.py`, `tests/test_auto_approve.py`, `tests/test_audit_lint.py` | build | [ ] |
| 33 | | Harness: the four Release B loop cases end to end against the installed memkernel (retain, export, review via `api.approve`, import, correct, next-session recall), plus the retry property (interrupted post-commit promote resolves from its receipt; export and import run twice create no duplicate pages, records or memories), never skipped or marked expected-failure in the clean-install job (FR-032) | `tests/integration/test_release_b_loop.py` | build | [ ] |

**Checkpoint US4** — verify before continuing:
- [ ] No code path reads frontmatter to decide `approved`
- [ ] The single-writer tests pass with the approval records written only by `promoter.py`
- [ ] Full gate green

---

## US5: `superseded_by`

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 34 | | Structural lint for `superseded_by`: normalised target must exist, be a page, not be the page itself, and not be superseded in turn; absolute or escaping target is a violation (FR-033, FR-034) | `src/wiki_studio/lint.py` | build | [ ] |
| 35 | | `review_state` reports `superseded` after only the `manifest_missing` rule, whatever the records say (`approve`'s refusal is already in US4) (FR-035) | `src/wiki_studio/review.py` | build | [ ] |
| 36 | | `corrects`: fixture with several corrections on one page; `yaml_lite` parses it as one scalar line; propose and promote preserve it byte for byte; the harness parses the same fixture with memkernel's page parser; ADR-0002's `corrects` and `superseded_by` text matches the build (FR-033, FR-036) | `tests/fixtures/corrects/multi-corrections.md`, `tests/test_superseded_by.py`, `tests/integration/test_memkernel_clean_install.py`, `docs/adr/0002-page-identity-and-review-keys.md` | build | [ ] |
| 37 | | Capability `superseded-by` (FR-010) | `src/wiki_studio/contract.py` | build | [ ] |
| 38 | | Tests: missing target, non-page target, self, chain and cycle each reported; a broken target after a hand rename reported; `superseded` regardless of an approved record; `approve` refuses a superseded page (FR-033..FR-035) | `tests/test_superseded_by.py`, `tests/test_lint.py` | build | [ ] |

**Checkpoint US5** — verify before continuing:
- [ ] A superseded page with a valid approved record reads `superseded`
- [ ] Full gate green

---

## US6: Findings without a model call, and release 0.7.0

| # | [P] | Task | File(s) | Owner | Done |
|---|-----|------|---------|-------|------|
| 39 | | `findings.py`: deterministic health kinds (health checks with no backend) plus review kinds from `review_state` (`unapproved`, `approval-stale`, `approval-policy-changed`), `superseded-still-indexed`, `no-page-id` (only if `page_id` shipped); `api.findings(paths, *, pages=None) -> FindingsResult` with no backend parameter; CLI `findings [--json] [--paths ...]`, exit 0 on a completed run; verb added to the dispatcher (FR-037, FR-038) | `src/wiki_studio/findings.py`, `src/wiki_studio/api.py`, `src/wiki_studio/cli.py` | build | [ ] |
| 40 | [P] | Format `findings: 1` and capability `findings`; `docs/knowledge-contract.md` documents the JSON (`findings_version`, `counts` first, `pages_checked`, `findings[]`) (FR-010, FR-038) | `src/wiki_studio/contract.py`, `docs/knowledge-contract.md` | build | [ ] |
| 41 | | Tests: every kind produced on a fixture wiki; `counts` is the first key; exit 0 with findings; no backend parameter and a run with backend resolution patched to fail still succeeds (FR-037, FR-038) | `tests/test_findings.py` | build | [ ] |
| 42 | | Release: 0.7.0 in `pyproject.toml`, `__init__.py`, the contract test; banner `v0.7.0`; SECURITY supported versions; CHANGELOG `[0.7.0]` Added / Changed / Upgrade notes / Limitations (memkernel item kept per FR-005, Release B not closed, any cut named), never stating memkernel's next release; `CLAUDE.md` layout and verbs; coverage gate stays 92 (FR-039) | `pyproject.toml`, `src/wiki_studio/__init__.py`, `tests/test_cli_contract.py`, `README.md`, `SECURITY.md`, `CHANGELOG.md`, `CLAUDE.md` | build | [ ] |
| 43 | | CI gating (two jobs, `memkernel-compat` blocking once green, `memkernel-loop` labelled expected-to-fail until memkernel #48 merges): if memkernel #48's counterpart is merged at release time, drop `continue-on-error` from `memkernel-integration` and run it in `release.yml` before publishing; otherwise leave it non-blocking and say so under Limitations (FR-004, FR-039) | `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `CHANGELOG.md` | build | [ ] |
| 44 | | Circuit-breaker audit: for every cut taken, the capability, format entry, ADR-0002 section, CHANGELOG and docs reflect the shipped build; the capability-resolution test passes (FR-040) | `src/wiki_studio/contract.py`, `docs/adr/0002-page-identity-and-review-keys.md`, `CHANGELOG.md` | build | [ ] |

**Checkpoint US6** — verify before continuing:
- [ ] `poetry run wiki-studio findings --json` prints `counts` first and exits 0
- [ ] `poetry run wiki-studio --version` prints 0.7.0; `poetry build` succeeds
- [ ] Full gate green

---

## Final Verification

- [ ] Type checker: 0 errors; linter and formatter: 0 errors
- [ ] Full suite green with coverage at or above 92 percent
- [ ] Single-writer tests, CLI contract tests, `tests/test_schema.py` and both evaluation runs' determinism tests green
- [ ] Exit codes unchanged (0, 2..11; 1 fatal lint); every new refusal is 4, 5, 6, 7, 9 or 10
- [ ] No runtime dependency added; memkernel absent from `pyproject.toml` dependencies and the default dev group
- [ ] `promoter.py` is the only writer of the manifest and the approval records
- [ ] No code path reaches a model from `findings`, `approve` or `review_state`
- [ ] `WikiLock` is unchanged and non-reentrant
- [ ] A symlink at the manifest, a schema override or any approval-tree level is refused with its target untouched or unread
- [ ] Frontmatter never makes a page `approved`; drafts are never `approved`; a reused path reads `stale`, never `approved`
- [ ] Every capability `info` advertises resolves in the shipped build; cut scopes advertise nothing
- [ ] Existing `info --json` keys keep their 0.6.0 names and meaning
- [ ] ADR-0002 exists for every new schema key, with a CHANGELOG entry
- [ ] The CHANGELOG keeps the memkernel limitation unless `docs/compatibility.md` lists a tested release without the snapshot, and declares no combined safety claim or Release B closure before the joint loop passes
