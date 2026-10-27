# The MCP adapter: `wiki-studio-mcp`

`wiki-studio-mcp` is an MCP server over stdio. It gives an agent in an MCP
host (Claude Code, Kiro) the same curation loop the CLI gives a shell, with
the same boundary: no model calls, a proposal kept apart from its promotion,
and no approval tool. It ships as an extra from 0.8.0. The dependency review
and the tool contract are recorded in
[ADR-0003](adr/0003-optional-mcp-dependency-and-tool-contract.md).

## Install

```bash
pip install 'wiki-studio[mcp]'
```

The extra adds the official MCP SDK (`mcp>=2.3,<3`). It is the package's
only optional dependency. `pip install wiki-studio` without the extra still
imports nothing outside the standard library. In that case `wiki-studio-mcp`
prints the following to stderr and exits 2:

```
wiki-studio-mcp needs the mcp extra: pip install 'wiki-studio[mcp]'
```

## Launch

The host starts the server and talks to it over stdin and stdout. Every
setting is read once at launch and held for the life of the process.

| Flag | Variable | Meaning |
|---|---|---|
| `--root PATH` | `WIKI_STUDIO_ROOT` | project root |
| `--wiki-dir PATH` | `WIKI_STUDIO_WIKI_DIR` | wiki directory |
| `--proposals-dir PATH` | `WIKI_STUDIO_PROPOSALS_DIR` | proposals directory |
| `--source-root PATH` (repeatable) | `WIKI_STUDIO_SOURCE_ROOTS` | directories outside the root that pages may link into |
| `--lock-timeout SECONDS` | `WIKI_STUDIO_LOCK_TIMEOUT` | wiki-lock wait |
| `--search-cache PATH` | `WIKI_STUDIO_SEARCH_CACHE` | the `fts5` search cache, outside the wiki |
| `--ranker {fts5,index-first}` | `WIKI_STUDIO_RANKER` | the `find` tool's default ranker |
| `--by NAME` | `WIKI_STUDIO_ACTOR` | the actor every `propose` and `promote` is attributed to |
| `--disable-tool NAME` (repeatable) | | remove a tool from the surface |
| `--trace PATH` | | append one JSON line per request (see Trace) |

The precedence is the CLI's: a flag, then its variable, then the default.
The server exits 2 without serving when:

- a flag is malformed;
- a value is rejected (a negative lock timeout, an unknown ranker, a search
  cache inside the wiki);
- `--disable-tool` names an unknown tool;
- `--trace` lies inside the wiki or cannot be opened for appending.

At start-up the server writes one line to stderr. The line names:

- the resolved wiki;
- the actor and its source (`flag`, `env` or `none`);
- the ranker and its source;
- the live tools;
- the wiki's policy, including `auto_approve_on_promote` when it is set.

stdout carries protocol frames only. Logging and Python warnings go to
stderr.

### Claude Code

```bash
claude mcp add wiki-studio -- wiki-studio-mcp --root /path/to/project --by claude-agent
```

or in the project's `.mcp.json`:

```json
{
  "mcpServers": {
    "wiki-studio": {
      "command": "wiki-studio-mcp",
      "args": ["--root", "/path/to/project", "--by", "claude-agent"]
    }
  }
}
```

### Kiro

`.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "wiki-studio": {
      "command": "wiki-studio-mcp",
      "args": ["--root", "/path/to/project", "--by", "kiro-agent"]
    }
  }
}
```

## Tools

The surface is exactly eight tools. Each one is a single synchronous call
into `wiki_studio.api`, and the SDK runs it on a worker thread, so a tool
that waits for the wiki lock does not block other requests. Every result is
a JSON object. It arrives as the tool result's one text block and as its
structured content. Paths in results are relative to the project root
(files) or to the wiki (pages).

| Tool | Arguments | Result |
|---|---|---|
| `find` | `question: str`, `max_pages: int = 5` (1..5), `max_bytes: int = 65536`, `ranker: str \| null` (per-call override of the launch default) | The `find --json` object: `question`, `index`, `pages[]` (`path`, `file`, `title`, `sha256`, `bytes`), `ranker`, `fallback_reason`, `bytes_loaded`, `max_bytes`, `ranker_config_hash`, `omitted[]`, `ineligible[]`, `warnings` |
| `read_page` | `path: str` (wiki-relative) | `{path, sha256, content}`, as `read --json` |
| `propose` | `edits: [{path, action, content, base_sha256?}]`, `name: str \| null`, `rationale: str = ""` | `{name, proposal_dir, warnings}` |
| `promote` | `name: str`, `dry_run: bool = false` | `{applied_paths, archived_dir, dry_run, unguarded_paths, warnings, approved_paths}` |
| `lint` | `health: bool = false`, `prose: bool = false`, `strict: bool = false` | `{violations, pages_checked, audit_errors, health: {pages_checked, findings[]} \| null, prose: {pages_checked, findings[]} \| null, passed}` |
| `info` | (none) | `info --json`'s contract keys (`package_version`, `schema_contract`, `formats`, `capabilities`, `manifest`, `discovery`) plus `adapter` |
| `findings` | `pages: [str] \| null` | `findings --json`'s object |
| `review_state` | `pages: [str] \| null` | `{states: [{path, page_key, state, reason, live_sha256, approved_sha256, record_path, warnings}]}` |

