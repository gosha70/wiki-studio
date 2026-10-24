# Patch-set directory format

A patch-set is the unit `wiki-studio promote` applies to the wiki in one
promotion: validated, serialised against other wiki-studio writers on the
same machine, rolled back on failure, and not crash-safe across files.
`wiki-studio ingest` writes one from a backend's answer; a library caller
writes one with `wiki_studio.api.propose`. Both produce the same directory,
and `promote` does not care which produced it. The format is public and
versioned with the package (see "Stability" in `wiki_studio.api`).

## Layout

```
<proposals-dir>/<name>/
├── plan.json                 # the patch-set: provenance + one entry per edit
├── preview/
│   └── <edit.path>           # the full content of each edit, at its wiki-relative path
├── .ingest-snapshot/         # optional: immutable copy of plan.json + preview/ taken at write time
│   ├── plan.json
│   └── preview/…
└── receipt.json              # written by promote only (see "Receipts"); never by ingest or propose
```

A proposal directory is never reused: `ingest` and `query --file-back`
create `<name>-2`, `-3`, … when their generated name exists, and `propose`
refuses a caller-selected name that exists (`OutputWriteError`). The
directory is created exclusively under the wiki lock.

`<proposals-dir>` is `WikiPaths.proposals_dir` (`doc_internal/proposals` by
default; `--proposals-dir` / `WIKI_STUDIO_PROPOSALS_DIR` override it). `ingest`
names the directory `<YYYY-MM-DD>-<source stem>`; `propose` uses the `name`
the caller passes: one path component of ASCII letters, digits, `.`, `_` and
`-`, not starting with `.` (hidden names such as `.applied` are reserved for
the archive). This is stricter than the names `ingest` derives from a source
file; `promote` accepts both.

## `plan.json`

```json
{
  "version": 1,
  "source_path": "notes/2026-10-12-outage.md",
  "backend": "claude",
  "rationale": "One incident, one new concept, index and log entries.",
  "edits": [
    {
      "path": "concepts/retry-budget.md",
      "action": "create",
      "rationale": "New durable concept introduced by the source.",
      "preview": "preview/concepts/retry-budget.md"
    },
    {
      "path": "index.md",
      "action": "append-index",
      "rationale": "Link the new page from the index.",
      "preview": "preview/index.md"
    },
    {
      "path": "log.md",
      "action": "append-log",
      "rationale": "Log the change.",
      "preview": "preview/log.md"
    }
  ]
}
```

| Key | Meaning |
|-----|---------|
| `version` | Format version; `1`. |
| `source_path` | What was ingested, as the caller passed it; free text for `propose` (`source=`). |
| `backend` | Who produced the edits: a backend name for `ingest`, `"api"` by default for `propose` (`backend=`). |
| `rationale` | Patch-set-level justification, rendered into the audit archive. |
| `edits[].path` | Wiki-relative target: `concepts/<slug>.md` for `create`/`update`; `index.md`, `<dir>/index.md` for `append-index`; `log.md` for `append-log`. Relative, no `..`. |
| `edits[].action` | `create`, `update`, `append-log` or `append-index` (`PageAction`). |
| `edits[].rationale` | One-line justification for this edit. |
| `edits[].base_sha256` | Optional, `update` only (0.6.0, a minor-version addition; older readers ignore it). The sha256 of the page bytes as read when the replacement was drafted: `wiki-studio read <path> --json` prints it, `ingest` takes it from the bytes it placed in the prompt, `propose --from` from the draft's `.base.json`, `api.propose` from `PageEdit.base_sha256`. `promote` applies the update only while the live page's sha256 still equals it (exit 9 otherwise, nothing written). No code path fills a missing value from the live page: an `update` without it is refused unless promote runs in compatibility mode (`--allow-unguarded-updates`), which records the path as unguarded. |
| `edits[].preview` | Where the content lives: `preview/<path>`; a second, third ... edit to the same path (several `append-index` or `append-log` lines) gets `preview/<path>.2`, `.3`, ... in edit order (`.2` is the second edit to that path, not a revision). `<path>` is normalised (`./` and repeated `/` dropped; `..` and absolute paths are rejected earlier), so `./index.md` is the same path as `index.md`. Always read the pointer. |
| `edits[].fact_warnings` | Optional, advisory. On an `update` whose live page exists: the facts the new content drops — `path:` citations (frontmatter `sources[].path`, body `path:line`), backticked identifiers and numbers with a unit (ms, s, min, h, d, KB, MB, GB, %, words, lines, tokens). Compared as normalized sets over the whole page, so a moved citation or a reflowed paragraph is no warning. Present only when non-empty; the CLI prints it to stderr as `fact-check: <path>: N item(s) removed`. `promote` ignores the key and never blocks on it. |
| `edits[].fact_check_error` | Optional, advisory. On an `update` whose live page exists but cannot be read or decoded as UTF-8: why the fact check did not run. The proposal is still written and no comparison is claimed; the CLI prints `fact-check: <path>: not compared (<reason>)` to stderr. `promote` ignores the key. |

