# The correction-loop demonstration

One scripted run of the governed loop between memkernel and wiki-studio: a
wrong decision is retained and exported as a draft, a curator corrects it
through a reviewed proposal carrying `corrects`, approves it, and the next
session imports the approved revision and answers with it while the old
memory is kept as superseded.

`demo.py` runs three processes on one persisted memkernel store and one wiki
under `--workdir`:

| Step | What it does |
|------|--------------|
| `session-1` | `api.init`; retains the wrong decision (a neutral first line names the topic, then the wrong rule); recalls it; exports it through the gate as one `status: draft` page. Prints the memory's `ref_id`, the page and the export's `submission_digest`. |
| `curator` | `wiki-studio read --json`; writes the corrected page into a draft directory outside the wiki (`status: stable`, `corrects: <memkernel_ref>`, the rule replaced in the title, the heading and the body); writes `.base.json`; runs `propose --from … --promote --by curator` and `approve … --by curator`; prints the receipt and the approval record. |
| `session-2` | Imports through memkernel's governed importer (the page imported, the wrong `ref_id` in `corrections`); recalls the question; prints the answer, the page, its `page_sha:` beside `approved_sha256`, the receipt's `submission_digest` and `committed_at`, and the approval record's `approver` and `timestamp`; shows the old record from `list_memories(include_superseded=True)` with `superseded_by`. |

Every step runs the Python calls memkernel's MCP tools make. No model backend
is on any path: the only model is memkernel's local embedding model.

## Running the demo

The environment needs memkernel 0.6.0, the built wiki-studio wheel, and the
`wiki-studio` console script beside the interpreter:

```bash
python demo.py --workdir /tmp/correction-loop
```

The orchestrator creates `--workdir` (it must be absent or empty), passes
memkernel's settings to each step through the environment, and stops at the
first failing step. Exit codes: 0 when every check passes; 1 when a check
fails, with one line naming it; 2 when the script cannot run (memkernel or
wiki-studio is not importable, the `wiki-studio` CLI is not beside the
interpreter, the embedding model could not be loaded, a bad argument, or a
non-empty `--workdir`). `--summary PATH` writes one JSON object with the
versions, the page, `page_sha`, `approved_sha256`, `submission_digest`,
`committed_at`, `approver`, `timestamp`, every check with its result, and the
UTC times at which the approval completed and the corrected recall returned.

## The recording protocol

`record.py` records one run, bound to the bytes it executed. It is run by CI
on every push (`.github/workflows/ci.yml`, job `demo-correction-loop`) and once
by hand for the committed run.

1. **Commit first.** The script, this recorder and this protocol are committed
   before any recorded run. The recorded run is an owner-run step in the
   evidence PR, after the commit that carries those bytes.
2. **Start from a clean tree.** `record.py` refuses (exit 2) unless
   `git status --porcelain` is empty, and records `HEAD`'s full commit SHA. It
   then works only from that commit: it archives the SHA (never the name
   `HEAD`), hashes the demo, the recorder and this protocol from the extracted
   tree, refuses if the running `record.py` differs from the committed one, and
   runs the demo and the end-state hash from that tree, so an edit or a commit
   during the run cannot change what executes or what the manifest names.
3. **Run once.** The recorder builds the wheel from that extracted commit in a
   temporary directory (`poetry build` there, so only committed bytes are
   built), downloads memkernel 0.6.0 (`pip download --no-deps
   --only-binary :all:`) and refuses unless its sha256 equals the one PyPI
   publishes for that file, installs both into a fresh virtual environment,
   and writes the environment's `pip freeze` to `environment.txt`. It then
   downloads the embedding model at the pinned revision, refuses any other
   snapshot, and runs the demo once. It never retries.
4. **A failed attempt is kept.** A refusal in the preflight (an existing
   `--out`, an unclean tree, no `poetry`) creates nothing and is not an attempt.
   The attempt starts when the run directory is created, right after the
   preflight. `manifest.json` is written at once with `outcome: running` and
   the current `stage` (`extract`, `build`, `download`, `install`, `embedding`,
   `demo`, `end-state`), rewritten at each stage, and ends as `outcome:
   completed` with the demo's exit code or `outcome: failed` with
   `failed_stage` and the error, for any exception, an interrupt included. A
   manifest still reading `outcome: running` means the process was killed in
   that stage. A failed run directory is committed as it is. A
   second attempt is a new directory: `--out` must not exist.
5. **Commit the run directory alone.** The run directory is committed under
   `examples/correction-loop/runs/<YYYY-MM-DD>-wiki-studio-<version>-memkernel-0.6.0/`
   in its own commit after the run, and is never edited afterwards. The commit
   order is: script, recorder and protocol; then the run.

## The run directory

```
<run>/
  transcript.txt     # stdout and stderr of the one demo run, in order
  environment.txt    # pip freeze of the fresh virtual environment
  end-state/         # knowledge/wiki/ and doc_internal/proposals/ as the run left them
  manifest.json
```

`end-state/` holds the wiki tree (pages, `index.md`, `log.md`, the whole
`.audit/` tree) and the proposals directory with its `.applied/` receipts. It
never holds the lock, the search cache or memkernel's store.

`manifest.json` carries `git_commit`, `git_clean`, `demo_sha256`,
`record_sha256`, `protocol_sha256`, `wiki_studio_version`, `wheel_file`,
`wheel_sha256`, `memkernel_version`, `memkernel_file`, `memkernel_sha256`,
`memkernel_pypi_sha256`, `embedding_model`, `embedding_revision`,
`python_version`, `platform`, `started_at`, `finished_at`, `exit_code`, the
demo's `summary`, `end_state_sha256`, `wall_time_seconds`
(`install_to_first_approved_revision`, `install_to_corrected_recall`) and
`wall_time_label`.

## The model

The recorded run uses the real local embedding model,
`sentence-transformers/all-MiniLM-L6-v2`, at revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. The recorder downloads that
snapshot, refuses any other revision, and runs the demo with
`MEMKERNEL_EMBEDDING_MODEL` pointing at the snapshot and `HF_HUB_OFFLINE=1`.
The CI job caches the Hugging Face cache keyed on the revision.

## Wall times

`wall_time_seconds` is measured from the start of the virtual-environment
install to the approval and to the corrected recall. It is machine time on a
scripted path, not a measure of human adoption (D15).

## What the end-state hash binds

`end_state_sha256` is `python -m conformance.mcp.run tree-hash` over
`end-state/`. It binds the committed files to the manifest: a hand-edited page,
receipt or approval record no longer hashes to the value the manifest records.
It does not reproduce across runs, because dates, page ids and memory ids
differ between runs; the hash is evidence about one run, not a checksum to
re-derive.

## CI

`demo-correction-loop` runs `record.py --out "$RUNNER_TEMP/demo-run"` on a
fresh checkout (a clean tree), then prints `transcript.txt` and
`manifest.json`. Its exit code is the recorder's, so a failed check fails the
job.
