# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.5.0: an ``update`` that drops a citation, identifier or number is flagged in ``plan.json`` (FR-014, FR-015)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from wiki_studio import api
from wiki_studio.fact_diff import removed_facts, removed_facts_checked
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

    def test_sign_is_part_of_the_number(self) -> None:
        self.assertEqual(removed_facts("Offset -5 ms.\n", "Offset 5 ms.\n"), ["-5 ms"])
        self.assertEqual(removed_facts("Offset 5 ms.\n", "Offset -5 ms.\n"), ["5 ms"])
        self.assertEqual(removed_facts("Offset -5 ms.\n", "Offset removed.\n"), ["-5 ms"])
        # A range is two unsigned numbers.
        self.assertEqual(removed_facts("Wait 5-10 ms.\n", "Wait 5 ms and 10 ms.\n"), [])

    def test_fraction_without_leading_zero(self) -> None:
        self.assertEqual(removed_facts("Limit .5 s.\n", "Limit removed.\n"), ["0.5 s"])
        self.assertEqual(removed_facts("Limit .5 s.\n", "Limit 0.5 s.\n"), [])
        self.assertEqual(removed_facts("Limit -.5 s.\n", "Limit .5 s.\n"), ["-0.5 s"])
        self.assertEqual(removed_facts("Wait v1.5 s.\n", "Wait.\n"), [])

    def test_citations_inside_fenced_code_are_code_samples(self) -> None:
        """Issue #33: a path:line or path: line inside a fence is not a citation."""
        self.assertEqual(removed_facts("See:\n\n```\nsrc/x.py:12\npath: docs/a.md\n```\n", "See.\n"), [])
        self.assertEqual(removed_facts("See src/x.py:12.\n", "See.\n"), ["src/x.py:12"])

    def test_number_unit_join_rule(self) -> None:
        """Issue #33: the stated contract for a unit on the next line."""
        self.assertEqual(removed_facts("Wait 250 ms.\n", "Wait 250\nms.\n"), [])  # wrapped line
        self.assertEqual(removed_facts("Keep 12.\nmin ago it ran.\n", "Keep.\n"), [])  # sentence ends
        self.assertEqual(removed_facts("Keep 12\n\nmin ago it ran.\n", "Keep.\n"), [])  # paragraph ends
        self.assertEqual(removed_facts("Keep 12\nmin per run.\n", "Keep.\n"), ["12 min"])  # wrapped

    def test_malformed_sources_are_reported_not_silently_dropped(self) -> None:
        """Issue #33: a `sources` that is not a list of mappings is an error beside the body comparison."""
        bad = "---\npage_type: concept\nslug: a\nsources: notes.md\n---\n\nBody `kept` and `gone` 5 ms.\n"
        good = "---\npage_type: concept\nslug: a\nsources:\n  - path: notes.md\n---\n\nBody `kept`.\n"
        removed, problem = removed_facts_checked(bad, good)
        self.assertEqual(removed, ["gone", "5 ms"])
        self.assertEqual(problem, "sources not compared (live page: frontmatter `sources` is not a list of mappings)")
        # The other way round the citation has no parseable home in the new page: reported removed, with the reason.
        removed, problem = removed_facts_checked(good, bad)
        self.assertEqual(removed, ["notes.md"])
        self.assertIn("new content:", problem or "")
        self.assertEqual(removed_facts_checked(good, good), ([], None))

    def test_fenced_code_is_not_an_identifier_source(self) -> None:
        old = "Run:\n\n```sh\necho `date` 5 ms\n```\n"
        self.assertEqual(removed_facts(old, "Run.\n"), [])

    def test_indented_backticks_do_not_hide_later_facts(self) -> None:
        old = "Intro.\n\n    ```\n    code\n\nCall `required_id` within 5 ms.\n"
        self.assertEqual(removed_facts(old, "Intro.\n"), ["required_id", "5 ms"])
        self.assertEqual(removed_facts("```x```\n\nCall `y` in 5 ms.\n", "Call.\n"), ["x", "y", "5 ms"])

    def test_fence_under_a_deep_list_item_is_code(self) -> None:
        steps = "".join(f"{n}. Step {n}.\n" for n in range(1, 10))
        old = steps + "10. Run:\n\n    ```bash\n    echo `date` 5 ms\n    ```\n\n11. Done.\n"
        self.assertEqual(removed_facts(old, steps + "10. Run.\n\n11. Done.\n"), [])
        nested = "- a\n  - b:\n\n    ~~~\n    `x` 5 ms\n    ~~~\n"
        self.assertEqual(removed_facts(nested, "- a\n"), [])

    def test_shorter_fence_inside_a_longer_one_does_not_close_it(self) -> None:
        old = "Example:\n\n````md\n```\necho `date` 5 ms\n```\n````\n"
        self.assertEqual(removed_facts(old, "Example.\n"), [])
        old = "Example:\n\n```\n~~~\n`x` 5 ms\n```\n"
        self.assertEqual(removed_facts(old, "Example.\n"), [])

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

    def test_undecodable_live_page_is_reported_and_the_proposal_is_written(self) -> None:
        live = self.paths.wiki_dir / "decisions" / "retry-backoff.md"
        live.write_bytes(PAGE.encode("utf-8") + b"\xff\n")
        [edit] = self.plan_edits([PageEdit("decisions/retry-backoff.md", "update", DROPPED, "tighten")], "bad")
        self.assertNotIn("fact_warnings", edit)
        self.assertEqual(edit["fact_check_error"], "live page not readable: not valid UTF-8")
        self.assertTrue((self.paths.proposals_dir / "bad" / "preview" / "decisions" / "retry-backoff.md").is_file())

    def test_unreadable_live_page_records_the_error_kind_not_the_path(self) -> None:
        from unittest import mock

        live = self.paths.wiki_dir / "decisions" / "retry-backoff.md"
        real_read_text = Path.read_text

        def read_text(path: Path, *args: object, **kwargs: object) -> str:
            if path == live:
                raise PermissionError(13, "Permission denied", str(live))
            return real_read_text(path, *args, **kwargs)  # type: ignore[arg-type]

        with mock.patch.object(Path, "read_text", read_text):
            [edit] = self.plan_edits([PageEdit("decisions/retry-backoff.md", "update", DROPPED, "tighten")], "denied")
        self.assertEqual(edit["fact_check_error"], "live page not readable: Permission denied")

    def test_malformed_sources_on_the_live_page_write_error_and_warnings(self) -> None:
        live = self.paths.wiki_dir / "decisions" / "retry-backoff.md"
        live.write_text(PAGE.replace("sources:\n  - path: notes.md\n  - path: docs/retry.md\n", "sources: notes.md\n"))
        [edit] = self.plan_edits([PageEdit("decisions/retry-backoff.md", "update", DROPPED, "tighten")], "bad-src")
        self.assertEqual(
            edit["fact_check_error"],
            "sources not compared (live page: frontmatter `sources` is not a list of mappings)",
        )
        self.assertEqual(edit["fact_warnings"], ["retry_budget", "8 s"])

    def test_create_edit_writes_no_key(self) -> None:
        page = PAGE.replace("retry-backoff", "jitter").replace("Retry backoff", "Jitter")
        [edit] = self.plan_edits([PageEdit("decisions/jitter.md", "create", page, "new")], "create")
        self.assertNotIn("fact_warnings", edit)


if __name__ == "__main__":
    unittest.main()