The content itself is not in `plan.json`: `preview/<path>` holds the full
page (frontmatter and body) for `create` and `update`, or the line(s) to
append for `append-index` and `append-log`. A curator may edit the preview
files before promoting; `promote` records the difference against
`.ingest-snapshot/` as `curator-delta.md` in the audit archive.

## What `promote` does with it

Everything below happens while holding the wiki lock, an OS advisory lock
at `<wiki-parent>/.<wiki-dir-name>.wiki-studio.lock` (keyed to the resolved
wiki directory, so two spellings of one wiki share it; outside the wiki, so
lint and staging never see it). The lock serialises every cooperating
wiki-studio writer on one machine: `promote`, `propose --promote`, the
ingest-log append and `audit-flush`. It is not distributed, does not
protect against direct edits of wiki files, and network filesystems are out
of scope. Acquisition waits `--lock-timeout` / `WIKI_STUDIO_LOCK_TIMEOUT`
seconds (default 30); on expiry promote exits 10 with reason
`lock_timeout`.

1. Captures the proposal once: every regular file in the directory is read
   into memory (the *submission manifest*: path and sha256 each). A symlink
   anywhere in it is refused (exit 9). Parsing, the digest, staging and the
   archive all use that capture; the directory is never reread.
2. Reads `plan.json` and each `preview/<path>` from the capture; a missing
   preview or a malformed plan is a validation error (exit 9), a `preview`
   pointer that does not name a regular file under `preview/` is a contract
   violation (exit 4), and nothing is applied either way.
3. Validates the edits against the live wiki: set-level invariants (at least
   one edit, relative paths, append targets, no duplicate creates) and
   per-edit checks (`create`/`update` content has frontmatter with
   `page_type`, `slug`, `title` and a non-empty `sources:`; the slug equals the
   file stem; the page type is promotable and matches its directory; `update`
   targets exist and `create` targets do not).
4. Stages a copy of the wiki (read relative to the open wiki-directory
   descriptor on POSIX), applies the edits, stages this proposal's audit
   archive, runs the structural linter over the staged tree, and only then
   commits. The commit writes **only** the paths the patch-set names (including
   `index.md` and `log.md` appends) plus `<wiki>/.audit/proposals/<name>/`
   (`plan.json` verbatim, a rendered `proposal.md`, any `curator-delta.md`);
   a staged file outside that set is never written back, and a path whose
   live bytes already equal the proposed bytes is a no-op. On an exception
   during the commit every touched file is restored. Append edits require
   their target file to exist.
   Immediately before the commit, still under the lock, the revision
   preconditions are checked against the live wiki: a `create` requires its
   target to be absent; an `update` with `base_sha256` requires the live
   page's sha256 to equal it; an `update` without one is refused unless
   `--allow-unguarded-updates` / `allow_unguarded_updates=True` was given, in
   which case it is applied and listed under `unguarded_paths` in the receipt
   and in `PromoteResult` (compatibility mode with incomplete conflict
   protection: a stale draft can overwrite a newer page). `append-index` and
   `append-log` lines land on the staged copy of the current content, which
   was taken under the same lock. A mismatch exits 9 naming each page, and
   nothing is written.
   `--dry-run` takes the lock, stages, checks these preconditions against
   the live wiki, releases the lock, then validates the staged snapshot. It
   writes no wiki content, no receipt and no proposal change; its result is
   point-in-time evidence and a real promote checks again.
