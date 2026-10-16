# A `wiki_studio` arm for memkernel's lifecycle suite

Layer 2 of [issue #10](https://github.com/gosha70/wiki-studio/issues/10): agent-level
evidence that consulting the wiki helps an agent, measured in an execution-graded
harness next to a files-plus-grep control. The harness is memkernel's
`eval/lifecycle-suite/` (memkernel `main`, read at d189f2b on 2026-10-16). This
directory holds a ready arm for it; adopting and running it happens in memkernel's
repository, by its owner.

## Files to copy

| This repository | memkernel |
|---|---|
| `docs/agent-arm/config.frozen.json` | `eval/lifecycle-suite/arms/wiki_studio/config.frozen.json` |
| `docs/agent-arm/instruction.md` | `eval/lifecycle-suite/arms/wiki_studio/instruction.md` |

The config uses the same keys and values as the other non-memkernel arms: the six
base tools (the CLI is used through Bash), no MCP server, no hooks, nothing
persisted. The instruction is 1,847 bytes, within 5 percent of memkernel's own
block (1,832), the same rule its `placebo` arm follows, so prompt length is not a
difference between the two treated arms.

## What the arm does

- **Session start:** `wiki-studio info`, then `wiki-studio find "<task>"`, then read
  `knowledge/wiki/index.md` and the listed pages. `find` is the querier's page
  selection without a model; it writes nothing.
- **Recording:** write a draft directory laid out like the wiki (a page, one index
  line, one log line), then `wiki-studio propose --from <draft> --promote`, which
  validates the page and lands it through the lint-gated promote, or refuses it
  with the reason. `wiki-studio init` first when `log.md` is missing.
- **Never:** `wiki-studio ingest` or `wiki-studio query`. Both start a second
  model inside the session, whose tokens the receipts would not see.

The workspace is not a git checkout, so wiki-studio's root is the session's
working directory: the wiki is `knowledge/wiki/` (the task's shared artifact) and
proposals land in `doc_internal/proposals/`, which the runner does not carry over;
only the promoted wiki (with its `.audit/` record) reaches the next session.
Checked with the installed 0.4.0 wheel on the lc-wiki fixture shape: session 0
`init` created the missing log, `propose --from … --promote` landed the page,
`lint` was clean; session 1, with only `knowledge/wiki/` copied, `find` returned
the page for a differently worded question.

All three verbs exist from wiki-studio **0.4.0**; pin `wiki-studio==0.4.0` on the run
machine (for example `pipx install wiki-studio==0.4.0`, so it is on the `PATH` the
runner passes through).

## Which tasks it can attempt

| Group | Meaningful for this arm | Why |
|---|---|---|
| `lc-wiki` (5) | yes, the primary target | Session 0 records a decision in `knowledge/wiki/`; session 1 runs in a second namespace and sees only that wiki, which the runner copies for every arm. This is exactly the claim #10 makes. The fixtures have `index.md` but no `log.md`; the instruction's `init` creates it. |
| `lc-compact` (5) | can attempt, measures nothing wiki-specific | One session; no hooks declared. |
| `lc-retain`, `lc-reval` (10) | no | With all persist flags false, what the arm wrote is gone in session n+1, so it behaves like `protocol`. Running it there is a sanity check, not evidence. |

## Changes needed in memkernel

The suite is fixed at six arms by its spec (FR-011 forbids arm discovery, FR-012
names the six) and in code. Adding the arm needs, in memkernel:

1. A spec amendment: seven arms, `wiki_studio` a second treated arm compared with
   the same primary comparators (`claude_md`, `fs_grep`) on `lc-wiki`.
2. `runner.py`: `ARM_NAMES` (also the argparse choices and the demo loop).
3. `receipt.schema.json`: the `arm` enum.
4. `report.py`: the arm description prose, and the treated-arm handling
   (`TREATMENT = "memkernel"` is hard-coded).
5. Tests: `EXPECTED` in `test_lifecycle_arms.py`, the arm list in
   `test_lifecycle_records.py`, and the demo expectations.
6. A diagnostic worth adding: count Bash calls that run `wiki-studio ingest` or
   `wiki-studio query` per session, so a breach of the "never" rule is visible in
   the receipts rather than hidden in a nested model's cost.

When to add it is memkernel's decision: before its 0.5 code freeze (the arm then
enters the preregistered run) or in the next version after 0.5's run (the 0.5
design stays as preregistered). After a freeze, `check_freeze.py` refuses changes
to arms and tasks.

## Verified in this repository

`tests/test_agent_verbs.py::TestLcWikiShape` follows the instruction's flow on the
lc-wiki fixture shape: an index without a log, `init`, a decision page with an
index and a log line proposed and promoted from a draft directory, then in a
fresh step `find` returns the page for a question about it and `lint` passes.
