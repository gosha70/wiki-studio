---
pitch_id: 38-release-b-governed-curation
title: "Release B, governed curation (wiki-studio side): combined integration gate, versioned contract, identity, approval bound to the revision, superseded_by, model-free findings"
appetite: 6w
bet_status: building
cycle: "02"
circuit_breaker: "Core is S1, S2 and S4; they are never cut. If S1 and S2 are not downhill at the end of week 2, cut S6. If S4 is not downhill at the end of week 4, also cut S3's rename identity (page_id); approvals and findings then key by wiki path, 0.7.0 may ship, and Release B stays open until page_id lands. If S5's lint rules are not done at the end of week 5, ship S5 as its ADR, its key and the superseded review state. If memkernel's counterpart is not merged by the end of week 5, ship 0.7.0 with this side only, keep the memkernel limitation in the CHANGELOG and do not declare Release B closed. Never take approval from frontmatter, weaken a gate test, add a dependency, a model call or an exit code, or make WikiLock reentrant to stay on schedule."
shaped_by: "pitch-shaper (Claude Code) for gosha70"
shaped_date: 2026-10-24
---

<!-- Shape-Up pitch. Origin: https://github.com/gosha70/wiki-studio/issues/38 -->
<!-- Bridge-side mirror: https://github.com/gosha70/memkernel/issues/48 -->
<!-- The issues and docs/roadmap.md (Release B) are the origin. This pitch shapes them; it does not replace them. -->

# Pitch: Release B, governed curation (wiki-studio side)

## Problem

0.6.0 made wiki-studio's own writers safe. It did not make the curation
loop trustworthy, and it says so. Three gaps remain.

1. **Mixed-writer safety is not claimed.** memkernel's bridge takes a
   whole-wiki snapshot before an export and restores it on failure. The
   restore runs outside the wiki lock. It can rewrite another writer's
   committed pages and delete that writer's archived `plan.json`. The
   0.6.0 CHANGELOG lists this under Limitations and defers the fix to "the
   combined integration gate", the first item of Release B.
2. **Nothing says which knowledge is approved.** A page's `status` is
   whatever its author wrote. memkernel's importer skips only `deprecated`
   pages, so it imports drafts. No record binds an approval to a revision,
   so a manual edit after review is indistinguishable from the reviewed
   text.
3. **Nothing says which contract a wiki follows.** `info` prints paths, not
   versions or capabilities. A project-local schema copy cannot be told
   apart from the packaged one. An adapter cannot check compatibility
   before it writes.

The cost is the roadmap's central claim. "Replacing a revision keeps the
obsolete version from returning as current knowledge" cannot be shown
today. A corrected page is imported beside the wrong memory it corrects,
and a draft is recalled as if it were reviewed.

## Findings from the code

wiki-studio was read at main 4979178 and memkernel at its local checkout
9d93544, on 2026-10-24. These facts drive the scopes and rabbit holes.

1. **The bridge emits three actions only.** `propose_and_promote`
   (`memkernel/wiki/studio.py:151-193`) builds `create` edits
   (`studio.py:169-172`), one `append-index` (`studio.py:173-181`) and one
   `append-log` (`studio.py:182-187`). It calls `api.propose` then
   `api.promote` (`studio.py:189-190`) with
   `WikiPaths.for_root(project_root, wiki_dir=..., proposals_dir=...)`
   (`studio.py:188`). The default proposals directory is
   `<project>/.memkernel/wiki-proposals` (`sync.py:50`), not wiki-studio's
   default. It never emits `update`, so 0.6.0's base-revision rule does
   not affect it.
2. **The snapshot covers the whole wiki and runs unlocked.**
   `_export_gated` takes `_WikiSnapshot` (`sync.py:221`), writes the
   scaffold (`sync.py:222`), calls the gate (`sync.py:223`), and on
   `GateError` or `OSError` calls `restore()` (`sync.py:228`). `_tracked`
   is every `*.md` plus every `.audit/**/plan.json` (`sync.py:326-333`).
   `restore` deletes any tracked file that appeared after `take`
   (`sync.py:338-343`) and rewrites any that changed (`sync.py:344-350`).
   The docstring gives the reason: pre-0.4.1 promote wrote back every
   differing `*.md` (`sync.py:300-311`). 0.6.0's scoped commit removed that
   reason.
3. **The scaffold is written directly.** `_ensure_scaffold`
   (`sync.py:238-243`) writes `index.md` and `log.md` with
   `exists()` then `write_text`. wiki-studio's `init_wiki` does the same
   job with exclusive creation (`promoter.py:1653-1673`) and is public as
   `api.init`.
4. **The importer has no approval check and keys by slug.**
   `import_pages` (`sync.py:387-418`) skips only `status == "deprecated"`
   (`sync.py:401`). Status feeds importance, not eligibility
   (`sync.py:413`). Identity is the tag `page:<slug>` (`sync.py:405-406`),
   so a rename creates a new memory. A changed page supersedes its previous
   memory (`sync.py:407`). memkernel's `Memory` already carries
   `supersedes` and `superseded_by` (`memkernel/core/models.py:161,168`).
5. **Exported pages carry the originating memory.** The exporter writes
   `status: draft` (`sync.py:273`) and the extra keys `memkernel_ref` and
   `memory_type` (`sync.py:277`), plus a `memkernel://<project>/<ref>`
   source (`sync.py:264-266`). This is the page-to-memory link the
   raw-memory reconciliation can start from.
6. **memkernel admits any 0.x wiki-studio.** The pin is
   `wiki-studio >=0.3.1,<1` in the `wiki` extra and the dev group
   (`memkernel/pyproject.toml:35,48`). memkernel's CI therefore already
   installs wiki-studio, and is the natural home for the real-package
   combined test.
7. **The lock is not reentrant, and a held lock can already be passed
   internally.** `WikiLock` opens a fresh file description and takes
   `flock` on it (`wikilock.py:179-184`), so a second acquisition in the
   same process waits for the timeout (`wikilock.py:19-20`). `api.propose`
   takes the lock itself (`api.py:598`). Two internal functions already
   accept a held lock and verify it: `write_patch_set_dir(..., lock=)`
   (`ingestor_multi.py:207-214`) and `append_ingest_log(..., lock=)`, which
   refuses a lock that is not held or whose `lock_path` is not this wiki's
   (`audit.py:415-417`).
