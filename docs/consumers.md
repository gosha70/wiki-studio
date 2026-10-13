# Consumer recipes

`wikiforge` ships one CLI (`wikiforge`) and one library module (`wikiforge.api`).
Every location it reads or writes resolves through one object,
`WikiPaths`, from (highest precedence first) the global options
`--root`, `--wiki-dir`, `--proposals-dir`, the environment variables
`WIKIFORGE_ROOT`, `WIKIFORGE_WIKI_DIR`, `WIKIFORGE_PROPOSALS_DIR`, and the defaults:
the git toplevel of the current directory, `knowledge/wiki` and
`doc_internal/proposals` under it. With no flags and no variables the
layout is byte-identical to the original code-copilot-team layout.

## code-copilot-team

The repository the code was extracted from keeps its two wrapper
scripts; each becomes a two-line `exec`.

`scripts/wiki`:

```bash
#!/usr/bin/env bash
exec wikiforge "$@"
```

`scripts/wiki-ingest` (the v1 single-source alias):

```bash
#!/usr/bin/env bash
exec wikiforge ingest --legacy-single-source "$@"
```

Install step for `.github/workflows/wiki-ingest-tests.yml` (and for
developers, once):

```yaml
      - name: Install the wiki maintainer
        run: pip install "wikiforge==0.1.0"
```

`tests/test-wiki-ingest.sh` passes unchanged: the verbs, flags and exit
codes are the same, and the defaults reproduce `knowledge/wiki` and
`doc_internal/proposals`. The structural linter now runs in Python inside
`wikiforge lint` and `wikiforge promote`; `knowledge/wiki/scripts/lint-wiki.sh`
can stay for direct use until it is retired.

Two renames, both backward compatible:

- `WIKI_INGEST_BACKEND` is now `WIKIFORGE_BACKEND`. The old name still works
  and prints a one-line deprecation warning on stderr.
- `pi` is auto-detected only with `WIKIFORGE_ENABLE_PI=1` (the
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
directory and lint after every export:

```bash
export MEMKERNEL_WIKI_DIR="$PWD/knowledge/wiki"
export WIKIFORGE_WIKI_DIR="$MEMKERNEL_WIKI_DIR"

memkernel wiki_export            # writes draft pages, index and log entries
wikiforge lint                     # zero violations expected
wikiforge lint --health            # stale sources, weak orphans, missing cross-links
```

The fixture `tests/fixtures/wiki/` in this repository contains three
exporter-shaped pages (`decision`, `concept`, `workflow`); the test suite
asserts they lint clean, which pins the schema contract between the two
packages. Changing frontmatter keys, page types or directory names needs a
decision record in `docs/adr/` here first.

From Python:

```python
import os
from pathlib import Path
from wikiforge import api
from wikiforge.paths import WikiPaths

paths = WikiPaths.for_root(Path.cwd(), wiki_dir=Path(os.environ["MEMKERNEL_WIKI_DIR"]))
result = api.lint(paths, health=True)
for violation in result.violations:
    print(violation)
```

## document-assistant

A wiki at a custom path, outside `knowledge/wiki`:

```bash
export WIKIFORGE_WIKI_DIR="$HOME/assistant/kb"
export WIKIFORGE_PROPOSALS_DIR="$HOME/assistant/inbox"

wikiforge ingest notes/2026-10-12-meeting.md --backend claude
wikiforge promote "$HOME/assistant/inbox/2026-10-12-2026-10-12-meeting"
wikiforge query "what did we decide about retrieval order?" --backend claude
```

The same three settings can be passed as `--root`, `--wiki-dir` and
`--proposals-dir`, before or after the verb. Sources and proposal
directories are confined to `--root` (the git toplevel by default);
`--allow-out-of-repo` lifts that for a deliberate external file. Pages
inside the wiki may still cite repo-relative `path:` sources; those are
resolved against `--root`.
