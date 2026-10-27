# ADR 0003: The optional `mcp` dependency and the MCP tool contract

- Status: accepted
- Date: 2026-10-27
- Issue: [#38](https://github.com/gosha70/wiki-studio/issues/38) (Release C)
- Feature: `specs/wiki-studio-0-8-0/` (FR-031..FR-042)

## Context

Through 0.7.0 wiki-studio had two surfaces, the CLI and a Python API, and no
runtime dependency. An MCP host that is not shell-first (Claude Code, Kiro)
had to wrap the CLI. Each wrapper had to rebuild the same boundary: no model
calls, a proposal kept apart from its promotion, and no approval. Release C
adds an MCP server so hosts get that boundary from wiki-studio itself.

Speaking MCP means taking a dependency or writing the protocol by hand. The
protocol has versions, negotiation and a per-request envelope (2026-07-28),
so a hand-written server would be a second product to maintain. The
official SDK is the smaller risk, provided it never reaches the core.

The page schema does not change. ADR-0002 is untouched.

## Decision

**One optional dependency.** `mcp`, the official SDK
(`modelcontextprotocol/python-sdk`), is declared optional:

```toml
[tool.poetry.dependencies]
mcp = { version = ">=2.3,<3", optional = true }

[tool.poetry.extras]
mcp = ["mcp"]
```

`mcp` is also in the dev group, so mypy, coverage and `pip-audit` see it.
The console script is `wiki-studio-mcp = "wiki_studio.mcp_adapter:main"`.

**The standard-library boundary.** Only `src/wiki_studio/mcp_adapter/server.py`
imports `mcp`. `mcp_adapter/__init__.py` imports it lazily inside `main()`.
Without the extra, `wiki-studio-mcp` prints
`wiki-studio-mcp needs the mcp extra: pip install 'wiki-studio[mcp]'` and
exits 2. The core never imports `mcp_adapter`. This is proved twice:

- `tests/test_package_boundaries.py` parses every module outside
  `mcp_adapter/` with `ast` and fails on any import that is not in
  `sys.stdlib_module_names` or `wiki_studio`.
- CI's `build-check` job checks the built wheel:
  - it installs the wheel without extras into a fresh environment;
  - it imports every core module under `python -I`;
  - it asserts that every module this loads is standard library or
    `wiki_studio`;
  - it checks that every `Requires-Dist` line carries `extra == "mcp"`;
  - it checks that `wiki-studio-mcp` exits 2 with the instruction.

`wiki-studio`'s verbs and exit codes are untouched.

## Dependency review

| Item | Finding |
|---|---|
| Package | `mcp`, the official Python SDK of the Model Context Protocol (`modelcontextprotocol/python-sdk`) |
| Licence | MIT |
| Maintenance (as of 2026-10-26) | 2.0.0 on 2026-07-28; 2.3.0 on 2026-10-02; the 1.x line still patched (1.30.0 on 2026-09-07) |
| Python | `Requires-Python >=3.10` (wiki-studio: 3.11–3.13) |
| Direct requirements | `anyio`, `httpx2`, `jsonschema`, `mcp-types`, `opentelemetry-api`, `pydantic`, `pyjwt[crypto]` (pulls `cryptography`), `python-multipart`, `sse-starlette`, `starlette`, `typing-extensions`, `typing-inspection`, `uvicorn`, `pywin32` on Windows |
| Pin | `>=2.3,<3`. 2.3 is the floor because it is the first release with the server API and protocol versions this adapter uses (`mcp.server.MCPServer`, `add_tool`, sync tools on a worker thread, `CallToolResult` passed through). `<3` because a major version may break the API. |
| Risk | Churn within 2.x: the API was renamed from 1.x (FastMCP to `MCPServer`) and is still moving. The transitive tree is large for a stdio server: HTTP, SSE, auth and telemetry packages come in although the adapter uses none of them. |
| Controls | The extra is opt-in, so the base install is unaffected. Only `server.py` imports the SDK, and only these names: `MCPServer`, `add_tool`, `run("stdio")`, `CallToolResult`. The trace observes the JSON-RPC wire, not SDK internals. `pip-audit` covers the dev group, which includes `mcp`. The `mcp-min` (`mcp==2.3.0`) and `mcp-latest` (newest `<3`) CI jobs (US5) are blocking. When `mcp-latest` breaks, the ceiling is lowered to the last known-good minor and an issue is opened; the pin is never widened and the job never gets `continue-on-error`. |

### Transitive licences

The specification requires this list to be re-checked from `poetry.lock` at
build time. **It has not been yet.** The build session that wrote this
record could not regenerate `poetry.lock` (`poetry lock` was unavailable in
its sandbox). The list below is taken from each package's published
metadata, not from the lock. It must be checked against the locked set, and
this note removed, in the commit that updates `poetry.lock`.

| Package | Licence |
|---|---|
| `mcp`, `mcp-types` | MIT |
| `anyio` | MIT |
| `httpx2`, `httpcore` | BSD-3-Clause |
| `h11` | MIT |
| `idna` | BSD-3-Clause |
| `certifi` | MPL-2.0 |
| `sniffio` | MIT or Apache-2.0 |
| `jsonschema`, `jsonschema-specifications`, `referencing`, `rpds-py`, `attrs` | MIT |
| `opentelemetry-api` | Apache-2.0 |
| `importlib-metadata` | Apache-2.0 |
| `zipp` | MIT |
| `pydantic`, `pydantic-core`, `annotated-types` | MIT |
| `pydantic-settings`, `python-dotenv` (if locked) | MIT, BSD-3-Clause |
| `pyjwt` | MIT |
| `cryptography` | Apache-2.0 or BSD-3-Clause |
| `cffi` | MIT |
| `pycparser` | BSD-3-Clause |
| `python-multipart` | Apache-2.0 |
| `sse-starlette`, `starlette` | BSD-3-Clause |
| `uvicorn`, `click` | BSD-3-Clause |
| `typing-extensions` | PSF-2.0 |
| `typing-inspection` | MIT |
| `pywin32` (Windows only) | PSF-2.0 |

None is copyleft. MPL-2.0 (`certifi`) is file-level and applies only to
modified files of that package.

## The tool contract

**Transport.** stdio only. The adapter has no HTTP, no SSE, no resources,
no prompts and no authentication.

**Surface.** Exactly eight tools: `find`, `read_page`, `propose`, `promote`,
`lint`, `info`, `findings` and `review_state`. `approve`, `ingest`, `query`,
`audit-flush` and `init` are not tools, and no flag or variable adds them in
0.8.0. Each tool is one synchronous call into `wiki_studio.api`, and every
result is a JSON object.

**Arguments.** No tool takes a root, directory, backend, actor or
escape-hatch argument. A test asserts that no input schema has a property
named `root`, `wiki_dir`, `proposals_dir`, `backend`, `by`, `actor`,
`allow_out_of_repo`, `allow_unguarded_updates`, `entry_point`,
`lock_timeout` or `ranker_config`.

The launch flags fix the layout, the actor and the default ranker once:
`--root`, `--wiki-dir`, `--proposals-dir`, `--source-root`,
`--lock-timeout`, `--search-cache`, `--ranker`, `--by`, `--disable-tool` and
`--trace`, with the matching `WIKI_STUDIO_*` variables. MCP roots advertised
by the client are never read.

The per-tool arguments and results are in `docs/mcp-adapter.md`. In brief:

- **`find`** returns `find --json`'s object; `max_pages` is 1..5, and
  `ranker` overrides the launch default for one call.
- **`propose`** records `source` and `backend` as `mcp`. It assigns a
  `page_id` to every create. Its default name is
  `mcp-<UTC yyyymmddThhmmssZ>-<8 hex>`.
- **`promote`** takes a name that must be one path component. It resolves
  the name under the proposals directory, passes
  `entry_point=PROMOTE_ENTRY_POINT_MCP` and never passes an escape hatch.
- **`lint`** passes `backend=None`, so no model is reached.
- **`info`** adds `adapter` to the contract keys.

**Receipt.** `promoter.entry_point` gains the value `mcp`
(`PROMOTE_ENTRY_POINT_MCP` beside `_API` and `_CLI`). The value is additive,
and `receipt_version` stays 1.

**Errors.** An `IngestError` subclass or a `ValueError` raised by a tool
becomes an error result `{error, exit_code, message}`, using `errors.py`'s
class-to-code table (`ValueError` is 1). Anything else becomes
`InternalError`, exit code 1, with the class name as its only message.
stdout carries protocol frames only; logs and warnings go to stderr.

**Actor.** The actor is fixed at launch by `--by` or `WIKI_STUDIO_ACTOR`
(`resolve_actor`) and is used for every `propose` and `promote`. The server
passes the launch `--by` value itself, or `None` when no flag was given.
`None` reads `WIKI_STUDIO_ACTOR`, which resolves to the same name with
source `env`. Tools take no `by`. As in 0.7.0, this is attribution, not
authentication.

**Auto-approval.** The `promote` tool honours the wiki's
`auto_approve_on_promote` policy (owner decision). There is no
`--allow-auto-approve` flag and no adapter override. When the policy
approves pages, the result lists them in `approved_paths`. A warning names
the policy and states that the pages were approved by policy as part of
this promotion, attributed to the server's actor. On such a wiki, an
agent's promote approves its own proposal; that is the host's configured
policy.

**`--disable-tool NAME`.** Removes a tool before registration. It can only
remove, never add, and an unknown name is a launch error (exit 2).
`--disable-tool promote` is propose-only mode.

**Trace.** `--trace PATH` appends one JSON line per request: `ts`,
`method`, `tool`, `protocol_version`, `client_name`, `client_version`,
`outcome` and `duration_ms`. It never records page content, question text,
edit content or paths. The file is append-only and must lie outside the
wiki; an unwritable path is a launch error. Without the flag, nothing is
written.

## Consequences

- `pip install wiki-studio` is unchanged and still has no runtime
  dependency.
- `pip install 'wiki-studio[mcp]'` brings in the SDK's full transitive tree.
- A new SDK minor can break the `mcp-latest` job. The response is to lower
  the ceiling, never to widen it.
- An MCP host gets the curation loop without a shell and without
  re-implementing the boundary. Approval stays with a person or with the
  wiki's own policy.
- The page schema, the patch-set format and the CLI exit codes do not
  change.
