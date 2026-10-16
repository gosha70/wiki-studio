# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""wiki_studio.schema — the page schema as code.

``PAGE_TYPES`` encodes what ``page-types.md`` (shipped beside this module)
says about every page type: the directory it lives in, the H2 sections its
body must have, whether it may be the target of a ``create``/``update`` edit,
and whether ``sources:`` is required. The linter, the prompts and the
validators read the constants derived below, so the package holds one copy. A
consumer that keeps its own table (memkernel's ``PAGE_SECTIONS``) tests it
against this module; ``tests/test_schema.py`` keeps this module and the
markdown document in step.

This module imports nothing from the rest of the package. The markdown
documents in this directory are the human-readable contract and are loaded
through ``importlib.resources`` by :mod:`wiki_studio.prompt`.
"""

from __future__ import annotations

from dataclasses import dataclass

# Directory value of the page types that live at the wiki root.
ROOT_DIR = "."


@dataclass(frozen=True)
class PageTypeSpec:
    """What the schema says about one page type.

    ``directory`` is relative to the wiki (``"."`` for the root);
    ``required_sections`` are the H2 headings in order, without ``## ``;
    ``promotable`` is False for the root-only types that an ingest may only
    append to; ``sources_required`` is False for the types exempt from the
    citation rule.
    """

    directory: str
    required_sections: tuple[str, ...]
    promotable: bool
    sources_required: bool


_CONCEPT_SECTIONS: tuple[str, ...] = ("Summary", "Key ideas", "Where this shows up", "Related")

# Insertion order is the order 0.1.0's VALID_PAGE_TYPES had; lint messages print it.
PAGE_TYPES: dict[str, PageTypeSpec] = {
    "concept": PageTypeSpec("concepts", _CONCEPT_SECTIONS, promotable=True, sources_required=True),
    "workflow": PageTypeSpec(
        "workflows", ("When to use this", "Steps", "Verification", "Related"), promotable=True, sources_required=True
    ),
    "incident": PageTypeSpec(
        "incidents",
        ("What happened", "Why it happened", "What we changed", "How to recognize a recurrence"),
        promotable=True,
        sources_required=True,
    ),
    "decision": PageTypeSpec(
        "decisions",
        ("Decision", "Context", "Alternatives considered", "Consequences"),
        promotable=True,
        sources_required=True,
    ),
    "playbook": PageTypeSpec(
        "playbooks", ("Symptom", "Recovery steps", "Verification", "Prevention"), promotable=True, sources_required=True
    ),
    "glossary": PageTypeSpec("glossary", ("Definition", "Where it appears"), promotable=True, sources_required=True),
    "open-question": PageTypeSpec(
        "open-questions",
        ("Question", "Why it matters", "What an answer might look like"),
        promotable=True,
        sources_required=True,
    ),
    "index": PageTypeSpec(ROOT_DIR, (), promotable=False, sources_required=False),
    "log": PageTypeSpec(ROOT_DIR, (), promotable=False, sources_required=False),
    "overview": PageTypeSpec(ROOT_DIR, _CONCEPT_SECTIONS, promotable=False, sources_required=True),
}

VALID_PAGE_TYPES: tuple[str, ...] = tuple(PAGE_TYPES)

# Directory (relative to the wiki) each page type lives in; "." is the wiki root.
PAGE_TYPE_DIRS: dict[str, str] = {name: spec.directory for name, spec in PAGE_TYPES.items()}

# The only types valid as the target of a create or update edit.
PROMOTABLE_PAGE_TYPES: frozenset[str] = frozenset(name for name, spec in PAGE_TYPES.items() if spec.promotable)

# Page types that need no ``sources:`` block.
SOURCELESS_PAGE_TYPES: frozenset[str] = frozenset(
    name for name, spec in PAGE_TYPES.items() if not spec.sources_required
)

# Frontmatter keys every page must carry.
REQUIRED_KEYS: tuple[str, ...] = ("page_type", "slug", "title", "status", "last_reviewed")
