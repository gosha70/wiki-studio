# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""US2: the duplicate-audit script on synthetic inputs (issue 121, FR-017).

Each end-to-end test writes a small development corpus, a small held-out corpus with its labels, review sample and
freeze file, and a protocol to a temporary directory laid out as the repository is; the protocol is the frozen
``protocol.json`` with only its development inputs replaced, so the rules under test are the frozen rules. The pages
of each corpus share words only within their intended pair, so every list and every flagged pair is known in advance.
Covered: remove-and-insert equal to a fresh index without the page on 12 pages; the query page absent from its own
ranking and present for every other page's; the page-type filter; mutual flags at k = 1, 3, 5 and both ranks; every
restatement rule and its exclusions; the bar at its edges; selection and the tie; the stop rule both ways; the
refusals, writing nothing; the same bytes twice; ``eval/`` unchanged by a run with ``--out-dir`` elsewhere; and
``--help``. Cases that rank skip when this Python's SQLite has no FTS5. No committed result is read here.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from eval.duplicate_audit import audit
from wiki_studio import discovery
from wiki_studio.discovery import DEFAULT_RANKER_CONFIG, similar_query
from wiki_studio.search_index import build_document, build_in_memory

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = REPO_ROOT / "eval"
CACHE_DIR_NAME = "__pycache__"
HAS_FTS5 = discovery.fts5_available().available
NO_FTS5 = "this Python's SQLite has no FTS5"

DECISION = "decision"
CONCEPT = "concept"
REDUNDANT = "redundant"
CONFLICTING = "conflicting"
SUPERSEDES = "supersedes"
COMPANION = "companion"
UNRELATED = "unrelated"
WIKI_STUDIO = "wiki-studio"
MEMKERNEL = "memkernel"
TOP_1, TOP_3, TOP_5 = "mutual-top-1", "mutual-top-3", "mutual-top-5"
CANDIDATES = (TOP_1, TOP_3, TOP_5)

# ── The development corpus ────────────────────────────────────
# A and B restate each other (one spec directory); C and D share words across repositories; E matches nothing;
# F and G share words and are unlabelled; H is a concept page with every word, so the page-type filter drops it.
A, B, C, E, F, G, H = (f"r1/{name}.md" for name in "abcefgh")
D = "r2/d.md"
DEV_ROWS: list[tuple[str, str, str, str, dict[str, Any]]] = [
    (A, DECISION, "Zebra yak", "zebra yak walrus", {"repository": "r1", "spec_path": "specs/feat-a/plan.md"}),
    (B, DECISION, "Walrus yak", "zebra yak walrus", {"repository": "r1", "spec_path": "specs/feat-a/spec.md"}),
    (C, DECISION, "Kiwi lemon", "kiwi lemon mango", {"repository": "r1", "spec_path": "specs/feat-c/plan.md"}),
    (D, DECISION, "Mango lemon", "kiwi lemon mango", {"repository": "r2", "spec_path": "specs/feat-d/plan.md"}),
    (E, DECISION, "Quartz", "quartz", {"repository": "r1", "spec_path": "specs/feat-e/plan.md"}),
    (F, DECISION, "Olive", "olive pepper", {"repository": "r1", "spec_path": "specs/feat-f/plan.md"}),
    (G, DECISION, "Pepper", "olive pepper", {"repository": "r1", "spec_path": "specs/feat-g/plan.md"}),
    (
        H,
        CONCEPT,
        "Everything",
        "zebra yak walrus kiwi lemon mango olive pepper",
        {"repository": "r1", "spec_path": "specs/feat-h/plan.md"},
    ),
]
DEV_LABELS: dict[str, Any] = {
    "groups": [{"id": "g-1", "family": "f", "pages": [A, B, E]}],
    "pairs": [
        {"pair": [A, B], "group": "g-1", "disposition": REDUNDANT, "reason": "same ruling"},
        {"pair": [A, E], "group": "g-1", "disposition": SUPERSEDES, "reason": "later ruling"},
        {"pair": [B, E], "group": "g-1", "disposition": UNRELATED, "reason": "no shared question"},
    ],
    "cross_pairs": [{"pair": [C, D], "scope": "cross-repository", "disposition": CONFLICTING, "reason": "disagree"}],
    "defaults": {"within_family": UNRELATED, "cross": UNRELATED},
    "true_pairs": 3,
}
DEV_LISTS = sorted(
    [f"{A} -> {B}", f"{B} -> {A}", f"{C} -> {D}", f"{D} -> {C}", f"{E} ->", f"{F} -> {G}", f"{G} -> {F}", f"{H} ->"]
)
DEV_PAIRS = [
    f"{A} {B} 1/1 redundant one-feature a",
    f"{C} {D} 1/1 conflicting cross-repository -",
    f"{F} {G} 1/1 unrelated within-repository -",
]

