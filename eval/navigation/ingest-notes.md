# One-time ingest record

The 0.3.0 spec was approved in `7f6290f`. Questions were preregistered in
`c99be65` (questions plus checksum only), then pinned by `b42b5b7` (manifest
commit hash only). The manifest records both the question commit and the
second, pre-ingest commit. The question, corpus and stop-list bytes remain
unchanged.

The run used wiki-studio 0.2.0 and Claude Code 2.1.300, with the existing
`opus` model alias explicitly configured through `ANTHROPIC_MODEL` for every
invocation. The shipped backend's 120-second timeout was unchanged. Each of
the ten documents was ingested once in manifest order. The one returned
proposal was promoted once. Nothing was manually repaired or rerun.

## Outcomes

- ADR-009 promoted: one decision page, with index and log appends.
- Eight sources failed semantic validation because model-generated paths
  included an extra `wiki/` prefix. No proposal directory was written for
  these failures. The final two also referenced a nonexistent update target
  under `wiki/wiki/decisions/`.
- README timed out after 120 seconds. It was not retried: the adapter did not
  establish whether any model output had already been received.
- Structural lint passed: three content pages, zero violations, audit format
  clean. This is a format check, not evidence that the run was uncontaminated.

Per-document stdout/stderr is preserved under `ingest-logs/`; the accepted
proposal and its snapshot are under `proposals/.applied/`, with the audit
copy under `wiki/.audit/`. The manifest contains every source's result and
wall time. Token counts were not exposed by the text-mode adapter.

## Validity finding: inherited Claude hooks

Final inspection found nine additional `backend=test` records in
`wiki/.audit/ingest-log.md`, plus test queries in
`doc_internal/wiki-query-log.jsonl`. The user's Claude configuration enables
`~/.claude/hooks/verify-on-stop.sh`. That hook auto-detects this Poetry
repository and runs `poetry run pytest --tb=short -q` after Claude responds.
Those child tests inherited the explicit `WIKI_STUDIO_ROOT`,
`WIKI_STUDIO_WIKI_DIR` and `WIKI_STUDIO_PROPOSALS_DIR` from the ingest process.
The observed audit timestamps align with those per-document completions.

All unexpected records are preserved, not deleted. The content of the
accepted decision page matches its archived preview, and index/log appends
match the proposal. Per-document wall time includes lifecycle-hook work,
including the test suite; it must not be presented as pure inference cost.

The manifest marks validity `requires_review`. Do not publish this run as an
uncontaminated benchmark. Gold assignment and metric implementation have not
started. A future run with isolated backend hooks/settings would require an
explicitly revised protocol and a separately identified fixture; this run
must not be silently regenerated to improve its outcome.
