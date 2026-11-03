# Quickstart: memkernel with a governed wiki

One path from an empty project to a wiki that memkernel writes into through
wiki-studio's gate, a curator correcting a wrong decision through a reviewed
proposal, and the next session importing only the approved revision. No model
backend is anywhere on the path: memkernel's local embedding model is the only
model that runs.

Every fenced block below whose info string starts `bash run` or `python run`
is executed in CI (`.github/workflows/ci.yml`, job `quickstart-memkernel`) by
`tests/integration/test_quickstart_memkernel.py`: the blocks run in page order
in one fresh temporary project directory, each in its own process. A block
marked "not executed in CI" is shown only.

memkernel's tools are MCP tools, not shell commands. Each executed Python block
below is the call memkernel's tool makes, and the prose names the tool beside
it (the loop test drives the same calls the same way).

## Install

Python 3.11–3.13. memkernel's `wiki` extra installs the wiki-studio floor the
gate needs; wiki-studio's `mcp` extra adds the MCP server `wiki-studio-mcp`.

```bash
pip install 'memkernel[wiki]==0.6.0' 'wiki-studio[mcp]==0.8.1'
python -c "import memkernel.wiki.sync, wiki_studio.api"
```

Not executed in CI: the `quickstart-memkernel` job installs the built wheel and
`memkernel==0.6.0` from PyPI into a fresh virtual environment. memkernel loads
`all-MiniLM-L6-v2` (about 90 MB) on the first `build_service()`; the job
downloads the model once at revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41` and runs the page with
`MEMKERNEL_EMBEDDING_MODEL` pointing at that snapshot and `HF_HUB_OFFLINE=1`.

## 1. Register both MCP servers

Not executed in CI: one `.mcp.json` in the project root registers memkernel's
server entry as memkernel's README gives it, with the wiki settings this
quickstart writes, and wiki-studio's server in propose-only mode. Promotion
and approval stay with the curator's CLI.

```json
{
  "mcpServers": {
    "memkernel": {
      "command": "/Users/you/.local/bin/memkernel",
      "args": [],
      "env": {
        "MEMKERNEL_PROJECT_ID": "wiki-studio-composition-quickstart",
        "MEMKERNEL_PROJECT_ROOT": "/path/to/project",
        "MEMKERNEL_CHROMA_PERSIST_PATH": "/path/to/project/.memkernel/chroma",
        "MEMKERNEL_WIKI_DIR": "/path/to/project/knowledge/wiki",
        "MEMKERNEL_WIKI_PROPOSALS_DIR": "/path/to/project/doc_internal/proposals"
      }
    },
    "wiki-studio": {
      "command": "wiki-studio-mcp",
      "args": ["--root", "/path/to/project", "--disable-tool", "promote"]
    }
  }
}
```

Use an absolute `command` for memkernel: a host does not necessarily see the
`PATH` your shell profile sets.

Not executed in CI: Kiro reads the same two entries from
`.kiro/settings/mcp.json`; memkernel's
[`templates/kiro/`](https://github.com/gosha70/memkernel/tree/v0.6.0/templates/kiro)
has its form, and wiki-studio's is in
[`docs/mcp-adapter.md`](mcp-adapter.md#kiro).

## 2. Create the project and its settings

The `.gitignore` below is the commit policy's executable half: only the wiki
lock and the search cache are ignored beside the wiki, and memkernel's store
and `.env` stay out of git as memkernel's own local files.

```bash run
git init -q
cat > .gitignore <<'EOF'
.wiki.wiki-studio.*
.memkernel/
.env
EOF
cat > .env <<EOF
MEMKERNEL_PROJECT_ROOT="$PWD"
MEMKERNEL_PROJECT_ID="wiki-studio-composition-quickstart"
MEMKERNEL_CHROMA_PERSIST_PATH="$PWD/.memkernel/chroma"
MEMKERNEL_WIKI_DIR="$PWD/knowledge/wiki"
MEMKERNEL_WIKI_PROPOSALS_DIR="$PWD/doc_internal/proposals"
EOF
```

memkernel reads `.env` from the working directory, and `MEMKERNEL_PROJECT_ROOT`
is set explicitly because its default is the current directory. Pointing
`MEMKERNEL_WIKI_PROPOSALS_DIR` at wiki-studio's default proposals directory
means both tools archive into one `doc_internal/proposals/.applied/`, where the
export's receipt lives.

## 3. Initialise the wiki

```bash run
wiki-studio init
```

`init` creates `knowledge/wiki/index.md`, `knowledge/wiki/log.md` and the root
manifest `knowledge/wiki/.wiki-studio.json`, which carries the review policy.
The exporter calls `api.init` too, but only when it has pages to write; running
it once here makes the scaffold explicit.

## 4. Session 1: retain the wrong decision

memkernel's `retain` tool stores a decision; `recall` searches the store. The
memory's first line names the topic and the second line carries the wrong rule:
the exporter takes a page's title from the memory's first line, so a wrong rule
on that line would be the page's title and path as well.

```python run contains=wrong-rule-current
from memkernel.core.models import MemoryType
from memkernel.factory import build_service

