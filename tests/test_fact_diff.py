# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.5.0: an ``update`` that drops a citation, identifier or number is flagged in ``plan.json`` (FR-014, FR-015)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from wiki_studio import api
from wiki_studio.fact_diff import removed_facts
from wiki_studio.paths import WikiPaths
from wiki_studio.proposal import PageEdit

PAGE = (
    "---\npage_type: decision\nslug: retry-backoff\ntitle: Retry backoff\nstatus: draft\nlast_reviewed: 2026-10-16\n"
    "sources:\n  - path: notes.md\n  - path: docs/retry.md\n---\n\n# Retry backoff\n\n"
    "## Decision\n\nStart at 250 ms and call `retry_budget()` per attempt, as `src/retry.py:42` does.\n\n"
    "## Context\n\nAgreed with the platform team; see src/retry.py:42.\n\n"
    "## Alternatives considered\n\nFixed 1 s delay.\n\n"
    "## Consequences\n\nLong outages wait at most 8 s between tries.\n"
)


def _edit(page: str, *replacements: tuple[str, str]) -> str:
    for old, new in replacements:
        page = page.replace(old, new)
    return page


# PAGE without the docs/retry.md citation, the retry_budget identifier and the "8 s" number.
DROPPED = _edit(
    PAGE,
    ("  - path: docs/retry.md\n", ""),
    (" and call `retry_budget()` per attempt", ""),
    ("at most 8 s", "a while"),
)


class TestRemovedFacts(unittest.TestCase):
    def test_identical_page_removes_nothing(self) -> None:
        self.assertEqual(removed_facts(PAGE, PAGE), [])

    def test_dropped_citation_identifier_and_number(self) -> None:
        new = DROPPED
        self.assertEqual(removed_facts(PAGE, new), ["docs/retry.md", "retry_budget", "8 s"])

    def test_body_path_line_reference_dropped(self) -> None:
        new = PAGE.replace(", as `src/retry.py:42` does", "").replace("; see src/retry.py:42", "")
        self.assertEqual(removed_facts(PAGE, new), ["src/retry.py:42"])

    def test_moved_citation_is_kept(self) -> None:
        # Frontmatter → body, and a path:line between sections.
        new = PAGE.replace("  - path: docs/retry.md\n", "").replace(
            "Fixed 1 s delay.", "Fixed 1 s delay (path: docs/retry.md)."
        )
        self.assertEqual(removed_facts(PAGE, new), [])
        self.assertEqual(removed_facts("Ref `a.py:3`.\n\n## B\n\nNone.\n", "Ref.\n\n## B\n\nSee a.py:3.\n"), [])

    def test_path_with_line_keeps_path_only_citation(self) -> None:
        new = PAGE.replace("  - path: docs/retry.md\n", "").replace("Fixed 1 s", "Fixed 1 s (docs/retry.md:7)")
        self.assertEqual(removed_facts(PAGE, new), [])

    def test_reflowed_paragraph_is_kept(self) -> None:
        old = "Start at 250 ms and call `retry budget` per attempt.\n"
        new = "Start at 250\nms and call `retry\nbudget` per\nattempt.\n"
        self.assertEqual(removed_facts(old, new), [])

    def test_normalization(self) -> None:
        old = "Limit 1,000 tokens, 50 %, 2 KB, `foo()` and 30ms.\n"
        new = "Limit 1000 TOKENS, 50%, 2 kb, ` foo ` and 30 ms.\n"
        self.assertEqual(removed_facts(old, new), [])

    def test_numbers_need_a_listed_unit(self) -> None:
        self.assertEqual(removed_facts("Wait 3 days, retry 2 times, v1.5 s.\n", "Wait.\n"), [])
        self.assertEqual(removed_facts("Keep 12 lines and 5 min.\n", "Keep.\n"), ["12 lines", "5 min"])

    def test_fenced_code_is_not_an_identifier_source(self) -> None:
        old = "Run:\n\n```sh\necho `date` 5 ms\n```\n"
        self.assertEqual(removed_facts(old, "Run.\n"), [])

    def test_page_without_or_with_broken_frontmatter(self) -> None:
        self.assertEqual(removed_facts("---\nno closing\n`x`\n", ""), ["x"])
        self.assertEqual(removed_facts("---\n---\nBody `y`.\n", "---\n---\nBody.\n"), ["y"])


class TestProposeFactWarnings(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-fact-")
        self.root = Path(self._tmp.name).resolve()
        (self.root / "notes.md").write_text("# notes\n", encoding="utf-8")
        self.paths = WikiPaths.for_root(self.root)
        api.init(self.paths)
        live = self.paths.wiki_dir / "decisions" / "retry-backoff.md"
        live.parent.mkdir(parents=True)
        live.write_text(PAGE, encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def plan_edits(self, edits: list[PageEdit], name: str) -> list[dict[str, object]]:
        written = api.propose(edits, self.paths, name=name)
        edits_out: list[dict[str, object]] = json.loads((written / "plan.json").read_text(encoding="utf-8"))["edits"]
        return edits_out

    def test_update_dropping_citation_identifier_and_number(self) -> None:
        new = DROPPED
        [edit] = self.plan_edits([PageEdit("decisions/retry-backoff.md", "update", new, "tighten")], "drop")
        self.assertEqual(edit["fact_warnings"], ["docs/retry.md", "retry_budget", "8 s"])

    def test_moved_citation_and_reflow_write_no_key(self) -> None:
        new = _edit(
            PAGE,
            ("  - path: docs/retry.md\n", ""),
            ("Fixed 1 s delay.", "Fixed 1 s delay (path: docs/retry.md)."),
            ("Start at 250 ms and call", "Start at 250 ms\nand call"),
        )
        [edit] = self.plan_edits([PageEdit("decisions/retry-backoff.md", "update", new, "reflow")], "reflow")
        self.assertNotIn("fact_warnings", edit)

    def test_create_edit_writes_no_key(self) -> None:
        page = PAGE.replace("retry-backoff", "jitter").replace("Retry backoff", "Jitter")
        [edit] = self.plan_edits([PageEdit("decisions/jitter.md", "create", page, "new")], "create")
        self.assertNotIn("fact_warnings", edit)


if __name__ == "__main__":
    unittest.main()
