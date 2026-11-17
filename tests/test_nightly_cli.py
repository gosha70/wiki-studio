# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.10.0 (US2): the ``nightly`` verb on the CLI contract (FR-009 - FR-012).

Every case runs ``wiki_studio.cli.main`` in-process through ``tests.conftest.run_cli``.
The FR-011 tests pin the no-promote guarantee twice: a static ``ast`` scan of
``nightly.py`` and a run with every promote and approve entry point patched to raise.
"""

from __future__ import annotations

import ast
import contextlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.conftest import PACKAGE_ROOT, make_repo_layout, run_cli
from wiki_studio import __version__, api, promoter
from wiki_studio.cli import _inject_legacy_v1_prefix
from wiki_studio.paths import WikiPaths

# The JSON keys FR-002 defines at this phase.
_JSON_KEYS = (
    "nightly_version",
    "package_version",
    "run_at",
    "wiki_dir",
    "proposals_dir",
    "lint",
    "findings",
    "needs_curator",
    "warnings",
    "exit_code",
)

_PAGE = (
    "---\n"
    "page_type: decision\n"
    "slug: {slug}\n"
    "title: {title}\n"
    "status: stable\n"
    "last_reviewed: 2026-11-17\n"
    "sources:\n"
    "  - path: notes.md\n"
    "---\n\n"
    "# {title}\n\n"
    "## Decision\n\nUse the queue.\n\n"
    "## Context\n\nAgreed with the platform team.\n\n"
    "## Alternatives considered\n\nFixed 1 s delay.\n\n"
    "## Consequences\n\nLong outages wait at most 8 s between tries.\n"
)


def _page(slug: str) -> str:
    """A valid decision page under ``decisions/``."""
    return _PAGE.format(slug=slug, title=slug.replace("-", " ").title())


class NightlyCliCase(unittest.TestCase):
    """A managed wiki in a temporary project layout, made with ``wiki-studio init``."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-nightly-cli-")
        self.root = make_repo_layout(Path(self._tmp.name))
        (self.root / "notes.md").write_text("# notes\n", encoding="utf-8")
        self.paths = WikiPaths.for_root(self.root)
        self.wiki = self.paths.wiki_dir
        result = self.run_cli("init")
        self.assertEqual(result.returncode, 0, result.stderr)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_cli(self, *argv: str):
        return run_cli(*argv, cwd=self.root)

    def write_page(self, rel: str, text: str) -> None:
        target = self.wiki / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


