# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Contract tests for memkernel's wiki bridge (0.7.0, US1): the bridge's
  create, append-index and append-log calls through `api.propose` and
  `api.promote`, a concurrency test with a CLI `promote`, a reproduction of
  the outer-snapshot hazard, and clean-install CI jobs against a pinned
  memkernel. `docs/consumers.md` describes the gate path without an outer
  rollback. The memkernel limitation in 0.6.0's notes still stands.
- The versioned knowledge contract (0.7.0, US2). `init` writes a root
  manifest, `<wiki>/.wiki-studio.json`, by exclusive no-follow creation: a
  `wiki_id`, the schema identity and version (`wiki-studio/page-schema`,
  version 2), the fingerprint of the project schema overrides, a policy of
  three booleans and `created_by`. It never overwrites; on a wiki made before
  0.7.0 it adds the manifest and nothing else. `InitResult.manifest` reports
  `created`, `existing` or `updated`.
- `api.info(paths) -> InfoResult` and new `info` keys: `package_version`,
  `schema_contract` (id, version, source, current and declared fingerprint,
  drift), `formats`, `capabilities` and `manifest`. Every 0.6.0 `info --json`
  key keeps its name and meaning.
- Schema drift: a changed project override (`<wiki>/schema/ingest-rules.md`,
  `page-types.md`, `citation-rules.md`) is refused by `propose` and `promote`
  (exit 4) on a governed wiki and is a warning on a managed one: stderr,
  `PromoteResult.warnings`, and a `DriftWarning` from `api.propose`.
  `init --update-schema` (`api.init(..., update_schema=True)`) acknowledges
  it. A package upgrade alone never causes drift. The recipe is in
  `docs/knowledge-contract.md`.
- `docs/compatibility.md`: the tested wiki-studio and memkernel pairs, their
  evidence, the capabilities each side needs, and how to re-create a proposal
  written before 0.6.0.
- Page identity (0.7.0, US3). An optional frontmatter key
  `page_id: pg-<32 hex>`. `propose --from` and multi-page `ingest` add a
  fresh one to every page they create, before the preview is written, so the
  preview and the committed page carry the same bytes. `api.propose` adds one
  only with `assign_page_ids=True` and otherwise writes the caller's bytes
  unchanged. A caller's `page_id` is never rewritten. The structural linter
  reports a malformed or duplicated `page_id`.
- Attribution (0.7.0, US3). `--by NAME` on `propose` and `promote`, `by=` on
  `api.propose` and `api.promote`, and the `WIKI_STUDIO_ACTOR` variable.
  `plan.json` gains an optional `proposer` and the receipt an optional
  `actor`, each `{name, source}` with `source` `flag`, `env` or `none`. The
  receipt version stays 1. The OS user name is never recorded. This is
  attribution, not authentication. `WikiPatchSet` gains `proposer` with a
  default.
- ADR-0002 (`docs/adr/0002-page-identity-and-review-keys.md`) registers
  `page_id`, `superseded_by` and memkernel's `corrects` (its syntax not yet
  final) and reserves `approved`, `approved_by`, `approval` and
  `review_state`. `info` advertises the capabilities `page-id` and
  `attribution`.
- Approval bound to the revision and the policy (0.7.0, US4).
  `wiki-studio approve <page>... [--revision SHA] [--by NAME]` and
  `api.approve(pages, paths, *, by=None, expected=None) -> ApproveResult`
  record that a page's live bytes are approved under the manifest's policy:
  one immutable file per decision under
  `<wiki>/.audit/approvals/{id/<page_id>|path/<path-digest>}/<sha256>/<policy_sha256>/approved.json`,
  written only by `promoter.py` under the wiki lock, published by an
  exclusive link and never rewritten. The batch is checked first and refused
  (exit 9, nothing written) for a draft, a page carrying `superseded_by`, a
  structural-lint violation, a `--revision` that is not the live one, or a
  missing approver when `approver_required` is set; a legacy wiki is refused
  (exit 4) until `init` adds a manifest. An I/O failure part way is exit 6
  naming what was published; a rerun is idempotent.
- `api.review_state(paths, *, pages=None) -> list[ReviewState]`: `approved`,
  `policy-changed`, `stale`, `unapproved` (with reason `manifest_missing`,
  `draft` or `no_record`) or `superseded`, with the live and approved sha256
  and the record path. It reads verified records only; frontmatter never
  makes a page approved, and `status: stable` alone is `unapproved`.
- `auto_approve_on_promote`: after a promotion has committed and archived, a
  second lock acquisition approves each created or updated content page whose
  live bytes still equal the receipt's post-commit hash, under the promoter's
  actor; drafts and changed pages are skipped with a warning, and a failure
  never fails the promotion. `PromoteResult.approved_paths` (default empty).
- The `policy_sha256` (SHA-256 of `{"approver_required": <bool>}` as
  canonical JSON), the record keys, verification and review states are
  documented in `docs/knowledge-contract.md`. `info` advertises the
  capability `approval-record` and the format `approval: 1`. The audit lint
  validates `.audit/approvals/`.
- Explicit replacement (0.7.0, US5). The structural linter checks
  `superseded_by: <wiki-relative path>`: once normalised, the target must be
  an existing page other than the page itself and not superseded in turn (no
  chains, so no cycles); an empty, absolute or escaping target is a
  violation, so a broken target after a hand rename fails lint and a
  `promote` that would create one is refused (exit 9). `review_state` reports
  a page carrying `superseded_by` `superseded` whatever its records say.
  memkernel's `corrects` line is kept byte for byte and not interpreted. `info`
  advertises the capability `superseded-by`.

### Changed

- Reserved edits, on every wiki: `propose` and `promote` refuse (exit 4) an
  edit whose normalised path has a dot-prefixed component or lies under
  `schema/` (the manifest, the audit trail, approval records, schema
  overrides), and a `create` or `update` whose frontmatter carries
  `approved`, `approved_by`, `approval` or `review_state`. A raw
  `./index.md` append still passes.

