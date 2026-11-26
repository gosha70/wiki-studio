# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""US2: the similar-pages ranking script on synthetic inputs (issue 121, FR-013).

Each end-to-end test writes a small corpus, labels, an issue 54 style fixture and a protocol to a temporary
directory laid out as the repository is; the protocol is the frozen ``protocol.json`` with its inputs, tries, bar and
fixture fields replaced, so the rules under test are the frozen rules. Covered: the slug rule and its collisions;
``query_text``; the query page absent from its try's index; the page-type filter; the tries built from the labels;
every edge of the bar; the noise labels; the refusal on a changed input, writing nothing; the same ``ranks.json``
bytes on two runs; ``eval/`` unchanged by a run with ``--out-dir`` elsewhere; and ``--help``. Cases that rank skip
when this Python's SQLite has no FTS5. The committed results are checked in US3, not here.
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

from eval.similar import rank
from wiki_studio import discovery
from wiki_studio.search_index import build_document

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = REPO_ROOT / "eval"
CACHE_DIR_NAME = "__pycache__"
HAS_FTS5 = discovery.fts5_available().available
NO_FTS5 = "this Python's SQLite has no FTS5"

DECISION = "decision"
CONCEPT = "concept"
INCIDENT = "incident"
COMPANION = "companion"

A = "repo/fam/a.md"
B = "repo/fam/b.md"
C = "repo/fam/c.md"
D = "repo/fam/d.md"
E = "repo/fam/e.md"
F = "repo/fam/f.md"
G = "repo/fam/g.md"

# page, page type, title, body. A and B share a title (a slug collision) and their words; C rules later than D;
# E shares one word with A and B; F is a concept page with every word; G shares none.
CORPUS: list[tuple[str, str, str, str]] = [
    (A, DECISION, "Shared title", "zebra yak walrus"),
    (B, DECISION, "Shared title", "zebra yak walrus"),
    (C, DECISION, "Later ruling", "kiwi lemon mango"),
    (D, DECISION, "Earlier ruling", "kiwi lemon mango"),
    (E, DECISION, "Noise page", "zebra"),
    (F, CONCEPT, "Concept page", "zebra yak walrus kiwi lemon mango"),
    (G, DECISION, "Unrelated", "quartz"),
]
LABELS: dict[str, Any] = {
    "pairs": [
        {"pair": [D, C], "disposition": rank.SUPERSEDES},
        {"pair": [B, A], "disposition": rank.REDUNDANT},
        {"pair": [A, E], "disposition": COMPANION},
    ],
    "cross_pairs": [],
}
TRIES = [
    {"query": A, "partner": B, "disposition": rank.REDUNDANT},
    {"query": B, "partner": A, "disposition": rank.REDUNDANT},
    {"query": C, "partner": D, "disposition": rank.SUPERSEDES},
]
BAR = {"min_found": 2, "tries": 3, "min_supersedes_found": 1, "supersedes_tries": 1}

P = "decisions/p.md"
Q = "decisions/q.md"
OLD = "decisions/old.md"
R = "incidents/r.md"
S = "decisions/s.md"
MISSING_PAGE = "decisions/missing.md"
FIXTURE_LABELS: dict[str, Any] = {
    "pattern_pairs": [{"pair": [Q, P], "disposition": rank.REDUNDANT}],
    "background_pairs": [
        {"pair": [R, S], "disposition": rank.REDUNDANT},
        {"pair": [P, S], "disposition": rank.UNRELATED},
    ],
}
FIXTURE_TRIES = [
    {"query": P, "partner": Q, "disposition": rank.REDUNDANT},
    {"query": Q, "partner": P, "disposition": rank.REDUNDANT},
]


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, document: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def page_text(page_type: str, title: str, body: str, extra: str = "") -> str:
    return f"---\npage_type: {page_type}\nslug: corpus-slug\ntitle: {title}\nstatus: stable\n{extra}---\n\n{body}\n"


