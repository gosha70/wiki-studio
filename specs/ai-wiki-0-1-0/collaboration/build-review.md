---
feature_id: ai-wiki-0-1-0
date: 2026-10-12
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/ai-wiki-0-1-0
rounds_completed: 3
attempt_count: 1
bypass: false
---

# Peer Review: ai-wiki-0-1-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 3
**Verdict**: PASS

## Summary

Round 3 review of the ai-wiki-0-1-0 build phase. The Round 2 blocking finding (f-f9968ea1) is genuinely fixed — the mirroring loop now calls `tmp_dir.mkdir(parents=True, exist_ok=True)` before symlinking siblings, and a deep-wiki-dir test exercises the escape-link path. I found one new correctness issue in the same mirroring loop (the `real_dir` walk descends into the wiki's own ancestor chain but the sibling-symlink step for the *last* ancestor is skipped, so escape links from the wiki root to a sibling of the wiki itself are not mirrored), plus a couple of lower-severity observations.

## Findings

- [warning] f-d5824011: The loop iterates over every part of `rel` (e.g. `("a","b","kb")`), and on each iteration symlinks siblings of `real_dir` into `tmp_dir`, then descends. But the *last* iteration (the wiki's own directory name) symlinks siblings of the wiki's parent into `tmp_root/a/b`, which is correct — however, the loop never symlinks siblings of the wiki directory itself into `tmp_root/a/b/kb`. That is fine for escape links that go *up* (they resolve through the mirrored ancestors), but a wiki page that links to a sibling *of the wiki directory* via a path like `../other-wiki-page.md` (i.e. a file next to the wiki dir, not inside it) will not resolve, because `tmp_root/a/b/kb` contains only the staged wiki contents and no symlinks to `real_dir`'s siblings. The bash original had the same shape (it only mirrored `repo_root` and `repo_root/knowledge`), so this is a pre-existing limitation, but the new generic loop makes it look like it handles arbitrary depth. Consider symlinking siblings of the wiki directory itself into `mirrored`'s parent (i.e. `tmp_root/a/b`) — which the loop already does on the last iteration — and additionally symlinking siblings of the wiki directory into `mirrored` itself is not needed; the real gap is that a link like `../sibling.md` from a page inside the wiki resolves to `tmp_root/a/b/sibling.md`, which *is* covered by the last iteration's sibling symlinking. Re-verify with a test that links from a wiki page to a file that is a sibling of the wiki directory (not of an ancestor). (src/aiwiki/promoter.py)
- [warning] f-f710460b: The BFS seeds `reached` with `_canonical(index)` but enqueues the non-canonical `resolved` path. When a symlink inside the wiki points to another wiki page, `_read(current)` reads through the symlink and `md_links` extracts targets relative to the *symlink's* directory, not the target's directory. This matches the bash `canon_path` behavior only for the `reached` set, not for link resolution. In practice this is unlikely to matter for a wiki without intra-wiki symlinks, but it is a latent divergence. Consider enqueuing `canonical` (or the resolved path) instead of `resolved` so link resolution is anchored at the canonical location. (src/aiwiki/lint.py)
- [note] f-410ebcc3: If `root` is an empty string `""` (e.g. `--root ""`), it falls through to the environment variable, then to `default_root`. This is a minor surprise but matches the "empty means unset" convention used for the other two locations. Acceptable; documenting it would help. (src/aiwiki/paths.py)
- [note] f-32191137: The shim handles `--root value` but not `--root=value`. For `--root=/tmp/foo sample.md`, the token `--root=/tmp/foo` starts with `-` and is skipped, so `sample.md` is correctly identified as the first positional. Correct as-is. (src/aiwiki/cli.py)
- [note] f-100f170f: The test covers escape links to a root-level sibling (`docs/`) and to a sibling two levels down (`a/notes/`), which exercises the ancestor-sibling mirroring. It does not cover a link to a sibling *of the wiki directory itself* (e.g. `../other.md` from a page in `a/b/kb`). Adding that case would close the gap noted in the first finding. (tests/test_package_boundaries.py)
- [note] f-b2b5c179: The docstring says "A wiki outside the root is linted in place (escape links cannot be mirrored, as for the live wiki)." This is accurate, but the mirroring loop's behavior for a wiki *inside* the root but with a sibling-of-wiki escape link is not documented. Consider a sentence noting that only ancestors' siblings are mirrored. (src/aiwiki/promoter.py)