# ── The held-out corpus ───────────────────────────────────────
# Nine pairs of pages, each pair with two words of its own; pairs 0-7 are labelled redundant, pair 8 companion; one
# memkernel page matches nothing. Spec paths give pair 0, 2, 4 rule a, pair 1 rule b, pair 6 rule c, and pairs 3, 5,
# 7, 8 no rule; pair 3 involves wiki-studio-0-1-0, a bundle with no origin issue.
PAIR_WORDS = [
    ("amber", "anvil"),
    ("basil", "birch"),
    ("cedar", "cobalt"),
    ("delta", "dune"),
    ("ember", "elm"),
    ("fjord", "flint"),
    ("grove", "garnet"),
    ("heron", "hazel"),
    ("ivory", "iris"),
]
PAIR_SOURCES: list[tuple[tuple[str, int | None], tuple[str, int | None]]] = [
    (("specs/f0/plan.md", 3), ("specs/f0/spec.md", 3)),
    (("specs/pitches/71-basil/pitch.md", None), ("specs/g71/plan.md", 71)),
    (("specs/f2/plan.md", 5), ("specs/f2/spec.md", 5)),
    (("specs/wiki-studio-0-1-0/plan.md", None), ("specs/h3/plan.md", 9)),
    (("specs/f4/plan.md", 6), ("specs/f4/spec.md", 6)),
    (("specs/x5/plan.md", 7), ("specs/y5/spec.md", 8)),
    (("specs/pitches/10-grove/pitch.md", None), ("specs/pitches/28-grove/pitch.md", None)),
    (("specs/x7/plan.md", 11), ("specs/y7/plan.md", 12)),
    (("specs/x8/plan.md", 13), ("specs/y8/plan.md", 14)),
]
FALSE_PAIR = 8
SOLO = "memkernel/mk-solo.md"
HELD_OUT_RULES = ["a", "b", "a", "-", "a", "-", "c", "-", "-"]


def held_page(i: int, side: str) -> str:
    return f"{WIKI_STUDIO}/p{i}-{side}.md"


def held_out_rows() -> list[tuple[str, str, str, str, dict[str, Any]]]:
    rows: list[tuple[str, str, str, str, dict[str, Any]]] = []
    for i, ((first, second), sources) in enumerate(zip(PAIR_WORDS, PAIR_SOURCES, strict=True)):
        for side, title, (spec_path, origin_issue) in zip(
            ("a", "b"), (f"{first} {second}", f"{second} {first}"), sources, strict=True
        ):
            fields: dict[str, Any] = {
                "repository": WIKI_STUDIO,
                "spec_path": spec_path,
                "source_kind": "pitch" if "/pitches/" in spec_path else "spec",
                "origin_issue": origin_issue,
            }
            rows.append((held_page(i, side), DECISION, title.title(), f"{first} {second}", fields))
    solo_fields: dict[str, Any] = {
        "repository": MEMKERNEL,
        "spec_path": "specs/memkernel-0-17-x/plan.md",
        "source_kind": "spec",
        "origin_issue": None,
    }
    rows.append((SOLO, DECISION, "Quartz", "quartz", solo_fields))
    return rows


def held_out_labels() -> dict[str, Any]:
    groups = [{"id": f"g{i}", "family": WIKI_STUDIO, "pages": [held_page(i, "a"), held_page(i, "b")]} for i in range(9)]
    pairs = [
        {
            "pair": [held_page(i, "a"), held_page(i, "b")],
            "group": f"g{i}",
            "disposition": COMPANION if i == FALSE_PAIR else REDUNDANT,
            "reason": "the same question",
        }
        for i in range(9)
    ]
    return {"groups": groups, "pairs": pairs, "cross_pairs": [], "true_pairs": 8}


def held_out_pair_lines() -> list[str]:
    lines = []
    for i, rule in enumerate(HELD_OUT_RULES):
        scope = "one-feature" if rule in ("a", "b") else "within-repository"
        label = COMPANION if i == FALSE_PAIR else REDUNDANT
        lines.append(f"{held_page(i, 'a')} {held_page(i, 'b')} 1/1 {label} {scope} {rule}")
    return sorted(lines)


# ── Writing the synthetic repository ──────────────────────────


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, document: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    document: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return document


def page_text(page_type: str, title: str, body: str) -> str:
    return f"---\npage_type: {page_type}\nslug: corpus-slug\ntitle: {title}\nstatus: stable\n---\n\n{body}\n"


