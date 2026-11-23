---
feature_id: wiki-studio-0-11-0
date: 2026-11-23
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-11-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-11-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The read-only git layer is well-structured and defensively designed: the allowlist, environment scrubbing, call cap, and timeout handling are all sound, and the test suite is unusually thorough (real repos, spy on subprocess, ambiguity fixtures, marker-script traps). I found a few correctness issues around the `_statuses` batching when a repository is skipped mid-run, the `_probe` "skipped_any" logic conflating distinct causes, and a subtle path-normalization mismatch between validation and status lookup. None are catastrophic, but the first two can produce misleading outcomes.

## Findings

- [warning] f-f526c644: When a repository is skipped after `_probe` matched a commit in it (e.g. a later p3 in another repo times out, or `_statuses`'s own p4 fails), sources already grouped under that repo get `not_checked(repo.reason or REASON_NOT_FOUND_SKIPPED)`. But `repo.reason` may be `None` if the repo was skipped via `_call` timeout inside `_statuses` itself — the `repo.skip(REASON_TIMED_OUT)` path sets reason, but the `p4 is None` branch then reads `repo.reason or REASON_TIMED_OUT`, which is fine; however the earlier `if not repo.usable` guard fires when a *different* repo's p3 failure skipped this one, and `repo.reason` there is the p3 message, not a p4 reason — acceptable but the fallback `REASON_NOT_FOUND_SKIPPED` masks the real cause when reason is None. (src/wiki_studio/revisions.py)
- [warning] f-e8519a55: `skipped_any` is set True both when a repo was already unusable *before* the probe and when a p3 call fails/times out during the probe. The final `if skipped_any: return _Probe(reason=REASON_NOT_FOUND_SKIPPED)` therefore reports "commit not found in the usable repositories" even when the only reason it wasn't found is that a repo was skipped mid-probe — which is correct — but it also fires when *every* usable repo returned `STDERR_NOT_FOUND` and one unrelated repo was pre-skipped, turning a legitimate `CAUSE_COMMIT_NOT_FOUND` finding into a not-checked. That is the intended conservative behavior per the docstring, but the distinction between "not found in any usable repo" (finding) and "not found, but some repo was skipped" (not-checked) hinges on `skipped_any` being set only for repos that could plausibly have held the commit. A pre-skipped repo (e.g. shallow) genuinely could have held it, so this is defensible — flagging as a note on intent clarity. (src/wiki_studio/revisions.py)
- [warning] f-c0d479f3: `contained_path` is called again here on `source.path`, but sources reaching `_statuses` already passed `contained_path(source.path) is not None` in `_run_plan`. The re-normalization is consistent, but the `cited` list is built with `str(contained_path(source.path))` and the lookup uses the same — so keys match. However if `contained_path` ever returns a value whose `str()` differs from the raw path git prints (e.g. git normalizes `./a` to `a`), the lookup silently misses and the source is marked `OUTCOME_UNCHANGED` (the `else` branch) rather than not-checked. Since `contained_path` already normalizes via `posixpath.normpath`, and `_is_clean_path` requires `contained_path(value) == value` for the allowlist, the p4 args carry the normalized form — so git should echo it back normalized. Still, a defensive `if letter is None: source.not_checked(...)` would be safer than defaulting to unchanged. (src/wiki_studio/revisions.py)
- [note] f-6bf469ce: `usable` is computed from `repo.head is not None`, but `_classify` sets `repo.head` only on the `STATUS_USED` path. A repo skipped *after* classification (e.g. by a p3 failure in `_probe` calling `repo.skip(...)`) retains its `head`, so `usable` stays True even though no repo is actually usable for matching. This means `state` can be `on` with zero usable repos, and the `reason` stays None — sources then fall through to `not_checked(leftover or REASON_NOT_FOUND_SKIPPED)`. The summary line would read "on (0 of N repositories used)". Arguably correct (the check ran, it just found nothing usable), but the `reason` being None while state is `on` with 0 used repos is a slightly odd contract. (src/wiki_studio/revisions.py)
- [note] f-a5542652: This walks all parents of a source root looking for a `.git` to distinguish "not a work tree" from "not the top". On a deep path this is O(depth) stat calls per source root, and it runs even when the p1 failure was `STDERR_CANNOT_CHANGE_DIRECTORY` (which means the directory itself doesn't exist — no parent walk needed). Minor, but the `exists()` check is also racy and could misclassify if a `.git` appears/disappears. (src/wiki_studio/revisions.py)
- [note] f-8cc385c7: A `sha:` value of `0` (int) or empty string becomes `None` → `REASON_NO_SHA`. A `sha:` of `False` also becomes `None`. This is fine for strings, but if frontmatter parsing yields a non-string (e.g. a YAML int for an all-digit sha), `str(entry[SOURCE_PATH_KEY])` coerces path but sha is passed raw to `_validate`, where `_SHA_RE.fullmatch(sha)` would raise `TypeError` on a non-str. `_validate` does `if not sha` then `_SHORT_SHA_RE.fullmatch(sha)` — a non-empty non-str would crash. (src/wiki_studio/revisions.py)
- [note] f-70ae5ca5: `protocol.allow=never` blocks all protocol transports, which is good, but `-c protocol.allow=never` is overridable by a later `-c protocol.<name>.allow=always` — none is passed here, so fine. However `GIT_CONFIG_GLOBAL`/`GIT_CONFIG_SYSTEM` are *kept* in the environment (per `KEPT_GIT_ENV`), meaning a user's global config could re-enable a protocol or set `core.fsmonitor` — the `-c` overrides win for fsmonitor/hooksPath, but a global `protocol.file.allow=always` combined with a malicious `url.*.insteadOf` could still redirect. Since no fetch/clone is ever run, this is low risk, but worth noting the kept-config surface. (src/wiki_studio/revisions.py)
- [note] f-0a5c6b34: The test asserts `len(spy.calls) == limit` and that all three sources are not-checked with the cap reason. But it doesn't assert *which* calls ran (p1/p2 for both repos, then one p3) — a regression that reordered classification vs. probing could still pass. The comment says "p1 and p2 for both repositories, then one p3" but this isn't verified. (tests/test_revisions.py)
- [note] f-34281d43: The test runs `git diff` (porcelain) to prove the traps fire, then runs the layer and asserts no markers. But it doesn't assert that the layer's p4 actually *ran* (only that the outcome is `OUTCOME_CHANGED`). If p4 were skipped due to a bug, the test would still pass with no markers. (tests/test_revisions.py)
- [note] f-b93ad568: Accurate, but the docstring doesn't mention that `_statuses` batches *all* sources sharing a (repo, commit) into one p4 — which is the key efficiency property. Minor. (src/wiki_studio/revisions.py)
- [note] f-4c0c690e: `repos.index(probe.repo)` is O(n) per source and relies on `_Repo` identity (no `__eq__` defined, so identity — fine). For large source lists this is O(n·m). Minor; could use `id(probe.repo)` as key and a dict from id→repo. (src/wiki_studio/revisions.py)
- [note] f-a79a86c0: An empty-string `WIKI_STUDIO_GIT_CALL_LIMIT=""` is falsy and silently ignored (falls back to default), whereas `"0"` is truthy and parsed. This matches the lock-timeout handling pattern, but an empty env var is arguably a misconfiguration that should raise rather than silently default. Consistent with existing behavior, so note only. (src/wiki_studio/paths.py)