def fixture_pages() -> dict[str, str]:
    """The fixture wiki: index.md links every page, log.md and a missing page; one page is superseded."""
    links = [P, Q, OLD, R, S, "log.md", MISSING_PAGE]
    index = page_text("index", "Index", "\n".join(f"- [{link}]({link})" for link in links))
    return {
        rank.INDEX_NAME: index,
        P: page_text(DECISION, "Echo rule", "echo foxtrot"),
        Q: page_text(DECISION, "Echo again", "echo foxtrot"),
        OLD: page_text(DECISION, "Old echo", "echo foxtrot", extra=f"superseded_by: {Q}\n"),
        R: page_text(INCIDENT, "Golf incident", "golf hotel"),
        S: page_text(DECISION, "Golf rule", "golf hotel"),
    }


def frozen_protocol() -> dict[str, Any]:
    document: dict[str, Any] = json.loads((REPO_ROOT / rank.PROTOCOL_PATH).read_text(encoding="utf-8"))
    return document


def write_study(root: Path, **overrides: Any) -> dict[str, Any]:
    """A synthetic repository under ``root``; the protocol written, with ``overrides`` applied, is returned."""
    protocol = frozen_protocol()
    corpus_root = root / protocol["corpus_pages"]["root"]
    entries = []
    for page, page_type, title, body in CORPUS:
        path = corpus_root / page
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page_text(page_type, title, body), encoding="utf-8")
        entries.append({"page": page, "title": title, "sha256": sha256_of(path)})
    write_json(root / rank.CORPUS_JSON_PATH, {"pages": entries})
    write_json(root / rank.LABELS_PATH, LABELS)
    write_json(root / rank.FIXTURE_LABELS_PATH, FIXTURE_LABELS)
    fixture = protocol["not_binding"]["fixture"]
    wiki_rel = fixture["wiki"]
    for rel, text in fixture_pages().items():
        path = root / wiki_rel / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    inputs = [rank.CORPUS_JSON_PATH, rank.LABELS_PATH, rank.FIXTURE_LABELS_PATH]
    inputs += [f"{wiki_rel}/{rel}" for rel in fixture_pages()]
    protocol["inputs"] = [{"path": rel, "sha256": sha256_of(root / rel)} for rel in inputs]
    protocol["tries"] = TRIES
    protocol["bar"] = BAR
    fixture["tries"] = FIXTURE_TRIES
    fixture["never_listed"] = {"pair": [S, R], "disposition": rank.REDUNDANT}
    fixture["superseded_pages_left_out"] = [OLD]
    protocol.update(overrides)
    write_json(root / rank.PROTOCOL_PATH, protocol)
    return protocol


def run(root: Path | None, out_dir: Path) -> tuple[int, str]:
    """``rank.main`` with ``--out-dir``; the exit code and what it wrote to stderr."""
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = rank.main(["--out-dir", str(out_dir)], root=root)
    return code, stderr.getvalue()


def read_json(path: Path) -> dict[str, Any]:
    document: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return document


def snapshot(directory: Path) -> dict[str, str]:
    """Path and sha256 of every file under ``directory``, bytecode caches left out (they are never committed)."""
    return {
        path.relative_to(directory).as_posix(): sha256_of(path)
        for path in sorted(directory.rglob("*"))
        if path.is_file() and CACHE_DIR_NAME not in path.parts
    }


def corpus_page(page: str) -> rank.Page:
    for key, page_type, title, body in CORPUS:
        if key == page:
            return rank.Page(key, f"decisions/{Path(key).stem}.md", page_text(page_type, title, body), page_type)
    raise KeyError(page)