def frozen_protocol() -> dict[str, Any]:
    return read_json(REPO_ROOT / audit.PROTOCOL_PATH)


def write_pages(
    root: Path, corpus_root: str, rows: list[tuple[str, str, str, str, dict[str, Any]]]
) -> list[dict[str, Any]]:
    entries = []
    for page, page_type, title, body, fields in rows:
        path = root / corpus_root / page
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page_text(page_type, title, body), encoding="utf-8")
        entries.append({"page": page, "title": title, "sha256": sha256_of(path), **fields})
    return entries


def write_freeze(root: Path) -> None:
    freeze: dict[str, Any] = {key: sha256_of(root / rel) for key, rel in audit.FREEZE_PINS}
    freeze.update({"true_pairs": 8, "testable": True})
    write_json(root / audit.FREEZE_PATH, freeze)


def write_study(root: Path, *, freeze: bool = True) -> dict[str, Any]:
    """Both synthetic sets under ``root`` and the protocol with its development inputs replaced; it is returned."""
    protocol = frozen_protocol()
    development = audit.study_set(audit.DEVELOPMENT, protocol)
    entries = write_pages(root, development.corpus_root, DEV_ROWS)
    write_json(root / development.corpus_json, {"pages": entries})
    write_json(root / development.labels, DEV_LABELS)
    protocol["development"]["inputs"] = [
        {"path": rel, "sha256": sha256_of(root / rel)} for rel in (development.corpus_json, development.labels)
    ]
    write_json(root / audit.PROTOCOL_PATH, protocol)
    held_out = audit.study_set(audit.HELD_OUT, protocol)
    write_json(root / held_out.corpus_json, {"pages": write_pages(root, held_out.corpus_root, held_out_rows())})
    write_json(root / held_out.labels, held_out_labels())
    write_json(root / audit.HELD_OUT_DIR / audit.REVIEW_SAMPLE_NAME, {"seed": 121, "pairs": []})
    if freeze:
        write_freeze(root)
    return protocol


def run(root: Path | None, study_set: str, out_dir: Path) -> tuple[int, str]:
    """``audit.main`` with ``--set`` and ``--out-dir``; the exit code and what it wrote to stderr."""
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = audit.main(["--set", study_set, "--out-dir", str(out_dir)], root=root)
    return code, stderr.getvalue()


def snapshot(directory: Path) -> dict[str, str]:
    """Path and sha256 of every file under ``directory``, bytecode caches left out (they are never committed)."""
    return {
        path.relative_to(directory).as_posix(): sha256_of(path)
        for path in sorted(directory.rglob("*"))
        if path.is_file() and CACHE_DIR_NAME not in path.parts
    }


def counts(found: int, false: int, non_restatement: int) -> dict[str, Any]:
    return {"found": found, "true": found, "false": false, "non_restatement_found": non_restatement}


# ── Mutual flags (FR-004) ─────────────────────────────────────


class FlagTest(unittest.TestCase):
    """Mutual flags at k = 1, 3, 5, read from one set of lists, with both ranks."""

    # P's nearest is Q, whose nearest is R, whose nearest is Q: at k = 1 only {Q, R} is mutual.
    LISTS = {
        "p": ["q", "r", "s"],
        "q": ["r", "p", "s"],
        "r": ["q", "p", "s"],
        "s": ["p", "q", "r"],
    }

    def test_k_1_flags_only_the_mutual_nearest(self) -> None:
        self.assertEqual(audit.flagged(self.LISTS, 1), [("q", "r", 1, 1)])

    def test_k_3_flags_every_pair_with_both_ranks(self) -> None:
        self.assertEqual(
            audit.flagged(self.LISTS, 3),
            [
                ("p", "q", 1, 2),
                ("p", "r", 2, 2),
                ("p", "s", 3, 1),
                ("q", "r", 1, 1),
                ("q", "s", 3, 2),
                ("r", "s", 3, 3),
            ],
        )

    def test_k_5_reaches_ranks_4_and_5(self) -> None:
        lists = {"p": ["w", "x", "y", "z", "r"], "r": ["v", "w", "x", "y", "p"]}
        self.assertEqual(audit.flagged(lists, 1), [])
        self.assertEqual(audit.flagged(lists, 3), [])
        self.assertEqual(audit.flagged(lists, 5), [("p", "r", 5, 5)])

    def test_a_one_sided_neighbour_is_not_flagged(self) -> None:
        lists = {"p": ["q"], "q": ["r"], "r": []}
        for k in (1, 3, 5):
            with self.subTest(k=k):
                self.assertEqual(audit.flagged(lists, k), [])