service = build_service()
wrong_ref = service.retain(
    "Deploy window\n\nDeploy on Fridays after 17:00 UTC.",
    MemoryType.DECISION,
)
results = service.recall("When may we deploy?")
current = [service.get(result.ref_id, touch=False) for result in results]
if not any(memory is not None and "Deploy on Fridays after 17:00 UTC." in memory.content for memory in current):
    raise SystemExit("session 1: the wrong rule is not a current answer")
print("wrong-rule-current")
print(f"ref_id: {wrong_ref}")
```

The wrong rule is what the store answers with, and it is the only current
memory.

## 5. Export a draft through the gate

memkernel's `wiki_export` tool constructs `WikiExporter` with the settings'
wiki directory, project root and proposals directory. An explicit proposals
directory, as in `.env`, asks for the gate: the page is proposed with its index
and log lines and promoted under wiki-studio's lock.

```python run contains=export-gated
from pathlib import Path

from memkernel.config import MemKernelSettings
from memkernel.factory import build_service
from memkernel.wiki.sync import WikiExporter

settings = MemKernelSettings()
service = build_service(settings)
proposals = settings.wiki_proposals_dir
report = WikiExporter(
    service,
    Path(settings.wiki_dir),
    project_root=Path(settings.project_root),
    proposals_dir=Path(proposals) if proposals else None,
).export()
if not report.gated or report.gate_error is not None:
    raise SystemExit(f"the export did not pass the gate: {report.gate_error}")
if len(report.written) != 1:
    raise SystemExit(f"expected one draft page, wrote {report.written}")
print("export-gated")
print(f"page: {report.written[0]}")
print(f"submission_digest: {report.submission_digest}")
```

The page lands under `knowledge/wiki/decisions/deploy-window.md` with
`status: draft`, and the report carries the receipt's `submission_digest`. A
draft is not importable: the curator reviews it first.

## 6. The curator reads the draft

```bash run
wiki-studio read --json decisions/deploy-window.md | tee read.json
```

The JSON carries the page's `content` and the `sha256` of exactly those bytes.
The next step records that sha as the update's base revision.

## 7. The curator writes the correction

The draft replaces the wrong rule in the title, the H1 heading and the body,
because the imported memory is the page's title plus its body. It sets
`status: stable` (approval refuses `status: draft`) and names the wrong memory
in `corrects:`; memkernel keeps that key byte for byte until the import reads
it. `.base.json` beside the draft is the guarded update: promote applies the
replacement only while the page still has that revision.

```python run contains=correction-drafted
import json
from pathlib import Path

read = json.loads(Path("read.json").read_text(encoding="utf-8"))
content = read["content"]
wrong = "Deploy on Fridays after 17:00 UTC."
right = "Deploy on Tuesdays before noon; never on Fridays."
if wrong not in content:
    raise SystemExit("the exported draft does not carry the wrong rule")
ref_line = next(line for line in content.splitlines() if line.startswith("memkernel_ref:"))
memkernel_ref = ref_line.split(":", 1)[1].strip()
content = content.replace("status: draft", f"status: stable\ncorrects: {memkernel_ref}", 1)
content = content.replace("title: Deploy window", f"title: {right}", 1)
content = content.replace("# Deploy window", f"# {right}", 1)
content = content.replace("Deploy window", right).replace(wrong, right)
if "Deploy window" in content or wrong in content:
    raise SystemExit("the correction left the old decision in the page")
