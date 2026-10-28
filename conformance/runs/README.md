# Recorded host runs

A host run is one MCP host, at a pinned version, doing the fixed scenario
(`conformance/mcp/scenario.md`) against `wiki-studio-mcp` on a copy of the
conformance fixture (0.8.0, FR-045). The owner performs it outside CI,
because it needs the owner's account and a model. `check-host-run` then
applies conformance cases 2-9 to the run's trace and the fixture's end
state. It never reads the transcript.

The trace holds no content, so a host run proves less than the protocol
suite does, and the checker labels each case with what proves it:

| Label | Cases | What the run shows |
|---|---|---|
| `proved` | 2, 3, 4 | From the trace's evidence lines: `tools/list` named exactly the eight tools; every `find` stayed within five pages and its `max_pages`, named a ranker and gave every page a sha256; `read_page` returned a sha256 and one `read_page` was refused with exit 7 (the scenario's traversal step). Not shown: the argument schemas, index linkage, the byte budget, that the sha256 is the file's. |
| `proved-by-end-state` | 5, 6, 9 | The trace's counts plus the end state: the update carried `base_sha256` and the proposal is archived (5); the promote applied paths, was not a dry run, and its receipt is `committed` with `entry_point: mcp`, the update landed from the fixture's revision with no unguarded path (6); `review_state` after the promote reports no approved page, the promote approved none and no approval record exists (9). Not shown: that the wiki stayed unchanged between propose and promote. |
| `not-provable-from-host-run (protocol suite)` | 7, 8 | The stale-update refusal and `promote` of `../x` are not in the scenario. Counted as skipped, never as passed. |

A run whose trace has no `read_page` refused with exit 7 fails case 4 with
"containment is not provable from this run". The verdict line names the
cases the run proves, and `verdict.proved` in `manifest.json` lists them.

The protocol-level suite in CI (`python -m conformance.mcp.run`, the
`mcp-min` and `mcp-latest` jobs) is the evidence for everything a host run
cannot show. It is not a substitute for a recorded host run, and a host run
is not a substitute for it. A failed attempt is recorded too, with its
verdict; it is never hidden or overwritten. A second attempt is a new
directory.

## The run directory

`conformance/runs/<YYYY-MM-DD>-claude-code-<version>/`:

| Entry | What it holds |
|---|---|
| `manifest.json` | The keys below. |
| `trace.jsonl` | The server's `--trace` file, one JSON line per request (`docs/mcp-adapter.md`, Trace). It has no page content, question text, edit content or path; its `tool_names`, `arg_keys`, `result_keys` and per-tool `summary` keys are the checker's evidence. |
| `end-state/` | The fixture project root after the run (the wiki, the proposals directory and its `.applied/` archive), without the derived lock and search-cache files beside the wiki. |
| `transcript.txt` | Optional. The host's output, kept for people. The checker does not read it. |

`manifest.json` keys:

| Key | Value |
|---|---|
| `claude_code_version` | `claude --version`, the pinned host version (for another host, its version under the same key) |
| `model` | The model by its full name |
| `wiki_studio_commit` | `git rev-parse HEAD` of the wiki-studio checkout that was installed |
| `wiki_studio_version` | `wiki-studio --version` |
| `mcp_version` | The installed `mcp` SDK version |
| `protocol_version` | The protocol version the host negotiated, as the trace records it |
| `scenario_sha256` | sha256 of `conformance/mcp/scenario.md` as used |
| `end_state_sha256` | `python -m conformance.mcp.run tree-hash <run>/end-state` |
| `verdict` | Written by `check-host-run --record`: `passed`, each case's status (`cases`) and proof label (`proof`), and the case lists `proved`, `not_provable` and `failed` |

## Claude Code

Run from the repository root, with `wiki-studio[mcp]` installed and the
`claude` CLI pinned to the version being recorded:

```bash
VERSION="$(claude --version | awk '{print $1}')"
RUN="$PWD/conformance/runs/$(date +%F)-claude-code-$VERSION"
WORK="$(mktemp -d)"
mkdir -p "$RUN"
cp -R conformance/mcp/fixture/project "$WORK/project"
cp conformance/mcp/fixture/variants/default/.wiki-studio.json "$WORK/project/knowledge/wiki/"
cat > "$WORK/mcp.json" <<EOF
{
  "mcpServers": {
    "wiki-studio": {
      "command": "wiki-studio-mcp",
      "args": ["--root", "$WORK/project", "--by", "claude-code-host-run", "--trace", "$RUN/trace.jsonl"]
    }
  }
}
EOF
claude -p "$(cat conformance/mcp/scenario.md)" \
  --mcp-config "$WORK/mcp.json" --strict-mcp-config \
  --allowedTools "mcp__wiki-studio" \
  --model "<full model name>" > "$RUN/transcript.txt"
cp -R "$WORK/project" "$RUN/end-state"
rm -f "$RUN"/end-state/knowledge/.wiki.wiki-studio.*
python -m conformance.mcp.run tree-hash "$RUN/end-state"
```

The fixture uses the default policy, without `auto_approve_on_promote`, so
the agent's promote must leave the page unapproved (case 9). Write
`manifest.json` with the keys above, then check and record the verdict:

```bash
python -m conformance.mcp.run check-host-run --run "$RUN" --record
```

The run directory, its verdict and a row in `docs/compatibility.md` (MCP
table) go into the evidence PR. A failed verdict is committed as it is.

## Kiro

Kiro reads `.kiro/settings/mcp.json` in the workspace. Prepare the fixture
copy as above and point the server at it, with the same `--by` and
`--trace` arguments:

```json
{
  "mcpServers": {
    "wiki-studio": {
      "command": "wiki-studio-mcp",
      "args": ["--root", "/tmp/…/project", "--by", "kiro-host-run", "--trace", "/abs/run-dir/trace.jsonl"]
    }
  }
}
```

If Kiro can run the scenario headless, record the run as for Claude Code
under `conformance/runs/<date>-kiro-<version>/`. The checker requires the
`claude_code_version` key: put Kiro's version there; the directory name
says which host it is. Otherwise give
it the scenario by hand in a fresh session and record the run the same way,
noting in `transcript.txt` that it was a manual run. `check-host-run`
applies the same cases. Kiro is not exit-blocking for Release C.