# ── Restatements and pair scope (FR-005) ──────────────────────


def entry(repository: str, spec_path: str, origin_issue: Any = None) -> dict[str, Any]:
    return {"repository": repository, "spec_path": spec_path, "origin_issue": origin_issue}


class RestatementTest(unittest.TestCase):
    """Rules a, b and c, named in that order, decided from the corpus.json entries only."""

    PITCH = entry(WIKI_STUDIO, "specs/pitches/71-some-pitch/pitch.md")

    def assert_rule(self, a: dict[str, Any], b: dict[str, Any], rule: str | None, scope: str) -> None:
        for first, second in ((a, b), (b, a)):
            with self.subTest(first=first, second=second):
                self.assertEqual(audit.is_restatement(first, second), rule)
                self.assertEqual(audit.pair_scope(first, second, rule), scope)

    def test_a_one_spec_directory(self) -> None:
        self.assert_rule(
            entry(WIKI_STUDIO, "specs/feat/plan.md", 5), entry(WIKI_STUDIO, "specs/feat/spec.md", 5), "a", "one-feature"
        )

    def test_a_directory_of_the_same_name_in_another_repository_is_another_directory(self) -> None:
        self.assert_rule(
            entry(WIKI_STUDIO, "specs/feat/plan.md"), entry(MEMKERNEL, "specs/feat/plan.md"), None, "cross-repository"
        )

    def test_a_on_development_entries_without_source_fields(self) -> None:
        plan = {"repository": "r1", "spec_path": "specs/x/plan.md"}
        spec = {"repository": "r1", "spec_path": "specs/x/spec.md"}
        other = {"repository": "r1", "spec_path": "specs/y/plan.md"}
        self.assert_rule(plan, spec, "a", "one-feature")
        self.assert_rule(plan, other, None, "within-repository")

    def test_b_a_pitch_and_the_bundle_of_its_issue(self) -> None:
        self.assert_rule(self.PITCH, entry(WIKI_STUDIO, "specs/bundle/plan.md", 71), "b", "one-feature")
        self.assert_rule(self.PITCH, entry(WIKI_STUDIO, "specs/bundle/spec.md", 71), "b", "one-feature")

    def test_b_needs_the_same_number(self) -> None:
        self.assert_rule(self.PITCH, entry(WIKI_STUDIO, "specs/bundle/plan.md", 72), None, "within-repository")

    def test_a_bundle_with_no_origin_issue_never_meets_b(self) -> None:
        self.assert_rule(self.PITCH, entry(WIKI_STUDIO, "specs/wiki-studio-0-1-0/plan.md"), None, "within-repository")
        missing = {"repository": WIKI_STUDIO, "spec_path": "specs/wiki-studio-0-6-0/spec.md"}
        self.assert_rule(self.PITCH, missing, None, "within-repository")

    def test_a_string_origin_issue_never_meets_b(self) -> None:
        memkernel_pitch = entry(MEMKERNEL, "specs/pitches/71-x/pitch.md")
        self.assert_rule(memkernel_pitch, entry(MEMKERNEL, "specs/mk/plan.md", "71"), None, "within-repository")
        self.assert_rule(
            memkernel_pitch, entry(MEMKERNEL, "specs/mk/plan.md", "memkernel#71"), None, "within-repository"
        )

    def test_a_pitch_number_matching_in_another_repository_is_not_a_restatement(self) -> None:
        self.assert_rule(self.PITCH, entry(MEMKERNEL, "specs/mk/plan.md", 71), None, "cross-repository")

    def test_a_pitch_id_without_a_leading_number_never_meets_b(self) -> None:
        pitch = entry(WIKI_STUDIO, "specs/pitches/release-c/pitch.md")
        self.assert_rule(pitch, entry(WIKI_STUDIO, "specs/bundle/plan.md", 71), None, "within-repository")

    def test_c_two_pitch_files(self) -> None:
        other = entry(WIKI_STUDIO, "specs/pitches/28-other/pitch.md")
        self.assert_rule(self.PITCH, other, "c", "within-repository")
        self.assert_rule(self.PITCH, entry(MEMKERNEL, "specs/pitches/5-x/pitch.md"), "c", "cross-repository")

    def test_two_items_of_one_pitch_meet_a_first(self) -> None:
        self.assert_rule(self.PITCH, dict(self.PITCH), "a", "one-feature")


# ── The bar, selection, the verdict and the stop rule (FR-006, FR-007) ──


