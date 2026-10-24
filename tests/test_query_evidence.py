# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Citation evidence (0.6.0 US4, FR-014): a query reply must quote the prompt snapshot.

Each citation's fragment is checked against the ``index_md`` and
``pages_content`` that went into the prompt, after whitespace
normalisation, never against a file reread after the backend returned. A
non-empty answer needs at least one citation; the abstention form (empty
answer, one citation quoting ``index.md``) passes; a failure exits 4 naming
the page.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from tests.conftest import make_repo_layout, run_cli
from wiki_studio.backends.test import TestBackend
from wiki_studio.errors import ContractViolationError
from wiki_studio.paths import WikiPaths
from wiki_studio.querier import DefaultQuerier

_PAGE = "concepts/foo.md"
_PAGE_TEXT = (
    "---\npage_type: concept\nslug: foo\ntitle: Foo\nstatus: stable\nlast_reviewed: 2026-05-06\n---\n\n"
    "# Foo\n\n"
    "Foo body spans\n"
    "  two lines with   extra spaces.\n"
)
_VERBATIM = "Foo body spans"
_WHITESPACE_VARIANT = "Foo body spans two lines with extra spaces."
_REPLACED_TEXT = "# Foo\n\nRewritten while the backend was running.\n"
_NEW_ONLY = "Rewritten while the backend was running."


def _build(tmp: Path) -> tuple[Path, WikiPaths]:
    """A wiki whose index links one concept page with multi-line body text."""
    root = make_repo_layout(tmp, with_schema=True, with_sample=False)
    wiki = root / "knowledge" / "wiki"
    (wiki / "index.md").write_text(
        "---\npage_type: index\nslug: index\ntitle: I\nstatus: stable\nlast_reviewed: 2026-05-06\n---\n\n"
        "# Index\n\n## Concepts\n\n- [Foo](concepts/foo.md) — about foo.\n",
        encoding="utf-8",
    )
    (wiki / "concepts").mkdir()
    (wiki / _PAGE).write_text(_PAGE_TEXT, encoding="utf-8")
    return root, WikiPaths.for_root(root)


class _ReplyBackend:
    """Returns a fixed reply; records the prompt it was given."""

    def __init__(self, answer: str, citations: list[dict[str, str]]) -> None:
        self.answer = answer
        self.citations = citations
        self.prompt: dict[str, Any] | None = None

    def call(self, prompt: dict[str, Any]) -> dict[str, Any]:
        self.prompt = prompt
        return {"version": 1, "answer": self.answer, "citations": self.citations}


class _RewritingBackend(_ReplyBackend):
    """Rewrites the live page during the call, then replies like :class:`_ReplyBackend`."""

    def __init__(self, page: Path, answer: str, citations: list[dict[str, str]]) -> None:
        super().__init__(answer, citations)
        self.page = page

    def call(self, prompt: dict[str, Any]) -> dict[str, Any]:
        self.page.write_text(_REPLACED_TEXT, encoding="utf-8")
        return super().call(prompt)


class _ForgingBackend:
    """A registry-shaped backend (no-arg constructor) that quotes text absent from the prompt."""

    def call(self, prompt: dict[str, Any]) -> dict[str, Any]:
        return {"version": 1, "answer": "forged", "citations": [{"page": _PAGE, "fragment": "not in the page"}]}


