# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""``wiki_studio.schema`` encodes ``page-types.md`` and is what the package reads (0.2.0 FR-005..007).

The first test parses the markdown document and compares it with ``PAGE_TYPES``
type for type, so the human-readable contract and the Python structure cannot
drift. The others pin the derived constants to the values 0.1.0 exported.
"""

from __future__ import annotations

import re
import unittest
from importlib import resources

from wiki_studio import lint, prompt, proposal, schema
from wiki_studio.schema import PAGE_TYPES, PageTypeSpec

_TYPE_HEADING_RE = re.compile(r"^### `([a-z-]+)` — `([^`]+)`")
_SECTION_BULLET_RE = re.compile(r"^- `## ([^`]+)`")
_INLINE_SECTION_RE = re.compile(r"`## ([^`]+)`")
_REQUIRED_MARKER = "Required H2 sections"
_SOURCES_EXEMPTION_RE = re.compile(r"`sources:` is required for every type \*\*except\*\* ([^.]+)\.")

SCHEMA_DOCUMENTS = frozenset(
    {"audit-rules.md", "citation-rules.md", "ingest-rules.md", "lint-rules.md", "page-types.md", "WIKI_MAINTAINER.md"}
)

# What 0.1.0 exported from wiki_studio.lint, verbatim.
V010_VALID_PAGE_TYPES = (
    "concept",
    "workflow",
    "incident",
    "decision",
    "playbook",
    "glossary",
    "open-question",
    "index",
    "log",
    "overview",
)
V010_PAGE_TYPE_DIRS = {
    "concept": "concepts",
    "workflow": "workflows",
    "incident": "incidents",
    "decision": "decisions",
    "playbook": "playbooks",
    "glossary": "glossary",
    "open-question": "open-questions",
    "index": ".",
    "log": ".",
    "overview": ".",
}
V010_PROMOTABLE = frozenset({"concept", "workflow", "incident", "decision", "playbook", "glossary", "open-question"})


def _page_types_md() -> str:
    return resources.files("wiki_studio").joinpath("schema", "page-types.md").read_text(encoding="utf-8")


def _required_sections(block: list[str]) -> tuple[str, ...]:
    """The H2 names under a type's ``Required H2 sections`` marker.

    Bullet form (``- `## Name` — …``, one list ended by a blank line) or the
    inline form ``overview`` uses (``Required H2 sections match `concept`:
    `## Summary`, …`` up to a blank line). Optional sections and the ADR note
    sit after a blank line and are not collected.
    """
    for i, line in enumerate(block):
        if not line.startswith(_REQUIRED_MARKER):
            continue
        if line.rstrip().endswith(":"):
            names: list[str] = []
            started = False
            for bullet in block[i + 1 :]:
                if bullet.strip() == "":
                    if started:
                        break
                    continue
                started = True
                match = _SECTION_BULLET_RE.match(bullet)
                if match:
                    names.append(match.group(1))
            found = tuple(names)
        else:
            text = []
            for part in block[i:]:
                if part.strip() == "":
                    break
                text.append(part)
            found = tuple(_INLINE_SECTION_RE.findall(" ".join(text)))
        if not found:
            raise AssertionError(
                f"page-types.md: {block[0]!r} has a '{_REQUIRED_MARKER}' marker but no parsable sections"
            )
        return found
    return ()


def parse_page_types_md(text: str) -> dict[str, tuple[str, str | tuple[str, ...]]]:
    """``{type: (directory, required_sections)}`` from the ``### `type` — `path``` blocks."""
    lines = text.splitlines()
    starts = [(i, m) for i, line in enumerate(lines) if (m := _TYPE_HEADING_RE.match(line))]
    parsed: dict[str, tuple[str, str | tuple[str, ...]]] = {}
    for n, (i, match) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        block = lines[i:end]
        name, path = match.group(1), match.group(2)
        directory = path.split("/", 1)[0] if "/" in path else schema.ROOT_DIR
        parsed[name] = (directory, _required_sections(block))
    return parsed


