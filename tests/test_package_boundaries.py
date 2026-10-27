# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Package boundaries (FR-016) and layout contract (FR-004, FR-005).

The package must not spell the original project's layout anywhere but
``paths.py`` (as the documented defaults) and ``cli.py`` (help text); the
bash linter must not ship; and an unflagged run must reproduce the old
layout byte-for-byte while every location is overridable.
"""

from __future__ import annotations

import ast
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.conftest import PACKAGE_ROOT, make_repo_layout, run_cli
from tests.test_cli_contract import _proposals_dir
from wiki_studio.paths import ENV_WIKI_DIR, SEARCH_CACHE_SUFFIX

FORBIDDEN_STRINGS = ("code-copilot-team", "shared/", "specs/", "doc_internal", "knowledge/wiki")
ALLOWED_FILES = {"paths.py", "cli.py"}


def _wiki(root: Path) -> Path:
    wiki = root / "kb"
    wiki.mkdir(parents=True)
    (wiki / "index.md").write_text(
        "---\npage_type: index\nslug: index\ntitle: KB\nstatus: stable\nlast_reviewed: 2026-05-06\n---\n\n# KB\n",
        encoding="utf-8",
    )
    (wiki / "log.md").write_text(
        "---\npage_type: log\nslug: log\ntitle: Log\nstatus: stable\nlast_reviewed: 2026-05-06\n---\n\n# Log\n",
        encoding="utf-8",
    )
    return wiki


class TestNoForeignLayoutStrings(unittest.TestCase):
    def test_only_paths_and_cli_name_the_original_layout(self) -> None:
        offenders: list[str] = []
        for py in sorted(PACKAGE_ROOT.rglob("*.py")):
            if py.name in ALLOWED_FILES:
                continue
            for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), start=1):
                hits = [s for s in FORBIDDEN_STRINGS if s in line]
                if hits:
                    offenders.append(f"{py.relative_to(PACKAGE_ROOT)}:{lineno}: {hits} in {line.strip()!r}")
        self.assertEqual(offenders, [], "\n".join(offenders))

    def test_bash_linter_is_not_shipped(self) -> None:
        shipped = [p for p in PACKAGE_ROOT.rglob("*") if p.name == "lint-wiki.sh"]
        self.assertEqual(shipped, [])
        for module in ("lint.py", "promoter.py"):
            source = (PACKAGE_ROOT / module).read_text(encoding="utf-8")
            self.assertNotIn("subprocess", source, f"{module} must not shell out")
            self.assertNotIn("lint-wiki", source)


class TestStandardLibraryCore(unittest.TestCase):
    """0.8.0 (FR-033a): every core module imports only the standard library and ``wiki_studio``.

    ``mcp_adapter/`` is excluded: it is the one place the optional ``mcp``
    SDK may be imported. The wheel-level proof is CI's ``build-check``.
    """

    ADAPTER = "mcp_adapter"
    PACKAGE = "wiki_studio"

    def test_no_core_module_imports_outside_the_standard_library(self) -> None:
        allowed = set(sys.stdlib_module_names) | {self.PACKAGE}
        offenders: list[str] = []
        checked = 0
        for py in sorted(PACKAGE_ROOT.rglob("*.py")):
            rel = py.relative_to(PACKAGE_ROOT)
            if rel.parts[0] == self.ADAPTER:
                continue
            checked += 1
            for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [self.PACKAGE if node.level else (node.module or "").split(".")[0]]
                else:
                    continue
                offenders += [f"{rel.as_posix()}:{node.lineno}: {name}" for name in names if name not in allowed]
        self.assertGreater(checked, 20)
        self.assertEqual(offenders, [], "imports outside the standard library in the core package")

    def test_the_adapter_is_the_only_place_mcp_is_imported(self) -> None:
        importers = sorted(
            {
                py.relative_to(PACKAGE_ROOT).as_posix()
                for py in PACKAGE_ROOT.rglob("*.py")
                for node in ast.walk(ast.parse(py.read_text(encoding="utf-8")))
                if (isinstance(node, ast.Import) and any(a.name.split(".")[0] == "mcp" for a in node.names))
                or (isinstance(node, ast.ImportFrom) and not node.level and (node.module or "").split(".")[0] == "mcp")
            }
        )
        self.assertEqual(importers, [f"{self.ADAPTER}/server.py"])


class TestSearchCacheSingleWriter(unittest.TestCase):
    """0.8.0 (FR-012): ``search_index.py`` is the only module that opens the search cache or any SQLite file."""

    CACHE_MODULE = "search_index.py"
    SUFFIX_DEFINED_IN = "paths.py"

    def _modules(self) -> list[tuple[str, ast.Module, str]]:
        return [
            (py.relative_to(PACKAGE_ROOT).as_posix(), ast.parse(source), source)
            for py in sorted(PACKAGE_ROOT.rglob("*.py"))
            for source in (py.read_text(encoding="utf-8"),)
        ]

    def test_only_search_index_calls_sqlite3_connect(self) -> None:
        offenders: list[str] = []
        for rel, tree, _source in self._modules():
            for node in ast.walk(tree):
                connects = (
                    isinstance(node, ast.Attribute)
                    and node.attr == "connect"
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "sqlite3"
                )
                imports_connect = (
                    isinstance(node, ast.ImportFrom)
                    and node.module == "sqlite3"
                    and any(alias.name in ("connect", "*") for alias in node.names)
                )
                if (connects or imports_connect) and rel != self.CACHE_MODULE:
                    offenders.append(f"{rel}:{getattr(node, 'lineno', '?')}")
        self.assertEqual(offenders, [], "sqlite3.connect outside search_index.py")

    def test_only_search_index_names_the_cache_suffix(self) -> None:
        offenders: list[str] = []
        for rel, tree, source in self._modules():
            names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
            names |= {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
            if "SEARCH_CACHE_SUFFIX" in names and rel not in (self.CACHE_MODULE, self.SUFFIX_DEFINED_IN):
                offenders.append(f"{rel}: SEARCH_CACHE_SUFFIX")
            if SEARCH_CACHE_SUFFIX in source and rel != self.SUFFIX_DEFINED_IN:
                offenders.append(f"{rel}: {SEARCH_CACHE_SUFFIX!r} spelled out")
        self.assertEqual(offenders, [])


class TestLayoutContract(unittest.TestCase):
    def test_unflagged_run_reproduces_the_original_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo_layout(Path(tmp), with_schema=True)
            env = {k: v for k, v in os.environ.items() if not k.startswith("WIKI_STUDIO_")}
            with patch.dict(os.environ, env, clear=True):
                result = run_cli("ingest", str(root / "sample-incident.md"), "--backend", "test", cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr)
            written = Path(result.stdout.strip())
            self.assertEqual(written.parent, root / "doc_internal" / "proposals")
            self.assertTrue((root / "knowledge" / "wiki" / ".audit" / "ingest-log.md").is_file())

    def test_environment_variable_points_lint_at_a_wiki_outside_the_default_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wiki = _wiki(root)
            with patch.dict(os.environ, {ENV_WIKI_DIR: str(wiki)}):
                result = run_cli("lint", cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("linted 2 pages, 0 violations", result.stdout)
            self.assertFalse((root / "knowledge").exists())

    def test_wiki_dir_flag_is_accepted_before_and_after_the_verb(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wiki = _wiki(root)
            before = run_cli("--wiki-dir", str(wiki), "lint", cwd=root)
            after = run_cli("lint", "--wiki-dir", str(wiki), cwd=root)
            for result in (before, after):
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("linted 2 pages, 0 violations", result.stdout)

    def test_flag_beats_environment_variable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wiki = _wiki(root)
            with patch.dict(os.environ, {ENV_WIKI_DIR: str(root / "missing")}):
                result = run_cli("lint", "--wiki-dir", str(wiki), cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_proposals_dir_override_receives_the_patch_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo_layout(Path(tmp), with_schema=True)
            out = root / "inbox"
            result = run_cli(
                "ingest", str(root / "sample-incident.md"), "--backend", "test", "--proposals-dir", str(out), cwd=root
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(result.stdout.strip()).parent, out)

    def test_promote_with_a_wiki_dir_under_the_root_lints_the_staged_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wiki = _wiki(root)
            prop = _proposals_dir(root)
            result = run_cli("promote", str(prop), "--wiki-dir", str(wiki), cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((wiki / "incidents" / "cli-fixture.md").is_file())
            self.assertIn("  + kb/incidents/cli-fixture.md", result.stdout)
            self.assertFalse((root / "knowledge").exists())

    def test_promote_with_a_deep_wiki_dir_resolves_escape_links_through_siblings(self) -> None:
        # Wiki at <root>/a/b/kb; a page links to a root-level sibling (docs/) and to a
        # sibling two levels down (a/notes/), both outside the wiki and inside the root.
        # The staged-tree lint must mirror both levels or promote would report broken
        # links. (An index entry may not leave the wiki, FR-013, so a page carries them.)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "guide.md").write_text("# guide\n", encoding="utf-8")
            (root / "a" / "notes").mkdir(parents=True)
            (root / "a" / "notes" / "todo.md").write_text("# todo\n", encoding="utf-8")
            wiki = root / "a" / "b" / "kb"
            (wiki / "concepts").mkdir(parents=True)
            (wiki / "index.md").write_text(
                "---\npage_type: index\nslug: index\ntitle: KB\nstatus: stable\nlast_reviewed: 2026-05-06\n---\n\n"
                "# KB\n\n- [links](concepts/links.md)\n",
                encoding="utf-8",
            )
            (wiki / "concepts" / "links.md").write_text(
                "---\npage_type: concept\nslug: links\ntitle: Links\nstatus: stable\nlast_reviewed: 2026-05-06\n"
                "sources:\n  - path: src.md\n    sha: abc\n---\n\n# Links\n\n"
                "- [guide](../../../../docs/guide.md)\n- [todo](../../../notes/todo.md)\n",
                encoding="utf-8",
            )
            (wiki / "log.md").write_text(
                "---\npage_type: log\nslug: log\ntitle: Log\nstatus: stable\nlast_reviewed: 2026-05-06\n---\n\n# Log\n",
                encoding="utf-8",
            )
            prop = _proposals_dir(root)
            result = run_cli("promote", str(prop), "--wiki-dir", str(wiki), cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((wiki / "incidents" / "cli-fixture.md").is_file())
            self.assertIn("  + a/b/kb/incidents/cli-fixture.md", result.stdout)

    def test_root_flag_confines_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo_layout(Path(tmp), with_schema=True)
            elsewhere = root.parent / "elsewhere"
            elsewhere.mkdir(exist_ok=True)
            result = run_cli(
                "ingest", str(root / "sample-incident.md"), "--backend", "test", "--root", str(elsewhere), cwd=root
            )
            self.assertEqual(result.returncode, 7)


if __name__ == "__main__":
    unittest.main()