Details:

- **`find`**: model-free page selection, the same as the `find` verb.
  `max_pages` outside 1..5 is a `ValueError` error result.
- **`propose`**: `action` is one of `create`, `update`, `append-index` or
  `append-log`. An `update` carries `read_page`'s `sha256` as `base_sha256`.
  An edit with any other key, or without a string `path`, `action` or
  `content`, is a `ValueError` error result.
  - `name` defaults to `mcp-<UTC yyyymmddThhmmssZ>-<8 hex>`.
  - `plan.json` records `source: "mcp"` and `backend: "mcp"`.
  - Every `create` gets a `page_id`, as with `propose --from`.
  - Schema drift on a managed wiki is reported in `warnings`.
  - The proposal is written under the proposals directory; the wiki is not
    touched.
- **`promote`**: `name` must be one path component of ASCII letters,
  digits, `.`, `_` and `-`, not starting with `.`. It is resolved as
  `<proposals_dir>/<name>`. Any other name (`../x`, an absolute path, `a/b`)
  is a `ValueError` error result, and nothing is read.
  - The receipt records `promoter.entry_point: "mcp"`.
  - The escape hatches (`allow_out_of_repo`, `allow_unguarded_updates`) are
    never used.
  - A stale `update` is an exit-9 error result, with the wiki unchanged.
- **`lint`**: runs without a backend, so the contradiction check is skipped
  and no model is reached. `passed` follows `lint`'s exit rule.
- **`info`**: `discovery.default_ranker` and `default_ranker_source` report
  the launch ranker (`flag` when `--ranker` was given). `adapter` has
  `adapter_version` (the package version), `sdk_version` (the installed
  `mcp`), `protocol_version` (negotiated, or `null` before initialisation),
  `tools` (the live list), `actor` (`{name, source}`), `ranker`
  (`{name, source}`) and `disabled_tools`.
- **`findings`** and **`review_state`**: read only, take no lock, call no
  model. `pages` scopes them; by default they cover the whole wiki.

`lint` has no `--json` in the CLI and `review_state` has no CLI verb. Their
result shapes above are defined here.

## The boundary

- **Not exposed.** `approve`, `ingest`, `query`, `audit-flush` and `init` are
  not tools. No flag or variable adds them. A host that needs more calls
  `wiki_studio.api` itself.
- **No location, backend, actor or escape-hatch argument.** No tool's input
  schema has `root`, `wiki_dir`, `proposals_dir`, `backend`, `by`, `actor`,
  `allow_out_of_repo`, `allow_unguarded_updates`, `entry_point`,
  `lock_timeout` or `ranker_config`. An agent may choose the ranker per
  call, but never its weights or tokenizer. MCP roots advertised by the
  client are not read and never widen the configured layout.
- **`--disable-tool`** only removes tools. With **`--disable-tool
  promote`** the server runs in **propose-only mode**: the agent's proposals
  wait in the proposals directory for a person to `promote` and `approve`
  them.
- **The fixed actor.** The actor is the launch `--by` value, else
  `WIKI_STUDIO_ACTOR`, else none. It is recorded as `plan.json`'s
  `proposer`, the receipt's `actor` and any approval record's `approver`.
  Tools take no `by`, so an agent cannot record a person's name. This is
  attribution, not authentication.