class SlugTest(unittest.TestCase):
    """The title-slug rule and its collisions (FR-003)."""

    def test_punctuation_case_and_digits(self) -> None:
        self.assertEqual(rank.slug_of("Host + Origin only."), "host-origin-only")
        self.assertEqual(rank.slug_of("Rule 42: Keep IT_simple"), "rule-42-keep-it-simple")
        self.assertEqual(rank.slug_of("--Already-slugged--"), "already-slugged")

    def test_a_non_ascii_letter_is_a_separator(self) -> None:
        self.assertEqual(rank.slug_of("Café déjà vu"), "caf-d-j-vu")

    def test_an_empty_result_is_untitled(self) -> None:
        self.assertEqual(rank.slug_of(""), rank.UNTITLED)
        self.assertEqual(rank.slug_of("!!! ---"), rank.UNTITLED)
        self.assertEqual(rank.slug_of("é"), rank.UNTITLED)

    def test_paths_use_the_template(self) -> None:
        paths = rank.slug_paths([{"page": "x.md", "title": "One Two"}])
        self.assertEqual(paths, {"x.md": "decisions/one-two.md"})

    def test_collisions_get_2_then_3(self) -> None:
        entries = [{"page": f"{n}.md", "title": "Same title"} for n in ("a", "b", "c")]
        self.assertEqual(
            rank.slug_paths(entries),
            {
                "a.md": "decisions/same-title.md",
                "b.md": "decisions/same-title-2.md",
                "c.md": "decisions/same-title-3.md",
            },
        )
        self.assertEqual(rank.slug_collisions(entries), {"same-title": ["a.md", "b.md", "c.md"]})

    def test_a_numbered_value_already_taken_is_skipped(self) -> None:
        later_holder = [
            {"page": "a.md", "title": "Foo"},
            {"page": "b.md", "title": "Foo"},
            {"page": "c.md", "title": "Foo 2"},
        ]
        self.assertEqual(
            rank.slug_paths(later_holder),
            {"a.md": "decisions/foo.md", "b.md": "decisions/foo-3.md", "c.md": "decisions/foo-2.md"},
        )
        earlier_holder = [
            {"page": "a.md", "title": "Foo 2"},
            {"page": "b.md", "title": "Foo"},
            {"page": "c.md", "title": "Foo"},
        ]
        self.assertEqual(
            rank.slug_paths(earlier_holder),
            {"a.md": "decisions/foo-2.md", "b.md": "decisions/foo.md", "c.md": "decisions/foo-3.md"},
        )
        self.assertEqual(rank.slug_collisions(earlier_holder), {"foo": ["b.md", "c.md"]})

    def test_a_collision_between_different_titles_follows_the_same_rule(self) -> None:
        entries = [{"page": "a.md", "title": "Keep it"}, {"page": "b.md", "title": "keep: IT!"}]
        self.assertEqual(rank.slug_paths(entries), {"a.md": "decisions/keep-it.md", "b.md": "decisions/keep-it-2.md"})
        self.assertEqual(rank.slug_collisions(entries), {"keep-it": ["a.md", "b.md"]})


class QueryTextTest(unittest.TestCase):
    """The query is the frontmatter title, one space, the body; no other frontmatter key (FR-004)."""

    def assert_query(self, text: str, expected: str) -> None:
        document = build_document("decisions/x.md", text)
        self.assertEqual(rank.query_text(text), document.title + " " + document.body)
        self.assertEqual(rank.query_text(text), expected)

    def test_a_page_with_frontmatter(self) -> None:
        text = (
            "---\npage_type: decision\nslug: sluggy\ntitle: My Title\nsources:\n  - path: x\n---\n"
            "\n## Decision\n\nBody.\n"
        )
        self.assert_query(text, "My Title \n## Decision\n\nBody.")
        query = rank.query_text(text)
        for word in ("sources", "slug", "sluggy", "page_type"):
            with self.subTest(word=word):
                self.assertNotIn(word, query)

    def test_a_page_without_frontmatter(self) -> None:
        self.assert_query("# Heading\n\nBody.\n", " # Heading\n\nBody.")

    def test_a_page_with_an_unclosed_block(self) -> None:
        self.assert_query("---\ntitle: Open\nBody.\n", "Open ---\ntitle: Open\nBody.")

    def test_the_readings_that_are_not_binding(self) -> None:
        text = "---\ntitle: My Title\n---\nBody.\n"
        self.assertEqual(rank.READINGS[rank.WHOLE_PAGE](text), text)
        self.assertEqual(rank.READINGS[rank.BODY_ONLY](text), "Body.")


