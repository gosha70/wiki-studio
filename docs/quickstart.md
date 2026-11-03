# Quickstart: the standalone wiki loop

One path from an empty directory to a reviewed, approved wiki page and a
guarded update, with no model backend anywhere. A curator writes the page,
a reviewer approves the bytes, and a later change lands only while the page
still has the revision the curator read.

Every fenced block below whose info string starts `bash run` or `python run`
is executed in CI (`.github/workflows/ci.yml`, job `quickstart`) by
`tests/test_quickstart.py`: the blocks run in page order in one fresh
temporary project directory. A block marked "not executed in CI" is shown
only. `bash server-cmd` marks the server launch line the MCP conformance
suite runs.

## Install

Python 3.11–3.13. The base install has no runtime dependencies; the `mcp`
extra adds the MCP server `wiki-studio-mcp`.

```bash
pip install 'wiki-studio[mcp]'
wiki-studio --version
```

Not executed in CI: the `quickstart` job installs the built wheel with the
same extra in a fresh virtual environment and runs this page from it.

## 1. Initialise the wiki

```bash run
wiki-studio init
```

`init` creates `knowledge/wiki/index.md`, `knowledge/wiki/log.md` and the
root manifest `knowledge/wiki/.wiki-studio.json`. The manifest carries the
review policy; without it every page reads `unapproved` and `approve`
refuses to run.

## 2. Write a draft outside the wiki

`propose --from` takes a directory laid out like the wiki and refuses one
that overlaps it, so the draft lives in `drafts/`, not in `knowledge/wiki/`.
`index.md` and `log.md` in that directory hold the lines to append, one per
line.

```bash run
mkdir -p drafts/deploy-window/decisions
cat > drafts/deploy-window/decisions/deploy-window.md <<'EOF'
---
page_type: decision
slug: deploy-window
title: Deploy window
status: stable
last_reviewed: 2026-11-03
sources:
  - url: "https://example.com/deploy-window"
    retrieved: 2026-11-03
---

# Deploy window

## Decision

Deploy on Tuesday between 10:00 and 12:00 UTC.

## Context

Production traffic is lowest on Tuesday morning.

## Alternatives considered

Wednesday morning, which overlaps the weekly backup.

## Consequences

The release owner must be present on Tuesday morning.
EOF
printf '%s\n' '- [Deploy window](decisions/deploy-window.md) — when a release may ship.' > drafts/deploy-window/index.md
printf '%s\n' '- 2026-11-03 — recorded the deploy-window decision.' > drafts/deploy-window/log.md
```

`status: stable` is what a curator writes. `approve` refuses
`status: draft`, and approval is recorded separately, never by frontmatter.

## 3. Propose and promote

```bash run
wiki-studio propose --from drafts/deploy-window --promote --by you
```

`propose` writes a patch-set under `doc_internal/proposals/` and `--promote`
lands it under the wiki lock. The page is now
`knowledge/wiki/decisions/deploy-window.md`, and the proposal's
`receipt.json` is archived under `doc_internal/proposals/.applied/`.

## 4. Read the review state

`review_state` has no CLI verb. It is a Python call, and the MCP server
exposes the same call as its `review_state` tool. The page has no approval
record yet:

```python run contains=state:unapproved
from wiki_studio import api
from wiki_studio.paths import WikiPaths

state = api.review_state(WikiPaths.resolve(), pages=["decisions/deploy-window.md"])[0]
print(f"state:{state.state}")
print(f"reason: {state.reason}")
print(f"live_sha256: {state.live_sha256}")
print(f"approved_sha256: {state.approved_sha256}")
```

## 5. Approve the live revision

```bash run
wiki-studio approve decisions/deploy-window.md --by you
```

`approve` writes one immutable record under
`knowledge/wiki/.audit/approvals/`, bound to the page's live sha256. The
same block now reads `approved`:

```python run contains=state:approved
from wiki_studio import api
from wiki_studio.paths import WikiPaths

state = api.review_state(WikiPaths.resolve(), pages=["decisions/deploy-window.md"])[0]
print(f"state:{state.state}")
print(f"reason: {state.reason}")
print(f"live_sha256: {state.live_sha256}")
print(f"approved_sha256: {state.approved_sha256}")
```