5. Archives the proposal: the captured tree plus the receipt are written to
   `<proposals-dir>/.applied/.<name>.<pid>.tmp/`, fsynced, and published by an
   atomic rename to `<proposals-dir>/.applied/<name>/` (`<name>-2`, `-3` on a
   name clash, as since 0.4.0). The original directory is then removed, only
   if every file in it still matches the archive and nothing new appeared (a
   file deleted from it after capture is not a change: the archive holds the
   captured bytes; `receipt.json` itself is not compared);
   otherwise it is left in place and promote exits 10 with reason
   `payload_changed` naming each file that differs or is new (the archive is
   complete; the remedy is to delete the leftover directory, or promote it
   afresh if it is a new proposal). `receipt.json` is deleted last.

The guarantee is: validated, serialised against other wiki-studio writers on
the same machine, rolled back on an exception during the commit. It is
**not** crash-safe across files: a process killed inside step 4's writes can
leave some files written and others not, and uncoordinated readers may
observe intermediate state.

## Receipts

`promote` writes `receipt.json` into the proposal directory before the
commit and moves it with the proposal into the archive. The submitted bytes
(`plan.json`, `preview/`, `.ingest-snapshot/`, any other file) are never
rewritten; execution metadata lives only in the receipt. Failed validation
attempts and dry runs persist no receipt.