class TriesTest(unittest.TestCase):
    """The tries built from the labels: both ways for redundant, the later page for supersedes (FR-005)."""

    def test_redundant_both_ways_then_supersedes_in_labels_order(self) -> None:
        tries = rank.build_tries(LABELS, rank.later_pages(TRIES), frozenset(frozen_protocol()["true_dispositions"]))
        self.assertEqual(
            tries,
            [
                rank.Try(A, B, rank.REDUNDANT),
                rank.Try(B, A, rank.REDUNDANT),
                rank.Try(C, D, rank.SUPERSEDES),
            ],
        )

    def test_cross_pairs_are_tried(self) -> None:
        labels = {"pairs": [], "cross_pairs": [{"pair": [E, G], "disposition": rank.REDUNDANT}]}
        tries = rank.build_tries(labels, {}, frozenset({rank.REDUNDANT}))
        self.assertEqual(tries, [rank.Try(E, G, rank.REDUNDANT), rank.Try(G, E, rank.REDUNDANT)])

    def test_a_supersedes_pair_without_a_later_page_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            rank.build_tries(LABELS, {}, frozenset({rank.REDUNDANT, rank.SUPERSEDES}))

    def test_tries_that_differ_from_the_protocol_are_reported(self) -> None:
        tries = rank.build_tries(LABELS, rank.later_pages(TRIES), frozenset({rank.REDUNDANT, rank.SUPERSEDES}))
        self.assertEqual(rank.check_tries("tries", tries, TRIES), [])
        self.assertTrue(rank.check_tries("tries", tries, list(reversed(TRIES))))

    def test_the_fixture_pair_of_two_page_types_is_never_listed(self) -> None:
        types = {P: DECISION, Q: DECISION, R: INCIDENT, S: DECISION}
        tries, never_listed = rank.build_fixture_tries(FIXTURE_LABELS, types, same_page_type=True)
        self.assertEqual(tries, [rank.Try(P, Q, rank.REDUNDANT), rank.Try(Q, P, rank.REDUNDANT)])
        self.assertEqual(
            never_listed, [{"pair": [S, R], "disposition": rank.REDUNDANT, "page_types": [DECISION, INCIDENT]}]
        )


class BarTest(unittest.TestCase):
    """The bar at its edges: 10 of 13 tries and 1 of the 3 supersedes tries (FR-006)."""

    def setUp(self) -> None:
        self.bar = frozen_protocol()["bar"]

    def test_9_of_13_fails(self) -> None:
        self.assertEqual(rank.verdict(9, 3, self.bar), rank.FAIL)

    def test_10_of_13_with_no_supersedes_found_fails(self) -> None:
        self.assertEqual(rank.verdict(10, 0, self.bar), rank.FAIL)

    def test_10_of_13_with_one_supersedes_found_passes(self) -> None:
        self.assertEqual(rank.verdict(10, 1, self.bar), rank.PASS)


class ScoreTest(unittest.TestCase):
    """The list, the partner's rank, found, and the noise labels (FR-006, FR-007)."""

    def test_list_rank_found_and_others(self) -> None:
        labels = rank.pair_labels(LABELS)
        record = rank.score_try(rank.Try(A, B, rank.REDUNDANT), [E, G, C, D, F, B], 5, labels)
        self.assertEqual(record["list"], [E, G, C, D, F])
        self.assertEqual(record["partner_rank"], 6)
        self.assertFalse(record["found"])
        self.assertEqual(
            record["others"],
            [
                {"page": E, "label": COMPANION},
                {"page": G, "label": rank.UNRELATED},
                {"page": C, "label": rank.UNRELATED},
                {"page": D, "label": rank.UNRELATED},
                {"page": F, "label": rank.UNRELATED},
            ],
        )

    def test_a_partner_that_matches_nothing_has_no_rank(self) -> None:
        record = rank.score_try(rank.Try(A, B, rank.REDUNDANT), [E], 5)
        self.assertIsNone(record["partner_rank"])
        self.assertNotIn("others", record)

    def test_noise_counts_by_label_and_summary(self) -> None:
        labels = rank.pair_labels(LABELS)
        records = [
            rank.score_try(rank.Try(A, B, rank.REDUNDANT), [B, E], 5, labels),
            rank.score_try(rank.Try(B, A, rank.REDUNDANT), [A, E, G], 5, labels),
            rank.score_try(rank.Try(C, D, rank.SUPERSEDES), [G], 5, labels),
        ]
        self.assertEqual(rank.noise(records), {COMPANION: 1, rank.UNRELATED: 3})
        self.assertEqual(
            rank.summarize(records),
            {
                "found": 2,
                "tries": 3,
                "supersedes_found": 0,
                "supersedes_tries": 1,
                "pairs_with_a_found_try": 1,
                "pairs": 2,
            },
        )