- The schema documents are read by one contained loader: a symlinked project
  schema override or schema directory is refused (exit 4) with its target
  unread, on every wiki. `prompt.load_schema_files` keeps its name, signature
  and return value.
- `init`, `propose`, `promote` and `info` refuse a malformed manifest, one
  whose `manifest_version` or `schema.version` is newer than this package, and
  an unknown `schema.id` (exit 4). A wiki without a manifest works as in 0.6.0.
- The packaged page schema is version 2 (ADR-0002): a new manifest declares
  `schema.version` 2, and a manifest declaring version 1 is still accepted.
  `propose --from` and `ingest` creates now carry a `page_id` line.

### Fixed

- The fact check (`fact_warnings`, issue #33): a `path:line` reference or a
  `path:` line inside a fenced code block is a code sample, not a citation,
  and is no longer reported as a removed fact; the number-and-unit rule is
  stated as the contract (a unit may follow its number across one wrapped
  line, never across sentence punctuation or a blank line); a page whose
  frontmatter `sources` is not a list of mappings is reported as
  `fact_check_error: sources not compared (…)` while its body facts are
  still compared, instead of silently dropping its citations.

## [0.6.0] — 2026-10-24

The safe-changes release (Release A of `docs/roadmap.md`, closes #39). Five
defects reproduced on `main` at 41cfe54 broke promises the README made: two
promotes that started together reverted each other's pages; a replacement
carried no record of the page it was drafted from; a symlinked page, an
outside link and `find` escaped the wiki; the query check accepted a forged
quotation; and "atomic promotion" meant rollback on exception. This release
fixes the first four, states the fifth as it is, and makes each reproduction a
regression test through both `promote` and `api.promote`. Exit codes 0 and
2..11 are unchanged; the patch-set format gains optional keys only; the `api`
changes are additive with defaults.

The guarantee this release earns is bounded: wiki-studio writers that
cooperate through its API or CLI on one machine do not lose each other's
changes and do not apply stale replacements. A promotion is validated,
serialised against other wiki-studio writers on the same machine, and rolled
back on failure; it is not crash-safe across files, and uncoordinated readers
may observe intermediate state.

### Added

- The wiki lock (`wiki_studio.wikilock.WikiLock`): an OS advisory lock
  (`fcntl.flock` on POSIX) on `<wiki-parent>/.<wiki-dir-name>.wiki-studio.lock`,
  keyed to the resolved wiki directory and held by `promote`,
  `propose --promote`, proposal-directory creation (`ingest`, `query
  --file-back`, `api.propose`), the ingest-log append and `audit-flush`. Two
  promotes that start together on the same machine no longer revert each
  other's pages (the lock is not distributed and does not cover direct edits).
  `--lock-timeout` and `WIKI_STUDIO_LOCK_TIMEOUT` (default 30 s; `inf` waits
  indefinitely); on expiry every holder, `ingest` included, exits 10 with
  reason `lock_timeout`. `info` prints the lock file and timeout.
- Receipts: `promote` writes `receipt.json` into the proposal directory before
  the commit (`committing`), rewrites it after (`committed`) and archives it
  with the proposal: the submission digest and manifest, the wiki's device and
  inode, every tracked write with its pre- and post-commit sha256, timing and
  the promoter's identity. Promoting the same directory again resolves the
  receipt instead of re-applying anything; refusals exit 10 with reasons
  `uncertain_outcome`, `wiki_mismatch`, `wiki_identity_unavailable` or
  `payload_changed`. Documented in `docs/patch-set-format.md`.
- `PromoteApplyError.reason` (`wiki_studio.errors.REASON_*`); the CLI prints
  it as `[reason=...]`.
- Base revisions for replacements: `PageEdit.base_sha256` (last field,
  default `None`) and the optional `plan.json` key `edits[].base_sha256`, the
  sha256 of the page bytes the author read. `ingest` records the hash of the
  exact bytes it placed in the prompt for each candidate page it shows (the
  model cannot set or change it); `propose --from` reads `<draft>/.base.json`
  (wiki path to sha256) and never the live page; `api.propose` passes the
  caller's value through.
- `wiki-studio read <path>` and `api.read_page(path, paths)`: one page, read
  once, returning bytes, UTF-8 text and the sha256 of those bytes (`--json`
  prints `{"path", "sha256", "content"}`); a path outside the wiki or through
  a symlink exits 7, a missing page 5, a page that is not UTF-8 exits 4. The
  documented procedure for a replacement is read, draft, record.
- Revision preconditions, checked under the lock immediately before the
  commit: a `create` requires its target absent, an `update` with
  `base_sha256` requires the live page to still have that hash, appends land
  on the current content. A mismatch is `PromoteValidationError` (exit 9)
  naming the page, with nothing written.
- `--allow-unguarded-updates` / `api.promote(allow_unguarded_updates=True)`:
  compatibility mode with incomplete conflict protection that applies
  `update` edits without a base hash and records them as `unguarded_paths` in
  the receipt. `PromoteResult.unguarded_paths` and `PromoteResult.warnings`
  (both last, with defaults); the CLI prints the warnings to stderr.
- Containment boundaries (`wiki_studio.paths.contain`, one check that
  resolves both sides, refuses absolute candidates and any symlink on the
  way, and is applied before every read and write): the wiki boundary for
  page writes, staging, `read` / `api.read_page` and the navigation reads of
  `find`, `query` and the eval selector; the proposal boundary for
  `plan.json`, every `preview` pointer, every file the digest enumeration
  and the curator delta read (referenced or not) and `receipt.json`; the
  source boundary for local links in page text. Staging refuses any symlink
  inside the wiki (exit 9 naming it) and the commit re-checks every target
  with `os.lstat` under the lock. `--source-root PATH` (repeatable) and
  `WIKI_STUDIO_SOURCE_ROOTS` (`os.pathsep`-separated) admit directories
  outside the root for source references; `WikiPaths.source_roots`; `info`
  prints them.
- Citation evidence for `query`: each citation's fragment must occur, after
  whitespace normalisation, in the `index.md` or page text that was in the
  prompt (never a file reread after the backend returned), and a non-empty
  answer must carry at least one citation; a reply that fails exits 4
  naming the page. The abstention form (empty answer, one citation quoting
  `index.md`) still passes. The check verifies quotation, not logical
  support. The test backend quotes the first non-blank line of each page it
  cites.

### Changed

- `ingest`, `propose` and `query --file-back` publish a proposal under one
  wiki lock: the directory, its files, `.ingest-snapshot/` and the
  ingest-log record are written before the lock is released, and a failed
  publication is cleaned up while the lock is still held, so a concurrent
  `promote` never finds a half-published proposal.
- `ingest --legacy-single-source` keeps its deterministic
  `<date>-<slug>.md` name but never overwrites: the path is checked against
  the proposal boundary (a symlink there is refused), a previous file is
  moved aside into `<name>.bak-<pid>-<n>` beside it and restored if the
  publication fails, and the file is created exclusively. Only a regular
  file is accepted at that name. A `.bak-*` file left beside a proposal is
  an earlier proposal that a failed restoration could not put back; review
  and remove it by hand. The error names it.
- The ingest-log append opens `.audit/ingest-log.md` relative to the
  verified wiki and `.audit/` directory descriptors with `O_NOFOLLOW`
  (path-based with `O_NOFOLLOW` on the final component where `dir_fd` is
  unsupported), writes the whole record, and refuses any symlink on the
  way.
- `promote` binds `proposals/.applied` to the proposal boundary before the
  receipt is written: a symlinked `.applied`, or a file by that name, is
  refused with nothing written. A receipt's `planned_writes` and
  `submission_manifest` paths must be normalised relative paths, and each
  is contained in the wiki before a recovery read; an escaping path makes
  the outcome uncertain (exit 10) and is never read. A directory `fsync`
  that fails with a real I/O error stops the promotion; only `EINVAL`,
  `ENOTSUP`, `EOPNOTSUPP` and `EBADF` (a filesystem that does not sync
  directories) are ignored.
- Ingest's wiki state excludes a symlinked page or a page under a
  symlinked directory from the candidates, and refuses a symlinked
  `index.md` or `log.md` (exit 4), so no file outside the wiki reaches the
  prompt.
- The link rule (`lint`, and so `promote`): the collector returns every
  local link target, not only `.md` ones. Web (`http`, `https`) and
  `mailto` targets are not filesystem links; a `.md` target inside the wiki
  is a wiki-page link and must exist; a `.md` target outside the wiki and
  any non-`.md` target (image, data, source file) is a source reference
  that must resolve inside the root or an allowed source root; absolute
  targets, targets that leave the root, targets that pass through a
  symlink, an `index.md` entry outside the wiki and a symlink inside the
  wiki are violations. `../` targets inside the root stay legal.
  Reachability counts wiki-page links only. `_extract_index_links` applies
  the index-entry rule as a defence, so `find` and `query` never list a
  file outside the wiki. `lint_wiki` takes `root` and `source_roots`
  (default: the git toplevel containing the wiki, else the wiki itself).

- An `update` without `base_sha256` is refused (exit 9) with the two
  remedies named: regenerate the proposal from a fresh `read`, or pass the
  compatibility option. Creates and appends from older proposals promote
  unchanged.
- `promote --dry-run` takes the lock, stages, checks the revision
  preconditions against the live wiki, releases the lock and then validates
  the staged snapshot; it still writes nothing. The result is point-in-time
  evidence; a real promote checks again.

- The commit writes only the paths the patch-set names plus the proposal's own
  `.audit/proposals/` archive; a staged file outside that set is never written
  back.
- The archive under `<proposals-dir>/.applied/<name>/` is written from the
  captured bytes into a hidden temporary sibling and published by one
  `rename`, so a reader sees no archive at the applied name or the whole
  one; names are unchanged (`<name>`, `-2`, `-3`). The original directory
  is removed only while it still matches the archive. Archived proposals
  now carry `receipt.json` beside `plan.json`, `preview/` and
  `.ingest-snapshot/`; those three are byte-identical copies of the
  submission and are never rewritten.
- Digest recipe 2 (`audit.payload_digest`: no dot-component exclusion) for
  receipts and for new ingest-log records, which carry the optional key
  `hash_recipe: 2`; recipe 1 (`audit.proposal_hash`) stays implemented to
  verify records written before 0.6.0. The audit lint accepts the optional key
  in `v: 1`. A consumer that recomputes `proposal_hash` against the documented
  recipe must pick the recipe by the key (`schema/audit-rules.md`).
- A `preview` pointer that does not name a regular file under `preview/` is a
  contract violation (exit 4).
- Proposal directories are created exclusively under the lock: `ingest` and
  `query --file-back` take `<name>-2`, `-3` on a clash instead of writing into
  an existing directory; `api.propose` still raises `OutputWriteError`.
- The `Operating System` classifier is narrowed to POSIX: the `msvcrt` lock
  backend and the path-based staging fallback exist but are untested and
  unsupported in this release.
- Package metadata and the README point to the project page at
  https://memkernel.dev/wiki-studio/ (PyPI shows the link from the next release).
- The guarantees are stated as they are. The README, `SECURITY.md`,
  `docs/patch-set-format.md`, `schema/audit-rules.md` and the promoter
  docstrings no longer call promotion "atomic": it is validated, serialised
  against other wiki-studio writers on the same machine, rolled back on
  failure, not crash-safe across files, and uncoordinated readers may
  observe intermediate state. The lock's scope (one machine, one
  filesystem; not distributed; no protection against direct edits; network
  filesystems out of scope) is documented. The fact-preservation check is
  described as a heuristic over citations, identifiers and quantities that
  does not detect a change of meaning; the stale-source check as verifying
  that a cited path exists, not that the recorded revision is current.
- The enforced coverage gate is 92 percent (`--cov-fail-under=92` in CI and
  `CLAUDE.md`), matching the level the suite holds, instead of 80.
- README banner pinned to the `v0.6.0` tag. The memkernel arm
  (`docs/agent-arm/`) stays pinned at `wiki-studio==0.4.1` with its note:
  the arm was checked against the 0.4.1 wheel and its frozen run is kept as
  measured.

### Security

- Containment escapes in `promote`, `lint` and `find`. Credit: the
  independent code review of 23 October 2026 (revision 3), which reported
  and reproduced each escape on `main` at 41cfe54 and was adopted with the
  owner's product proposal of the same date
  (`docs/proposals/2026-10-23-product-proposal.md`). A symlinked page
  inside the wiki was staged and written
  through to its target; a page could link to an absolute path or a path
  outside the project and lint accepted it; an `index.md` entry pointing
  outside the wiki was followed by `find` and `query`; a `preview` pointer
  or an unreferenced symlink under `preview/` or `.ingest-snapshot/` could
  make the digest or the curator delta read a file outside the proposal
  directory. Every read and write surface now passes the containment check
  described under Added. Present since 0.1.0 (`find` since 0.4.0).
- A fabricated citation was accepted by `query`: a fragment that did not
  occur in the cited page passed the check, and so did a non-empty answer
  with no citation at all. Same reporter. See citation evidence under
  Added. Present since 0.1.0.
- Found on the 0.6.0 build itself, before release, by the code review of
  PR #41 (five rounds), and fixed in the same release: a proposal was
  published in pieces (files, then snapshot, then audit record) with the
  lock released in between, so a concurrent `promote` could archive a
  half-published proposal; the ingest-log append followed a symlinked
  `.audit/` or `ingest-log.md` and could report a short write as success;
  a symlinked `proposals/.applied` received the archive and the source
  proposal was removed; a receipt's tracked paths were joined to the wiki
  directory and read during recovery without containment; ingest's
  candidate pages, `index.md` and `log.md` were read through symlinks into
  the model prompt; a directory `fsync` failure (`EIO`, `ENOSPC`) was
  swallowed and the promotion continued; the legacy single-source proposal
  was written through a pre-existing symlink and a failed publication could
  delete or overwrite an earlier proposal at the same deterministic name.
  See Changed for the behaviour each fix introduces.

### Upgrade notes

Stated per operation. The patch-set format and the library API are
supersets of 0.5.0; what changes is what `promote` accepts.

- `create` edits from proposals written before 0.6.0 promote unchanged,
  unless the target page now exists (exit 9, as `create` of an existing
  page always was at validation time; now also checked under the lock).
- `append-index` and `append-log` edits from older proposals promote
  unchanged; the lines land on the current content.
- `update` edits from older proposals carry no `base_sha256` and are refused
  (exit 9) with the two remedies named. Either regenerate the proposal from
  a fresh `wiki-studio read <path> --json` (or `api.read_page`) so the edit
  records the page it was drafted from, or pass `--allow-unguarded-updates`
  (`api.promote(allow_unguarded_updates=True)`). That option is
  compatibility mode with incomplete conflict protection: a stale draft can
  overwrite a newer page, and the paths are recorded as `unguarded_paths` in
  the receipt and in `PromoteResult`.
- `ingest` records `base_sha256` for an `update` to a page the prompt showed
  the model (the hash of the exact bytes it placed there); an `update` to a
  page the prompt did not show is unguarded. A
  `propose --from` draft needs `<draft>/.base.json` for each replaced page;
  `propose` never fills it from the live page. An `api.propose` caller
  passes `PageEdit.base_sha256` itself.
- Pages that link to a file outside the project root (or through a symlink)
  now fail `lint`, and so `promote`. Add `--source-root PATH` or
  `WIKI_STUDIO_SOURCE_ROOTS` for directories outside the root that pages
  may legitimately reference; `../` targets inside the root need nothing.
- `lint_wiki` callers that pass only a wiki directory are unchanged; the
  new `root` and `source_roots` parameters default to the git toplevel
  containing the wiki, else the wiki itself.
- A proposal directory with a leftover `receipt.json` from an interrupted
  promotion is resolved, not re-applied; the refusal reasons and the manual
  remedy are in `docs/patch-set-format.md`. Add
  `.<wiki-dir-name>.wiki-studio.lock` (beside the wiki) to `.gitignore`.
- Consumers that recompute the ingest-log `proposal_hash` must pick the
  recipe by the record's `hash_recipe` key (`schema/audit-rules.md`).
- Windows is no longer in the `Operating System` classifier; see Changed.

### Limitations

- The lock serialises wiki-studio writers on one machine and one
  filesystem. It is not distributed, does not cover direct edits of wiki
  files by other tools, and network filesystems are out of scope.
- A promotion is not crash-safe across files. A process killed inside the
  commit can leave some files written and others not; the receipt protocol
  recovers from a failure between its steps (before the commit, between the
  commit and the archive, during the archive) and not from a crash inside
  the commit itself. Recovery needs a filesystem with stable inode identity.
- memkernel's wiki bridge takes a whole-wiki snapshot around its lifecycle
  and rolls the wiki back to it on failure. That outer rollback can still
  undo another writer's committed changes until memkernel holds the same
  lock across its lifecycle or removes that workaround. Mixed-writer safety
  across the memkernel stack is therefore not claimed by this release; it is
  claimed only when both halves ship, after the combined integration gate
  (bridge compatibility of creates and appends through `api.propose`,
  receipt and `.applied/` layout, lock coordination) that is the first item
  of Release B in `docs/roadmap.md`.

## [0.5.0] — 2026-10-20

Plain technical English for wiki pages (closes #28): writing rules in the
prompts, a glossary term lock, advisory prose checks and fact-preservation
warnings on updates. Exit codes are unchanged; the patch-set format and the
page schema gain one optional key each; `promote` is never blocked by the new
findings.

### Added

- Writing rules for wiki prose (issue #28). `schema/ingest-rules.md` gains a
  `## Writing rules` section: one fact per sentence, at most 25 words per
  sentence (20 in numbered steps), one instruction per step, active voice, no
  semicolons, the glossary term for each concept, and a first `## Summary`
  sentence that states the main claim. A preserve list keeps identifiers,
  paths, numbers, `path:` citations and the words "if", "unless" and
  "not verified", and tells the model to split long sentences, not cut them.
  The ingest, multi-page ingest and query prompts already load
  `ingest-rules.md`, so all three now carry the rules. `page-types.md`,
  `WIKI_MAINTAINER.md` and `lint-rules.md` point to the section.
- Optional `avoid:` key on glossary pages (page schema addition, issue #28).
  A per-file glossary page may carry `avoid: alignment check, origin check`,
  and a `glossary/index.md` entry may carry an `Avoid: …` line as the first
  line after its `### <term>` heading. The value is one line of
  comma-separated terms, unquoted or double-quoted; a term cannot contain a
  comma, `"` or `\`. Any other form is reported by `lint --health` as the new
  `avoid-format` finding and contributes no terms. A per-file glossary page's
  avoid terms count as mentions of that page in the missing-cross-links
  check. Existing pages stay valid. Decision record:
  `docs/adr/0001-glossary-avoid-key.md`.
- `wiki-studio lint --prose` (issue #28): advisory prose checks for sentence
  length, semicolons, filler phrases, `## Summary` and `## Key ideas` length,
  and the glossary term lock, which reports each avoid term used on a
  non-glossary page with its canonical term. Code, tables, quotes and HTML
  comments are skipped. Findings go to stderr as `path:line [check] message`;
  the exit code is 0, or 1 under `--strict`. `--paths` limits the pages
  scanned; the term lock still reads the whole glossary. `api.lint` gains
  `prose: bool = False` and `LintResult.prose`.
- Fact-preservation warnings on updates (issue #28). When `ingest`,
  `query --file-back` or `propose` writes an `update` edit whose page exists,
  the citations (`sources[].path`, `path:line`), backticked identifiers and
  numbers with a unit that the new content drops are recorded as
  `edits[].fact_warnings` in `plan.json` (an optional key, documented in
  `docs/patch-set-format.md`) and printed to stderr as
  `fact-check: <path>: N item(s) removed`. `propose --promote` prints them
  before it applies the patch-set. The warnings are advisory: no exit code
  changes and `promote` ignores the key. A number keeps its minus sign and a
  fraction without a leading zero (`.5 s`) is read as `0.5 s`. When the live
  page cannot be read or decoded, `edits[].fact_check_error` records why,
  the CLI prints `fact-check: <path>: not compared (<reason>)` and the
  proposal is still written.

### Changed

- Whole-word slug matching in the missing-cross-links check. A slug used to
  count as mentioned when it appeared anywhere as a substring, so `lint`
  matched `linter` and `lint-rules`. Letters, digits, `_` and `-` now count
  as word characters on both sides, and a slug written with spaces matches
  only within one paragraph. This removes false `missing-cross-link`
  findings, which can change the result of `lint --health --strict`.

### Upgrade notes

- A wiki with its own `schema/ingest-rules.md` overrides the packaged copy, so
  its prompts do not get the writing rules. Merge the `## Writing rules`
  section from the packaged `src/wiki_studio/schema/ingest-rules.md` into the
  local copy.

## [0.4.1] — 2026-10-17

Fixes only. The one addition is `propose --allow-out-of-repo` (#24); exit codes,
the patch-set format and the page schema are unchanged.

### Fixed

- `promote` keeps its all-or-nothing guarantee when a write into the wiki fails
  (issue #21). The file being written when the error hit was never restored,
  because a target counted as written only after its write returned, so a new
  page stayed half-written and an existing `index.md` or `log.md` stayed
  truncated. Rollback ran only for `OSError`, so any other exception (an
  encoding error, `KeyboardInterrupt`) left every earlier write in place. And
  rollback rewrote a page from its decoded text, which turned CRLF line endings
  into LF. Each target is now recorded before it is written, rollback restores
  each file's exact original bytes and removes directories the commit created,
  and it runs on any exception: an
  `Exception` still exits 10, while `KeyboardInterrupt` and `SystemExit` are
  re-raised after the rollback. Present since 0.1.0.
- Two edits that spell the same file differently (`index.md` and
  `./index.md`) no longer share a preview file (issue #23). The #18 fix counted
  edits per raw path string, so the second append overwrote the first and
  promote rejected the first page as an orphan. Previews are now allocated by
  normalised path; `./index.md` is still accepted. Affected 0.4.0.
- `propose --from DIR --promote` works with a proposals directory outside the
  root (issue #24). It wrote the proposal and then exited 7, telling the user to
  pass `--allow-out-of-repo`, which `propose` did not accept. `propose` now
  takes `--allow-out-of-repo` and forwards it to the promote step; without it
  the refusal is unchanged. Affected 0.4.0.

### Changed

- README banner pinned to the `v0.4.1` tag; the memkernel arm (`docs/agent-arm/`)
  and the consumer install step pin `wiki-studio==0.4.1`.

## [0.4.0] — 2026-10-16

What an agent needs to use the wiki from a shell with no model backend, and a
ready arm for memkernel's lifecycle suite (issue #10, layer 2).

### Added

- `wiki-studio init` / `api.init`: create the wiki directory with a minimal
  `index.md` and `log.md` when absent (promote needs both); never overwrites.
  Lives in the promoter, which stays the only module that writes into the wiki.
- `wiki-studio propose --from DIR [--promote]` / `api.edits_from_dir`: pages an
  agent wrote, laid out like the wiki, become a validated patch-set (`create`,
  or `update` when the page exists); `DIR/index.md` and `DIR/log.md` hold the
  lines to append and are refused if they carry frontmatter. `--promote`
  applies it at once. No backend.
- `wiki-studio find "<question>"` / `api.find`, `FindResult`, `FoundPage`: the
  pages `query` would load, without a model and without writing the query log.
- `docs/agent-arm/`: a `wiki_studio` arm for memkernel's
  `eval/lifecycle-suite/` (config in its format, an instruction within 5
  percent of memkernel's block length, the list of memkernel changes needed).
  Adopting and running it happens in memkernel.

### Fixed

- Several `append-index` or `append-log` edits to the same file in one
  patch-set are all applied, in order (issue #18). The patch-set writer gave
  every edit the preview file `preview/<path>`, so a second edit to the same
  path overwrote the first and only the last line survived; promote then
  rejected the earlier pages as orphans. Each edit now has its own preview
  file (`preview/<path>`, then `preview/<path>.2`, `.3`, ...), which `plan.json`
  already points at. This affected `ingest`, `api.propose` and the new
  `propose --from` with a multi-line `index.md` or `log.md` since 0.1.0. The
  workaround of joining lines into one edit keeps working.
- `promote` no longer leaves a proposal behind when the archive already holds
  one with the same name: it is archived next to it as `<name>-2`, `-3`, ...
  (as `.audit/proposals/` already did), and the CLI no longer prints
  "archived to" for a move that did not happen. Old behaviour, reachable once
  `propose --from` made repeated same-day recordings routine.

### Changed

- README banner pinned to the `v0.4.0` tag.
- `propose --from` names a proposal `<date>-<HHMMSS>-<dir-name>`, with a
  numeric suffix if that name is taken, so repeated recordings never collide.
- `find` on a wiki without `index.md` exits 5 and points at `init`.

## [0.3.1] — 2026-10-16

### Fixed

- Multi-page ingest no longer leaves the model to guess how `index.md` and
  `log.md` change (issue #15). In run 2 of the navigation evaluation, three of
  ten documents were rejected because the model returned `index.md` as a full
  page edit (`page_type: index`, no sources) instead of an `append-index`
  line. The prompt now says that the root `index.md` changes only through a
  one-line `append-index` edit and `log.md` only through a one-line
  `append-log` edit, never as a full page and never with frontmatter; that a
  `<dir>/index.md` which is itself a content page (`glossary/index.md`) is
  edited with `create` or `update`; and that `create` and `update` are only
  for content pages; the response schema's `action` and
  `new_content` carry the same rule. The validator is unchanged: a full-page
  index edit is still a contract violation (exit 4). Run 2 is kept as
  measured on 0.3.0.

### Added

- `py.typed`: the package declares its type hints (PEP 561), so type
  checkers in consuming projects (memkernel) read them without a per-package
  override.

### Changed

- The README banner points at the image at this release's tag, so the PyPI
  page shows it (0.3.0's page cannot; PyPI descriptions are frozen per
  version) and stays intact if the file later moves.

## [0.3.0] — 2026-10-16

The evidence release: the first measured numbers about the tool, with the
caveats they need (issue #10, mirror of memkernel #17).

### Added

- `eval/navigation/`: a frozen corpus (memkernel's documentation at tag
  `v0.4.0`, attributed in NOTICE), a question set committed before any
  ingest ran, a wiki the tool produced from the corpus once through its own
  gate, gold pages assigned afterwards with a written reason each, and
  `run.py`, a stdlib script reporting ingest coverage, navigation hit rate at
  1 and at 5, and words loaded by `query` against a written-down grep rule.
  `tests/test_navigation_eval.py` asserts the script reproduces the committed
  `results.json` and that the fixture is the preregistered one.
- README "Evidence" section with run 1's numbers and caveats, and run 2's
  next to them: `eval/navigation/run2/` is a second measurement on the 0.3.0
  code under a revised protocol (`eval/navigation/run2_protocol.py`: Claude
  hooks isolated and verified by a recorded probe before any attempt, commit,
  versions, model and settings pinned, one attempt per document), with the
  same questions, corpus and stop list used in place. Run 1 is unchanged.
- `wiki-studio info`: prints the resolved layout (default or custom; root,
  wiki and proposals directories with their source, flag, variable or
  default, and whether they exist; logs; which schema copy applies), or the
  same as JSON with `--json`. Read-only, exit 0. `--version` is unchanged.

### Fixed

- Ingest at a custom wiki location (issue #11). The prompt shows wiki files
  under `<wiki-dir>/…` headings but never said that edit paths are relative
  to the wiki directory; with a one-word directory name the model copied the
  prefix and eight of ten ingests in the navigation evaluation's run 1 failed
  validation. The multi-page response instructions and the response schema
  now state the rule, and the exact configured prefix is removed once before
  the unchanged validators run, unless the path already has a valid
  wiki-relative shape (a wiki directory named `concepts` keeps
  `concepts/x.md`). Run 1's numbers were measured on 0.2.0 and are kept as
  measured.

### Changed

- `ingest --help` no longer says multi-page ingest "lands in Phase 1" or that
  `--legacy-single-source` is required; multi-page has been the default since
  0.1.0. Help text only.

### Not built

- The mutation suite for the promote gate (spec US4) is dropped for this
  release under its own condition: run 1 archived a single patch-set, too few
  to generate a corpus from, and a hand-written one would duplicate the unit
  tests.

### Known issues

- Run 1 of the navigation evaluation was measured on 0.2.0, before the
  issue #11 fix above, and promoted one document in ten; it is kept as
  measured. Run 2, on the fixed code, promoted seven.
- In run 2 the three documents that did not promote were rejected by the
  per-edit validator, correctly: the model answered with `index.md` as a full
  page edit (`frontmatter page_type 'index' is not promotable for
  create/update`; `'sources:' must be a non-empty list`) instead of an
  `append-index` line. The validator did its job; the gap is in the prompt,
  which tells the model to "add a link from the appropriate section of
  index.md" without naming the action. To be filed and fixed in a later
  release; run 2 is kept as measured.
- The `claude` text-mode backend exposes no token counts, so ingest cost is
  reported as wall time only. In run 1 a Claude Code Stop hook ran this
  repository's test suite inside each backend call with the fixture's paths
  inherited, which inflated wall time and added test records to the fixture's
  audit and query logs; everything is preserved and the manifest marks the
  run `requires_review` (`eval/navigation/ingest-notes.md`).

## [0.2.0] — 2026-10-15

The memkernel release: the two contracts memkernel 0.5's `memkernel[wiki]`
extra builds against, and a recipe fix (issue #7).

### Added

- `wiki_studio.api.propose(edits, paths, *, name, source="", rationale="", backend="api")`:
  a library caller hands a list of `PageEdit`s to the package and gets back a
  patch-set directory under the proposals dir that `api.promote` applies
  through the usual gate. The edits are validated first with the checks
  `ingest` and `promote` already run; an invalid list, an invalid `name` or an
  existing directory writes nothing. `propose` never touches the wiki or the
  ingest log.
- `PageEdit`, `PageAction` and `WikiPatchSet` are re-exported from
  `wiki_studio.api` and, together with the `api` functions, the result
  dataclasses and the patch-set directory format, declared public under
  semantic versioning (`api.__all__` lists the surface).
- `docs/patch-set-format.md`: the on-disk patch-set format (`plan.json`,
  `preview/`, `.ingest-snapshot/`) and what `promote` does with it.
- `wiki_studio.schema`: the page schema as code. `PAGE_TYPES: dict[str, PageTypeSpec]`
  (`directory`, `required_sections`, `promotable`, `sources_required`) for the
  ten page types of `page-types.md`, plus the derived `VALID_PAGE_TYPES`,
  `PAGE_TYPE_DIRS`, `PROMOTABLE_PAGE_TYPES`, `SOURCELESS_PAGE_TYPES` and
  `REQUIRED_KEYS`. A test parses `page-types.md` and fails when the two
  disagree.

### Changed

- `wiki_studio/schema/` is now a package (it gained `__init__.py`); the six
  markdown documents stay there and are loaded as before. `lint.VALID_PAGE_TYPES`,
  `lint.PAGE_TYPE_DIRS` and `lint.REQUIRED_KEYS` are re-exports of the schema
  module; the linter, the prompt composer, the edit validator and the audit
  record builder read the schema module instead of their own copies of the
  page-type tables. Lint and validation messages are unchanged.
- For consumers probing for the module: on 0.1.0 `import wiki_studio.schema`
  succeeds as an empty namespace package; test for `wiki_studio.schema.PAGE_TYPES`.

### Fixed

- `docs/consumers.md`: the memkernel recipe ran `memkernel wiki_export`, which
  is not a shell command (`wiki_export` is memkernel's MCP tool). The recipe
  now shows the library call and the propose → promote flow a memkernel ≥ 0.5
  bridge uses.

## [0.1.0] — 2026-10-12

The extraction release. The maintainer that lived in
`code-copilot-team/scripts/wiki_ingest` becomes the `wiki_studio` package with
the `wiki-studio` console script. Behaviour, verbs, flags and exit codes are
unchanged; the paths are decoupled.

### Moved

- Every module of `code-copilot-team/scripts/wiki_ingest/` at commit
  `df2c29212e3bed8b547f47bf7976105a6a4678c0` is now `src/wiki_studio/`:
  `__main__.py` became `cli.py` (a two-line `__main__.py` remains for
  `python -m wiki_studio`); the other modules keep their names, including the
  `backends/` package with `copilot_cli.py`, `json_extract.py` and `test.py`.
- The six schema documents from `code-copilot-team/knowledge/wiki/schema/`
  ship as package data under `wiki_studio/schema/`.
- The 240 tests moved to `tests/` and pass in-process (see "Tests" below).

### Added

- `wiki_studio.paths.WikiPaths`: every location (`root`, `wiki_dir`,
  `proposals_dir`, `query_log`, `audit_log`, `schema_dir`) resolved once
  from the global options `--root`, `--wiki-dir`, `--proposals-dir`, then
  `WIKI_STUDIO_ROOT`, `WIKI_STUDIO_WIKI_DIR`, `WIKI_STUDIO_PROPOSALS_DIR`, then the
  defaults (git toplevel of the current directory; `knowledge/wiki`;
  `doc_internal/proposals`). The defaults reproduce the original layout
  byte for byte. The options are accepted before or after the verb.
- `wiki_studio.lint`: the six structural checks of `lint-wiki.sh` in Python,
  with the same messages; `lint` and `promote` run it in-process.
- `wiki_studio.api`: `ingest`, `promote`, `query`, `lint`, `audit_flush` taking
  a `WikiPaths` and returning typed results; `cli.py` is a thin parser over
  them and maps exceptions to exit codes in one place.
- `wiki_studio.errors.PathOutsideRootError` (exit 7) so the library can report
  the confinement refusal the CLI always had.
- `WIKI_STUDIO_BACKEND` names the default backend; `WIKI_STUDIO_ENABLE_PI=1` adds
  `pi` to the auto-detect order.
- `wiki-studio --version`.
- A fixture wiki (`tests/fixtures/wiki/`) with one page of every page type
  and three draft pages in the shape memkernel 0.3's `WikiExporter`
  writes; the suite asserts it lints clean, which pins the schema
  contract between the two packages.
- `docs/consumers.md` with the recipes for code-copilot-team, memkernel and
  document-assistant; CI on Python 3.11, 3.12 and 3.13; a PyPI release
  workflow using trusted publishing.

### Changed

- The distribution, console script and repository are named `wiki-studio`
  (import `wiki_studio`, variables `WIKI_STUDIO_*`). The bundle's earlier
  working names were `aiwiki` (`ai-wiki` is taken on PyPI) and `wikiforge`
  (PyPI rejects it as too similar to the existing `wiki-forge`). The GitHub
  repository was renamed to `gosha70/wiki-studio` on 2026-10-13.
- `load_schema_files` prefers `<wiki-dir>/schema/` when that directory
  exists and otherwise reads the packaged documents.
- The root is no longer derived from the package's own location (which is
  meaningless once installed) but from the working directory's git
  toplevel.
- The `pi` backend no longer reads `shared/capabilities/pi.yaml`;
  `--backend pi` works as before, auto-detection needs `WIKI_STUDIO_ENABLE_PI=1`.
- Rendered prompts label wiki pages with the root-relative wiki directory
  (`knowledge/wiki/...` by default) or the directory name when the wiki is
  outside the root.
- `health_lint.lint_health(paths, only=...)`: the first parameter is a
  `WikiPaths`; the page filter formerly called `paths` is now `only`.
- `audit_flush.flush` is a printing wrapper around the new `flush_state`.
- The CLI help text mentions the new wrapper name and the configurable
  directories instead of the old script paths; wording of error prefixes
  on stderr is unchanged.

### Deprecated

- `WIKI_INGEST_BACKEND`: still honoured, prints a one-line warning on
  stderr; use `WIKI_STUDIO_BACKEND`.

### Removed

- The bash structural linter is not shipped; `lint` no longer exits 2 when
  it is missing (it cannot be).
- The `code-copilot-team` capability-file lookup and the `PYTHONPATH`
  wrapper scripts (replaced by the console script; see
  `docs/consumers.md` for the two `exec` lines).

### Tests

357 tests (240 moved, 117 added). Moved tests that were renamed or
re-homed:

- `tests/test_e2e.py::TestE2EBashEntrypoint::test_bash_entrypoint_runs_test_backend`
  is now `TestE2EModuleEntryPoint::test_python_m_wiki_studio_help_lists_verbs`,
  the one subprocess test (`python -m wiki-studio --help`); every other CLI test
  calls `wiki_studio.cli.main(argv)` in-process inside a temporary layout.
- `tests/test_e2e.py::TestE2ESingleWriterInvariant::test_only_promoter_writes_to_knowledge_wiki`
  is now `test_only_promoter_writes_to_wiki_dir` and keys on `wiki_dir`.
- `tests/test_audit.py::TestLintWikiShellAuditExclusion` (two tests of the
  bash linter) is now `tests/test_lint.py::TestAuditExclusion`.
- `tests/test_pi_wiki_backend.py::test_capability_reader_reflects_the_real_pi_yaml`
  is now `test_pi_auto_detect_is_gated_by_environment_flag`; the patched
  symbol `_pi_capability_enabled` is `_pi_enabled`.
- `tests/test_copilot_cli.py` reads `WIKI_STUDIO_BACKEND`; the deprecated alias
  has its own tests in `TestBackendEnvironmentVariables`.
- `tests/test_prompt.py` and `tests/test_ingestor_with_test_backend.py`
  build a temporary layout instead of locating the repository.

New modules: `test_cli_contract.py`, `test_paths.py`, `test_lint.py`,
`test_package_boundaries.py`, `test_api.py`, `test_fixture_wiki.py`.

### Known issues

Pre-existing behaviour of the moved code, flagged in review and recorded
for 0.2 rather than changed in the extraction release:

- `audit_flush` counts data lines after a fixed two-line preamble; a
  working log without the marker is rejected as malformed before the
  count is used, so the count cannot be acted on, but the helper does not
  verify the marker itself.
- `audit_flush` treats any `git show HEAD:<log>` failure other than
  "not a git repository" as "file absent at HEAD".
- Multi-page `ingest --dry-run` is not dry: the backend drafts every page
  and the patch-set directory is written; only the audit record is marked
  (`proposal_hash` null). A dry-run signal in the prompt contract that the
  backends honour is planned for 0.2.
- The legacy single-source ingest records the proposals directory, not the
  proposal file, as `proposal_dir`, hashes an empty payload, and leaves an
  empty `.ingest-snapshot/` next to the file. This is the v1 shim's
  original behaviour; consumers parsing the log would see the change, so
  it is kept for 0.1.0.
- The legacy single-source ingest passes the dry-run intent to the prompt
  through the `WIKI_INGEST_TASK` environment variable; the multi-page path
  does not use it.
- `build_log_record` records a source inside the root as repo-relative
  even with `--allow-out-of-repo` (the flag only matters for sources
  outside the root).
- `append_ingest_log` rewrites the file rather than renaming a temp file;
  a torn write is detected and refused by `audit-flush`.
- The contradiction check assumes a backend returns a dict; a backend that
  returns a non-string, non-dict value would raise inside the health pass.
- The cross-link heuristic strips frontmatter by searching for the first
  `\n---` after the opening marker.
- The legacy argv shim (`python -m wiki_studio <source>` without a verb) treats
  the value of a flag other than the three global options as a positional
  when deciding whether a verb is present; the documented shapes work.

[Unreleased]: https://github.com/gosha70/wiki-studio/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/gosha70/wiki-studio/compare/v0.5.0...v0.6.0
[0.1.0]: https://github.com/gosha70/wiki-studio/releases/tag/v0.1.0