draft = Path("drafts/correction/decisions/deploy-window.md")
draft.parent.mkdir(parents=True, exist_ok=True)
draft.write_text(content, encoding="utf-8")
Path("drafts/correction/.base.json").write_text(
    json.dumps({"decisions/deploy-window.md": read["sha256"]}), encoding="utf-8"
)
print("correction-drafted")
print(f"corrects: {memkernel_ref}")
```

## 8. The curator promotes, lints and approves

```bash run
wiki-studio propose --from drafts/correction --promote --by curator
```

```bash run
wiki-studio lint
```

```bash run
wiki-studio approve decisions/deploy-window.md --by curator
```

`propose --from` writes the patch-set under `doc_internal/proposals/`, and
`--promote` applies it under the lock; the receipt is archived under
`doc_internal/proposals/.applied/`. `lint` is the structural gate, and
`approve` writes one immutable record under `knowledge/wiki/.audit/approvals/`
bound to the page's live sha256.

## 9. The next session imports the approved revision

memkernel's `wiki_import` tool constructs `WikiImporter` with the same wiki
directory and project root. With wiki-studio installed it is governed: only
pages whose review state is `approved`, and whose bytes are still the approved
revision, are imported. The approved page's `corrects:` key supersedes the
memory it names.

```python run contains=right-rule-current
from pathlib import Path

from memkernel.config import MemKernelSettings
from memkernel.factory import build_service
from memkernel.wiki.sync import WikiImporter

page = "decisions/deploy-window.md"
settings = MemKernelSettings()
service = build_service(settings)
report = WikiImporter(service, Path(settings.wiki_dir), project_root=Path(settings.project_root)).import_pages()
if not report.governed:
    raise SystemExit(f"the import is not governed: {report.import_error}")
if page not in report.imported:
    raise SystemExit(f"the approved page was not imported: {report.not_approved} {report.skipped}")
page_text = (Path(settings.wiki_dir) / page).read_text(encoding="utf-8")
ref_line = next(line for line in page_text.splitlines() if line.startswith("memkernel_ref:"))
wrong_ref = ref_line.split(":", 1)[1].strip()
if {"page": page, "ref_id": wrong_ref} not in report.corrections:
    raise SystemExit(f"corrects did not supersede the wrong memory: {report.corrections} {report.unresolved}")
wrong = "Deploy on Fridays after 17:00 UTC."
right = "Deploy on Tuesdays before noon; never on Fridays."
results = service.recall("When may we deploy?")
current = [service.get(result.ref_id, touch=False) for result in results]
if not any(memory is not None and right in memory.content for memory in current):
    raise SystemExit("the right answer is not a current memory")
if any(memory is not None and wrong in memory.content for memory in current):
    raise SystemExit("the wrong rule is still a current answer")
if any(wrong in memory.content for memory in service.list_memories()):
    raise SystemExit("a current memory still carries the wrong rule")
print("right-rule-current")
print(f"corrected: {page}")
```

The wrong memory is kept as a record and marked `superseded_by`; a plain
`recall` and `list_memories()` do not return it.

## 10. The commit policy, path by path

Everything the quickstart creates is either committed or ignored for a stated
reason. Commit the whole tree the executed setup writes:

| Path | Commit? | Why |
|------|---------|-----|
| `knowledge/wiki/.wiki-studio.json` | yes | The root manifest carries the wiki's identity and review policy. |
| `knowledge/wiki/decisions/deploy-window.md` | yes | The curated page is the knowledge. |
| `knowledge/wiki/index.md`, `knowledge/wiki/log.md` | yes | The wiki's entry points; the export appended to both. |
| `knowledge/wiki/.audit/` (the ingest log, `proposals/`, `approvals/`) | yes, the whole tree | The governed import reads the approval records; a clone without them reads every page `unapproved`. The audit tree is the promotion history. |
| `doc_internal/proposals/` including `.applied/` | yes | The receipt exists only under `.applied/<name>/receipt.json`; the `.audit/proposals/<name>/` copy holds the plan, the preview and the curator delta, not the receipt. |
| `knowledge/.wiki.wiki-studio.lock` | no | The OS advisory lock exists only while a writer runs. |
| `knowledge/.wiki.wiki-studio.search.sqlite` | no | The `fts5` search cache is derived data, refreshed on every `fts5` call. |
| `.memkernel/` | no | memkernel's Chroma store is machine-local; memkernel's README says to ignore it. |
| `.env` | no | It holds absolute machine paths. |

The lock and the cache share one pattern, `.wiki.wiki-studio.*`, which is what
the setup block writes into `.gitignore`. `.memkernel/` and `.env` are
memkernel's own local files, outside wiki-studio's commit policy.

## 11. Hand off the committed wiki

The working files (`drafts/` and `read.json`) are removed before the commit:
they produced the proposal and are not part of the result. Then the project is
committed and cloned into a sibling directory.

```bash run
rm -rf drafts read.json
git add -A
git -c user.name=quickstart -c user.email=quickstart@example.invalid commit -q -m "quickstart: the reviewed wiki"
git clone -q . ../teammate
```

The clone has its own `.env` and a fresh memkernel store. Its check block exits
non-zero, naming the check, if anything the original kept out of git is found
there, if any page the original approved does not read `approved`, if the
import differs from those pages, if a `page_sha:` tag differs from the page's
`approved_sha256`, or if the wrong rule is a current answer.

```python run contains=handoff-ok
import os
from pathlib import Path