@unittest.skipUnless(HAS_FTS5, NO_FTS5)
class RankingTest(unittest.TestCase):
    """The query page is not in its try's index; the page-type filter keeps the query page's type (FR-003)."""

    def setUp(self) -> None:
        self.pages = [corpus_page(page) for page, *_ in CORPUS]
        self.query_page = corpus_page(A)
        self.query = rank.query_text(self.query_page.text)

    def compared(self, *, same_page_type: bool = True, include_query_page: bool = False) -> list[str]:
        return rank.compared_pages(
            self.pages,
            self.query_page,
            self.query,
            same_page_type=same_page_type,
            include_query_page=include_query_page,
        )

    def test_the_query_page_is_absent_from_its_index(self) -> None:
        self.assertNotIn(A, self.compared())
        self.assertIn(A, self.compared(include_query_page=True))

    def test_pages_of_another_type_are_not_compared(self) -> None:
        self.assertNotIn(F, self.compared())
        self.assertIn(F, self.compared(same_page_type=False))

    def test_only_matching_pages_are_compared_best_first(self) -> None:
        self.assertEqual(self.compared(), [B, E])


@unittest.skipUnless(HAS_FTS5, NO_FTS5)
class EndToEndTest(unittest.TestCase):
    """A run on the synthetic study: the results, the same bytes twice (FR-012)."""

    def test_ranks_and_timing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, out_dir = Path(tmp) / "repo", Path(tmp) / "results"
            write_study(root)
            code, stderr = run(root, out_dir)
            self.assertEqual(code, 0, stderr)
            ranks = read_json(out_dir / rank.RANKS_NAME)
            timing = read_json(out_dir / rank.TIMING_NAME)
            protocol_sha256 = sha256_of(root / rank.PROTOCOL_PATH)
        self.assertEqual(
            ranks["summary"],
            {
                "found": 3,
                "tries": 3,
                "supersedes_found": 1,
                "supersedes_tries": 1,
                "pairs_with_a_found_try": 2,
                "pairs": 2,
                "verdict": rank.PASS,
            },
        )
        self.assertEqual([entry["list"] for entry in ranks["tries"]], [[B, E], [A, E], [D]])
        self.assertEqual([entry["partner_rank"] for entry in ranks["tries"]], [1, 1, 1])
        self.assertEqual(
            [entry["others"] for entry in ranks["tries"]],
            [[{"page": E, "label": COMPANION}], [{"page": E, "label": rank.UNRELATED}], []],
        )
        self.assertEqual(ranks["noise"], {COMPANION: 1, rank.UNRELATED: 1})
        self.assertEqual(ranks["k"], 5)
        self.assertEqual(ranks["paths"][A], "decisions/shared-title.md")
        self.assertEqual(ranks["paths"][B], "decisions/shared-title-2.md")
        self.assertEqual(len(ranks["paths"]), len(CORPUS))
        self.assertEqual(ranks["collisions"], {"shared-title": [A, B]})
        self.assertEqual(ranks["inputs"][rank.PROTOCOL_PATH], protocol_sha256)
        self.assertEqual(ranks["ranker"]["ranker_config_hash"], discovery.ranker_config_hash())
        self.assertNotIn("post_hoc", ranks)
        for name in (rank.WHOLE_PAGE, rank.BODY_ONLY):
            with self.subTest(reading=name):
                self.assertFalse(ranks["readings"][name]["binding"])
                self.assertEqual(ranks["readings"][name]["summary"]["tries"], 3)
        fixture = ranks["fixture"]
        self.assertFalse(fixture["binding"])
        self.assertEqual([entry["list"] for entry in fixture["tries"]], [[Q, S], [P]])
        self.assertEqual(fixture["summary"]["found"], 2)
        self.assertEqual(
            fixture["never_listed"],
            [{"pair": [S, R], "disposition": rank.REDUNDANT, "page_types": [DECISION, INCIDENT]}],
        )
        self.assertEqual(fixture["superseded_left_out"], [OLD])
        self.assertEqual(set(timing), {"study", "clock", "pages", "tries", "fixture_pages", "fixture_tries", "seconds"})
        self.assertEqual(set(timing["seconds"]), {"binding", rank.WHOLE_PAGE, rank.BODY_ONLY, "fixture"})
        self.assertEqual((timing["pages"], timing["tries"], timing["fixture_tries"]), (len(CORPUS), 3, 2))

    def test_two_runs_write_the_same_ranks_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            write_study(root)
            outputs = []
            for name in ("first", "second"):
                code, stderr = run(root, Path(tmp) / name)
                self.assertEqual(code, 0, stderr)
                outputs.append((Path(tmp) / name / rank.RANKS_NAME).read_bytes())
        self.assertEqual(outputs[0], outputs[1])
        self.assertTrue(outputs[0].endswith(b"}\n"))
        self.assertFalse(outputs[0].endswith(b"\n\n"))


