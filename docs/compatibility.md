# Compatibility

This page lists the wiki-studio and memkernel pairs that are tested together.
It names the evidence for each pair and the capabilities each side needs. A
pair that is not listed here is not claimed as compatible.

## Tested pairs

| wiki-studio | memkernel | Evidence | Status |
|---|---|---|---|
| 0.7.0 (unreleased, `feature/wiki-studio-0-7-0`) | git ref `641a508a2289b2d20775e6d149a0bb47678d1621` (main at the merge of `release/0.5.0rc1`, 2026-10-26) | The `memkernel-compat` job in `.github/workflows/ci.yml`: it builds the wheel, installs it with memkernel at that ref into a fresh virtual environment and runs `tests/integration/` | Not yet claimed. The job is non-blocking and no green run on main is recorded yet. |

The bridge-shaped tests (`tests/test_bridge_contract.py`) replay memkernel's
call sequence without importing memkernel. They run in every build. They are
evidence for wiki-studio's side only, not for a pair.

A row moves to "tested" only when a green run of the clean-install job is
named here with its CI run.

## Capabilities each side needs

`wiki-studio info --json` lists the capabilities of the installed build. A
host checks them before it writes.

| Capability | What it gives | Needed by memkernel's bridge for |
|---|---|---|
| `wiki-lock` | One OS lock beside the wiki serialises cooperating writers. | Concurrent exports and CLI promotes. |
| `receipts` | A receipt beside each proposal; a retry resolves from it and never re-applies. | Recovery without an outer rollback. |
| `base-revision` | An `update` carries the `sha256` it was drafted from; a stale one is refused. | Guarded updates of exported pages. |
| `root-manifest` | `.wiki-studio.json`: `wiki_id`, schema contract, fingerprint, policy. `api.init` scaffolds it. | The scaffold, and the compatibility check before a write. |

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
