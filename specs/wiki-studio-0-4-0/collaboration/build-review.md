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

The 0.4.0 change adds three model-free CLI verbs (`init`, `propose --from`, `find`) plus library equivalents, tests, and a documentation-only agent arm. The implementation is generally clean and well-tested, but there are correctness concerns around `find`'s reuse of a private querier helper, `edits_from_dir`'s handling of nested `index.md`/`log.md` files, and the `--from` directory being scanned recursively without excluding the wiki itself.

## Findings

- [warning] f-71800581: `find` imports and calls the private `_select_query_candidates` from `querier.py`, coupling the new public API to a private symbol; any refactor of the querier's internals silently changes `find`'s contract. (src/wiki_studio/api.py)
- [warning] f-4bbaf468: The docstring says "``index.md`` holds index bullets and ``log.md`` log entries" without qualifying "at the root"; the code only treats root-level `index.md`/`log.md` as append targets, so a nested `sub/log.md` is a page. Behavior is right, doc is ambiguous. (src/wiki_studio/api.py)
- [warning] f-cf51134a: `rglob` walks the entire tree; if `--from` points at a directory containing the wiki itself (or a checkout), every wiki page becomes an edit and the command tries to `update` the whole wiki. The overlap guard only checks `source_dir` vs `wiki_dir`, not nested overlap. (src/wiki_studio/api.py)
- [warning] f-1813920b: The helper assumes frontmatter starts on line 0 and stops at the next `---`; a page with no frontmatter or frontmatter not on line 0 can pick up an unrelated `title:` from prose, and the 50-line truncation silently drops a title in a long frontmatter block. (src/wiki_studio/api.py)
- [warning] f-a50db75c: The CLI prints the proposal directory as the first stdout line, and `test_default_name_is_dated_and_safe` relies on `result.stdout.splitlines()[0]` being that path — an implicit contract that any future log line printed before it would break. (src/wiki_studio/cli.py)
- [note] f-8d8be936: The scaffold's `last_reviewed` is set to today's date at creation time, making the index/log immediately "stale" relative to any later review workflow and non-reproducible across runs (relevant to determinism tests). (src/wiki_studio/promoter.py)
- [note] f-cd96264b: `init_wiki` can raise `UnicodeEncodeError` (unlikely with fixed ASCII templates) or `FileExistsError` from a race between `target.exists()` and `write_text`; the exclusive-open path handles the race, but `api.init` only catches `OSError`, so a `UnicodeEncodeError` would surface unhandled. (src/wiki_studio/promoter.py)
- [note] f-e2ff624d: The test asserts `written.name.endswith("-draft")` and reads `plan.json`, but does not assert the date prefix format or that the name is sanitized for a directory with spaces/special characters; `_default_proposal_name` sanitization is only partially covered. (tests/test_agent_verbs.py)
- [note] f-59d47053: The instruction uses `$TMPDIR` without defining it; on systems where `TMPDIR` is unset the shell expands to an empty string and the draft lands at `/wiki-draft/...`, which will fail. The arm is meant to be run by an agent that may not set `TMPDIR`. (docs/agent-arm/instruction.md)
- [note] f-573c521c: `import datetime` and `import re` are done inside `_default_proposal_name` rather than at module top, inconsistent with the rest of `cli.py` and adding per-call import overhead. (src/wiki_studio/cli.py)
