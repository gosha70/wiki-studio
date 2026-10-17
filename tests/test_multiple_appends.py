# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Issue #18: several append-index / append-log edits to one file in a patch-set are all applied, in order."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.conftest import run_cli
from wiki_studio import api
from wiki_studio.api import PageEdit
from wiki_studio.lint import lint_wiki
from wiki_studio.paths import WikiPaths


def _page(slug: str) -> str:
    return (
        f"---\npage_type: decision\nslug: {slug}\ntitle: {slug.upper()}\nstatus: draft\n"
        f"last_reviewed: 2026-10-16\nsources:\n  - path: notes.md\n---\n\n# {slug.upper()}\n\n## Decision\n\nx\n"
    )


class _Wiki(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-appends-")
        self.root = Path(self._tmp.name).resolve()
        (self.root / "notes.md").write_text("notes\n", encoding="utf-8")
        self.paths = WikiPaths.for_root(self.root)
        api.init(self.paths)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def read(self, name: str) -> str:
        return (self.paths.wiki_dir / name).read_text(encoding="utf-8")


class TestIssueRepro(_Wiki):
    def test_two_append_index_edits_both_land_in_order(self) -> None:
        edits = [
            PageEdit("decisions/a.md", "create", _page("a"), "r"),
            PageEdit("decisions/b.md", "create", _page("b"), "r"),
            PageEdit("index.md", "append-index", "- [A](decisions/a.md)", "r"),
            PageEdit("index.md", "append-index", "- [B](decisions/b.md)", "r"),
        ]
        written = api.propose(edits, self.paths, name="x")
        plan = json.loads((written / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(
            [e["preview"] for e in plan["edits"]],
            ["preview/decisions/a.md", "preview/decisions/b.md", "preview/index.md", "preview/index.md.2"],
        )
        api.promote(written, self.paths)
        index = self.read("index.md")
        self.assertLess(index.index("- [A](decisions/a.md)"), index.index("- [B](decisions/b.md)"))
        self.assertEqual(lint_wiki(self.paths.wiki_dir), [])

    def test_equivalent_spellings_of_one_path_get_separate_previews(self) -> None:
        """Issue #23: index.md and ./index.md are one file and must not share a preview."""
        edits = [
            PageEdit("decisions/a.md", "create", _page("a"), "r"),
            PageEdit("decisions/b.md", "create", _page("b"), "r"),
            PageEdit("index.md", "append-index", "- [A](decisions/a.md)", "r"),
            PageEdit("./index.md", "append-index", "- [B](decisions/b.md)", "r"),
        ]
        written = api.propose(edits, self.paths, name="spellings")
        plan = json.loads((written / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual([e["preview"] for e in plan["edits"]][2:], ["preview/index.md", "preview/index.md.2"])
        self.assertEqual([e["path"] for e in plan["edits"]][3], "./index.md")
        api.promote(written, self.paths)
        index = self.read("index.md")
        self.assertLess(index.index("- [A](decisions/a.md)"), index.index("- [B](decisions/b.md)"))
        self.assertEqual(lint_wiki(self.paths.wiki_dir), [])

    def test_three_append_log_edits_all_land(self) -> None:
        lines = [f"- 2026-10-16 — entry {n}" for n in (1, 2, 3)]
        edits = [PageEdit("log.md", "append-log", line, "r") for line in lines]
        api.promote(api.propose(edits, self.paths, name="logs"), self.paths)
        log = self.read("log.md")
        self.assertEqual([line for line in log.splitlines() if line.startswith("- 2026")], lines)

    def test_single_edit_layout_is_unchanged(self) -> None:
        edits = [PageEdit("log.md", "append-log", "- 2026-10-16 — one", "r")]
        plan = json.loads((api.propose(edits, self.paths, name="one") / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["edits"][0]["preview"], "preview/log.md")

    def test_curator_edit_of_a_second_preview_is_applied_and_recorded(self) -> None:
        edits = [
            PageEdit("log.md", "append-log", "- 2026-10-16 — first", "r"),
            PageEdit("log.md", "append-log", "- 2026-10-16 — second", "r"),
        ]
        written = api.propose(edits, self.paths, name="curated")
        (written / "preview" / "log.md.2").write_text("- 2026-10-16 — second, curated", encoding="utf-8")
        api.promote(written, self.paths)
        log = self.read("log.md")
        self.assertLess(log.index("- 2026-10-16 — first"), log.index("- 2026-10-16 — second, curated"))
        delta = self.paths.wiki_dir / ".audit" / "proposals" / "curated" / "curator-delta.md"
        self.assertIn("second, curated", delta.read_text(encoding="utf-8"))


class TestProposeFromMultiLineIndex(_Wiki):
    def test_every_index_and_log_line_of_a_draft_lands(self) -> None:
        draft = self.root / "draft"
        (draft / "decisions").mkdir(parents=True)
        for slug in ("a", "b", "c"):
            (draft / "decisions" / f"{slug}.md").write_text(_page(slug), encoding="utf-8")
        (draft / "index.md").write_text(
            "".join(f"- [{s.upper()}](decisions/{s}.md)\n" for s in ("a", "b", "c")), encoding="utf-8"
        )
        (draft / "log.md").write_text("- 2026-10-16 — created a, b, c\n- 2026-10-16 — second line\n", encoding="utf-8")
        result = run_cli("propose", "--from", str(draft), "--promote", cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        index = self.read("index.md")
        for slug in ("a", "b", "c"):
            self.assertIn(f"decisions/{slug}.md", index)
        self.assertIn("second line", self.read("log.md"))
        self.assertEqual(lint_wiki(self.paths.wiki_dir), [])


if __name__ == "__main__":
    unittest.main()
