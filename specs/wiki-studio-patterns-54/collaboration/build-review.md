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

The US3 freeze artifacts are well-structured and the freeze test is a solid guard. I found one blocking correctness issue: the `protocol.json` `labels_sha256`/`questions_sha256` values and the test's `PROTOCOL_SHA256` constant cannot all be self-consistent given the diff, and the test's `test_protocol_records_the_frozen_file_hashes` will fail if the protocol's embedded hashes don't match the actual file bytes. I also found a few warnings around label consistency and test coverage gaps.

## Findings

- [blocking] f-f25e05ed: The protocol embeds `labels_sha256` and `questions_sha256`, and `tests/test_patterns_frozen.py` asserts `protocol["labels_sha256"] == sha256_of(LABELS)` and the same for questions. But `protocol.json` itself is also pinned by `PROTOCOL_SHA256` in the test. If the embedded hashes are correct, the protocol file's own hash is determined; if the embedded hashes are wrong, `test_protocol_records_the_frozen_file_hashes` fails. The diff cannot be verified as self-consistent without recomputing — but the risk is that the author computed `PROTOCOL_SHA256` before finalizing the embedded hashes, or vice versa. This is a chicken-and-egg that must be verified by actually running the test. (eval/patterns/protocol.json)
- [warning] f-5804448c: This pair is labelled `redundant` with reason "Both pages decide the trace archive's privacy floor and name the same archive path calling `redact_text`". But the README states the eligible true pairs number two (the conflict pair and this one), and the pass bar says "any verdict rests on those two pairs". If this label is wrong, the entire pass bar collapses. The reason text is plausible but the two pages are described elsewhere as distinct decisions (one is "never archive raw JSONL", the other is "reuse the ingest redaction path"). A curator should confirm these are genuinely the same decision, not two facets of one. (eval/patterns/labels.json)
- [warning] f-2d498ea8: The single `background_pairs` entry is labelled `redundant`, and the README says "one is named ... and it is labelled `redundant`". But the pass bar says "A pair involving a background page is false unless `background_pairs` lists it with a true disposition." So this pair counts as a true candidate. Combined with the two eligible pattern-pattern true pairs, the true count is three, not two. The README's "The eligible true pairs number two" is therefore inconsistent with the background rule unless background pairs are excluded from the "eligible true pairs" count. This ambiguity will bite whoever implements the scorer. (eval/patterns/labels.json)
- [warning] f-2f2691d3: The test asserts `entry["question"] in self.corpus_text` and `entry["record"] in self.corpus_text`. Substring containment is weak: a question that is a prefix of a longer corpus line, or a record heading that appears twice, would pass. It also does not verify the question is the `later-task:` text verbatim as the README claims. (tests/test_patterns_frozen.py)
- [warning] f-32d58bf4: The test checks that `gold`, `reuse_target`, `trap`, and `superseded` pages exist, but does not check that `reuse_target` is in `gold`, that `trap` is in `gold` (for the config-redaction question it is), or that `superseded` is not in `gold`. These invariants are stated in the README and are load-bearing for the retrieval metrics. (tests/test_patterns_frozen.py)
- [warning] f-9247e376: The test asserts the set of annotated pairs equals `ANNOTATED_PAIRS`, but does not assert that non-annotated pairs have `annotation is None` (it does, implicitly, via set equality) nor that the annotation string actually appears in the corpus. The README says annotations are "the corpus line that names the pair", so a typo in the annotation string would not be caught. (tests/test_patterns_frozen.py)
- [note] f-286e15c9: Signal (c) is defined by reference to `health_lint._entity_mentions` and `prose_lint.load_avoid_map`, which are private helpers. Pinning the protocol to private functions means a refactor of those helpers silently changes the signal definition without changing the frozen protocol. The freeze test only pins the JSON bytes, not the referenced code. (eval/patterns/protocol.json)
- [note] f-66884c16: The README describes signal (b) as "Jaccard similarity of `wiki_state._tokenise(title + " " + the first paragraph of the Decision section)`" but does not specify what "first paragraph" means (blank-line delimited? first non-empty line?). The protocol.json repeats the same ambiguity. Implementers will guess differently. (eval/patterns/README.md)
- [note] f-f3007f31: The pass bar says "its false candidates do not outnumber its true ones across the whole scope". "Outnumber" is strict (`false > true` fails) or non-strict (`false >= true` fails)? The protocol.json says the same. This is a one-character ambiguity that changes the verdict on ties. (eval/patterns/README.md)
- [note] f-5d78d95d: The reason is "Both pages supersede an earlier decision, but for different features, and neither page names the other." This is a meta-reason about the pages' relationship to their predecessors, not about the two pages' decisions. It is a valid `unrelated` justification but is stylistically inconsistent with the other reasons, which describe the two pages' content. Not a correctness bug, but a curator reading the labels will notice. (eval/patterns/labels.json)