| Key | Meaning |
|-----|---------|
| `receipt_version` | `1`. |
| `state` | `committing` (written before the commit, fsynced) or `committed` (rewritten after it, fsynced). |
| `proposal` | The proposal directory's name. |
| `submission_digest` | The submission identity: recipe 2 (`payload_digest`, `schema/audit-rules.md`) over `plan.json` and every file under `preview/`, hidden files included; `.ingest-snapshot/` is outside it. Equal to the ingest-log `proposal_hash` of a proposal promoted unchanged when that record carries `hash_recipe: 2` (records written before 0.6.0 used recipe 1 and differ); different after a curator edit, which `curator-delta.md` records. |
| `digest_recipe` | `2`. |
| `submission_manifest` | Every captured file as `{"path", "sha256"}` (proposal-relative), so a later process can prove which archive is this proposal's and which source files remain. |
| `plan_sha256` | sha256 of `plan.json`, for provenance. |
| `wiki_target` | The wiki being written: `st_dev` and `st_ino` from `os.fstat` on the wiki-directory descriptor opened under the lock, plus the resolved `path` as a diagnostic that is never used to accept. Zero values count as unavailable. |
| `planned_writes` | Every path the commit actually writes (no-ops excluded, this proposal's `.audit/proposals/` archive included): `pre_sha256` (null when absent) and `post_sha256`. |
| `written_paths` | The paths written, filled at `committed`. |
| `unguarded_paths` | The `update` paths applied without a `base_sha256` under `--allow-unguarded-updates` (compatibility mode with incomplete conflict protection); empty otherwise. |
| `lock_wait_seconds`, `started_at`, `committing_at`, `committed_at` | Timing. |
| `promoter` | Software identity only: `package`, `version`, `entry_point` (`cli` or `api`). |

### Promoting the same directory again

A later `promote` of a directory that carries a receipt resolves it instead
of re-applying anything. Before any recovery step, archival or outcome
report it compares the receipt's `wiki_target` with the invoked wiki by
device and inode only: a mismatch exits 10 with reason `wiki_mismatch`
(nothing written), and a receipt or wiki without a usable identity exits 10
with reason `wiki_identity_unavailable` (no path fallback). Then:

- `committed`: finish the archive only, with no appends. When a complete
  archive for the receipt's `submission_digest` already exists, the directory
  is removed if it still matches that archive, else left in place with
  `payload_changed`. When no archive exists and the directory's digest still
  equals the receipt's, the archive is written from the directory's bytes and
  the directory removed. When it does not, no archive can be written (the
  promoted bytes now exist only in the wiki): promote exits 10 with
  `payload_changed`, leaves the directory in place, and names the receipt's
  tracked post-commit hashes; the remedy is to move the directory aside and
  keep its receipt as the record of what was applied, or promote it afresh if
  it is a new proposal.
- `committing`: each tracked write's live sha256 is compared with the receipt.
  All at their pre-commit state means not committed: the receipt is removed
  (it recorded an attempt that wrote nothing, and is not preserved) and the
  proposal is promoted afresh in the same run. All at their post-commit state
  means committed: steps 3 to 5 are finished. Anything else, including a
  tracked path that is unreadable or not a regular file, exits 10 with reason
  `uncertain_outcome` naming the paths, with no writes.
- Under `.applied/`: the recorded outcome, no writes.
- A missing or corrupt receipt is never taken to mean committed and never
  causes a silent re-application; a corrupt one exits 10 with reason
  `uncertain_outcome`.

Recovery of an interrupted promotion needs a filesystem with stable inode
identity. When a wiki was legitimately restored or re-cloned at the same
path (`wiki_mismatch`), or the filesystem reports no identity, the remedy is
manual: compare the receipt's tracked writes (pre- and post-commit sha256)
with the live pages, then either finish by promoting afresh or discard the
proposal directory by hand. Promote never does this automatically. The
protocol covers failures between its steps; it does not claim recovery from
an arbitrary crash inside the commit beyond the exception rollback.

Windows: the lock has an `msvcrt.locking` backend and the identity falls
back to `os.stat` with staging by path, but this release is not tested on
Windows and its classifier says POSIX; that behaviour is unsupported rather
than a weaker guarantee.

## Writing one from a library

```python
from pathlib import Path
from wiki_studio import api
from wiki_studio.api import PageEdit
from wiki_studio.paths import WikiPaths

paths = WikiPaths.for_root(Path.cwd(), wiki_dir=Path("knowledge/wiki"))
edits = [
    PageEdit("concepts/retry-budget.md", "create", page_markdown, "New concept."),
    PageEdit("index.md", "append-index", "- [Retry budget](concepts/retry-budget.md) — draft.", "Index it."),
    PageEdit("log.md", "append-log", "- 2026-10-15 — created retry-budget (concept): draft.", "Log it."),
]
proposal = api.propose(edits, paths, name="2026-10-15-retry-budget", source="memkernel", rationale="Export.")
api.promote(proposal, paths)
```

A replacement records the page it was drafted from: read it once, draft
from that text, and pass the hash of those bytes as `base_sha256`.

```python
page = api.read_page("concepts/retry-budget.md", paths)        # one read: data, text, sha256
revised = page.text.replace("draft", "stable")
proposal = api.propose(
    [PageEdit("concepts/retry-budget.md", "update", revised, "Promote to stable.", base_sha256=page.sha256)],
    paths,
    name="2026-10-16-retry-budget-stable",
)
api.promote(proposal, paths)   # PromoteValidationError (exit 9) if the page changed since the read
```

`propose` runs step 3 above before writing and raises
`ContractViolationError` with every problem listed, so a bad edit never
reaches disk. For `append-index` and `append-log` edits that check is only
that the content is non-empty; the target file must exist at promote time.
`propose` refuses to overwrite an existing directory (`OutputWriteError`)
and, whatever the failure while writing, removes the directory it could only
partly write (and a proposals directory it created for it). Validation is against the
live wiki: propose and promote patch-sets one at a time rather than proposing
several that depend on each other.
