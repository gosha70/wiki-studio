# Compatibility

This page lists the wiki-studio and memkernel pairs that are tested together.
It names the evidence for each pair and the capabilities each side needs. A
pair that is not listed here is not claimed as compatible.

## Tested pairs

| wiki-studio | memkernel | Evidence | Status |
|---|---|---|---|
| 0.7.0 | git ref `641a508a2289b2d20775e6d149a0bb47678d1621` (main at the merge of `release/0.5.0rc1`, 2026-10-26) | The `memkernel-compat` job in `.github/workflows/ci.yml`: it builds the wheel, installs it with memkernel at that ref into a fresh virtual environment and runs `tests/integration/test_memkernel_clean_install.py`. The `memkernel-loop` job runs the four Release B loop cases (`tests/integration/test_release_b_loop.py`) the same way; it is expected to fail until memkernel #48 is merged | **Tested** for the bridge path (export, re-export, import of creates and appends): `memkernel-compat` green on `main` at `6d7f886` (the merge of PR #47), CI run [40430238344](https://github.com/gosha70/wiki-studio/actions/runs/40430238344), job 121945851144, 2026-10-27; the job is blocking from then on. The Release B loop is **not** claimed: `memkernel-loop` fails on that run, as expected, until memkernel #48 is merged. |

The bridge-shaped tests (`tests/test_bridge_contract.py`) replay memkernel's
call sequence without importing memkernel. They run in every build. They are
evidence for wiki-studio's side only, not for a pair.

A row moves to "tested" only when a green run of the clean-install job is
named here with its CI run.

## MCP adapter

The `wiki-studio[mcp]` extra (`wiki-studio-mcp`, `docs/mcp-adapter.md`)
is tested against an MCP SDK version, a protocol version and, for the
release evidence, a host at a pinned version. The evidence is one of two
things:

- a green `mcp-min` or `mcp-latest` CI run of the conformance suite
  (`conformance/mcp/`), named by its run;
- a recorded host run under `conformance/runs/` whose `check-host-run`
  verdict passed.

| Adapter (wiki-studio) | `mcp` | Protocol version | Host and version | Evidence | Status |
|---|---|---|---|---|---|

No row is recorded yet. The CI rows are added from the first green
`mcp-min` and `mcp-latest` runs on `main`. The Claude Code row is added
from the recorded host run in the 0.8.0 evidence PR. Kiro is documented
but is not release-blocking. A combination with no green run or recorded
run is not listed as tested.

## Capabilities each side needs

`wiki-studio info --json` lists the capabilities of the installed build. A
host checks them before it writes.

| Capability | What it gives | Needed by memkernel's bridge for |
|---|---|---|
| `wiki-lock` | One OS lock beside the wiki serialises cooperating writers. | Concurrent exports and CLI promotes. |
| `receipts` | A receipt beside each proposal; a retry resolves from it and never re-applies. | Recovery without an outer rollback. |
| `base-revision` | An `update` carries the `sha256` it was drafted from; a stale one is refused. | Guarded updates of exported pages. |
| `root-manifest` | `.wiki-studio.json`: `wiki_id`, schema contract, fingerprint, policy. `api.init` scaffolds it. | The scaffold, and the compatibility check before a write. |
| `page-id` | An optional `page_id: pg-<32 hex>` key; `api.propose(..., assign_page_ids=True)` adds one to each create, and lint refuses a malformed or duplicated one. | One memory identity across a page rename, once the bridge opts in. |
| `attribution` | `by=` on `api.propose` and `api.promote` (and `WIKI_STUDIO_ACTOR`), recorded as `plan.json` `proposer` and receipt `actor`. Not authentication. | Naming the exporter in the audit trail. |

memkernel's own requirements of wiki-studio are recorded on memkernel's side.

## Re-creating a proposal written before 0.6.0

A proposal written before 0.6.0 may carry `update` edits without a revision
precondition (`base_sha256`). `promote` refuses such an update (exit 9). The
safe remedy is to re-create the proposal from the live page:

1. Run `wiki-studio read --json <path>` for each page the proposal updates.
   Note the `sha256` it prints.
2. Re-draft the page from the printed `content`.
3. Propose again. With `propose --from DIR`, write `DIR/.base.json` mapping
   each page path to its `sha256`. With `api.propose`, set each
   `PageEdit.base_sha256`.

`promote --allow-unguarded-updates` applies the old proposal as it is. It is a
compatibility mode with incomplete conflict protection: a stale draft can
overwrite a newer page.
