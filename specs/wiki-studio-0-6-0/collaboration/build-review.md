---
feature_id: wiki-studio-0-6-0
date: 2026-10-24
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-6-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-6-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The containment work is well-structured and the `contain` primitive is a solid, reusable boundary check. However, there are several correctness gaps: `contain` does not detect symlinks in the *base* path itself (only in the candidate's components), the `_link_violation` fallback loop can silently accept a target that resolves inside a source root but whose real path is a symlink target, and `_recheck_write_targets` only walks the planned write path but not the parent directories that the commit will create. There is also a subtle inconsistency between `contain`'s handling of `..` after a symlink and the documented "refuse even when a later `..` would step back out" behavior when the symlink is the *base*.

## Findings

- [warning] f-4b7fcbac: `base` is resolved with `Path.resolve()`, which follows symlinks. If `base` itself is (or passes through) a symlink, the containment check silently accepts it — the docstring promises "no symlink on the way" but only checks the candidate's components. A caller passing a symlinked `base` (e.g. a symlinked wiki dir) gets a false pass. (src/wiki_studio/paths.py)
- [warning] f-cf40dd31: When the first `contain(candidate, boundary, base=live_wiki_dir)` raises `CONTAIN_OUTSIDE`, the loop `continue`s to the next boundary. But `contain` returns the *real* path; if a later boundary admits the candidate, the code returns `None if real.exists() else ...`. If the real path is a symlink target that exists but the symlink itself was on the way, `contain` would have raised `CONTAIN_SYMLINK` — so this is safe. However, if the candidate resolves inside a source root via a path that *does not* exist yet, `real.exists()` is False and the message says "broken source reference" — correct. The real gap: the loop does not distinguish "candidate is inside this boundary but broken" from "candidate is outside this boundary"; a broken reference inside the *root* is reported as "escapes the project root" if a source root is checked first and also fails. Order matters and is undocumented. (src/wiki_studio/lint.py)
- [warning] f-e4e96ff7: The recheck walks `Path(plan.rel).parts` from `wiki_dir`, but `plan.rel` is the *file* path. If the commit will create intermediate directories (e.g. `incidents/` for `incidents/cli-fixture.md`), those directories are not `lstat`ed — only the final file and its existing ancestors. A symlink planted at `incidents/` after planning but before the recheck would be caught only if `incidents` already exists as a symlink at recheck time; if it is created between recheck and `_apply_planned`, the race remains. The test `test_a_symlink_appearing_after_planning_is_caught_by_the_lstat_recheck` passes because the symlink is created before the recheck runs, but the window between recheck and write is not closed. (src/wiki_studio/promoter.py)
- [warning] f-c3733031: The recheck is a check-then-act: between `_recheck_write_targets` and the actual `write_bytes`, a symlink can be planted. The diff does not show `_apply_planned` using `O_NOFOLLOW` or `os.open(..., O_CREAT (src/wiki_studio/promoter.py)
- [warning] f-b358ee86: The pruning happens *after* `found.append((base, list(dirnames), filenames))`, so `symlinks_in` sees the symlinked directory in `dirnames` and reports it — good. But `list_pages` iterates `_walk_wiki` and for each `base` checks `filenames`; a symlinked *file* is in `filenames` and is filtered by `not path.is_symlink()`. Correct. However, `_walk_wiki` calls `(base / d).is_symlink()` for every directory on every walk — a TOCTOU if the tree changes mid-walk, and a performance cost on large wikis. Minor. (src/wiki_studio/lint.py)
- [warning] f-c6146a79: The function calls `contain(target, wiki_dir)` but discards the returned real path. It returns `True` if `contain` succeeds, meaning the target resolves inside the wiki — but `contain` does not require existence, so a link to a non-existent page inside the wiki passes the filter and is later read by `_select_query_candidates`. The downstream read presumably handles missing files, but the docstring says "keeps `find`, `query` and the eval selector from reading a file outside the wiki" — it does not claim to filter missing files, so this is consistent. However, `_extract_index_links` is also used by the eval selector; if a missing page is selected, the eval may error. Verify downstream handles missing files gracefully. (src/wiki_studio/querier.py)
- [note] f-20ac29d8: The `current != boundary_real` guard is redundant: `Path.is_relative_to` returns True for equal paths. Harmless but confusing. (src/wiki_studio/paths.py)
- [note] f-34dda53d: On Windows, `Path("a/b").parts` splits on both `/` and `\`, but on POSIX only `/`. A candidate like `a\..\..\etc` on POSIX is a single component named `a\..\..\etc` and would be treated as a literal filename — safe (it won't escape), but the behavior differs across platforms. The `_WINDOWS_ABSOLUTE_RE` catches drive/UNC prefixes but not backslash-separated relative escapes. (src/wiki_studio/paths.py)
- [note] f-ee03ed96: The title regex is applied *after* splitting on `#`. A target like `[t](x.md#frag "Title")` — the `#` split yields `x.md` and `frag "Title"`, so the title is lost and `x.md` is returned. Correct. But `[t](x.md "Title#with-hash")` — the `#` split yields `x.md "Title` and `with-hash")`, so the title regex sees `x.md "Title` which does not match `\s+(?:"[^"]*" (src/wiki_studio/lint.py)
- [note] f-7a29b959: The test patches `_plan_commit` to plant the symlink *after* planning returns, then asserts the recheck catches it. This validates the recheck but not the race between recheck and write (see finding above). (tests/test_containment.py)
- [note] f-0b3ff366: The docstring says "``base`` and ``boundary`` with ``Path.resolve``" — this is accurate but the security implication (base symlinks are followed) is not called out. Callers may assume `base` is also symlink-checked. (src/wiki_studio/paths.py)
- [note] f-45fdb743: `root` defaults to `default_root(wiki_dir)` which runs `git_toplevel` — a subprocess call. `lint_wiki` is called from `promote` (via `_lint_staged_tree`) and from `api.lint`. In `promote`, `paths.root` is passed explicitly, so no subprocess. In `api.lint`, `paths.root` is passed. Only direct callers of `lint_wiki` without `root` pay the subprocess cost. Acceptable, but the default is surprising for a pure function. (src/wiki_studio/lint.py)