class RefusalTest(unittest.TestCase):
    """A changed input is refused, naming the file and both values, and nothing is written (FR-011)."""

    def assert_refused(self, root: Path, out_dir: Path, *names: str) -> None:
        code, stderr = run(root, out_dir)
        self.assertEqual(code, rank.REFUSED)
        self.assertFalse(out_dir.exists())
        for name in names:
            with self.subTest(name=name):
                self.assertIn(name, stderr)

    def test_a_changed_corpus_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            protocol = write_study(root)
            page = root / protocol["corpus_pages"]["root"] / A
            expected = sha256_of(page)
            page.write_text(page.read_text(encoding="utf-8") + "changed\n", encoding="utf-8")
            self.assert_refused(root, Path(tmp) / "results", A, expected, sha256_of(page))

    def test_a_changed_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            write_study(root)
            labels = root / rank.LABELS_PATH
            expected = sha256_of(labels)
            labels.write_text(labels.read_text(encoding="utf-8") + " ", encoding="utf-8")
            self.assert_refused(root, Path(tmp) / "results", rank.LABELS_PATH, expected, sha256_of(labels))

    def test_a_changed_fixture_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            protocol = write_study(root)
            rel = f"{protocol['not_binding']['fixture']['wiki']}/{P}"
            (root / rel).write_text("changed\n", encoding="utf-8")
            self.assert_refused(root, Path(tmp) / "results", rel)

    def test_tries_that_differ_from_the_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            write_study(root, tries=list(reversed(TRIES)))
            self.assert_refused(root, Path(tmp) / "results", "tries")


@unittest.skipUnless(HAS_FTS5, NO_FTS5)
class RepositoryUnchangedTest(unittest.TestCase):
    """A run on the study's own inputs with ``--out-dir`` elsewhere leaves ``eval/`` as it was."""

    def test_eval_is_unchanged_by_a_run_elsewhere(self) -> None:
        before = snapshot(EVAL_DIR)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "results"
            code, stderr = run(None, out_dir)
            self.assertEqual(code, 0, stderr)
            written = sorted(path.name for path in out_dir.iterdir())
        self.assertEqual(snapshot(EVAL_DIR), before)
        self.assertEqual(written, sorted((rank.RANKS_NAME, rank.TIMING_NAME)))


class HelpTest(unittest.TestCase):
    def test_help_exits_zero(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(rank.main(["--help"]), 0)


if __name__ == "__main__":
    unittest.main()