8. **`info` has no versions or capabilities, and there is no `api.info`.**
   `_do_info` prints paths, sources, schema location and lock file
   (`cli.py:646-693`). `info` exists only in the CLI. The formats already
   carry versions: `plan.json` `version: 1` (`ingestor_multi.py:308`),
   `receipt_version = 1` (`promoter.py:101`), ingest-log `v: 1`.
9. **`init` writes no manifest.** `init_wiki` creates `index.md` and
   `log.md` only (`promoter.py:1653-1673`). The packaged rules the code
   runs are Python constants (`schema/__init__.py`, `lint.py`); the
   markdown documents are loaded only by the prompts, and only three of
   them (`ingest-rules`, `page-types`, `citation-rules`), where a project
   copy under `<wiki>/schema/` wins file by file (`prompt.py:36-46`). So
   the package version identifies the packaged rules, and only a project
   override can make a wiki's rules differ from them.
10. **The page schema has no identity, approval or supersession keys.**
    Required keys are `page_type, slug, title, status, last_reviewed`
    (`schema/__init__.py:93`); `status` is `draft | stable | deprecated`
    (`page-types.md:16`). There is no `page_id`, `superseded_by` or
    approval key anywhere in `src/` or the schema documents.
11. **There is no move or delete action.** `PageAction` is `create`,
    `update`, `append-log`, `append-index` (`proposal.py:70`). A rename
    today is a hand edit.
12. **No actor is recorded.** The receipt's `promoter` field is software
    identity only: package, version, entry point (`promoter.py:1003`,
    `docs/patch-set-format.md:180`). No verb takes `--by`.
13. **Health checks are already model-free unless a backend is passed.**
    The contradiction check is a no-op without a backend
    (`health_lint.py:323-328`). The other four kinds are deterministic
    (`proposal.py:152-158`). What is missing is review-state findings and a
    surface that cannot take a backend at all.
14. **Exit codes in use** are 0, 1 (fatal lint), 2-7, 9, 10, 11
    (`errors.py`), with 8 for "not implemented". Every refusal this pitch
    adds maps to an existing code: 4 (contract violation), 9 (validation),
    10 (lock or recovery).

## Appetite

**6w**, one bet, released as **0.7.0** (owner decision, 2026-10-24). For
an LLM executor the work content is about
33-44 hours across six scopes:

| Scope | Estimate |
|-------|----------|
| S1 Combined integration gate | 5-7h |
| S2 Versioned knowledge contract | 7-9h |
| S3 Identity and attribution | 5-7h (page_id 3-4h, attribution 2-3h) |
| S4 Approval bound to revision and policy | 10-13h |
| S5 `superseded_by` | 3-4h |
| S6 Model-free findings | 3-4h |

That is about 2.3-2.5 times the 0.5.0 pitch (14.5-17.5h in 2w). Three
things push the wall-clock budget past 4w:

