---
feature_id: wiki-studio-0-7-0
date: 2026-10-26
status: final
phase: build
mode: review
subject_provider: claude
peer_provider: deepseek
peer_profile: deepseek
runner_fingerprint: ae8dc147cf1264834bab35d116b6ab96b06618f438763cde3a90621d78036dba
verdict: PASS
blocking_findings_open: 0
target_ref: feature/wiki-studio-0-7-0
rounds_completed: 1
attempt_count: 1
bypass: false
---

# Peer Review: wiki-studio-0-7-0 — Build Phase

**Reviewer**: deepseek
**Scope**: both
**Rounds**: 1
**Verdict**: PASS

## Summary

The change implements page identity (`page_id`) and attribution (`--by`/`WIKI_STUDIO_ACTOR`) for 0.7.0. The design is coherent and well-documented, with good test coverage. I found one correctness issue in `with_page_id` around CRLF handling and a couple of smaller concerns around the `page_id` detection in `with_page_id` (prefix match could match `page_id_extra:`), plus a minor concern about `frontmatter_page_id` vs. lint's `_field` consistency.

## Findings

- [warning] f-be999992: The check `line.startswith("page_id:")` will also match a key like `page_id_extra:` or `page_id_foo:` since it only checks the prefix `page_id:`. A page with `page_id_extra: x` would be treated as already having a `page_id` and skip assignment, silently leaving the create without an id. Lint's `_field` presumably matches the exact key, so this is inconsistent. (src/wiki_studio/proposal.py)
- [warning] f-153abf1e: `lines[0][3:]` assumes the opening marker is exactly `---` followed by the line ending. If the opening line is `---\r\n`, `lines[0][3:]` is `"\r\n"` — correct. But if the opening line is `---` with no trailing newline (single-line file, no closing `---`), the loop won't find a close and returns unchanged — fine. However if the opening line is `--- \n` (trailing space, which `_FM_CLOSE_RE` accepts via `\s*`), `lines[0][3:]` is `" \n"`, and the inserted line becomes `page_id: pg-... \n` — a trailing space before the newline. Minor but produces a byte the caller didn't write. (src/wiki_studio/proposal.py)
- [note] f-cf637ed8: `frontmatter_page_id` uses `line.startswith(prefix)` where `prefix = "page_id:"`, so it also matches `page_id_extra:`. It also strips only one pair of double quotes but not single quotes, while the docstring says "one pair of double quotes removed" — consistent with lint's `_field`? Worth confirming `_field` in lint.py behaves identically (it likely strips both quote styles or neither). If lint accepts `page_id: 'pg-...'` as well-formed but `frontmatter_page_id` returns `'pg-...'` with quotes, `is_page_id` fails and the key falls back to path — a divergence between lint and review key. (src/wiki_studio/review.py)
- [note] f-59c2c21b: `_parse_proposer` accepts `source == "flag"` with any string name, including an empty string `""`. `resolve_actor` never produces `Actor("", "flag")` (it strips and falls through), so a hand-edited plan.json with `{"name": "", "source": "flag"}` would be accepted and recorded. Not a security issue (attribution is not authentication), but it's an inconsistency with what `resolve_actor` can produce. (src/wiki_studio/promoter.py)
- [note] f-dc81aebb: `assign_page_ids` is called before `validate_patch_set`, so a create with malformed frontmatter (no closing `---`) is passed through unchanged and then validation reports it — good. But a create whose frontmatter has a `page_id` line with a malformed value (e.g. `page_id: pg-BAD`) is also left unchanged (per "caller's id is never rewritten"), and lint will catch it at promote. That's consistent with the ADR, but the API docstring could note that a caller-supplied malformed `page_id` is preserved and will fail lint at promote rather than being rejected at propose. (src/wiki_studio/api.py)
- [note] f-9dd6baf0: The test writes `with_id(..., "")` producing `page_id: ` (empty value). `_field` presumably returns `""`, and `_PAGE_ID_RE.fullmatch("")` is None — good. But the test doesn't cover a `page_id` with a trailing comment or quoted value that lint might accept differently from `frontmatter_page_id`. Given the review.py divergence risk above, a test asserting `page_key` and `lint_wiki` agree on the same page would harden this. (tests/test_page_id.py)
- [note] f-720a8f71: The ADR says wiki-studio "checks nothing beyond the single-line scalar form every frontmatter key already has" for `corrects`, but the diff doesn't show any code that validates `corrects` at all (it's just preserved). That's consistent with "checks nothing", but the phrase "beyond the single-line scalar form" implies some check exists. Minor wording. (docs/adr/0002-page-identity-and-review-keys.md)
