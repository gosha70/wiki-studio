# Consumer recipes

`wiki_studio` ships one CLI (`wiki-studio`) and one library module (`wiki_studio.api`).
Every location it reads or writes resolves through one object,
`WikiPaths`, from (highest precedence first) the global options
`--root`, `--wiki-dir`, `--proposals-dir`, the environment variables
`WIKI_STUDIO_ROOT`, `WIKI_STUDIO_WIKI_DIR`, `WIKI_STUDIO_PROPOSALS_DIR`, and the defaults:
the git toplevel of the current directory, `knowledge/wiki` and
`doc_internal/proposals` under it. With no flags and no variables the
layout is byte-identical to the original code-copilot-team layout.

## code-copilot-team

The repository the code was extracted from keeps its two wrapper
scripts; each becomes a two-line `exec`.

`scripts/wiki`:

```bash
#!/usr/bin/env bash
exec wiki-studio "$@"
```

`scripts/wiki-ingest` (the v1 single-source alias):

```bash
#!/usr/bin/env bash
exec wiki-studio ingest --legacy-single-source "$@"
```

Install step for `.github/workflows/wiki-ingest-tests.yml` (and for
developers, once):

```yaml
      - name: Install the wiki maintainer
        run: pip install "wiki-studio==0.5.0"
```

`tests/test-wiki-ingest.sh` passes unchanged: the verbs, flags and exit
codes are the same, and the defaults reproduce `knowledge/wiki` and
`doc_internal/proposals`. The structural linter now runs in Python inside
`wiki-studio lint` and `wiki-studio promote`; `knowledge/wiki/scripts/lint-wiki.sh`
can stay for direct use until it is retired.

Two renames, both backward compatible:

- `WIKI_INGEST_BACKEND` is now `WIKI_STUDIO_BACKEND`. The old name still works
  and prints a one-line deprecation warning on stderr.
- `pi` is auto-detected only with `WIKI_STUDIO_ENABLE_PI=1` (the
  `shared/capabilities/pi.yaml` lookup is gone). `--backend pi` works as
  before.

Once the version is pinned and the workflow is green, delete
`scripts/wiki_ingest/` from code-copilot-team; `knowledge/wiki/schema/`
stays there as the project's own copy of the schema (it takes precedence
over the packaged copy whenever `<wiki-dir>/schema/` exists).

## memkernel

memkernel's `WikiExporter` writes draft pages in the same schema
(`status: draft`, the extra keys `memkernel_ref` and `memory_type`, a
`memkernel://<project>/<ref>` source). Point both tools at the same
directory and lint after every export. `wiki_export` is one of memkernel's
MCP tools, not a shell command: call it from the agent session, or run the
exporter from Python.

```bash
export MEMKERNEL_WIKI_DIR="$PWD/knowledge/wiki"
export WIKI_STUDIO_WIKI_DIR="$MEMKERNEL_WIKI_DIR"
```

```python
from pathlib import Path
from memkernel.factory import build_service
from memkernel.wiki.sync import WikiExporter

WikiExporter(build_service(), Path("knowledge/wiki")).export()   # draft pages, index and log entries
```

```bash
wiki-studio lint                     # zero violations expected
wiki-studio lint --health            # stale sources, weak orphans, missing cross-links
```

From Python, the lint result is typed:

```python
import os
from pathlib import Path
from wiki_studio import api
from wiki_studio.paths import WikiPaths

paths = WikiPaths.for_root(Path.cwd(), wiki_dir=Path(os.environ["MEMKERNEL_WIKI_DIR"]))
result = api.lint(paths, health=True)
for violation in result.violations:
    print(violation)
```

### Through the promote gate (memkernel ≥ 0.5, wiki-studio ≥ 0.2)

With the `memkernel[wiki]` extra installed, the exporter no longer writes
the wiki itself: it hands its pages to `api.propose` and applies them with
`api.promote`, so a page that fails the structural lint never lands and the
wiki is left untouched. The same flow, written out:

