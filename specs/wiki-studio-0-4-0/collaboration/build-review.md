---
feature_id: wiki-studio-0-4-0
date: 2026-10-16
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-4-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-4-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The 0.4.0 change adds three model-free CLI verbs (`init`, `propose --from`, `find`) plus library equivalents, tests, and a documentation-only agent arm for memkernel. The implementation is generally clean and well-tested, but there are a few correctness concerns around `find`'s reuse of a private querier helper, `edits_from_dir`'s handling of nested `index.md`/`log.md` files, and the `--from` directory being scanned recursively without excluding the wiki itself.

## Findings

- [warning] f-f93a71e6: `find` imports and calls the private `_select_query_candidates` from `querier.py`. This couples the new public API to a private symbol; any refactor of the querier's internals silently changes `find`'s contract, and the underscore prefix signals it is not a stable interface. (src/wiki_studio/api.py)
- [warning] f-9b6eaea7: The check compares the full relative path against `"index.md"`/`"log.md"`, so only the root-level files are treated as append targets. A nested `glossary/index.md` is correctly treated as a page (tested), but a nested `sub/log.md` would also be treated as a page — which is probably intended, yet the docstring says "``index.md`` holds index bullets and ``log.md`` log entries" without qualifying "at the root". The behavior is right; the doc is ambiguous. (src/wiki_studio/api.py)
- [warning] f-c81952a0: `rglob` walks the entire tree, including any `.audit/`, `.git/`, or nested proposal directories that happen to contain `.md` files. If a user points `--from` at a directory that contains the wiki itself (or a checkout), every wiki page becomes an edit and the command will try to `update` the whole wiki. There is no guard against `source_dir` overlapping `paths.wiki_dir`. (src/wiki_studio/api.py)
- [warning] f-52f6d447: The helper skips line 0 (assumed to be `---`) and stops at the next `---`. If a page has no frontmatter (or frontmatter that does not start on line 0), the loop scans body lines looking for `title:` and may pick up an unrelated `title:` in prose. It also silently truncates at 50 lines, so a long frontmatter block loses the title. The fallback to the file stem is reasonable, but the heuristic is fragile. (src/wiki_studio/api.py)
- [warning] f-ae1c0cda: `api.propose` returns the proposal directory path; the CLI prints it as the first stdout line, and the test `test_default_name_is_dated_and_safe` relies on `result.stdout.splitlines()[0]` being that path. This is an implicit contract between CLI output and tests, and any future log line printed before it would break the test. It also makes the CLI output harder to parse for scripts. (src/wiki_studio/cli.py)
- [note] f-ffe05e83: The scaffold's `last_reviewed` is set to today's date at creation time. For a fresh wiki this is fine, but it means the index/log are immediately "stale" relative to any later review workflow, and the date is not reproducible across runs (relevant for the determinism tests mentioned in the plan). (src/wiki_studio/promoter.py)
- [note] f-c458a6d8: `init_wiki` can also raise `UnicodeEncodeError` (unlikely with the fixed ASCII templates) or `FileExistsError` from a race between `target.exists()` and `write_text`. The latter is a real TOCTOU: two concurrent `init` calls could both see the file absent and one would raise `FileExistsError`, which is not caught and would surface as an unhandled exception rather than a clean error. (src/wiki_studio/api.py)
- [note] f-edd569b6: The test asserts `written.name.endswith("-draft")` and reads `plan.json` from the returned path, but does not assert the date prefix format or that the name is sanitized for a directory with spaces/special characters. The `_default_proposal_name` sanitization logic is therefore only partially covered. (tests/test_agent_verbs.py)
- [note] f-59d47053: The instruction uses `$TMPDIR` without defining it; on systems where `TMPDIR` is unset the shell expands to an empty string and the draft lands at `/wiki-draft/...`, which will fail. The arm is meant to be run by an agent that may not set `TMPDIR`. (docs/agent-arm/instruction.md)
- [note] f-b9627d3b: `import datetime` and `import re` are done inside `_default_proposal_name` rather than at module top. This is inconsistent with the rest of `cli.py` and adds per-call import overhead (negligible, but stylistically off). (src/wiki_studio/cli.py)