class TestCitationEvidence(unittest.TestCase):
    def _query(self, backend: Any, question: str = "foo") -> Any:
        with tempfile.TemporaryDirectory() as tmp:
            _root, paths = _build(Path(tmp))
            return DefaultQuerier(backend=backend, paths=paths).query(question)

    def test_forged_fragment_rejected_naming_the_page(self) -> None:
        backend = _ReplyBackend("an answer", [{"page": _PAGE, "fragment": "text that is not in the page"}])
        with self.assertRaises(ContractViolationError) as ctx:
            self._query(backend)
        message = str(ctx.exception)
        self.assertIn(_PAGE, message)
        self.assertIn("does not occur", message)

    def test_verbatim_fragment_accepted(self) -> None:
        answer = self._query(_ReplyBackend("an answer", [{"page": _PAGE, "fragment": _VERBATIM}]))
        self.assertEqual(answer.answer, "an answer")
        self.assertEqual([c.page for c in answer.citations], [_PAGE])

    def test_whitespace_variant_accepted(self) -> None:
        # The page breaks the sentence over two lines with extra spaces; the
        # reply quotes it on one line with single spaces.
        self.assertNotIn(_WHITESPACE_VARIANT, _PAGE_TEXT)
        padded = "  " + _WHITESPACE_VARIANT.replace(" ", "\n ", 1) + "\n"
        for fragment in (_WHITESPACE_VARIANT, padded):
            with self.subTest(fragment=fragment):
                answer = self._query(_ReplyBackend("an answer", [{"page": _PAGE, "fragment": fragment}]))
                self.assertEqual(answer.citations[0].fragment, fragment)

    def test_non_empty_answer_without_citations_rejected(self) -> None:
        with self.assertRaises(ContractViolationError) as ctx:
            self._query(_ReplyBackend("an answer with no evidence", []))
        self.assertIn("no citations", str(ctx.exception))

    def test_abstention_accepted(self) -> None:
        answer = self._query(_ReplyBackend("", [{"page": "index.md", "fragment": "## Concepts"}]))
        self.assertEqual(answer.answer, "")
        self.assertEqual(len(answer.citations), 1)

    def test_abstention_must_quote_the_index(self) -> None:
        with self.assertRaises(ContractViolationError) as ctx:
            self._query(_ReplyBackend("", [{"page": "index.md", "fragment": "(no answer found)"}]))
        self.assertIn("'index.md'", str(ctx.exception))

    def test_empty_answer_without_citations_is_not_an_evidence_failure(self) -> None:
        answer = self._query(_ReplyBackend("", []))
        self.assertEqual(answer.answer, "")
        self.assertEqual(answer.citations, [])

    def test_fragment_from_unloaded_page_still_rejected(self) -> None:
        with self.assertRaises(ContractViolationError) as ctx:
            self._query(_ReplyBackend("an answer", [{"page": "concepts/other.md", "fragment": "x"}]))
        self.assertIn("concepts/other.md", str(ctx.exception))

    def test_page_changed_during_call_original_prompt_fragment_validates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, paths = _build(Path(tmp))
            page = root / "knowledge" / "wiki" / _PAGE
            backend = _RewritingBackend(page, "an answer", [{"page": _PAGE, "fragment": _VERBATIM}])
            answer = DefaultQuerier(backend=backend, paths=paths).query("foo")
            # The live file no longer holds the fragment; the prompt snapshot did.
            self.assertNotIn(_VERBATIM, page.read_text(encoding="utf-8"))
            assert backend.prompt is not None
            self.assertIn(_VERBATIM, backend.prompt["wiki_state"]["candidate_pages"][_PAGE])
            self.assertEqual(answer.citations[0].fragment, _VERBATIM)

    def test_page_changed_during_call_new_file_only_fragment_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, paths = _build(Path(tmp))
            page = root / "knowledge" / "wiki" / _PAGE
            backend = _RewritingBackend(page, "an answer", [{"page": _PAGE, "fragment": _NEW_ONLY}])
            with self.assertRaises(ContractViolationError) as ctx:
                DefaultQuerier(backend=backend, paths=paths).query("foo")
            # The fragment is in the live file now, but it was never in the prompt.
            self.assertIn(_NEW_ONLY, page.read_text(encoding="utf-8"))
            self.assertIn(_PAGE, str(ctx.exception))

    def test_test_backend_fixture_satisfies_the_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _root, paths = _build(Path(tmp))
            querier = DefaultQuerier(backend=TestBackend(), paths=paths)
            answered = querier.query("foo")
            self.assertTrue(answered.answer)
            self.assertEqual([c.page for c in answered.citations], [_PAGE])
            self.assertIn(answered.citations[0].fragment, _PAGE_TEXT)
            abstained = querier.query("zzz nothing matches")
            self.assertEqual(abstained.answer, "")
            self.assertEqual(abstained.citations[0].page, "index.md")
            self.assertEqual(abstained.citations[0].fragment, "---")

    def test_cli_reply_quoting_text_absent_from_prompt_exits_4(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, _paths = _build(Path(tmp))
            with patch.dict("wiki_studio.backends._REGISTRY", {"forge": _ForgingBackend}):
                result = run_cli("query", "foo", "--backend", "forge", cwd=root)
        self.assertEqual(result.returncode, 4, result.stderr)
        self.assertIn("contract violation", result.stderr)
        self.assertIn(_PAGE, result.stderr)
        self.assertFalse((root / "doc_internal" / "wiki-query-log.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