- **Review depth.** 0.6.0's build needed five review rounds on one PR
  (#41). S4 adds a new record format and a new write path into the wiki,
  which will draw the same scrutiny.
- **A cross-project dependency.** The exit evidence is a joint loop. It
  needs memkernel's snapshot removal and approved-only import, which are
  memkernel's work on memkernel's schedule.
- **A shaping decision with memkernel before build** (Rabbit holes: the
  snapshot closure), plus the `corrects` key question in S5.

Why not split into two bets (A: S1+S2, 2w; B: S3-S6, 4w)? The scopes
divide cleanly there, and the split stays available. One bet is preferred
for three reasons:

- S3's attribution and S4's record extend the formats S2 versions. One
  release publishes the contract once, with every capability it names.
- The owner's constraint is one version, 0.7.0, additive.
- The week-2 checkpoint in the circuit breaker gives the same early signal
  a split would.

Planned order, as wall-clock weeks:

- **Week 0 (before any build phase):** settle the snapshot closure and the
  `corrects` key with memkernel. Record both in this pitch's bet log and
  in memkernel #48.
- **Weeks 1-2:** S1 and S2. memkernel removes the snapshot in parallel.
- **Weeks 3-5:** S3, S4, S5.
- **Weeks 5-6:** S6, the joint loop run on clean installs, release.

## Solution shape

Six additions, all standard library, all additive to the 0.6.0 API and
formats. No new exit code and no new runtime dependency. `promoter.py`
stays the only module that writes into the wiki directory. That now
includes the root manifest and the approval records.

1. **Prove the bridge path (S1).** Test the exact call sequence the bridge
   makes, test a concurrent promote during an export, and reproduce the
   snapshot hazard so its removal is evidenced. No API change, given the
   shaping decision below.
2. **Publish the contract (S2).** `init` writes a root manifest with a
   stable `wiki_id`, the schema identity and version, and a fingerprint of
   any project schema. `info` and a new `api.info` report format versions
   and capabilities. Writers refuse a manifest newer than they support.
3. **Name the page and the actor (S3).** An optional `page_id` key gives a
   page an identity that survives a rename. `--by` records who proposed,
   promoted or approved, as attribution with its source, never as
   authentication.
4. **Record approval as a fact about one revision (S4).** A new `approve`
   verb (and `api.approve`) records a decision for the exact sha256 of a
   page under the current policy. `api.review_state` compares the live
   page and the current policy with the record. Frontmatter never makes a
   page approved.
5. **Mark replacement explicitly (S5).** An optional `superseded_by` key,
   decided in an ADR on both sides, and a `superseded` review state.
6. **Report what needs attention, without a model (S6).** A `findings`
   verb and `api.findings` that cannot take a backend. They return health
   and review-state findings in a versioned JSON shape the host can turn
   into curation debt.

How the four acceptance cases land on this side (memkernel's importer
enforces them on its side; see Counterpart):

| Acceptance case | wiki-studio's part |
|---|---|
| A draft page is never imported | `approve` refuses `status: draft`; auto-approval skips drafts; `review_state` never reports a draft as `approved` (S4) |
| Self-declared approval is refused | `review_state` ignores frontmatter; `propose` and `promote` refuse the reserved approval keys (S4) |
| An approved page edited after approval is re-reviewed | the live sha256 no longer matches the record, so `review_state` is `stale` until `approve` runs again (S4) |
| A superseded wrong memory is not a current answer | the approved page keeps `memkernel_ref`, and `corrects` if adopted; `superseded_by` and the `superseded` state cover page-to-page replacement (S3, S5) |

## Scopes

Build order: S1 and S2 start at once. S3 needs S2's manifest and version
bump. S4 needs S2 (policy in the manifest) and S3's attribution, and uses
S3's `page_id` when present. S5 needs S2. S6 needs S4.

### S1: The combined integration gate, ~5-7h (test-only on this side)

This assumes the recommended closure (remove the snapshot). If week 0
chooses the held-lock alternative, S1 grows by about 3h (Rabbit holes).

- **Bridge-shaped contract tests** in `tests/`, without importing
  memkernel. They replay `studio.py`'s sequence: `create` edits with
  memkernel-shaped pages (`status: draft`, `memkernel_ref`, `memory_type`,
  a `memkernel://` source), one `append-index`, one `append-log`,
  `name="memkernel-export-<ts>-<hex>"`, `source="memkernel wiki_export"`,
  `backend="memkernel"`, and a proposals directory outside the wiki
  (`<root>/.memkernel/wiki-proposals`). Assert:
  - the pages land, and the index and log lines land on current content;
  - `<proposals>/.applied/<name>/receipt.json` is `committed` and carries
    the submission digest; the archived `plan.json` and `preview/` are
    byte-identical to the submission;
  - a second export of the same page is refused as `create` of an existing
    page (exit 9 through the CLI, `PromoteValidationError` through the
    API) with nothing written;
  - a promote interrupted after its commit (receipt left in the proposal
    directory) resolves from the receipt on retry and re-applies nothing;
  - the lock file sits beside the wiki, never inside it, and the wiki
    lints clean afterwards.
- **Combined concurrency test.** A wiki-studio `promote` of another
  proposal (a subprocess through the CLI) runs while a bridge-shaped export
  is in `api.promote`. Both land, neither is reverted, and both archives
  exist.
- **Reproduction of the hazard.** A fixture copies `_WikiSnapshot.take`
  and `restore` from `sync.py:299-363` with the source lines cited, as
  0.5.0 copied memkernel's quoting rules. A failing export wrapped in it,
  with a second writer committing between `take` and `restore`, shows the
  second writer's page rewritten and its archived `plan.json` deleted. The
  same failing export without the wrapper leaves the second writer's work
  intact. This is the evidence for the closure, not a test of memkernel.
- **Clean-install harness.** `tests/integration/`, skipped unless
  memkernel is importable. A CI job, separate from the coverage job,
  builds the wiki-studio wheel, installs it with memkernel at a pinned
  release or git ref into a fresh virtual environment, and runs the real
  `WikiExporter` and `WikiImporter` against it. It starts non-blocking. It
  becomes blocking for the 0.7.0 tag once memkernel's counterpart is
  merged. S4 and S5 add the acceptance cases to it. memkernel is never a
  dependency of the package or of the default dev group.
- **Docs.** `docs/consumers.md`'s memkernel section: the gate path, receipt
  recovery instead of an outer rollback, `api.init` for the scaffold, and
  the lock file in `.gitignore`. CHANGELOG Limitations: the memkernel item
  is replaced only when the compatibility matrix (S2) lists a memkernel
  release without the snapshot. The CHANGELOG never states what
  memkernel's next release does.

### S2: The versioned knowledge contract, ~7-9h

- **Root manifest.** `init` writes `<wiki>/.wiki-studio.json` with
  exclusive creation, never overwriting, through the containment check
  with `O_NOFOLLOW`: a symlink at that path, or a symlinked wiki parent,
  is refused and its target untouched, as Release A requires of every
  write. Every read of the manifest passes the same check. A dot-file
  keeps it out of page listing and lint, and `init_wiki` is already in
  `promoter.py`, so the single-writer rule holds. Keys:
  - `manifest_version: 1`;
  - `wiki_id`: a random UUID, the wiki's identity across clones and moves
    (the receipt's device and inode stay for recovery only);
  - `schema`: `{id: "wiki-studio/page-schema", version: 2}` (version 1 is
    the 0.6.0 schema, version 2 adds S3 and S5's optional keys);
  - `schema_fingerprint` (S2's recipe); `schema_source` is **derived** at
    read time (`project` when any loaded override exists, else
    `packaged`), never persisted, so it cannot go stale;
  - `policy`: S4's section, defaulting to managed (no approval required);
  - `created_by`: package and version.
  `init` on an existing wiki without a manifest adds one and touches
  nothing else.
- **Schema identity.** The packaged rules are identified by
  `schema.version`, which only an ADR bumps; a package upgrade that keeps
  the version changes nothing a wiki must react to. The **fingerprint**
  covers only the project's override files that are actually loaded
  (`ingest-rules.md`, `page-types.md`, `citation-rules.md` under
  `<wiki>/schema/`, finding 9): sha256 over the present ones, sorted by
  name, each as name, a NUL byte, then the raw bytes; with no override the
  value is the SHA-256 of empty input (`e3b0c442…`), never a literal
  empty string, so the key is always a digest. The recipe is documented. The bytes come
  from **one shared loader** that replaces `load_schema_files`
  (`prompt.py:36-46`, which today follows a symlink through `is_file()`
  and `read_text()`): it passes each override through the containment
  check and opens it with `O_NOFOLLOW`, refusing (exit 4) a symlinked
  override or schema directory, and the exact bytes it returns feed both
  the prompt and the fingerprint, so what is hashed is what the model
  was shown. A test plants an override symlink pointing outside the wiki
  and checks it is refused with its target unread. **Drift** is
  judged on that project part only: the manifest stores the fingerprint
  declared at `init`, `info` reports declared and current, and a mismatch
  is refused (exit 4, naming both) by `propose`, `promote` and `approve`
  only on a **governed** wiki (see the definition under S4); a managed
  wiki gets a warning. **Where drift shows:** `info` and `api.info`
  report the declared and the current fingerprint; `propose` and
  `promote` print the warning to stderr and return it in their results'
  `warnings`; `approve` likewise. A host learns about drift on a governed
  wiki before it writes by checking `api.info` first, which is what
  memkernel's governed mode does; the exit-4 refusal is the backstop for
  a host that did not. `init --update-schema` rewrites only
  that key, by writing the whole manifest to a temporary sibling and
  replacing it atomically under the lock, never in place; tests cover
  adding the first override and removing the last one, and `info`
  reporting the derived source correctly after each. A wiki without a manifest has nothing to drift from. This
  rule never blocks a write after an ordinary package upgrade: 0.5.0 and
  0.6.0 both changed packaged schema bytes, and neither would have
  tripped it.
- **`api.info(paths) -> InfoResult`** and new keys in `info --json`:
  package version, `schema` (id, version, source, fingerprint), `formats`
  (`patch_set: 1`, `receipt: 1`, `ingest_log: 1`, `approval: 1`,
  `findings: 1`), `capabilities` (a list of stable strings: `wiki-lock`,
  `receipts`, `base-revision`, `root-manifest`, `page-id`, `attribution`,
  `approval-record`, `superseded-by`, `findings`), and `manifest`
  (present, or missing for a wiki made before 0.7.0). Existing `info`
  keys keep their names and meaning. Both lists describe the **shipped
  build**, not this pitch: a scope the circuit breaker cuts has no
  capability string and no format entry, and a test pins that every
  advertised capability resolves to a verb or key that exists, since hosts
  decide compatibility from this list.
- **Compatibility check.** `propose`, `promote`, `approve` and `init` read
  the manifest. A `manifest_version` or `schema.version` newer than this
  package supports is a contract violation (exit 4) that names both
  versions and the upgrade. A missing manifest means a legacy wiki: every
  0.6.0 verb works as in 0.6.0, and `info` says how to add a manifest.
  The new governed operations need one: `approve`, auto-approval and
  memkernel's governed import require a manifest written by `init`
  (`approve` exits 4 naming `init`), because a record needs `wiki_id` and
  a policy hash. `review_state` reports every page of such a wiki as
  `unapproved` with reason `manifest_missing`.
- **Compatibility matrix.** `docs/compatibility.md`: each tested
  wiki-studio × memkernel pair, what evidence covers it (S1's harness run,
  with the CI run named), and the capabilities each side needs. It also
  states how to re-create a pre-0.6.0 proposal whose `update` edits lack
  revision preconditions (`read --json`, then `propose` again).
- **Tests.** `init` creates the manifest once and never overwrites it.
  The fingerprint changes when one byte of a loaded project override
  changes, is independent of directory listing order, ignores packaged
  files and files the prompts do not load, and a package upgrade alone
  never trips the drift check. `info --json` pins the new keys. A newer
  manifest is refused with exit 4. A wiki without a manifest behaves as in
  0.6.0.

### S3: Identity and attribution, ~5-7h

**S3a, stable page identity (~3-4h, the first part cut after S6).**

- Optional frontmatter key `page_id: pg-<32 hex>`, a single-line scalar.
  That form survives memkernel's parse and render (ADR-0001's finding).
- The CLI (`propose --from`) and `ingest` add a fresh `page_id` to a
  `create` edit whose content has none, so the preview, the commit and any
  approval cover the same bytes. `api.propose` does **not** change a
  caller's bytes by default: it takes `assign_page_ids=False`, so the
  memkernel bridge's creates land byte for byte as today until it opts
  in (listed in memkernel #48's counterpart items). A caller-supplied
  `page_id` is kept if well formed.
- Structural lint: a malformed `page_id`, or two pages with the same one,
  is a violation. This also stops a `create` that copies an existing id.
- Identity rule: a page's key is its `page_id`, or its wiki-relative path
  when it has none. Approval records, `review_state` and findings use that
  key. A byte-identical rename does not exist here: lint requires `slug`
  to equal the file stem and the page type fixes the directory, so any
  rename changes the bytes and the page goes `stale`. What `page_id`
  buys is thinner: after a rename, `review_state` reports `stale` with
  the earlier record and its approved revision, instead of `unapproved`,
  and memkernel can keep one memory identity across the move. That is
  why S3a is the first scope cut after S6.
- No `move` or `delete` action (No-gos). Existing pages get a `page_id`
  through an ordinary guarded `update`. That update moves the page's key
  from the `path/` namespace to `id/`, so `review_state` looks in both:
  `id/<page_id>/` first, then `path/<digest>/` for records written before
  the page had an id, and reports the newest matching record. Adding the
  key therefore never hides an earlier approval; the page simply reads
  `stale` until its new bytes are approved, like any other update.

**S3b, actor attribution (~2-3h, kept).**

- `--by NAME` on `propose`, `promote` and `approve`, and the
  `WIKI_STUDIO_ACTOR` environment variable. The record carries
  `{name, source}` with `source` one of `flag`, `env` or `none`. There is
  no implicit capture of the OS user name, so no personal data lands in
  audit files by default.
- Recorded as optional keys: `plan.json` `proposer`, receipt `actor`
  (receipt version stays 1, with the key documented as a minor-version
  addition, like `base_sha256` in 0.6.0), approval record `approver`
  (S4). `api.propose`, `api.promote` and `api.approve` take `by=`.
- README, `SECURITY.md` and `docs/patch-set-format.md` say it plainly:
  `--by` is attribution, not authentication; the host supplies authority;
  local audit files provide traceability, not tamper-proof evidence.

**ADR.** `docs/adr/0002-page-identity-and-review-keys.md` records
`page_id`, the reserved approval keys (S4) and `superseded_by` (S5) in one
decision record, schema version 2.

### S4: Approval bound to the revision and the policy, ~10-13h

**Policy** (the manifest's `policy` section; the host edits it, a proposal
cannot, see the edit-path rule below). Three keys only:

- `approval_required` (default `false`): the wiki is **governed**. That is
  the one meaning of the word in this pitch: a wiki with a manifest whose
  policy sets `approval_required: true`. A wiki with a manifest and the
  default policy is *managed*: it has an identity, can be approved into,
  and gets drift warnings rather than refusals. A wiki without a manifest
  is *legacy*. memkernel's governed configuration can require governed
  through `info`.
- `approver_required` (default `false`): `approve` refuses without an
  actor name.
- `auto_approve_on_promote` (default `false`): a successful promote also
  approves each page it wrote, except drafts, under the promoter's actor.

`policy_sha256` is the sha256 of the canonical JSON (sorted keys, no
whitespace) of the one key that defines acceptance, `approver_required`,
only (owner decision, 2026-10-26: `approval_required` decides whether
approval is enforced, not what it accepts, so turning a managed wiki
governed keeps its approvals). `auto_approve_on_promote` is a convenience of
how a record comes to exist, not of what it accepts, so toggling it never
makes an approved page `policy-changed`. A wiki without a manifest has no policy and cannot
be approved into: `approve` refuses (exit 4) until `init` writes one.

**`approve`.** `wiki-studio approve <page>... [--revision SHA] [--by NAME]`
and `api.approve(pages, paths, *, by=None, expected=None)`. `--revision`
is accepted only with exactly one page (exit 4 otherwise); the API takes
`expected`, a mapping from wiki path to the sha256 the caller read, so a
batch can state each page's revision. It runs in `promoter.py` under the
wiki lock:

1. Read each live page once, through the containment check, and hash it.
2. Preflight the whole batch; refuse (exit 9, nothing written) when, for
   any page:
   - an expected revision is given and differs from the live hash;
   - the page fails structural lint;
   - `status` is `draft`;
   - the page carries `superseded_by`;
   - the policy requires an approver and none is given.
3. Write one record per page, then release the lock. Validation is
   atomic (step 2 writes nothing); publication is not: an I/O failure
   after some records are published leaves those records in place, since
   each is independent and immutable, and the error (exit 6) names the
   pages published and the pages not. Running `approve` again is
   idempotent: the published tuples are reported, the rest are written.

**Record** (every component of the approval tree is created, enumerated
and read inside the wiki boundary: directories created with no symlink
followed, records opened with `O_NOFOLLOW`, enumeration skipping and
reporting any symlink, and a test that a symlink planted anywhere under
`.audit/approvals/` pointing outside the wiki is refused with its target
untouched).
`<wiki>/.audit/approvals/id/<page_id>/<sha256>/<policy-sha256>/<decision>.json`
for a page with a `page_id`, and
`<wiki>/.audit/approvals/path/<path-digest>/<sha256>/<policy-sha256>/<decision>.json`
for one without, where `<path-digest>` is the SHA-256, lowercase hex, of
the canonical wiki-relative path: the edit path normalised with
`posixpath.normpath` (so `./concepts/x.md` and `concepts/x.md` are one
page), with forward slashes, no leading `./` or `/`, encoded as UTF-8.
The identity of a decision is the tuple (page key, revision, policy,
decision) and every element is in the path, so the same bytes approved
again under a changed policy get their own record instead of colliding
with, or overwriting, the earlier one. The page key maps to a directory
in one of two namespaces, so a path-derived key can never share a
directory with a `page_id`: `.audit/approvals/id/<page_id>/` for a page
with an id, and `.audit/approvals/path/<sha256-of-the-wiki-path>/` for
one without. The digest is injective in practice and keeps every path
character out of the filesystem; the record's `page_key` and `path` keys
hold the readable identity, and every read verifies the stored
`page_key` against the key being looked up before a record counts, so
an enumeration of stale records can never attribute another page's
history to the current page. A collision test covers `concepts/x.md`
beside a root page named `concepts__x.md`, and a `page_id` equal to a
path-derived name; an equivalence test checks that `concepts/x.md` and
`./concepts/x.md` locate the same records. The mapped name passes the containment check against
`.audit/approvals/` before anything is created. The file
is written to a temporary name and published by an exclusive link or
create that never replaces an existing file (never a plain `rename`,
which replaces on POSIX); a record that already exists for the exact
tuple is reported as the no-op, never rewritten. Keys:

- `approval_version: 1`, `wiki_id`;
- `page_key` (the `page_id` or the path), `path`, `sha256`;
- `policy_sha256`, `decision: "approved"`;
- `proposal` (name and submission digest, when the revision came through
  a receipt that wrote these bytes);
- `proposer`, `approver`, `promoter` (each `{name, source}`);
- `timestamp`.

The audit lint validates the tree.

**`review_state`.** `api.review_state(paths, *, pages=None) ->
list[ReviewState]` reads without the lock. It is advisory and
point-in-time, like `promote --dry-run`. Each page gets one state:

- `approved`: a record for the live sha256 under the current
  `policy_sha256`;
- `stale`: a record exists for the page, but not for its live bytes. This
  is the manual-edit and update case;
- `policy-changed`: records for the live bytes exist but none satisfies the
  current policy (records are judged against the current policy, so
  relaxing it reopens nothing; owner decision, 2026-10-26);
- `superseded`: the page carries `superseded_by` (S5);
- `unapproved`: no record. This includes every draft and every page that
  only declares itself stable.

It also returns the approved sha256 and record path, so an importer can
compare the bytes it reads.

**Reserved paths.** `propose` and `promote` refuse (exit 4, naming the
path) any edit whose **normalised** path (`posixpath.normpath`, as
`promoter.py` already applies to edit paths) has a dot-prefixed component
or lies under `schema/`, with a test for the manifest, an approval record
and a schema override, and a test that a raw `./index.md` still passes,
as `docs/patch-set-format.md` documents. Today those paths are refused only incidentally, by the
page-type placement rule; the named rule is what keeps the policy, the
records and the rules out of a proposal's reach.

**Self-declared approval.** `propose` and `promote` refuse frontmatter
keys reserved for the gate's record: `approved`, `approved_by`,
`approval`, `review_state` (exit 4, naming the key). The spec checks the
fixtures and code-copilot-team's wiki for existing uses before the list is
final. `status: stable` is allowed and stays a lifecycle label; it never
makes a page `approved`.

**Auto-approval.** With `auto_approve_on_promote`, approval is a
**separate operation after the promotion has completed** (receipt
`committed`, archive published), not part of the receipt protocol: the
records are not planned in the `committing` receipt, not tracked, and
never affect recovery. `promote` runs it as `approve` would, taking the
lock again, over the content pages the promotion created or updated;
`index.md` and `log.md` appends are never approval targets. Because the
lock was released in between, another writer may have replaced a page by
then, so auto-approval validates **per page**, not as the all-or-nothing
batch `api.approve` runs for a caller: under one lock acquisition it
checks each promoted page's live hash against the receipt's post-commit
hash, approves the pages that still match, and writes **no record and
no promoter attribution** for a page whose bytes no longer match, with a
warning naming it. That page's review state is whatever the records say
(`stale` if an older record exists, `approved` if another operation
already approved the intervening revision, else `unapproved`); the
guarantee is only that this promotion did not approve bytes it did not
promote. One intervening edit never blocks the approval of the other
pages. A failure there is never a failed promote: the promotion stays
committed, the approvals already published in this operation remain,
each failed or mismatched page gets a warning in
`PromoteResult.warnings`, and its review state derives from the records
that exist. A crash between the records is recovered by nothing more
than running `approve` again, which is idempotent per tuple. An interleaving test over a multi-page promotion (a second writer
updating one page between the archive and the auto-approval) pins that
no record is written for the intervening revision under the promoter's
identity, while the unchanged pages are approved.

**Tests**, one per acceptance case on this side:

- a draft is refused by `approve` and skipped by auto-approval;
- a page with `status: stable` and no record is `unapproved`, and a
  proposal carrying `approved_by:` is refused;
- an approved page edited by hand is `stale`, and approving its new bytes
  makes it `approved` again;
- tightening the policy makes approver-less pages `policy-changed`, and
  relaxing it reopens nothing.

S1's clean-install harness gains the four cases end to end once
memkernel's importer reads `review_state`.

### S5: `superseded_by`, ~3-4h

- Optional frontmatter key `superseded_by: <wiki-relative path>` on the
  replaced page. ADR-0002 records it. memkernel records its side in its own
  ADR; this pitch supplies the shared text and does not write memkernel's
  file.
- Why a path and not a `page_id`: it resolves and lints without S3a, and
  S3a can be cut. A broken target after a hand rename is a lint violation.
- Structural lint: the target exists, is a page, is not the page itself,
  and is not superseded in turn (no chains, no cycles).
- `review_state` reports `superseded` whatever the page's records say.
  `approve` refuses a superseded page.
- **Review state stays separate from memory tier.** ADR-0002 says
  wiki-studio's states (`approved`, `stale`, `policy-changed`,
  `superseded`, `unapproved`) describe the wiki revision. Mapping them to
  memkernel's tiers, withdrawal and `Memory.superseded_by` is memkernel's
  decision.
- **Page-to-memory corrections** (decided in week 0 with memkernel). The
  decision (owner, 2026-10-24): memkernel owns a `corrects:` key listing
  the `memkernel_ref` values a page corrects, and ADR-0002 registers it as
  a memkernel-interpreted key. Its value syntax is **not final** until
  memkernel defines a restricted reference-token grammar that excludes
  commas and ambiguous quoting; the comma-separated single line is only
  the starting proposal. The round trip is pinned by a fixture parsed by
  both sides (wiki-studio's `yaml_lite`, memkernel's page parser) with
  several corrections on one page. wiki-studio checks only the agreed
  format and preserves the key; a multi-source page then withdraws only
  what it names.

### S6: Findings without a model call, ~3-4h (the first scope cut)

- `api.findings(paths, *, pages=None) -> FindingsResult` and
  `wiki-studio findings [--json] [--paths ...]`. Neither takes a backend,
  so no code path can reach a model.
- `findings_version: 1`. Each finding has `kind`, `severity`, `pages` and
  `description`, the shape memkernel's `HealthItem` already mirrors
  (`studio.py:32-38`). Kinds:
  - the deterministic health kinds: `stale-claim`, `weak-orphan`,
    `missing-cross-link`, `avoid-format`;
  - the review kinds: `unapproved`, `approval-stale`,
    `approval-policy-changed`, `superseded-still-indexed` (an `index.md`
    entry links a superseded page as current), and `no-page-id` (only with
    S3a).
- Counts by kind come first in the JSON, so a host can report curation
  debt at session start without parsing descriptions.
- Exit 0 always: findings are information. `lint --health --strict` stays
  the CI gate.
- If S6 is cut, the host still has `lint --health` without a backend and
  `review_state`, which carry the same facts in two calls.

## Counterpart: memkernel's Release B (memkernel #48; not this pitch's scopes)

Listed so the exit evidence is traceable. None of it is built from this
repository.

- Remove the outer snapshot and restore (the week-0 decision), or hold the
  lock if the alternative is chosen; use `api.init` for the scaffold.
- A governed configuration that requires the gate, refuses the unchecked
  fallback writer, and checks `info` capabilities and the manifest's
  `approval_required`; an identified ungated mode.
- Idempotent import by page identity and revision hash, of `approved`
  revisions only, through `api.review_state`; refuse drafts, self-declared
  approval and a hash that is not the approved one.
- Withdrawal on supersession, deprecation and explicit deletion; a
  pending / applied / failed sync state with a retry path; no claimed
  transaction across Markdown and the memory store.
- Raw-memory reconciliation through the explicit page-to-memory mapping
  (S5), provenance retained.
- Curation debt at session start (from S6), bounded candidate batches,
  source content hashes with git revision metadata.
- The gate checklist items in #48 that only the bridge can tick: consume
  receipts, ignore the lock file, honour `hash_recipe`.
- Opt into `page_id` assignment on its creates (`api.propose(...,
  assign_page_ids=True)`) when it is ready to carry the key; until then
  its bytes land unchanged.

## Exit evidence

Release B closes when one complete correction loop passes on clean
installs of compatible versions (a row in `docs/compatibility.md`) and
survives retries. The loop is retain, export, review, import, correct,
next-session recall. It runs in S1's clean-install harness, with these
cases named:

1. A draft page is never imported.
2. A page that declares itself approved without the gate's record is
   refused.
3. An approved page edited after approval is re-reviewed before its new
   revision is imported.
4. A wrong raw memory that a corrected page supersedes is not returned as
   a current answer next session, and its provenance is retained.

"Survives retries" means: a promote interrupted after its commit resolves
from the receipt, and an export or import run twice creates no duplicate
pages, records or memories. wiki-studio 0.7.0 can ship before the loop
passes (circuit breaker, step 4). Release B is not declared closed, and no
combined safety claim is made, until it does.

## Decisions taken in shaping

The owner could not be asked during shaping. Items marked *assumption*
are open in Questions for the owner.

- **The snapshot closure: remove it** (recommendation; decided with
  memkernel in week 0, see Rabbit holes). wiki-studio's API is unchanged
  and S1 is test-only.
- **Approval is a separate act from promotion.** Promotion lands a valid
  revision; `approve` accepts it. One policy flag allows acceptance on
  promote for non-draft pages. This follows the proposal's "separate
  creating a valid draft from accepting it as current project knowledge".
- **The approval record is one file per decision under
  `.audit/approvals/`,** written by `promoter.py` under the lock. There is
  no ledger file to append to and no new recovery protocol.
- **The policy lives in the root manifest.** Its hash is bound into every
  record, so a policy change is visible as `policy-changed`.
- **`wiki_id` in the manifest is the wiki's identity in records.** Device
  and inode change on clone, so they stay a recovery check in receipts.
- **`page_id` is optional and assigned at `create` time by `propose` and
  `ingest`.** Existing pages fall back to their path. No move action.
- **`superseded_by` holds a wiki path,** so it works without `page_id`.
- **Attribution records its source** (`flag`, `env`, `none`) and never
  captures the OS user implicitly.
- **One ADR (0002) for all new keys,** schema version 2, because the
  identity, approval and supersession keys are one contract decision.
- **memkernel never becomes a wiki-studio dependency.** The real-package
  test runs in a separate CI environment.
- **Owner decision (2026-10-24): one 6w bet, released as 0.7.0.** S2, S3
  and S4 publish one connected contract, and the week-2 checkpoint gives
  the scope control a split would.
- **Owner decision (2026-10-24): memkernel's counterpart runs in the same
  cycle.** Snapshot removal lands by the end of week 2, approved-only
  import by week 5. If it slips, 0.7.0 ships with the limitation intact
  and Release B stays open.
- **Owner decision (2026-10-24), to record with memkernel in week 0:**
  remove the whole-wiki snapshot and use `api.init` for scaffolding; adopt
  a memkernel-owned `corrects` field registered by ADR-0002, whose value
  syntax is not final until memkernel defines a restricted
  reference-token grammar that excludes commas and ambiguous quoting, with
  a cross-parser round-trip fixture carrying several corrections.

## Rabbit holes

- **The snapshot closure (decide in shaping, not in a build phase).** The
  bridge's whole-wiki snapshot and restore run outside the wiki lock
  (finding 2). A failed export can therefore rewrite another writer's
  committed pages. There are two closures.
  - *Preferred: remove the snapshot.* wiki-studio stays the only owner of
    wiki writes and rollback. 0.6.0 has a scoped commit, exception
    rollback, receipts and a per-proposal archive. The snapshot's stated
    reason was pre-0.4.1 promote (`sync.py:300-311`), which no longer
    exists. The scaffold left after a failed export is `index.md` and
    `log.md`, which `api.init` creates safely and which every later export
    needs anyway. wiki-studio's API is unchanged, and S1 is test-only here.
  - *Only if the bridge must undo several promotes as one unit:* add a
    keyword `lock: WikiLock | None = None` to `api.propose` and
    `api.promote`. The lock must be held and must belong to the same
    resolved wiki, checked as `append_ingest_log` already does
    (`audit.py:415-417`). A test shows that a held lock for a different
    wiki is refused. `WikiLock` takes `flock` on a fresh open file
    description and must not be made reentrant. About +3h on S1.
  - *What would overturn the recommendation:* memkernel showing that one
    export must span several `propose`/`promote` calls that succeed or fail
    together. `studio.py` makes one call pair per export today
    (`studio.py:189-190`). Or a bridge-side write, other than the
    scaffold, that must be undone with the promote and cannot move into
    the patch-set.
  - The choice is made with memkernel before any build phase starts and is
    recorded in the bet log and in memkernel #48.
- **A policy language.** Per-path, per-page-type or per-actor rules, quorum
  approval and approval expiry all look small. *Workaround:* three boolean
  keys. Anything finer is the host's job, through `api.approve` and its
  own permissions.
- **A durable approval ledger.** An append-only log invites compaction,
  replay and a recovery protocol of its own. *Workaround:* one immutable
  file per decision, published by an exclusive link or create that never
  replaces a file, under the lock. Its absence means "not approved", which is the safe reading.
  No signatures and no hash chain (No-gos).
- **Rename identity.** A `move` action, redirect stubs, history chains and
  automatic `page_id` backfill of a whole wiki can each eat days.
  *Workaround:* an optional key, assigned at create, unique by lint.
  Approval binds bytes, not paths. This is the trim-able part of S3.
- **The cross-project harness.** Installing memkernel in wiki-studio's CI
  brings pydantic and memkernel's own dependencies, and memkernel's API can
  move. *Workaround:* a separate job in a fresh virtual environment, a
  pinned memkernel ref, skipped locally when memkernel is absent. The
  bridge-shaped tests are the always-on evidence. Do not mock memkernel's
  `MemoryService` inside wiki-studio's test suite.
- **Fingerprint canonicalisation.** Line endings, encodings and file order
  invite a normaliser. *Workaround:* hash raw bytes in sorted name order. A
  line-ending change is a schema change for this purpose, and the
  documentation says so.

## No-gos

- No hosted collaboration, no new runtime, no required vector store, no
  mandatory semantic judges, no prose auto-rewrite (roadmap, by decision).
- No crash-safe multi-file transaction. Approval records and auto-approval
  follow 0.6.0's guarantee: validated, serialised and rolled back on
  failure, not crash-safe across files.
- No changes to memkernel from this repository. Its code, ADRs and CI are
  its own. This pitch supplies text and tests only.
- No authentication, signatures or tamper-proof audit. `--by` is
  attribution.
- No `move` or `delete` patch-set action.
- No new exit code. 0 and 2..11 keep their meaning, and 1 stays fatal lint.
- No runtime dependency, and memkernel is not in the default dev group.
- No model call in `findings`, `approve` or `review_state`.
- No reentrant `WikiLock`.
- No schema key without ADR-0002 and a CHANGELOG entry.
- Not in this pitch: the two tested quickstarts of the roadmap's Docs item.
  They document the loop and are written once it passes, under a
  follow-up issue.

## Circuit breaker

Core is S1, S2 and S4. The exit evidence depends on all three, and they
are never cut. The triggers and actions, in order:

1. **End of week 2.** If S1 and S2 are not downhill, cut S6 now. Record it
   as a follow-up issue. Hosts use `lint --health` without a backend and
   `review_state` meanwhile.
2. **End of week 4.** If S4 is not downhill, also cut S3a (`page_id` and
   rename identity). Approvals and findings key by wiki path. ADR-0002
   drops the `page_id` section. S3b attribution stays, because S4's record
   needs the approver. 0.7.0 may still ship, but the roadmap requires
   stable page identity for Release B, so Release B stays open until S3a
   lands in a later release, exactly as it does for a memkernel slip.
3. **End of week 5.** If S5's lint rules are not done, ship S5 as its ADR
   text, the key and the `superseded` review state, without the chain and
   cycle checks.
4. **End of week 5, memkernel side.** If memkernel's snapshot removal and
   approved-only import are not merged, ship 0.7.0 with this side's
   scopes. The CHANGELOG keeps the memkernel limitation. Release B is not
   declared closed. The joint loop runs when memkernel ships, as a
   follow-up, not as a reason to extend this bet.
5. **Never, to save time:** cut S1, S2 or S4; derive approval from
   frontmatter; weaken or skip a gate or concurrency test; add a runtime
   dependency, a model call or an exit code; make `WikiLock` reentrant;
   write memkernel code from here; ship a schema key without its ADR.

"Exhausted" means six working weeks have passed. A third review round on
one scope is not exhaustion (0.6.0 needed five on one PR); it is an
escalation to the owner, who decides between a fix session, a cut from
the list above, or a hold.

## Owner decisions (2026-10-24, confirmed 2026-10-25)

Proposed by the first pitch review on 2026-10-24 and recorded then; on
2026-10-25 the owner was asked directly whether to adopt them as their own
decisions and adopted all three. The pitch above follows them.

1. **Appetite:** one 6w bet, released as 0.7.0. The A/B split stays
   possible at the scope boundary but is not taken.
2. **memkernel's schedule:** same cycle. Snapshot removal by the end of
   week 2, approved-only import by week 5; on a slip, 0.7.0 ships with the
   limitation intact and Release B stays open.
3. **Week-0 decisions, to record in memkernel #48:** remove the whole-wiki
   snapshot and scaffold through `api.init`; adopt a memkernel-owned
   `corrects` field registered by ADR-0002, syntax finalised only once
   memkernel defines the restricted token grammar, with a cross-parser
   round-trip fixture.

## Bet log

| Date | bet_status | Note |
|------|------------|------|
| 2026-10-24 | shaping | Pitch drafted from wiki-studio #38 and memkernel #48. wiki-studio read at main 4979178, memkernel at 9d93544. |
| 2026-10-24 | shaping → shaped | 6 scopes, 6w appetite, one bet (assumption), 0.7.0. Core S1, S2, S4; trim S6, then S3a. Snapshot closure recommended: remove; to be settled with memkernel before build. 3 owner questions with stated assumptions. |
| 2026-10-24 | shaped (revised) | Pitch review, six findings folded in: approval records keyed by (page, revision, policy, decision) and never replaced; `approve`, auto-approval and governed import require a manifest, `review_state` reports `manifest_missing`; the fingerprint covers the effective merged schema, with declared-versus-current drift refused by governed writers until `init --update-schema`; auto-approval is a separate post-promotion operation outside the receipt, content pages only; batch approval takes a per-path `expected` mapping, preflights the batch and documents partial publication; `info` lists only shipped capabilities. Owner decisions recorded: one 6w bet; memkernel in the same cycle; week 0 = remove the snapshot, memkernel-owned `corrects` with a grammar still to define. |
| 2026-10-24 | shaped (revised, 2) | Second pitch review on PR #44: schema identity is `schema.version`, the fingerprint covers only the loaded project overrides and drift is refused only on a governed wiki (a package upgrade never blocks writes); one definition of governed / managed / legacy; `policy_sha256` over the acceptance keys only; `decision` in the record path, page-key mapping and containment stated, no `rename` publication; an explicit reserved-path refusal for dot components and `schema/`; `page_id` opt-in on `api.propose`; the rename claim restated as what `page_id` actually buys; a third review round is an escalation, not exhaustion. |
| 2026-10-25 | shaped (revised, 3) | Third review on PR #44: auto-approval passes the receipt's post-commit hashes as `expected`, so an intervening writer's revision is never approved under the promoter's identity (interleaving test); the manifest and every approval-tree component are created, enumerated and read inside the wiki boundary with no symlink followed, the manifest is replaced atomically and `schema_source` is derived, not persisted; cutting S3a keeps Release B open like a memkernel slip. The three owner decisions, first proposed by the review, were put to the owner directly and adopted. |
| 2026-10-25 | shaped (revised, 4) | Fourth review on PR #44: one contained, no-follow schema loader feeds both the prompt and the fingerprint (an outside-pointing override symlink is refused unread); approval records live in separate `id/` and `path/<sha256>` namespaces with the stored `page_key` verified on every read; auto-approval validates per page under one lock, approving unchanged pages and warning on changed ones. |
| 2026-10-25 | shaped (revised, 5) | Fifth and sixth reviews on PR #44: both approval-record layouts documented with a canonical path-digest recipe (normalised POSIX path, UTF-8, SHA-256) and an equivalence test; auto-approval's guarantee restated as "no record and no attribution for mismatched bytes", not a review state; a per-page failure leaves the promotion committed and published approvals in place, with review state from the records. |
| 2026-10-25 | shaped (revised, 6) | Seventh review on PR #44: managed replaces ungoverned in the drift rule and the policy default; the drift warning's surfaces are named (info, stderr, result warnings) with api.info as the host's pre-write check; the reserved-path rule applies to the normalised path and `./index.md` stays legal; the empty-override fingerprint is the digest of empty input; `review_state` looks in both namespaces after a page gains a `page_id`; bet log in date order. |
| 2026-10-25 | bet | Bet for cycle 02. |
| 2026-10-25 | building | Cycle 02 started; hill chart initialized. |
| 2026-10-26 | building | Spec review on PR #46, owner decisions: `policy_sha256` covers `approver_required` only, so turning a wiki governed keeps its approvals; the unattended run's caps are raised to 12h and $150 with no milestone pause. |
| 2026-10-26 | building | Owner decision on the spec review: `review_state` judges a record against the current policy, so relaxing `approver_required` reopens nothing and tightening it reopens only records without a named approver; record paths keep the policy hash. |
| 2026-10-26 | building | Owner decisions on the PR #46 review: a path-keyed approval is a fact about a path and exact bytes, so identical-byte recreation keeps it and recreation safety comes from a fresh `page_id`; an acknowledged schema change does not reopen approvals; the week checkpoints are manual cycle gates applied at the build-PR review. |
