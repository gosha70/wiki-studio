# The knowledge contract

A wiki says which contract it follows in a root manifest. A host reads that
contract with `api.info` (or `wiki-studio info --json`) before it writes.
This page is the reference for the manifest, the schema fingerprint, drift,
the `info` keys, the approval policy, approval records and review states. It
describes 0.7.0.

## Vocabulary

| Word | Meaning |
|---|---|
| **governed** wiki | It has a manifest whose policy sets `approval_required: true`. |
| **managed** wiki | It has a manifest with the default policy. |
| **legacy** wiki | It has no manifest. It works as in 0.6.0. |

A legacy wiki gets three integrity refusals that apply to every wiki: a
symlinked project schema override, a reserved edit path and a self-declared
approval key. All three are described below.

## The root manifest

`wiki-studio init` (or `api.init`) writes `<wiki>/.wiki-studio.json`. Only
`promoter.py` writes it. The write is an exclusive, no-follow creation after
the containment check. It never overwrites a file. Running `init` on a wiki
made before 0.7.0 adds the manifest and changes nothing else. Running it on a
wiki with a manifest changes nothing. `InitResult.manifest` is `created`,
`existing` or `updated`.

| Key | Value |
|---|---|
| `manifest_version` | `1`. |
| `wiki_id` | A random UUID. It names the wiki across clones and moves. |
| `schema` | `{"id": "wiki-studio/page-schema", "version": 2}`. Version 1 is the 0.6.0 page schema; version 2 adds the optional keys of `docs/adr/0002-page-identity-and-review-keys.md` and accepts version 1 manifests. Only a decision record in `docs/adr/` bumps it. |
| `schema_fingerprint` | The fingerprint acknowledged at `init` (see below). |
| `policy` | `approval_required`, `approver_required`, `auto_approve_on_promote`. Each is `false` by default. The host edits them by hand. |
| `created_by` | `{"package": "wiki-studio", "version": "<version>"}`. |

`schema_source` is never stored. It is derived on every read.

Every read of the manifest passes the containment check and opens the file
with `O_NOFOLLOW`. These cases are a contract violation (exit 4):

- a symlink at the manifest path, or a symlinked wiki directory when `init`
  writes; the symlink's target is never touched;
- a manifest that is not JSON, lacks a key or has a key of the wrong type; the
  message names the key, such as `policy.approval_required`;
- a `manifest_version` or `schema.version` newer than this package supports;
  the message names both versions and says to upgrade wiki-studio;
- a `schema.id` other than `wiki-studio/page-schema`, whatever its version.

`init`, `propose`, `promote` (dry run included), `approve` and `info` apply these checks.

## The schema documents and the fingerprint

The prompts load three schema documents: `ingest-rules.md`, `page-types.md`
and `citation-rules.md`. A project copy of one under `<wiki>/schema/`
overrides the packaged copy. One loader reads them for the prompts and for the
fingerprint, so the bytes hashed are the bytes the model was shown. The loader
checks containment and opens each file with `O_NOFOLLOW`. A symlinked override
or schema directory is refused (exit 4), and its target is never read.
`prompt.load_schema_files` keeps its name, signature and return value.

`schema_source` is `project` when any of the three overrides exists. It is
`packaged` otherwise.

The fingerprint recipe:

1. Take the overrides that are present, sorted by file name:
   `citation-rules.md`, `ingest-rules.md`, `page-types.md`.
2. For each, feed the UTF-8 file name, one NUL byte, then the raw file bytes
   into one SHA-256.
3. Write the digest as lowercase hex.

With no override the fingerprint is the SHA-256 of empty input,
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. It is
never an empty string. Packaged files never enter it. Other files under
`<wiki>/schema/`, such as `lint-rules.md`, never enter it either.

The bytes are hashed without normalisation. A line-ending change is therefore
a schema change. A checkout that converts line endings shows drift. On a
managed wiki that is only a warning.

## Drift