from memkernel.config import MemKernelSettings
from memkernel.factory import build_service
from memkernel.wiki.sync import WikiImporter
from wiki_studio import api
from wiki_studio.paths import WikiPaths


def check(condition: bool, name: str) -> None:
    if not condition:
        raise SystemExit(f"handoff check failed: {name}")


original = Path.cwd()
clone = (original.parent / "teammate").resolve()
check(not (clone / ".env").exists(), "the original .env is not in the clone")
check(not (clone / ".memkernel").exists(), "memkernel's store is not in the clone")
check(not (clone / "knowledge" / ".wiki.wiki-studio.lock").exists(), "the wiki lock is not in the clone")
check(not (clone / "knowledge" / ".wiki.wiki-studio.search.sqlite").exists(), "the search cache is not in the clone")
approved = [state for state in api.review_state(WikiPaths.for_root(original)) if state.state == "approved"]
check(bool(approved), "the original has an approved page")

page_text = (clone / "knowledge" / "wiki" / "decisions" / "deploy-window.md").read_text(encoding="utf-8")
ref_line = next(line for line in page_text.splitlines() if line.startswith("memkernel_ref:"))
wrong_ref = ref_line.split(":", 1)[1].strip()

(clone / ".env").write_text(
    "\n".join(
        [
            f"MEMKERNEL_PROJECT_ROOT={clone}",
            "MEMKERNEL_PROJECT_ID=wiki-studio-composition-quickstart",
            f"MEMKERNEL_CHROMA_PERSIST_PATH={clone}/.memkernel/chroma",
            f"MEMKERNEL_WIKI_DIR={clone}/knowledge/wiki",
            f"MEMKERNEL_WIKI_PROPOSALS_DIR={clone}/doc_internal/proposals",
            "",
        ]
    ),
    encoding="utf-8",
)
os.chdir(clone)
settings = MemKernelSettings()
service = build_service(settings)
report = WikiImporter(service, Path(settings.wiki_dir), project_root=Path(settings.project_root)).import_pages()
check(report.governed, "the clone's import is governed")
check(
    sorted(report.imported) == sorted(state.path for state in approved),
    "the clone imports exactly the approved pages",
)
states = {state.path: state for state in api.review_state(WikiPaths.for_root(clone))}
memories = {memory.source: memory for memory in service.list_memories()}
for path in sorted(states):
    state = states[path]
    check(state.state == "approved", f"{path} reads approved in the clone")
    memory = memories.get(path)
    check(memory is not None, f"{path} has a current memory")
    check(f"page_sha:{state.approved_sha256}" in memory.tags, f"{path} carries its approved page_sha")
wrong = "Deploy on Fridays after 17:00 UTC."
right = "Deploy on Tuesdays before noon; never on Fridays."
results = service.recall("When may we deploy?")
current = [service.get(result.ref_id, touch=False) for result in results]
check(any(memory is not None and right in memory.content for memory in current), "recall returns the right answer")
check(
    not any(memory is not None and wrong in memory.content for memory in current),
    "no current answer has the wrong rule",
)
check(not any(wrong in memory.content for memory in service.list_memories()), "the store has no current wrong rule")
print("handoff-ok: the clone imports exactly the approved revisions")
```

The clone's `corrects:` reference names a memory that was never in its fresh
store, so it is reported as unresolved there and supersedes nothing; the wrong
rule cannot be a current answer because it was never imported.

## What you have

memkernel retained a wrong decision, exported it through wiki-studio's gate,
and a curator corrected it through a reviewed proposal carrying `corrects:` and
approved it. The next session imported only the approved revision, and a clone
of the committed tree imports exactly the approved pages with their approval
records and receipts. The wiki itself — pages, review state and the audit
tree — is described in [`knowledge-contract.md`](knowledge-contract.md), and
the model-free path with no memkernel is in
[`quickstart.md`](quickstart.md).
