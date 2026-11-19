---
feature_id: wiki-studio-patterns-54
date: 2026-11-18
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-patterns-54
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-patterns-54 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The US6 staleness script is well-scoped, read-only, and correctly uses argument-list subprocess calls with no shell. The main correctness concerns are around the `_revision` helper's handling of the `sha` argument (potential for argument injection via a crafted `sha:` value in frontmatter), the `_body` frontmatter-stripping logic, and a subtle mismatch between the README's claim of "24 sources" and the test's expectation that only `path:`-bearing sources are counted. Overall the implementation is sound and the tests cover the key behaviors.

## Findings

- [warning] f-65e91cbb: The `sha` value comes from page frontmatter and is passed directly to `git cat-file -e f"{sha}^{{commit}}"` and `git diff --quiet sha pin -- path`. A malicious or malformed `sha:` (e.g. starting with `-` or containing `--`) could be interpreted as a git option rather than a revision, since git does not universally require `--` before revisions. The `path` is protected by `--` in the diff call, but `sha` and `pin` are not. (eval/patterns/staleness.py)
- [warning] f-f144064c: The `^{commit}` peel is applied to `sha` but not to `pin` in the diff call. If `pin` is an annotated tag or non-commit ref, `git diff --quiet sha pin` may behave differently than the `cat-file -e pin^{commit}` check in `run_staleness` implies. The manifest pin is a full SHA here, so this is latent, but the asymmetry is a correctness trap if the pin format ever changes. (eval/patterns/staleness.py)
- [warning] f-6d187f97: `_body` looks for `"\n---"` starting at index 3 and slices `text[close + 4:]`. If the frontmatter closing delimiter is `---\n` (no trailing newline before body) or the file uses `\r\n`, the offset `+4` may skip a character of the body or leave a stray `\r`. Also, a body line beginning with `---` (e.g. a horizontal rule) after frontmatter is fine, but a frontmatter value containing `\n---` inside a block scalar would truncate early. (eval/patterns/staleness.py)
- [warning] f-dd0113a9: `_page_sources` silently drops any source entry that has `path` but no `sha` (or vice versa). The README and the test `test_results_list_exactly_the_pattern_pages_path_sources` both assume every `path:` source has a `sha:`. If a future page adds a `path:` without `sha:`, the script will silently omit it and the committed results will drift from the fixture without any error. (eval/patterns/staleness.py)
- [note] f-de14b2f0: `present` is computed with `cat-file -e f"{pin}:{path}"` but `_revision` independently re-checks `sha` and runs `diff`. If `path` is missing at the pin, `git diff --quiet sha pin -- path` still returns 1 (changed) rather than erroring, so a deleted-at-pin file reports `revision_check: "changed"` — which the test asserts and the README describes. This is intentional but subtle; a reader may expect `null`/reason for a missing path. (eval/patterns/staleness.py)
- [note] f-62948284: The test suite does not exercise `run_staleness` end-to-end against a temp checkout + temp patterns dir; it only tests `check_sources` and the committed-results shape. The `CheckoutError` path (unreadable pin → exit 2, nothing written) and the `--out` write path are untested. (tests/test_patterns_eval.py)
- [note] f-9666bffc: The README states "24 sources on the fourteen pages" and the totals block matches, but the test `test_results_list_exactly_the_pattern_pages_path_sources` only counts sources with a `path:` key. If any page has a `url:`/`issue:`-only source, the README's "24 sources" and the test's count would diverge silently. Worth a one-line note that "sources" here means `path:`+`sha:` entries only. (eval/patterns/README.md)
- [note] f-51e8823e: `main` catches `SystemExit` from `parse_args` and returns `exc.code`, but `argparse` writes usage to stderr and exits 2 on error — the same code as `CHECKOUT_UNREADABLE`. A caller cannot distinguish "bad arguments" from "unreadable checkout" by exit code alone. (eval/patterns/staleness.py)