class BarTest(unittest.TestCase):
    """The bar at its edges, with the frozen protocol's values."""

    def setUp(self) -> None:
        self.protocol = frozen_protocol()
        self.bar = self.protocol["bar"]

    def conditions(self, found: int, false: int, non_restatement: int, n: int = 8) -> dict[str, bool]:
        return audit.bar_conditions(counts(found, false, non_restatement), n, self.bar)

    def test_7_true_pairs_are_not_testable(self) -> None:
        result = self.conditions(7, 0, 7, n=7)
        self.assertFalse(result["testable"])
        self.assertFalse(result["passes"])
        self.assertEqual(audit.verdict_of(7, None, self.protocol), "not testable")

    def test_recall_6_of_8_passes_and_5_of_8_fails(self) -> None:
        self.assertTrue(self.conditions(6, 0, 2)["passes"])
        result = self.conditions(5, 0, 2)
        self.assertFalse(result["recall"])
        self.assertFalse(result["passes"])

    def test_false_equal_to_true_passes_and_one_more_fails(self) -> None:
        self.assertTrue(self.conditions(6, 6, 2)["passes"])
        result = self.conditions(6, 7, 2)
        self.assertFalse(result["false_not_above_true"])
        self.assertFalse(result["passes"])

    def test_one_non_restatement_found_fails_and_two_pass(self) -> None:
        result = self.conditions(6, 0, 1)
        self.assertFalse(result["non_restatement"])
        self.assertFalse(result["passes"])
        self.assertTrue(self.conditions(6, 0, 2)["passes"])


class SelectionTest(unittest.TestCase):
    """The fewest false pairs per true pair wins; a tie goes to the smaller k."""

    def setUp(self) -> None:
        self.protocol = frozen_protocol()

    def candidate(self, name: str, k: int, found: int, false: int) -> tuple[str, int, dict[str, Any]]:
        record = counts(found, false, 2)
        record["bar"] = audit.bar_conditions(record, 8, self.protocol["bar"])
        return name, k, record

    def test_the_fewest_false_per_true_wins(self) -> None:
        candidates = [self.candidate(TOP_1, 1, 6, 3), self.candidate(TOP_3, 3, 8, 2), self.candidate(TOP_5, 5, 8, 4)]
        self.assertEqual(audit.select_winner(candidates), TOP_3)
        self.assertEqual(audit.verdict_of(8, TOP_3, self.protocol), "winner")

    def test_a_tie_goes_to_the_smaller_k(self) -> None:
        candidates = [self.candidate(TOP_5, 5, 8, 4), self.candidate(TOP_3, 3, 8, 4), self.candidate(TOP_1, 1, 6, 3)]
        self.assertEqual(audit.select_winner(candidates), TOP_1)

    def test_a_failing_candidate_never_wins(self) -> None:
        candidates = [self.candidate(TOP_1, 1, 5, 0), self.candidate(TOP_3, 3, 8, 6)]
        self.assertEqual(audit.select_winner(candidates), TOP_3)
        none_pass = [self.candidate(TOP_1, 1, 5, 0), self.candidate(TOP_3, 3, 8, 9)]
        self.assertIsNone(audit.select_winner(none_pass))
        self.assertEqual(audit.verdict_of(8, None, self.protocol), "no candidate clears the bar")


class StopRuleTest(unittest.TestCase):
    """``go`` when at least one candidate's false pairs do not outnumber its true pairs, else ``stop``."""

    def setUp(self) -> None:
        self.protocol = frozen_protocol()

    def test_go_when_one_candidate_holds(self) -> None:
        candidates = {TOP_1: counts(1, 2, 0), TOP_3: counts(2, 2, 0), TOP_5: counts(2, 9, 0)}
        result = audit.stop_rule(candidates, self.protocol)
        self.assertEqual(result["false_not_above_true"], {TOP_1: False, TOP_3: True, TOP_5: False})
        self.assertEqual(result["outcome"], "go")
        self.assertEqual(result["line"], "Development stage: go")

    def test_stop_when_every_candidate_fails(self) -> None:
        candidates = {TOP_1: counts(0, 1, 0), TOP_3: counts(1, 2, 0), TOP_5: counts(2, 3, 0)}
        result = audit.stop_rule(candidates, self.protocol)
        self.assertEqual(result["outcome"], "stop")
        self.assertEqual(result["line"], "Development stage: stop")


# ── The index and the lists (FR-003) ──────────────────────────

WORDS = [
    "alpha",
    "bravo",
    "charlie",
    "delta",
    "echo",
    "foxtrot",
    "golf",
    "hotel",
    "india",
    "juliet",
    "kilo",
    "lima",
    "mike",
    "november",
]
TWELVE = 12


