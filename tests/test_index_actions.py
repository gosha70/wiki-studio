# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Issue #15: index.md and log.md change only through one-line append edits, and the prompt says so.

Also covers the 0.3.1 packaging change: the ``py.typed`` marker ships with the package.
"""

from __future__ import annotations

import tempfile
import unittest
from importlib import resources
from pathlib import Path
from typing import Any

from tests.conftest import make_repo_layout
from wiki_studio.backends.copilot_cli import _render_plain_text_prompt
from wiki_studio.errors import ContractViolationError
from wiki_studio.ingestor_multi import DefaultMultiIngestor
from wiki_studio.paths import WikiPaths
from wiki_studio.prompt import (
    _PATCH_SET_RESPONSE_SCHEMA,
    INDEX_LOG_ACTION_RULE,
    compose_multi_prompt,
    compose_prompt,
    load_schema_files,
)
from wiki_studio.proposal import IngestRequest
from wiki_studio.schema import PROMOTABLE_PAGE_TYPES
from wiki_studio.wiki_state import load_wiki_state

PAGE = (
    "---\npage_type: concept\nslug: x\ntitle: X\nstatus: draft\nlast_reviewed: 2026-10-16\n"
    "sources:\n  - path: sample-incident.md\n    sha: abc1234\n---\n\n# X\n\n## Summary\n\nBody.\n"
)
# The shape run 2 returned for ADR-009, licensing and sibling-projects.
FULL_INDEX = (
    "---\npage_type: index\nslug: index\ntitle: Index\nstatus: stable\nlast_reviewed: 2026-10-16\n---\n\n# Index\n"
)


class _Backend:
    def __init__(self, index_edit: dict[str, str]) -> None:
        self.index_edit = index_edit

    def call(self, prompt: dict[str, Any]) -> dict[str, Any]:
        return {
            "version": 1,
            "rationale": "one concept",
            "edits": [
                {"path": "concepts/x.md", "action": "create", "new_content": PAGE, "rationale": "r"},
                self.index_edit,
                {"path": "log.md", "action": "append-log", "new_content": "- 2026-10-16 — created x", "rationale": "r"},
            ],
        }


class TestPromptStatesTheIndexLogRule(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-index-")
        self.root = make_repo_layout(Path(self._tmp.name))
        self.paths = WikiPaths.for_root(self.root)
        self.source = self.root / "sample-incident.md"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _rendered_multi(self) -> str:
        content = self.source.read_text(encoding="utf-8")
        prompt = compose_multi_prompt(
            source_path=self.source,
            source_content=content,
            schema_files=load_schema_files(self.paths),
            wiki_state=load_wiki_state(paths=self.paths, source_path=self.source, source_content=content),
            source_kind="file",
        )
        return _render_plain_text_prompt(prompt, wiki_label=self.paths.wiki_label)

    def test_multi_page_prompt_names_the_actions_and_forbids_rewriting(self) -> None:
        rendered = self._rendered_multi()
        self.assertIn(INDEX_LOG_ACTION_RULE, rendered)
        self.assertIn("'append-index' edit", rendered)
        self.assertIn("'append-log' edit", rendered)
        self.assertIn("never rewrite them", rendered)

    def test_rule_lists_exactly_the_promotable_types(self) -> None:
        # The rule ends with the promotable types in parentheses; that list is exactly the schema's.
        listed = INDEX_LOG_ACTION_RULE.rstrip(".").rsplit("(", 1)[1].rstrip(")")
        self.assertEqual(listed.split(", "), sorted(PROMOTABLE_PAGE_TYPES))

    def test_schema_carries_the_rule(self) -> None:
        item = _PATCH_SET_RESPONSE_SCHEMA["properties"]["edits"]["items"]["properties"]
        self.assertEqual(item["action"]["description"], INDEX_LOG_ACTION_RULE)
        self.assertIn("exactly one line", item["new_content"]["description"])

    def test_legacy_prompt_is_unchanged(self) -> None:
        prompt = compose_prompt(self.source, self.source.read_text(encoding="utf-8"), load_schema_files(self.paths))
        rendered = _render_plain_text_prompt(prompt, wiki_label=self.paths.wiki_label)
        self.assertNotIn(INDEX_LOG_ACTION_RULE, rendered)


class TestFullPageIndexEditStaysRejected(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-index-")
        self.root = make_repo_layout(Path(self._tmp.name))
        self.paths = WikiPaths.for_root(self.root)
        self.request = IngestRequest(
            source_path=self.root / "sample-incident.md", source_kind="file", backend_name="stub"
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _ingest(self, index_edit: dict[str, str]) -> list[str]:
        patch = DefaultMultiIngestor(backend=_Backend(index_edit), paths=self.paths).ingest_multi(self.request)
        return [f"{e.action}:{e.path}" for e in patch.edits]

    def test_full_page_index_update_is_a_contract_violation(self) -> None:
        with self.assertRaises(ContractViolationError) as ctx:
            self._ingest({"path": "index.md", "action": "update", "new_content": FULL_INDEX, "rationale": "r"})
        message = str(ctx.exception)
        self.assertEqual(ctx.exception.exit_code, 4)
        self.assertIn("page_type 'index' is not promotable for create/update", message)
        self.assertIn("'sources:' must be a non-empty list", message)

    def test_rule_scopes_appends_to_the_root_index_and_allows_content_index_pages(self) -> None:
        self.assertIn("The root index.md changes only through an 'append-index' edit", INDEX_LOG_ACTION_RULE)
        self.assertIn(
            "glossary/index.md with page_type glossary, is edited like any content page", INDEX_LOG_ACTION_RULE
        )
        self.assertNotIn("any <dir>/index.md) changes only", INDEX_LOG_ACTION_RULE)

    def test_full_page_glossary_index_update_is_valid(self) -> None:
        # Review of PR #16: glossary/index.md is a content page (page_type glossary); a full-page
        # update must stay valid, which the rule now says too.
        glossary = self.paths.wiki_dir / "glossary"
        glossary.mkdir()
        page = (
            "---\npage_type: glossary\nslug: glossary\ntitle: Glossary\nstatus: draft\nlast_reviewed: 2026-10-16\n"
            "sources:\n  - path: sample-incident.md\n    sha: abc1234\n---\n\n# Glossary\n\n### Term\n\nMeaning.\n"
        )
        (glossary / "index.md").write_text(page, encoding="utf-8")
        updated = page.replace("Meaning.", "Meaning, revised.")
        edits = self._ingest(
            {"path": "index.md", "action": "append-index", "new_content": "- [X](concepts/x.md) — x.", "rationale": "r"}
        )
        self.assertIn("append-index:index.md", edits)
        backend = _Backend({"path": "glossary/index.md", "action": "update", "new_content": updated, "rationale": "r"})
        patch = DefaultMultiIngestor(backend=backend, paths=self.paths).ingest_multi(self.request)
        self.assertIn("update:glossary/index.md", [f"{e.action}:{e.path}" for e in patch.edits])

    def test_append_index_line_is_accepted(self) -> None:
        edits = self._ingest(
            {"path": "index.md", "action": "append-index", "new_content": "- [X](concepts/x.md) — x.", "rationale": "r"}
        )
        self.assertEqual(edits, ["create:concepts/x.md", "append-index:index.md", "append-log:log.md"])


class TestTypedMarkerShips(unittest.TestCase):
    def test_py_typed_is_package_data(self) -> None:
        self.assertTrue(resources.files("wiki_studio").joinpath("py.typed").is_file())


if __name__ == "__main__":
    unittest.main()