## 6. Find the page a question needs

`find` is model-free: it reads `index.md` and selects the linked pages the
question shares words with, under a byte budget.

```bash run
wiki-studio find "when may we deploy?"
```

## 7. Read the bytes you will replace

```bash run
wiki-studio read --json decisions/deploy-window.md | tee read.json
```

The JSON carries the page's `content` and the `sha256` of the bytes read.
The next step records that sha as the update's base revision.

## 8. Land a guarded update

The draft is made from the content `read --json` printed; the base revision
goes in `.base.json` beside it.

```bash run
mkdir -p drafts/update/decisions
python - <<'PY'
import json
from pathlib import Path

read = json.loads(Path("read.json").read_text(encoding="utf-8"))
old = "Deploy on Tuesday between 10:00 and 12:00 UTC."
new = "Deploy on Wednesday between 09:00 and 11:00 UTC."
if old not in read["content"]:
    raise SystemExit("the page does not carry the sentence this draft replaces")
draft = Path("drafts/update/decisions/deploy-window.md")
draft.parent.mkdir(parents=True, exist_ok=True)
draft.write_text(read["content"].replace(old, new), encoding="utf-8")
Path("drafts/update/.base.json").write_text(
    json.dumps({"decisions/deploy-window.md": read["sha256"]}), encoding="utf-8"
)
PY
wiki-studio propose --from drafts/update --promote --by you
```

`promote` applies the replacement because the live page still has the base
revision. The previous approval now covers the old bytes, not the live page.

```bash run exit=9
wiki-studio propose --from drafts/update --promote --by you
```

The same draft proposed again is refused at promote with exit 9: the base
revision is stale. The wiki is unchanged.

## 9. Check the wiki

```bash run
wiki-studio lint
```

```bash run
wiki-studio findings
```

`lint` is the structural gate. `findings` reports what needs a curator's
attention without a model; after the update it reports the approval as
stale (`approval-stale`), and it still exits 0 because it is a report, not
a gate.

## The MCP server

The server exposes the same loop over MCP. This exact launch line is what
the conformance suite runs (its `{root}` placeholder takes the place of
`$PWD` in a temporary project):

```bash server-cmd
wiki-studio-mcp --root "$PWD"
```

The actor is named through `WIKI_STUDIO_ACTOR`. A `--by` flag would beat
the variable, and the conformance suite sets its actor through the
variable, so the launch line names no actor.

The host steps below are not executed in CI: they configure a host and
need a live agent session. The recorded Claude Code host run in
[`conformance/runs/2026-10-29-claude-code-2.1.312/`](../conformance/runs/2026-10-29-claude-code-2.1.312/)
is the evidence for the Claude Code path.

Not executed in CI: register the server in Claude Code.

```bash
claude mcp add --env WIKI_STUDIO_ACTOR=you wiki-studio -- wiki-studio-mcp --root "$PWD"
```

Not executed in CI: propose-only mode for a host that drafts but leaves
promotion and approval to the curator.

```bash
wiki-studio-mcp --root "$PWD" --disable-tool promote
```

Not executed in CI: the same server in a project's `.mcp.json`.

```json
{
  "mcpServers": {
    "wiki-studio": {
      "command": "wiki-studio-mcp",
      "args": ["--root", "/path/to/project"],
      "env": {"WIKI_STUDIO_ACTOR": "you"}
    }
  }
}
```

Not executed in CI: Kiro reads the same server entry from
`.kiro/settings/mcp.json`; the settings form is in
[`docs/mcp-adapter.md`](mcp-adapter.md#kiro), beside the recorded Claude
Code host run above.

Not executed in CI: `ingest` needs a model backend, and nothing on this
page does.

```bash
wiki-studio ingest sources/note.md --backend claude
```

`ingest` is the backend-driven path. This quickstart stays model-free:
pages are written by hand (or by an agent) and land through
`propose --from` and `approve`.

## What you have

A governed wiki with a reviewed page, an approval bound to its revision, a
recorded base revision for the replacement, and a stale update refused. The
workspace contract behind these commands is in
[`docs/knowledge-contract.md`](knowledge-contract.md).