def twelve_pages() -> list[audit.Page]:
    """Twelve pages, each sharing words with its neighbours; the last is a concept page."""
    pages = []
    for i in range(TWELVE):
        page_type = CONCEPT if i == TWELVE - 1 else DECISION
        text = page_text(page_type, f"{WORDS[i]} {WORDS[i + 1]}", " ".join(WORDS[i : i + 3]))
        pages.append(audit.Page(f"page-{i:02d}", f"decisions/{WORDS[i]}-{WORDS[i + 1]}.md", text, page_type))
    return pages


def fresh_ranking(pages: list[audit.Page], query_page: audit.Page, *, same_page_type: bool = True) -> list[str]:
    """The query page's list from a fresh index built without it."""
    others = [page for page in pages if page.key != query_page.key]
    by_path = {page.path: page for page in others}
    with build_in_memory(
        [build_document(page.path, page.text) for page in others], tokenizer=DEFAULT_RANKER_CONFIG.tokenizer
    ) as index:
        ranked = index.rank(
            similar_query(query_page.text),
            order=[page.path for page in others],
            weights=DEFAULT_RANKER_CONFIG.weights,
            min_match_tokens=DEFAULT_RANKER_CONFIG.min_match_tokens,
        )
    return [
        by_path[path].key for path in ranked if not same_page_type or by_path[path].page_type == query_page.page_type
    ]


@unittest.skipUnless(HAS_FTS5, NO_FTS5)
class PageListsTest(unittest.TestCase):
    """One index, the page's row removed for its own query and back for every other page's (pitch finding 12)."""

    def setUp(self) -> None:
        self.pages = twelve_pages()
        self.lists = audit.page_lists(self.pages)

    def test_every_list_equals_a_fresh_index_without_the_page(self) -> None:
        self.assertEqual(set(self.lists), {page.key for page in self.pages})
        for page in self.pages:
            with self.subTest(page=page.key):
                self.assertEqual(self.lists[page.key], fresh_ranking(self.pages, page))
        self.assertTrue(all(self.lists[page.key] for page in self.pages[: TWELVE - 1]))

    def test_the_query_page_is_absent_from_its_own_list_and_present_for_the_others(self) -> None:
        decisions = self.pages[: TWELVE - 1]
        for i, page in enumerate(decisions):
            with self.subTest(page=page.key):
                self.assertNotIn(page.key, self.lists[page.key])
                neighbours = [decisions[j].key for j in (i - 1, i + 1) if 0 <= j < len(decisions)]
                for neighbour in neighbours:
                    self.assertIn(page.key, self.lists[neighbour])

    def test_pages_of_another_type_are_not_compared(self) -> None:
        concept, last_decision = self.pages[TWELVE - 1], self.pages[TWELVE - 2]
        self.assertIn(concept.key, fresh_ranking(self.pages, last_decision, same_page_type=False))
        self.assertNotIn(concept.key, self.lists[last_decision.key])
        self.assertEqual(self.lists[concept.key], [])


# ── End to end ────────────────────────────────────────────────