- **Auto-approval by policy.** On a wiki whose manifest policy sets
  `auto_approve_on_promote`, the `promote` tool honours the policy and never
  refuses because of it. The result lists the approved pages in
  `approved_paths`. One warning names the policy and states that these pages
  were approved by policy as part of this promotion, attributed to the
  server's actor. **On such a wiki an agent's promote approves its own
  proposal; that is the host's configured policy.** Use `--disable-tool
  promote`, or a wiki without the policy, when a person must approve.
- **Errors.** Every wiki-studio error and every `ValueError` raised by a
  tool becomes an error result (`isError: true`) whose text is
  `{error, exit_code, message}`, with the exit codes of the CLI table
  (`README.md`, Exit codes; `ValueError` is 1). Any other exception becomes
  `{error: "InternalError", exit_code: 1, message: <class name>}`, with no
  traceback or path. The traceback goes to stderr.

## Trace

With `--trace PATH`, the server appends one JSON line per request to
`PATH`:

```json
{"ts":"2026-10-27T12:00:00.000Z","method":"tools/call","tool":"find","protocol_version":"2025-06-18","client_name":"claude-code","client_version":"2.1.0","outcome":0,"duration_ms":12}
```

- `outcome` is 0, or the error result's `exit_code` (1 for a protocol-level
  error).
- Page content, question text, edit content and file paths are never
  traced.
- The file is opened append-only and must lie outside the wiki. A path
  inside the wiki, or one that cannot be opened, is a launch error (exit 2),
  never a silent drop.
- Without the flag, nothing is written.

The server reads the JSON-RPC frames as they pass between stdio and the SDK,
and copies them unchanged. Because the trace comes from the wire, it does
not depend on SDK internals.

## SDK versions

`mcp>=2.3,<3`. CI runs the adapter tests and the conformance suite at the
locked dev-group version. The `mcp-min` and `mcp-latest` jobs run them at
`mcp==2.3.0` and at the newest `mcp<3`; both are blocking. A new SDK release can therefore
turn an unrelated PR red. The response is a fix PR that lowers the ceiling to
the last known-good minor (for example `>=2.3,<2.5`) and opens an issue for
the adaptation. The pin is never widened and the job never gets
`continue-on-error`.

## Conformance

`conformance/mcp/` holds a suite that checks this tool contract against any
server command. It imports nothing from `wiki_studio`, so another
implementation of the surface can run it too. It needs the `mcp` SDK.

```bash
python -m conformance.mcp.run --server-cmd "wiki-studio-mcp --root {root}"
```

The suite copies `conformance/mcp/fixture/` into a temporary root (`{root}`
in the command becomes that root) and drives the server through the SDK's
client over stdio. It runs once per tested protocol version:

- `2025-06-18` and `2025-11-25`, by the initialize handshake;
- `2026-07-28`, by the per-request envelope.

`--protocol-version V` (repeatable) narrows the run. `--trace PATH` passes
`--trace PATH` to every launch. Each version runs twelve named cases:

1. The server negotiates the version, or refuses it cleanly.
2. `tools/list` is exactly the eight tools, with none of the forbidden
   arguments. Started with `--disable-tool promote`, the list lacks
   `promote`, a `promote` call is an error, and the other seven work.
3. `find` returns at most five index-linked pages within the budget and
   names its ranker.
4. `read_page`'s `sha256` is the file's. An absolute path, `../` and a
   symlink are exit-7 errors.
5. `propose` writes under the proposals directory, leaves the wiki
   byte-identical, and its create carries a `page_id`.
6. `promote` lands that proposal with a `committed` receipt and the archive.
7. A guarded `update` lands. The same update after a hand edit is an exit-9
   error, and the wiki is unchanged.
8. `promote` of `../x` or of an absolute name is refused, and a proposal
   placed there is not applied.
9. On the default-policy fixture the promoted page is not `approved`.
10. On the `auto_approve_on_promote` fixture the promote succeeds, lists the
    page in `approved_paths` with the policy warning, and the approval
    record's approver is the launch actor.
11. `lint` with `health` makes no backend call. A stub that records every
    invocation stands in for the backend CLI.
12. stdout carries JSON-RPC frames only. A relay records every byte the
    server writes.

The suite exits 0 when every case passes, 1 when one fails, and 2 when it
cannot run (for example without the SDK).
`tests/test_mcp_conformance.py` runs it against `wiki-studio-mcp`.

### Host runs

A host run is the evidence the protocol suite cannot give: a real MCP host,
at a pinned version, doing the fixed scenario in
`conformance/mcp/scenario.md` (find, read, propose an update carrying the
hash, promote, `review_state`) against the default-policy fixture with
`--trace`.

```bash
python -m conformance.mcp.run check-host-run --run conformance/runs/<date>-claude-code-<version>
```

The checker applies cases 2-9 to the run's trace and end state. It never
reads the transcript. `conformance/runs/README.md` gives the run
directory's layout and the Claude Code (`claude -p --mcp-config`) and Kiro
instructions. The owner performs host runs outside CI. `docs/compatibility.md`
lists what has been run.

## What the adapter does not do

- No HTTP or SSE transport, resources, prompts or authentication.
- No model calls: no `query`, no `ingest`, no contradiction check.
- No approval tool, and no override of the wiki's approval policy.
- No registry publication.