```python
from pathlib import Path
from wiki_studio import api
from wiki_studio.api import PageEdit
from wiki_studio.paths import WikiPaths

paths = WikiPaths.for_root(Path.cwd(), wiki_dir=Path("knowledge/wiki"))
edits = [
    PageEdit("concepts/retry-budget.md", "create", page_markdown, "Draft compiled from memory mem-1."),
    PageEdit("index.md", "append-index", "- [Retry budget](concepts/retry-budget.md) — draft (fact).", "Index it."),
    PageEdit("log.md", "append-log", "- 2026-10-15 — created `retry-budget` (concept): from mem-1", "Log it."),
]
proposal = api.propose(edits, paths, name="2026-10-15-memkernel-export", source="memkernel")
api.promote(proposal, paths)        # PromoteResult; PromoteValidationError leaves the wiki untouched
```

`propose` validates the edits before writing anything (the same checks
`ingest` and `promote` run) and raises `ContractViolationError` listing every
problem. The directory it writes is described in
[`patch-set-format.md`](patch-set-format.md).

memkernel keeps its own `PAGE_SECTIONS`, `EXPORT_MAP` and `IMPORT_MAP` so the
bridge works without the extra; with it installed, a contract test compares
them with `wiki_studio.schema.PAGE_TYPES` (directory and required H2
sections per page type). On 0.1.0 `import wiki_studio.schema` succeeds as an
empty namespace package, so probe for `PAGE_TYPES`, not for the import.

#### Since wiki-studio 0.6.0: the lock, receipts, no outer rollback

`api.propose` and `api.promote` take the wiki lock themselves, and `promote`
writes only the paths the patch-set names, archives the proposal under
`<proposals>/.applied/<name>/` with a `receipt.json`, and rolls back its own
writes on failure. A bridge therefore needs no rollback of its own:

- **The gate path** is `api.propose` then `api.promote`, as above. Do not
  take a whole-wiki snapshot around it and restore it on failure: that
  restore runs outside the lock and can undo another writer's committed
  pages (memkernel #48). On a `GateError` report the error and leave the
  wiki to `promote`'s own rollback.
- **Recovery is by receipt.** A promotion interrupted between its commit
  and its archive leaves `receipt.json` in the proposal directory; calling
  `api.promote` on that directory again resolves it from the receipt and
  never re-applies an append. See the recovery rules in
  [`patch-set-format.md`](patch-set-format.md).
- **The scaffold comes from `api.init`.** It creates `index.md` and
  `log.md` only when absent and never overwrites; a bridge should call it
  rather than write the scaffold itself.
- **Ignore the lock file.** The lock is
  `.<wiki-dir-name>.wiki-studio.lock` beside the wiki directory; add it to
  `.gitignore` where the wiki lives in a git checkout.

The contract tests in `tests/test_bridge_contract.py` replay the bridge's
calls against wiki-studio, and `tests/test_snapshot_hazard.py` reproduces
the outer-rollback hazard with a copy of the bridge's snapshot. The
clean-install CI job `memkernel-compat` runs the real packages against a
pinned memkernel revision named in the workflow.

The fixture `tests/fixtures/wiki/` in this repository contains three
exporter-shaped pages (`decision`, `concept`, `workflow`); the test suite
asserts they lint clean, which pins the schema contract between the two
packages. Changing frontmatter keys, page types or directory names needs a
decision record in `docs/adr/` here first.

## document-assistant

A wiki at a custom path, outside `knowledge/wiki`:

```bash
export WIKI_STUDIO_WIKI_DIR="$HOME/assistant/kb"
export WIKI_STUDIO_PROPOSALS_DIR="$HOME/assistant/inbox"

wiki-studio ingest notes/2026-10-12-meeting.md --backend claude
wiki-studio promote "$HOME/assistant/inbox/2026-10-12-2026-10-12-meeting"
wiki-studio query "what did we decide about retrieval order?" --backend claude
```

The same three settings can be passed as `--root`, `--wiki-dir` and
`--proposals-dir`, before or after the verb. Sources and proposal
directories are confined to `--root` (the git toplevel by default);
`--allow-out-of-repo` lifts that for a deliberate external file. Pages
inside the wiki may still cite repo-relative `path:` sources; those are
resolved against `--root`.