@unittest.skipUnless(HAS_FTS5, NO_FTS5)
class EndToEndTest(unittest.TestCase):
    """Runs on both synthetic sets: the results, the timing keys, the same bytes twice (FR-016)."""

    def run_set(self, study_set: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Path]:
        tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        root, out_dir = tmp / "repo", tmp / "results"
        protocol = write_study(root)
        code, stderr = run(root, study_set, out_dir)
        self.assertEqual(code, 0, stderr)
        results = read_json(out_dir / f"{study_set}{audit.RESULTS_SUFFIX}")
        timing = read_json(out_dir / f"{study_set}{audit.TIMING_SUFFIX}")
        self.assertEqual(
            sorted(path.name for path in out_dir.iterdir()), sorted([f"{study_set}.json", f"{study_set}-timing.json"])
        )
        return results, timing, protocol, root

    def test_the_development_set(self) -> None:
        results, timing, protocol, root = self.run_set(audit.DEVELOPMENT)
        development = audit.study_set(audit.DEVELOPMENT, protocol)
        self.assertEqual(
            results["inputs"],
            {
                development.corpus_json: sha256_of(root / development.corpus_json),
                development.labels: sha256_of(root / development.labels),
                audit.PROTOCOL_PATH: sha256_of(root / audit.PROTOCOL_PATH),
            },
        )
        self.assertEqual(results["ranker"]["ranker_config_hash"], discovery.ranker_config_hash())
        self.assertEqual(results["pages"], len(DEV_ROWS))
        self.assertEqual(results["paths"][A], "decisions/zebra-yak.md")
        self.assertEqual(results["lists"], DEV_LISTS)
        self.assertEqual(
            results["true_pairs"], {"n": 3, "by_disposition": {CONFLICTING: 1, REDUNDANT: 1, SUPERSEDES: 1}}
        )
        for name, k in zip(CANDIDATES, (1, 3, 5), strict=True):
            with self.subTest(candidate=name):
                candidate = results["candidates"][name]
                self.assertEqual(candidate["k"], k)
                self.assertEqual(candidate["pairs"], DEV_PAIRS)
                self.assertEqual(
                    {key: candidate[key] for key in ("flagged", "true", "false", "found", "non_restatement_found")},
                    {"flagged": 3, "true": 2, "false": 1, "found": 2, "non_restatement_found": 1},
                )
                readings = candidate["not_binding"]
                self.assertFalse(readings["binding"])
                self.assertEqual(
                    readings["false_by_disposition"], {COMPANION: 0, "distinct-by-precondition": 0, UNRELATED: 1}
                )
                self.assertEqual(
                    readings["by_scope"], {"one-feature": 1, "within-repository": 1, "cross-repository": 1}
                )
                self.assertEqual(readings["flagged_by_restatement"], {"a": 1, "b": 0, "c": 0, "-": 2})
                self.assertEqual(readings["found_by_restatement"], {"a": 1, "b": 0, "c": 0, "-": 1})
                self.assertEqual(readings["per_100_pages"], {"flagged": 37.5, "true": 25.0, "false": 12.5})
                self.assertEqual(readings["groups_with_a_flagged_true_pair"], ["g-1"])
                self.assertNotIn("bar", candidate)
        self.assertEqual(
            results["stop_rule"],
            {
                "false_not_above_true": {TOP_1: True, TOP_3: True, TOP_5: True},
                "outcome": "go",
                "line": "Development stage: go",
            },
        )
        for key in ("verdict", "winner", "winner_line", "post_hoc"):
            self.assertNotIn(key, results)
        self.assertEqual(set(timing), {"study", "set", "clock", "pages", "seconds"})
        self.assertEqual(timing["pages"], len(DEV_ROWS))

    def test_the_held_out_set(self) -> None:
        results, timing, _protocol, root = self.run_set(audit.HELD_OUT)
        expected_inputs = {rel: sha256_of(root / rel) for _, rel in audit.FREEZE_PINS}
        expected_inputs[audit.FREEZE_PATH] = sha256_of(root / audit.FREEZE_PATH)
        self.assertEqual(results["inputs"], expected_inputs)
        self.assertEqual(results["pages"], len(held_out_rows()))
        self.assertEqual(results["paths"][held_page(0, "a")], "decisions/amber-anvil.md")
        self.assertIn(f"{SOLO} ->", results["lists"])
        self.assertEqual(
            results["true_pairs"], {"n": 8, "by_disposition": {CONFLICTING: 0, REDUNDANT: 8, SUPERSEDES: 0}}
        )
        no_origin = [f"{held_page(3, 'a')} {held_page(3, 'b')} 1/1 redundant within-repository -"]
        for name in CANDIDATES:
            with self.subTest(candidate=name):
                candidate = results["candidates"][name]
                self.assertEqual(candidate["pairs"], held_out_pair_lines())
                self.assertEqual(
                    {key: candidate[key] for key in ("flagged", "true", "false", "found", "non_restatement_found")},
                    {"flagged": 9, "true": 8, "false": 1, "found": 8, "non_restatement_found": 3},
                )
                self.assertEqual(
                    candidate["bar"],
                    {
                        "testable": True,
                        "recall": True,
                        "false_not_above_true": True,
                        "non_restatement": True,
                        "passes": True,
                    },
                )
                readings = candidate["not_binding"]
                self.assertEqual(readings["flagged_by_restatement"], {"a": 3, "b": 1, "c": 1, "-": 4})
                self.assertEqual(readings["found_by_restatement"], {"a": 3, "b": 1, "c": 1, "-": 3})
                self.assertEqual(
                    readings["by_scope"], {"one-feature": 4, "within-repository": 5, "cross-repository": 0}
                )
                self.assertEqual(readings["per_100_pages"], {"flagged": 47.37, "true": 42.11, "false": 5.26})
                self.assertEqual(readings["groups_with_a_flagged_true_pair"], [f"g{i}" for i in range(8)])
                self.assertEqual(readings["no_origin_issue_found"], no_origin)
        self.assertEqual(results["verdict"], "winner")
        self.assertEqual(results["winner"], TOP_1)
        self.assertEqual(results["winner_line"], "Winner: mutual-top-1")
        self.assertNotIn("stop_rule", results)
        self.assertNotIn("post_hoc", results)
        self.assertEqual(set(timing), {"study", "set", "clock", "pages", "seconds", "synthetic"})
        self.assertEqual(set(timing["synthetic"]), {"pages", "seconds"})
        self.assertEqual(timing["synthetic"]["pages"], frozen_protocol()["time_bound"]["pages"])

    def test_two_runs_write_the_same_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            write_study(root)
            for study_set in audit.SETS:
                outputs = []
                for name in ("first", "second"):
                    code, stderr = run(root, study_set, Path(tmp) / study_set / name)
                    self.assertEqual(code, 0, stderr)
                    outputs.append((Path(tmp) / study_set / name / f"{study_set}.json").read_bytes())
                with self.subTest(study_set=study_set):
                    self.assertEqual(outputs[0], outputs[1])
                    self.assertTrue(outputs[0].endswith(b"}\n"))
                    self.assertFalse(outputs[0].endswith(b"\n\n"))


