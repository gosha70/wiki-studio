# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Issue #11: one path frame between the ingest prompt and the edit contract, and the ``info`` verb."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from tests.conftest import make_repo_layout, run_cli
from wiki_studio import api
from wiki_studio.backends.copilot_cli import _render_plain_text_prompt
from wiki_studio.errors import ContractViolationError
from wiki_studio.ingestor_multi import DefaultMultiIngestor
from wiki_studio.paths import ENV_WIKI_DIR, WikiPaths
from wiki_studio.prompt import _PATCH_SET_RESPONSE_SCHEMA, compose_multi_prompt, compose_prompt, load_schema_files
from wiki_studio.proposal import IngestRequest
from wiki_studio.wiki_state import load_wiki_state

PAGE = (
    "---\npage_type: concept\nslug: x\ntitle: X\nstatus: draft\nlast_reviewed: 2026-10-16\n"
    "sources:\n  - path: sample-incident.md\n    sha: abc1234\n---\n\n# X\n\n## Summary\n\nBody.\n"
)


class _PrefixingBackend:
    """A backend that copies the heading label into its paths, as the model did in run 1."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def call(self, prompt: dict[str, Any]) -> dict[str, Any]:
        p = self.prefix
        return {
            "version": 1,
            "rationale": "one concept, indexed and logged",
            "edits": [
                {"path": f"{p}concepts/x.md", "action": "create", "new_content": PAGE, "rationale": "r"},
                {
                    "path": f"{p}index.md",
                    "action": "append-index",
                    "new_content": "- [X](concepts/x.md)",
                    "rationale": "r",
                },
                {
                    "path": f"{p}log.md",
                    "action": "append-log",
                    "new_content": "- 2026-10-16 — created x",
                    "rationale": "r",
                },
            ],
        }


def _layout_with_wiki_at(tmp: Path, rel: str) -> WikiPaths:
    """A layout whose wiki lives at ``<root>/<rel>`` (index and log copied from the default one)."""
    root = make_repo_layout(tmp)
    default_wiki = root / "knowledge" / "wiki"
    wiki = root / rel
    if wiki != default_wiki:
        shutil.copytree(default_wiki, wiki)
    return WikiPaths.for_root(root, wiki_dir=wiki)


class TestStripWikiLabel(unittest.TestCase):
    def test_removes_exactly_one_configured_prefix(self) -> None:
        paths = WikiPaths.for_root(Path("/proj"), wiki_dir=Path("/proj/wiki"))
        self.assertEqual(paths.wiki_label, "wiki")
        self.assertEqual(paths.strip_wiki_label("wiki/concepts/x.md"), "concepts/x.md")
        self.assertEqual(paths.strip_wiki_label("wiki/wiki/concepts/x.md"), "wiki/concepts/x.md")
        self.assertEqual(paths.strip_wiki_label("wikis/x.md"), "wikis/x.md")
        self.assertEqual(paths.strip_wiki_label("concepts/wiki/x.md"), "concepts/wiki/x.md")
        self.assertEqual(paths.strip_wiki_label("wiki"), "wiki")
        self.assertEqual(paths.strip_wiki_label("index.md"), "index.md")

    def test_nested_and_root_labels(self) -> None:
        nested = WikiPaths.for_root(Path("/proj"))
        self.assertEqual(nested.strip_wiki_label("knowledge/wiki/decisions/d.md"), "decisions/d.md")
        self.assertEqual(nested.strip_wiki_label("wiki/decisions/d.md"), "wiki/decisions/d.md")
        at_root = WikiPaths.for_root(Path("/proj"), wiki_dir=Path("/proj"))
        self.assertEqual(at_root.wiki_label, ".")
        self.assertEqual(at_root.strip_wiki_label("./concepts/x.md"), "concepts/x.md")


class TestMultiIngestForgivesTheLabel(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-frame-")
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _ingest(self, paths: WikiPaths, prefix: str) -> list[str]:
        request = IngestRequest(source_path=paths.root / "sample-incident.md", source_kind="file", backend_name="stub")
        patch_set = DefaultMultiIngestor(backend=_PrefixingBackend(prefix), paths=paths).ingest_multi(request)
        return [e.path for e in patch_set.edits]

    def test_one_word_label(self) -> None:
        paths = _layout_with_wiki_at(self.tmp, "wiki")
        self.assertEqual(self._ingest(paths, "wiki/"), ["concepts/x.md", "index.md", "log.md"])

    def test_nested_default_label(self) -> None:
        paths = _layout_with_wiki_at(self.tmp, "knowledge/wiki")
        self.assertEqual(self._ingest(paths, "knowledge/wiki/"), ["concepts/x.md", "index.md", "log.md"])

    def test_unprefixed_paths_are_untouched(self) -> None:
        paths = _layout_with_wiki_at(self.tmp, "wiki")
        self.assertEqual(self._ingest(paths, ""), ["concepts/x.md", "index.md", "log.md"])

    def test_double_prefix_still_fails_validation(self) -> None:
        paths = _layout_with_wiki_at(self.tmp, "wiki")
        with self.assertRaises(ContractViolationError) as ctx:
            self._ingest(paths, "wiki/wiki/")
        self.assertIn("wiki/concepts/x.md: page_type 'concept' should live under concepts/", str(ctx.exception))

    def test_api_ingest_end_to_end_with_a_one_word_label(self) -> None:
        # The exact shape run 1 of the navigation evaluation failed on.
        paths = _layout_with_wiki_at(self.tmp, "wiki")
        result = api.ingest(paths.root / "sample-incident.md", paths, backend=_PrefixingBackend("wiki/"))
        self.assertEqual(result.disposition, "accept")
        self.assertEqual(result.edits, ("concepts/x.md", "index.md", "log.md"))
        assert result.written is not None
        self.assertTrue((result.written / "preview" / "concepts" / "x.md").is_file())
        promoted = api.promote(result.written, paths)
        self.assertIn("concepts/x.md", promoted.applied_paths)


class TestPromptStatesTheFrame(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-frame-")
        self.paths = _layout_with_wiki_at(Path(self._tmp.name), "wiki")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_multi_page_prompt_names_the_label_and_the_rule(self) -> None:
        source = self.paths.root / "sample-incident.md"
        content = source.read_text(encoding="utf-8")
        prompt = compose_multi_prompt(
            source_path=source,
            source_content=content,
            schema_files=load_schema_files(self.paths),
            wiki_state=load_wiki_state(paths=self.paths, source_path=source, source_content=content),
            source_kind="file",
        )
        rendered = _render_plain_text_prompt(prompt, wiki_label=self.paths.wiki_label)
        self.assertIn("--- wiki/index.md ---", rendered)
        self.assertIn("never start a path with 'wiki/'", rendered)
        self.assertIn("relative to the wiki directory", rendered)
        self.assertIn("Never prefixed with the wiki directory's name", rendered)

    def test_legacy_prompt_is_unchanged(self) -> None:
        source = self.paths.root / "sample-incident.md"
        prompt = compose_prompt(source, source.read_text(encoding="utf-8"), load_schema_files(self.paths))
        rendered = _render_plain_text_prompt(prompt, wiki_label=self.paths.wiki_label)
        self.assertNotIn("never start a path with", rendered)

    def test_schema_path_property_carries_the_rule(self) -> None:
        path_property = _PATCH_SET_RESPONSE_SCHEMA["properties"]["edits"]["items"]["properties"]["path"]
        self.assertIn("Relative to the wiki directory", path_property["description"])


class TestInfoVerb(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-info-")
        self.root = make_repo_layout(Path(self._tmp.name))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_default_layout(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            for name in ("WIKI_STUDIO_ROOT", "WIKI_STUDIO_WIKI_DIR", "WIKI_STUDIO_PROPOSALS_DIR"):
                os.environ.pop(name, None)
            result = run_cli("info", cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("layout: default", result.stdout)
        self.assertIn("knowledge/wiki", result.stdout)
        self.assertIn("(default", result.stdout)
        self.assertIn("exists", result.stdout)
        self.assertIn("schema: packaged", result.stdout)

    def test_custom_layout_names_the_source(self) -> None:
        kb = self.root / "kb"
        shutil.copytree(self.root / "knowledge" / "wiki", kb)
        with patch.dict(os.environ, {ENV_WIKI_DIR: str(kb)}):
            result = run_cli("info", cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("layout: custom", result.stdout)
        self.assertIn(f"env {ENV_WIKI_DIR}", result.stdout)
        self.assertIn("label 'kb'", result.stdout)
        flagged = run_cli("info", "--proposals-dir", "inbox", cwd=self.root)
        self.assertIn("layout: custom", flagged.stdout)
        self.assertIn("(flag", flagged.stdout)
        self.assertIn("missing", flagged.stdout)

    def test_json_output(self) -> None:
        result = run_cli("info", "--json", "--wiki-dir", "kb", cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        info = json.loads(result.stdout)
        self.assertEqual(info["layout"], "custom")
        self.assertEqual(info["wiki_dir_source"], "flag")
        self.assertEqual(info["proposals_dir_source"], "default")
        self.assertFalse(info["wiki_dir_exists"])
        self.assertEqual(info["wiki_label"], "kb")
        self.assertEqual(info["schema"], "packaged")

    def test_version_stays_one_line(self) -> None:
        from wiki_studio import __version__

        result = run_cli("--version", cwd=self.root)
        self.assertEqual(result.stdout.strip(), __version__)

    def test_info_in_an_empty_directory_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            result = run_cli("info", cwd=Path(empty))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("missing", result.stdout)


if __name__ == "__main__":
    unittest.main()
