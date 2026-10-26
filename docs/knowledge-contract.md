# The knowledge contract

A wiki says which contract it follows in a root manifest. A host reads that
contract with `api.info` (or `wiki-studio info --json`) before it writes.
This page is the reference for the manifest, the schema fingerprint, drift and
the `info` keys. It describes 0.7.0.

## Vocabulary

| Word | Meaning |
|---|---|
| **governed** wiki | It has a manifest whose policy sets `approval_required: true`. |
| **managed** wiki | It has a manifest with the default policy. |
| **legacy** wiki | It has no manifest. It works as in 0.6.0. |

A legacy wiki gets three integrity refusals that apply to every wiki. One is a
symlinked project schema override, described below. The other two arrive with
the approval scope: reserved edit paths and self-declared approval keys.

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
| `schema` | `{"id": "wiki-studio/page-schema", "version": 1}`. Version 1 is the 0.6.0 page schema. Only a decision record in `docs/adr/` bumps it. |
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

`init`, `propose`, `promote` (dry run included) and `info` apply these checks.

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
| `formats` | `patch_set: 1`, `receipt: 1`, `ingest_log: 1`. |
| `capabilities` | `wiki-lock`, `receipts`, `base-revision`, `root-manifest`. |
| `manifest` | Present: `state`, `manifest_version`, `wiki_id`, `policy`, `mode` (`governed` or `managed`). Missing: `state`, `mode: legacy` and an `instruction` to run `wiki-studio init`. |

Both lists describe the shipped build. A scope that does not ship adds no
capability and no format. A test checks that every advertised capability
resolves to a verb, an API function or a key. `api.info(paths)` returns the
same facts as an `InfoResult`. Its `warnings` carry the drift message. It
reads only and takes no lock.