# ── Refusals (FR-015) ─────────────────────────────────────────


class RefusalTest(unittest.TestCase):
    """A changed input or a missing freeze is refused, naming the file and both values, and nothing is written."""

    def assert_refused(self, root: Path, study_set: str, out_dir: Path, *names: str) -> None:
        code, stderr = run(root, study_set, out_dir)
        self.assertEqual(code, audit.REFUSED)
        self.assertFalse(out_dir.exists())
        for name in names:
            with self.subTest(name=name):
                self.assertIn(name, stderr)

    def test_a_changed_development_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            protocol = write_study(root)
            labels = root / audit.study_set(audit.DEVELOPMENT, protocol).labels
            expected = sha256_of(labels)
            labels.write_text(labels.read_text(encoding="utf-8") + " ", encoding="utf-8")
            self.assert_refused(root, audit.DEVELOPMENT, Path(tmp) / "results", expected, sha256_of(labels))

    def test_a_changed_development_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            protocol = write_study(root)
            page = root / audit.study_set(audit.DEVELOPMENT, protocol).corpus_root / A
            expected = sha256_of(page)
            page.write_text(page.read_text(encoding="utf-8") + "changed\n", encoding="utf-8")
            self.assert_refused(root, audit.DEVELOPMENT, Path(tmp) / "results", A, expected, sha256_of(page))

    def test_a_missing_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            write_study(root, freeze=False)
            self.assert_refused(root, audit.HELD_OUT, Path(tmp) / "results", audit.FREEZE_PATH)

    def test_held_out_labels_changed_after_the_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            protocol = write_study(root)
            labels = root / audit.study_set(audit.HELD_OUT, protocol).labels
            expected = sha256_of(labels)
            labels.write_text(labels.read_text(encoding="utf-8") + " ", encoding="utf-8")
            self.assert_refused(
                root, audit.HELD_OUT, Path(tmp) / "results", "labels_sha256", expected, sha256_of(labels)
            )

    def test_a_changed_protocol_after_the_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            write_study(root)
            protocol = root / audit.PROTOCOL_PATH
            protocol.write_text(protocol.read_text(encoding="utf-8") + " ", encoding="utf-8")
            self.assert_refused(root, audit.HELD_OUT, Path(tmp) / "results", "protocol_sha256")

    def test_a_changed_held_out_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            protocol = write_study(root)
            page = root / audit.study_set(audit.HELD_OUT, protocol).corpus_root / SOLO
            expected = sha256_of(page)
            page.write_text("changed\n", encoding="utf-8")
            self.assert_refused(root, audit.HELD_OUT, Path(tmp) / "results", SOLO, expected, sha256_of(page))


# ── The repository, and the parser ────────────────────────────


@unittest.skipUnless(HAS_FTS5, NO_FTS5)
class RepositoryUnchangedTest(unittest.TestCase):
    """A run on the study's own inputs with ``--out-dir`` elsewhere leaves ``eval/`` as it was; nothing is read back."""

    def test_eval_is_unchanged_by_a_run_elsewhere(self) -> None:
        before = snapshot(EVAL_DIR)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "results"
            code, stderr = run(None, audit.DEVELOPMENT, out_dir)
            self.assertEqual(code, 0, stderr)
            written = sorted(path.name for path in out_dir.iterdir())
        self.assertEqual(snapshot(EVAL_DIR), before)
        self.assertEqual(written, sorted([f"{audit.DEVELOPMENT}.json", f"{audit.DEVELOPMENT}-timing.json"]))


class HelpTest(unittest.TestCase):
    def test_help_exits_zero(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(audit.main(["--help"]), 0)


if __name__ == "__main__":
    unittest.main()