class TestTheReportOnStdout(NightlyCliCase):
    def test_a_clean_wiki_prints_the_markdown_and_exits_zero(self) -> None:
        result = self.run_cli("nightly")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# wiki-studio nightly report", result.stdout)
        self.assertIn("## Lint\n\nclean", result.stdout)
        self.assertIn("## Findings\n\nnone", result.stdout)

    def test_json_prints_one_object_with_the_fr_002_keys_and_exits_zero(self) -> None:
        result = self.run_cli("nightly", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        for key in _JSON_KEYS:
            self.assertIn(key, data)
        self.assertEqual(data["nightly_version"], 1)
        self.assertEqual(data["package_version"], __version__)
        self.assertEqual(data["exit_code"], 0)
        self.assertNotIn("# wiki-studio nightly report", result.stdout)


class TestTheReportFile(NightlyCliCase):
    def test_report_writes_the_file_and_prints_no_markdown(self) -> None:
        target = self.root / "reports" / "nightly.md"
        result = self.run_cli("nightly", "--report", str(target))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        report = target.read_text(encoding="utf-8")
        self.assertIn("# wiki-studio nightly report", report)
        self.assertIn("## Lint\n\nclean", report)

    def test_a_broken_wiki_exits_one_and_the_report_holds_the_violations(self) -> None:
        self.write_page("decisions/orphan.md", _page("orphan"))
        target = self.root / "reports" / "nightly.md"
        result = self.run_cli("nightly", "--report", str(target))
        self.assertEqual(result.returncode, 1, result.stderr)
        report = target.read_text(encoding="utf-8")
        self.assertIn("Lint failed with structural violations:", report)
        self.assertIn("decisions/orphan.md", report)

    def test_a_report_path_inside_the_wiki_exits_one_before_anything_runs(self) -> None:
        target = self.wiki / "report.md"
        with patch("wiki_studio.api.nightly", side_effect=AssertionError("must not run")) as run_mock:
            result = self.run_cli("nightly", "--report", str(target))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse(target.exists())
        self.assertIn(str(target.resolve()), result.stderr)
        run_mock.assert_not_called()

    def test_an_unwritable_report_exits_six_with_the_reason_on_stderr(self) -> None:
        blocker = self.root / "blocker"
        blocker.write_text("a regular file\n", encoding="utf-8")
        target = blocker / "report.md"
        result = self.run_cli("nightly", "--report", str(target))
        self.assertEqual(result.returncode, 6, result.stderr)
        self.assertIn(f"error: could not write the report to {target}", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_an_unwritable_report_on_a_broken_wiki_still_exits_six(self) -> None:
        self.write_page("decisions/orphan.md", _page("orphan"))
        blocker = self.root / "blocker"
        blocker.write_text("a regular file\n", encoding="utf-8")
        result = self.run_cli("nightly", "--report", str(blocker / "report.md"))
        self.assertEqual(result.returncode, 6, result.stderr)
        self.assertIn("could not write the report", result.stderr)

    def test_json_after_a_failed_report_write_carries_the_final_exit_code(self) -> None:
        blocker = self.root / "blocker"
        blocker.write_text("a regular file\n", encoding="utf-8")
        result = self.run_cli("nightly", "--report", str(blocker / "report.md"), "--json")
        self.assertEqual(result.returncode, 6, result.stderr)
        self.assertIn("could not write the report", result.stderr)
        self.assertEqual(json.loads(result.stdout)["exit_code"], 6)


class TestTheCliSurface(NightlyCliCase):
    def test_nightly_help_names_its_flags_and_no_later_phase_flags(self) -> None:
        result = self.run_cli("nightly", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--report", result.stdout)
        self.assertIn("--json", result.stdout)
        for flag in ("--backend", "--max-proposals", "--by"):
            self.assertNotIn(flag, result.stdout)

    def test_top_level_help_lists_the_verb(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nightly", result.stdout)

    def test_the_legacy_shim_passes_nightly_through(self) -> None:
        self.assertEqual(_inject_legacy_v1_prefix(["nightly"]), ["nightly"])
        self.assertEqual(_inject_legacy_v1_prefix(["--wiki-dir", "w", "nightly"]), ["--wiki-dir", "w", "nightly"])


def _promoter_imports(tree: ast.AST) -> list[str]:
    """Every import that reaches ``wiki_studio.promoter``, in any form (FR-011)."""
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = [alias.name for alias in node.names]
            if node.level:
                if module == "promoter" or module.startswith("promoter."):
                    found.append(module)
                elif not module and "promoter" in names:
                    found.append("promoter")
            elif module == "wiki_studio.promoter" or module.startswith("wiki_studio.promoter."):
                found.append(module)
            elif module == "wiki_studio" and "promoter" in names:
                found.append("wiki_studio.promoter")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "wiki_studio.promoter" or alias.name.startswith("wiki_studio.promoter."):
                    found.append(alias.name)
    return found


class TestNoPromotePath(unittest.TestCase):
    def test_nightly_py_imports_nothing_from_promoter_and_names_no_promote_or_approve(self) -> None:
        tree = ast.parse((PACKAGE_ROOT / "nightly.py").read_text(encoding="utf-8"))
        self.assertEqual(_promoter_imports(tree), [])
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                self.assertNotIn(node.id, ("promote", "approve"))
            elif isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, ("promote", "approve"))
            elif isinstance(node, ast.Import | ast.ImportFrom):
                for alias in node.names:
                    self.assertNotIn(alias.name, ("promote", "approve"))
                    self.assertNotIn(alias.asname, ("promote", "approve"))

    def test_a_run_completes_with_every_promote_and_approve_entry_point_patched_to_raise(self) -> None:
        def boom(*args: object, **kwargs: object) -> None:
            raise AssertionError("the nightly pass must not reach promote or approve")

        public = [
            name
            for name, member in inspect.getmembers(promoter, inspect.isfunction)
            if not name.startswith("_") and member.__module__ == "wiki_studio.promoter"
        ]
        self.assertTrue({"promote", "approve"} <= set(public), public)
        with tempfile.TemporaryDirectory(prefix="wiki_studio-nightly-cli-") as tmp:
            root = make_repo_layout(Path(tmp))
            api.init(WikiPaths.for_root(root))
            with contextlib.ExitStack() as stack:
                for target in (
                    "wiki_studio.api.promote",
                    "wiki_studio.api.approve",
                    "wiki_studio.api._promote",
                    "wiki_studio.api._approve",
                ):
                    stack.enter_context(patch(target, side_effect=boom))
                for name in public:
                    stack.enter_context(patch.object(promoter, name, side_effect=boom))
                result = run_cli("nightly", cwd=root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# wiki-studio nightly report", result.stdout)


if __name__ == "__main__":
    unittest.main()