class TestSchemaMatchesPageTypesMd(unittest.TestCase):
    def test_every_type_in_the_document_matches_the_module(self) -> None:
        parsed = parse_page_types_md(_page_types_md())
        self.assertEqual(set(parsed), set(PAGE_TYPES))
        for name, (directory, sections) in parsed.items():
            with self.subTest(page_type=name):
                self.assertEqual(PAGE_TYPES[name].directory, directory)
                self.assertEqual(PAGE_TYPES[name].required_sections, sections)

    def test_parser_reads_the_shapes_the_document_uses(self) -> None:
        parsed = parse_page_types_md(_page_types_md())
        # Bullet form with an optional section after it (incident), the inline
        # "match `concept`" form (overview), and a type without sections (index).
        self.assertEqual(
            parsed["incident"][1],
            ("What happened", "Why it happened", "What we changed", "How to recognize a recurrence"),
        )
        self.assertEqual(parsed["overview"][1], parsed["concept"][1])
        self.assertEqual(parsed["index"], (".", ()))
        self.assertEqual(parsed["glossary"][0], "glossary")

    def test_sources_exemption_matches_the_document(self) -> None:
        # "`sources:` is required for every type **except** `index` and `log`."
        match = _SOURCES_EXEMPTION_RE.search(_page_types_md())
        assert match is not None, "page-types.md no longer states the sources exemption"
        exempt = frozenset(re.findall(r"`([a-z-]+)`", match.group(1)))
        self.assertEqual(schema.SOURCELESS_PAGE_TYPES, exempt)
        for name, spec in PAGE_TYPES.items():
            self.assertEqual(spec.sources_required, name not in exempt, name)

    def test_promotable_means_the_document_gives_the_type_a_directory(self) -> None:
        # Root-only types are headed "`index.md` only"; promotable ones "<dir>/<slug>.md".
        parsed = parse_page_types_md(_page_types_md())
        for name, (directory, _) in parsed.items():
            with self.subTest(page_type=name):
                self.assertEqual(PAGE_TYPES[name].promotable, directory != schema.ROOT_DIR)


class TestDerivedConstants(unittest.TestCase):
    def test_values_and_order_are_those_of_0_1_0(self) -> None:
        self.assertEqual(schema.VALID_PAGE_TYPES, V010_VALID_PAGE_TYPES)
        self.assertEqual(schema.PAGE_TYPE_DIRS, V010_PAGE_TYPE_DIRS)
        self.assertEqual(list(schema.PAGE_TYPE_DIRS), list(V010_VALID_PAGE_TYPES))
        self.assertEqual(schema.PROMOTABLE_PAGE_TYPES, V010_PROMOTABLE)
        self.assertEqual(schema.REQUIRED_KEYS, ("page_type", "slug", "title", "status", "last_reviewed"))

    def test_root_only_types_are_not_promotable(self) -> None:
        for name in ("index", "log", "overview"):
            with self.subTest(page_type=name):
                self.assertFalse(PAGE_TYPES[name].promotable)
                self.assertEqual(PAGE_TYPES[name].directory, schema.ROOT_DIR)
        self.assertTrue(PAGE_TYPES["overview"].sources_required)

    def test_spec_is_frozen(self) -> None:
        spec = PageTypeSpec("x", ("A",), promotable=True, sources_required=True)
        with self.assertRaises(AttributeError):
            spec.directory = "y"  # type: ignore[misc]

    def test_package_modules_read_the_schema(self) -> None:
        self.assertIs(lint.VALID_PAGE_TYPES, schema.VALID_PAGE_TYPES)
        self.assertIs(lint.PAGE_TYPE_DIRS, schema.PAGE_TYPE_DIRS)
        self.assertIs(lint.REQUIRED_KEYS, schema.REQUIRED_KEYS)
        self.assertIs(prompt.PROMOTABLE_PAGE_TYPES, schema.PROMOTABLE_PAGE_TYPES)
        self.assertIs(proposal.PROMOTABLE_PAGE_TYPES, schema.PROMOTABLE_PAGE_TYPES)

    def test_schema_module_imports_nothing_from_the_package(self) -> None:
        source = resources.files("wiki_studio").joinpath("schema", "__init__.py").read_text(encoding="utf-8")
        self.assertNotIn("from .", source)
        self.assertNotIn("from wiki_studio", source)
        self.assertNotIn("import wiki_studio", source)


class TestSchemaDocumentsStillPackaged(unittest.TestCase):
    def test_six_markdown_documents_sit_beside_the_module(self) -> None:
        names = {entry.name for entry in resources.files("wiki_studio").joinpath("schema").iterdir()}
        self.assertEqual(names & SCHEMA_DOCUMENTS, SCHEMA_DOCUMENTS)
        self.assertIn("__init__.py", names)


if __name__ == "__main__":
    unittest.main()