Drift is a difference between the manifest's `schema_fingerprint` and the
current fingerprint. A package upgrade alone never causes drift, because
packaged documents are not hashed.

| Surface | Governed wiki | Managed wiki |
|---|---|---|
| `propose` (CLI) | exit 4 | warning on stderr; the proposal is written |
| `api.propose` | `ContractViolationError` (exit 4) | `DriftWarning` through `warnings.warn`; returns the proposal path |
| `promote` (CLI, dry run included) | exit 4 | warning on stderr |
| `api.promote` | `ContractViolationError` (exit 4) | the message in `PromoteResult.warnings` |
| `info` / `api.info` | `drift: true` and the message | `drift: true` and the message |

The message names the declared and the current fingerprint and the remedy
`wiki-studio init --update-schema`. `DriftWarning` is a `UserWarning`
subclass in `wiki_studio.errors`. A caller can turn it into an error with the
standard warnings filter. A legacy wiki has nothing to drift from.

`init --update-schema` (`api.init(paths, update_schema=True)`) acknowledges
the change. It rewrites only `schema_fingerprint`. It writes the whole
manifest to an exclusive, no-follow temporary sibling, fsyncs it and replaces
the manifest atomically under the wiki lock. It never edits the file in place.

## `info` keys

`info --json` prints every 0.6.0 key with its 0.6.0 name and meaning. The
string key `schema` is still `project` when `<wiki>/schema/` exists and
`packaged` otherwise. These keys follow:

| Key | Content |
|---|---|
| `package_version` | The installed wiki-studio version. |
| `schema_contract` | `id`, `version` (the manifest's, else this package's), `source`, `fingerprint` (current), `declared_fingerprint` (the manifest's, or `null`), `drift`. |
| `formats` | `patch_set: 1`, `receipt: 1`, `ingest_log: 1`, `approval: 1`. |
| `capabilities` | `wiki-lock`, `receipts`, `base-revision`, `root-manifest`, `page-id`, `attribution`, `approval-record`. |
| `manifest` | Present: `state`, `manifest_version`, `wiki_id`, `policy`, `mode` (`governed` or `managed`). Missing: `state`, `mode: legacy` and an `instruction` to run `wiki-studio init`. |

Both lists describe the shipped build. A scope that does not ship adds no
capability and no format. A test checks that every advertised capability
resolves to a verb, an API function or a key. `api.info(paths)` returns the
same facts as an `InfoResult`. Its `warnings` carry the drift message. It
reads only and takes no lock.

## The policy and its hash

The manifest's `policy` has exactly three booleans. The host edits them by
hand; a proposal cannot, because the manifest is a reserved path.

| Key | Meaning |
|---|---|
| `approval_required` | The wiki is governed: drift is refused (exit 4) instead of warned about. |
| `approver_required` | `approve` refuses (exit 9) when no approver is named (`--by`, `by=` or `WIKI_STUDIO_ACTOR`). |
| `auto_approve_on_promote` | A successful promote also approves each content page it wrote, except drafts, under the promoter's actor. |

`policy_sha256` is the lowercase hex SHA-256 of the canonical JSON of
`{"approver_required": <bool>}`: sorted keys, separators `,` and `:`, no
whitespace, UTF-8. With the default policy that is the SHA-256 of
`{"approver_required":false}`. Only `approver_required` enters it, because it
is the only key that changes what an approval accepts. Turning a managed wiki
governed, or toggling `auto_approve_on_promote`, therefore keeps every
existing approval `approved`.

Approvals attest page bytes under the approver rule, not the project's schema
overrides. A record does not store the schema fingerprint, and an
acknowledged schema change (`init --update-schema`) leaves every approval as
it was. `approved` means this revision was accepted under the approver rule;
it does not mean the page is valid against the latest schema. The change
stays visible in `info`, and structural lint re-checks every page at
`promote` and `approve`.

## Approval records

A decision is one immutable JSON file. Its path carries the whole decision
tuple (page key, revision, policy, decision):

```
<wiki>/.audit/approvals/id/<page_id>/<sha256>/<policy_sha256>/approved.json
<wiki>/.audit/approvals/path/<path-digest>/<sha256>/<policy_sha256>/approved.json
```

A page with a well-formed `page_id` is filed under `id/`; any other page under
`path/`. `<sha256>` is the hash of the page's exact bytes. The same bytes
approved under a changed policy get their own record and never collide with
the earlier one. The two namespaces keep a path-derived key from ever sharing
a directory with a `page_id`.

The path-digest recipe:

1. Normalise the wiki-relative path with `posixpath.normpath`, with forward
   slashes and no leading `./` or `/`. `./concepts/x.md` and `concepts/x.md`
   are one page.
2. Encode it as UTF-8.
3. Take the SHA-256 and write it as lowercase hex.

A record has these keys:

| Key | Value |
|---|---|
| `approval_version` | `1`. |
| `wiki_id` | The manifest's `wiki_id`. |
| `page_key` | The `page_id` (under `id/`) or the canonical path (under `path/`). |
| `path` | The page's canonical path when it was approved. |
| `sha256`, `policy_sha256`, `decision` | The tuple, equal to the directory and file names; `decision` is `approved`. |
| `proposal` | `{name, submission_digest}` of the receipt that wrote these bytes, or `null`. |
| `proposer`, `approver`, `promoter` | Each `{name, source}` or `null`. |
| `timestamp` | UTC, ISO 8601 with microseconds. |

For auto-approval, `proposal` is the promoting receipt. For an explicit
`approve`, it is the newest committed receipt under the caller's own
`<proposals_dir>/.applied/` whose tracked write gave this path the live
sha256, best effort: receipts another writer archived elsewhere (such as the
bridge's `.memkernel/wiki-proposals`) are not searched. `promoter` is then
that receipt's actor and `proposer` its plan's.

Every read verifies a record before it counts: a regular file inside the wiki
boundary, opened with `O_NOFOLLOW`, that parses, has `approval_version` 1, the
manifest's `wiki_id`, a `page_key` equal to the key being looked up, and
`sha256`, `policy_sha256` and `decision` equal to its location. A record that
fails is skipped and reported in the result's warnings, so an enumeration
never attributes another page's history to the current page. A symlink
anywhere in the tree is skipped and reported by `review_state` and refused
(exit 4) by `approve`.

Only `promoter.py` writes records, under the wiki lock. Each name passes the
containment check before anything is created. Directories are created and
opened without following a symlink. A record is written to a temporary name
in its directory, fsynced, and published by an exclusive `os.link` (or, on a
filesystem without hard links, an exclusive create of the final name). Neither
ever replaces a file, so an existing record is never rewritten. A record torn
by a crash fails verification and reads as absent; the audit lint reports it
and any stray temporary file for removal by hand.

## `approve`

`wiki-studio approve <page>... [--revision SHA] [--by NAME]` and
`api.approve(pages, paths, *, by=None, expected=None) -> ApproveResult`.
`--revision` is the sha256 the curator reviewed (`read --json`) and is
accepted with exactly one page (exit 4 otherwise); `expected` maps page paths
to reviewed hashes.

Under the wiki lock, `approve`:

1. reads each page once through the wiki boundary (exit 7 outside it or
   through a symlink, exit 5 when missing);
2. checks the whole batch and refuses it (exit 9, nothing written), naming
   each page and reason, when an expected revision differs from the live
   hash, the structural linter reports a violation for the page, the page is
   not one the linter lists, its `status` is `draft`, it carries
   `superseded_by`, or the policy requires an approver and none is named;
3. for each page, reports in `existing` a verified record for the live bytes
   that already satisfies the current policy (under any policy hash), and
   otherwise writes one record under the current `policy_sha256`.

A legacy wiki is refused (exit 4) naming `init`, because a record needs the
`wiki_id` and a policy. A newer or malformed manifest and drift on a governed
wiki are exit 4; drift on a managed wiki is in `ApproveResult.warnings` and on
stderr.

Validation is atomic; publication is not. An I/O failure after some records
are published leaves them in place, since each is independent and immutable,
and the error (exit 6) names the pages published and the pages not. Running
`approve` again is idempotent: the published records are reported as
existing and the rest are written.

## Review states

`api.review_state(paths, *, pages=None) -> list[ReviewState]` reads without
the lock; the result is advisory and point-in-time. `pages=None` covers every
page the structural linter lists except the root `index.md` and `log.md`.
Each `ReviewState` has `path`, `page_key`, `state`, `reason`, `live_sha256`,
`approved_sha256`, `record_path` and `warnings`. The first rule that applies
decides:

| State | Reason | When |
|---|---|---|
| `unapproved` | `manifest_missing` | The wiki has no manifest. |
| `superseded` | `superseded_by` | The page carries `superseded_by`, whatever its records say. |
| `unapproved` | `draft` | The live `status` is `draft`. |
| `approved` | `record_matches_live` | A verified record for the live bytes satisfies the current policy. |
| `policy-changed` | `no_record_satisfies_policy` | Records for the live bytes exist, but none satisfies the policy. |
| `stale` | `live_bytes_differ` | A verified record exists for the page, but not for its live bytes. |
| `unapproved` | `no_record` | No verified record. |

A record satisfies the policy when `approver_required` is false, or when it is
true and the record's `approver` has a name. Relaxing the policy therefore
never reopens approvals made under the stricter rule; tightening it turns
approvals without a named approver `policy-changed`. Records are looked up
under `id/<page_id>/` first, when the page has one, then under
`path/<digest>/` (records written before the page had an id). The newest
matching record by `timestamp` is reported. Frontmatter never makes a page
approved: `status: stable` alone is `unapproved`.

A path-keyed approval is a fact about this path and these exact bytes, not
about a page's history. wiki-studio has no delete action and cannot observe a
deletion. A page created later at the path of a deleted page reads at most
`stale` when its bytes differ, and `approved` when they are byte-identical,
because the two cannot be told apart. A create through `propose --from` or
`ingest` receives a fresh `page_id`, so it is looked up under its new id, its
bytes differ, and it reads `unapproved`.

## Auto-approval

With `auto_approve_on_promote`, approval is a separate operation after the
promotion has completed (receipt `committed`, archive published), outside the
receipt protocol: its records are not planned, not tracked and never affect
recovery. `promote` takes the wiki lock again and, under one acquisition,
checks each content page the promotion created or updated (never the
`index.md` and `log.md` appends) against the receipt's post-commit sha256:

- a page that still matches and passes `approve`'s per-page conditions gets a
  record with `approver` and `promoter` the promoter's actor, `proposer` from
  `plan.json` and `proposal` from the receipt;
- a page whose bytes no longer match gets no record and no promoter
  attribution, and a warning naming it; it never blocks the other pages.

A failure there never fails the promotion: it stays committed, records already
published remain, and each skipped, failed or changed page gets a warning in
`PromoteResult.warnings`. `PromoteResult.approved_paths` lists the pages that
carry a record for their committed bytes. A crash between records is
recovered by running `approve` again.

## Reserved edits

On every wiki, legacy included, `propose` and `promote` (before staging,
after the escape checks, which keep their exit codes) refuse with exit 4:

- an edit whose normalised path has a dot-prefixed component or lies under
  `schema/`: the manifest, the audit trail and its approval records, and the
  schema overrides are the gate's own state. A raw `./index.md` normalises to
  `index.md` and passes;
- a `create` or `update` whose frontmatter carries `approved`,
  `approved_by`, `approval` or `review_state` (ADR-0002). `status: stable`
  stays allowed as a lifecycle label and never makes a page approved.
