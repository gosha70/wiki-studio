# Patch-set directory format

A patch-set is the unit `wiki-studio promote` applies to the wiki atomically.
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
└── .ingest-snapshot/         # optional: immutable copy of plan.json + preview/ taken at write time
    ├── plan.json
    └── preview/…
```

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
| `edits[].preview` | Where the content lives: `preview/<path>`; a second, third ... edit to the same path (several `append-index` or `append-log` lines) gets `preview/<path>.2`, `.3`, ... Always read the pointer. |

The content itself is not in `plan.json`: `preview/<path>` holds the full
page (frontmatter and body) for `create` and `update`, or the line(s) to
append for `append-index` and `append-log`. A curator may edit the preview
files before promoting; `promote` records the difference against
`.ingest-snapshot/` as `curator-delta.md` in the audit archive.

## What `promote` does with it

1. Reads `plan.json` and each `preview/<path>`; a missing preview or a
   malformed plan is a validation error (exit 9) and nothing is applied.
2. Validates the edits against the live wiki: set-level invariants (at least
   one edit, relative paths, append targets, no duplicate creates) and
   per-edit checks (`create`/`update` content has frontmatter with
   `page_type`, `slug`, `title` and a non-empty `sources:`; the slug equals the
   file stem; the page type is promotable and matches its directory; `update`
   targets exist and `create` targets do not).
3. Stages a copy of the wiki, applies the edits, runs the structural linter
   over the staged tree, and only then writes the result into the wiki.
   Append edits require their target file to exist.
4. Archives the directory: a copy of `plan.json`, a rendered `proposal.md` and
   any `curator-delta.md` go to `<wiki>/.audit/proposals/<name>/`; the
   proposal directory itself moves to `<proposals-dir>/.applied/<name>/`.
   `--dry-run` stops after step 3 and moves nothing.

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

`propose` runs step 2 above before writing and raises
`ContractViolationError` with every problem listed, so a bad edit never
reaches disk. For `append-index` and `append-log` edits that check is only
that the content is non-empty; the target file must exist at promote time.
`propose` refuses to overwrite an existing directory (`OutputWriteError`)
and, whatever the failure while writing, removes the directory it could only
partly write (and a proposals directory it created for it). Validation is against the
live wiki: propose and promote patch-sets one at a time rather than proposing
several that depend on each other.
