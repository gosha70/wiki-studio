# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The near-duplicate study's extraction rule and review sample, before any page exists (issue 121, FR-009).

Every case runs on inputs written here: decision sections and items, the title rule, each body step, the page
bytes, the left-out item, the families, ``sample.py`` on synthetic labels, and the git reading on temporary
repositories (skipped only when git is not on PATH). The six fixed items are real items of the two pinned
repositories, written out as read with ``git show <pin>:<path>``, each with its title and the paragraph the scorer
reads written out by hand: the first paragraph of each item's text after its label.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import random
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest
from itertools import combinations
from pathlib import Path
from typing import Any
from unittest import mock

from eval.duplicates import extract, sample
from eval.duplicates.extract import (
    CLOSING_KEYWORD_RE,
    CODE_COPILOT_TEAM,
    EXTENSION_ORDER,
    FORM_BOLD_PARAGRAPH,
    FORM_H3,
    FORM_H3_ADR,
    FORM_LIST_ITEM,
    MEMKERNEL,
    PINS,
    Item,
    Snapshot,
    build_page,
    decision_sections,
    extract_corpus,
    family_directories,
    file_items,
    item_body,
    item_label,
    item_title,
    section_items,
    slug_for,
    title_from_label,
)
from eval.patterns.duplicates import _first_paragraph, _title
from wiki_studio.wiki_state import _tokenise

GIT = shutil.which("git")
REPO_ROOT = Path(__file__).resolve().parents[1]
DUPLICATES_DIR = REPO_ROOT / "eval" / "duplicates"
CCT_DATE = "2026-11-22"
MK_DATE = "2026-11-23"
SETUP_DATE = "2026-01-02 03:04:05 +0000"
ADR_LABEL_RE = re.compile(r"^\*\*(?:Context|Decision|Consequences)\*\*: ")
MARKER_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)]) ")

# A closing-keyword phrase, built at run time so that no file holds one (FR-007).
CLOSING_TEXT = "fix" + "es #" + "12"


def fixed(
    repository: str, spec_path: str, line_start: int, form: str, raw: list[str], title: str, paragraph: str
) -> dict[str, Any]:
    return {
        "repository": repository,
        "spec_path": spec_path,
        "line_start": line_start,
        "line_end": line_start + len(raw) - 1,
        "form": form,
        "raw": "\n".join(raw),
        "title": title,
        "paragraph": paragraph,
    }


# FR-009: the six fixed items, one per form in each repository (O12). code-copilot-team's base holds H3 items only
# in pi-harness-adoption's ADR section, so its H3 item is of form h3-adr, with a Decision line alone.
FIXED_ITEMS: dict[str, dict[str, Any]] = {
    "cct-routing-calibration-plan-03": fixed(
        CODE_COPILOT_TEAM,
        "specs/routing-calibration/plan.md",
        86,
        FORM_LIST_ITEM,
        [
            "3. **Reports bind to corpus AND policy.**",
            "   `corpus_id = sha256(canonical JSON of the sorted consumed set ids)`.",
            "   `policy_id = sha256(canonical JSON of the full evaluation policy)`:",
            "   the feature-vocabulary version, k, k_min, distance metric,",
            "   weighting epsilon, normalization scheme, tier floor, the canonical",
            "   digest of the current security/role policy source, and",
            "   `max_false_downgrade_rate`. Evaluation and gate reports carry BOTH;",
            "   serving recomputes both from the live corpus and configuration and",
            "   marks any mismatch `stale: true` — a stale report renders with an",
            "   explicit stale state and satisfies no gate. An evaluation produced",
            "   under an old metric, floor, or policy can never pass G3–G5.",
        ],
        "Reports bind to corpus AND policy",
        "`corpus_id = sha256(canonical JSON of the sorted consumed set ids)`. `policy_id = sha256(canonical JSON of"
        " the full evaluation policy)`: the feature-vocabulary version, k, k_min, distance metric, weighting"
        " epsilon, normalization scheme, tier floor, the canonical digest of the current security/role policy"
        " source, and `max_false_downgrade_rate`. Evaluation and gate reports carry BOTH; serving recomputes both"
        " from the live corpus and configuration and marks any mismatch `stale: true` — a stale report renders"
        " with an explicit stale state and satisfies no gate. An evaluation produced under an old metric, floor,"
        " or policy can never pass G3–G5.",
    ),
    "cct-routing-context-limit-plan-03": fixed(
        CODE_COPILOT_TEAM,
        "specs/routing-context-limit/plan.md",
        97,
        FORM_BOLD_PARAGRAPH,
        [
            "**D3 — fail-closed only where a requirement exists.** A task with no",
            "`min_context_tokens` filters nothing, so every existing registry and",
            "feature keeps behaving byte-identically. The fail-closed rule engages",
            "only once someone states a requirement. This is what makes rule 2 safe",
            "to adopt: it cannot retroactively strand an existing configuration.",
        ],
        "fail-closed only where a requirement exists",
        "A task with no `min_context_tokens` filters nothing, so every existing registry and feature keeps behaving"
        " byte-identically. The fail-closed rule engages only once someone states a requirement. This is what"
        " makes rule 2 safe to adopt: it cannot retroactively strand an existing configuration.",
    ),
    "cct-pi-harness-adoption-plan-04": fixed(
        CODE_COPILOT_TEAM,
        "specs/pi-harness-adoption/plan.md",
        115,
        FORM_H3_ADR,
        [
            "### ADR-4: Launcher symmetry with `claude-code` (R4)",
            "**Decision**: `pi-code` mirrors `claude-code` for `init`/`sync`/peer-review",
            "flags and the `CCT_PEER_*` env contract, reusing the existing scaffolder",
            "and sync implementations rather than forking them.",
        ],
        "Launcher symmetry with `claude-code`",
        "`pi-code` mirrors `claude-code` for `init`/`sync`/peer-review flags and the `CCT_PEER_*` env contract,"
        " reusing the existing scaffolder and sync implementations rather than forking them.",
    ),
    "mk-memkernel-0-12-capture-core-spec-01": fixed(
        MEMKERNEL,
        "specs/memkernel-0-12-capture-core/spec.md",
        306,
        FORM_LIST_ITEM,
        [
            "- **D1 Key.** (session, `tool_use_id`, extractor), with the extractor version as a tag. No version"
            " supersede; a",
            "  session is captured once, under the version installed then. (Amended by the owner, R2: the key named"
            " the record",
            "  UUID, which several results in one entry share.)",
        ],
        "Key",
        "(session, `tool_use_id`, extractor), with the extractor version as a tag. No version supersede; a session"
        " is captured once, under the version installed then. (Amended by the owner, R2: the key named the record"
        " UUID, which several results in one entry share.)",
    ),
    "mk-memkernel-0-7-wiring-spool-spec-02": fixed(
        MEMKERNEL,
        "specs/memkernel-0-7-wiring-spool/spec.md",
        32,
        FORM_BOLD_PARAGRAPH,
        [
            "**W2. Spool pruning (#79 follow-up).** At each `startup` drain:",
            "- A session with no `ended` line whose newest line is older than `SPOOL_UNENDED_MAX_AGE` (a named"
            " constant, 7",
            "  days) is removed. The current session is never removed.",
            '- Such a session gets no "ended without a saved checkpoint" line, because its window never closed.',
            '- If any were removed, the block says so once: "N earlier session(s) recorded no end (crashed, or'
            " session-end.py",
            '  is not registered under SessionEnd)."',
            "- The spool then holds at most the current session, sessions under 7 days old without an end, and ended"
            " sessions",
            "  not yet drained.",
        ],
        "Spool pruning",
        "At each `startup` drain: A session with no `ended` line whose newest line is older than"
        " `SPOOL_UNENDED_MAX_AGE` (a named constant, 7 days) is removed. The current session is never removed. Such"
        ' a session gets no "ended without a saved checkpoint" line, because its window never closed. If any were'
        ' removed, the block says so once: "N earlier session(s) recorded no end (crashed, or session-end.py is not'
        ' registered under SessionEnd)." The spool then holds at most the current session, sessions under 7 days'
        " old without an end, and ended sessions not yet drained.",
    ),
    "mk-memkernel-0-3-plan-03": fixed(
        MEMKERNEL,
        "specs/memkernel-0-3/plan.md",
        72,
        FORM_H3_ADR,
        [
            "### ADR-3: `forget_expired` leaves the MCP surface",
            "",
            "**Context**: `ask` is the tenth tool; the ceiling is ten exclusive.",
            "**Decision**: remove the `forget_expired` tool (consolidate already purges); keep the service method.",
            "**Consequences**: noted in CHANGELOG as a removal in a pre-1.0 release.",
        ],
        "`forget_expired` leaves the MCP surface",
        "remove the `forget_expired` tool (consolidate already purges); keep the service method.",
    ),
}
COMMIT_DATES = {CODE_COPILOT_TEAM: CCT_DATE, MEMKERNEL: MK_DATE}


def fixed_item(slug: str) -> Item:
    """The fixed item ``slug`` as extract.py reads it: its raw text taken as a decision section's lines."""
    spec = FIXED_ITEMS[slug]
    items = section_items(spec["raw"].split("\n"), spec["line_start"])
    if len(items) != 1:
        raise AssertionError(f"{slug}: expected one item, got {len(items)}")
    return items[0]


def fixed_page(slug: str) -> tuple[str, str]:
    """The fixed item's title and page, built by extract.py's page builder."""
    spec = FIXED_ITEMS[slug]
    repository = spec["repository"]
    return build_page(
        fixed_item(slug),
        slug=slug,
        spec_path=spec["spec_path"],
        pin=PINS[repository],
        commit_date=COMMIT_DATES[repository],
    )


def items_of(*lines: str, first_line: int = 1) -> list[Item]:
    return section_items(list(lines), first_line)


def one_item(*lines: str) -> Item:
    items = items_of(*lines)
    assert len(items) == 1, items
    return items[0]


def body_lines(item: Item) -> list[str]:
    """The body below ``## Decision`` (for any form but h3-adr)."""
    body = item_body(item)
    assert body.startswith("## Decision\n\n"), body
    return body[len("## Decision\n\n") :].split("\n")


def memory_snapshot(repository: str, files: dict[str, str], *, pin: str = "0" * 40) -> Snapshot:
    return Snapshot(
        repository=repository,
        pin=pin,
        commit_date=COMMIT_DATES[repository],
        paths=frozenset(files),
        read=files.__getitem__,
    )


def tree_digest(root: Path) -> dict[str, str]:
    """Path and sha256 of every file under ``root``, ``.git`` included."""
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class SectionsAndFormsTest(unittest.TestCase):
    """FR-004: decision sections, the three forms by precedence, item boundaries, h3-adr."""

    def test_decision_sections_are_h2_lines_outside_fences_up_to_the_next_h2(self) -> None:
        lines = [
            "# Title",
            "## Decisions",
            "a",
            "```",
            "## A fenced decision heading",
            "```",
            "b",
            "## Files",
            "c",
            "## Design DECISIONS to confirm",
            "d",
            "### Not an H2 decision",
        ]
        self.assertEqual(decision_sections(lines), [(2, 7), (10, 12)])

    def test_file_items_reads_every_section_in_document_order(self) -> None:
        text = "\n".join(
            [
                "## Decisions",
                "- **D1 One.** first",
                "## Other",
                "- **X1 Not read.** never",
                "## Two wiring decisions",
                "**W1 — Two.** second",
            ]
        )
        items = file_items(text)
        self.assertEqual(
            [(item.form, item.line_start, item.line_end) for item in items],
            [
                (FORM_LIST_ITEM, 2, 2),
                (FORM_BOLD_PARAGRAPH, 6, 6),
            ],
        )

    def test_h3_items_and_their_spans(self) -> None:
        items = items_of("Intro.", "", "### D1 — Alpha", "text", "", "### D2 — Beta", "more", "", first_line=10)
        self.assertEqual(
            [(item.form, item.line_start, item.line_end) for item in items],
            [
                (FORM_H3, 12, 13),
                (FORM_H3, 15, 16),
            ],
        )

    def test_bold_paragraphs_keep_their_column_0_bullets(self) -> None:
        items = items_of(
            "Intro text.",
            "",
            "**A. First.** body",
            "- bullet one",
            "- **bullet two**",
            "",
            "**B. Second.**",
            "- x",
            "**not a start: no blank line before it**",
        )
        self.assertEqual([item.form for item in items], [FORM_BOLD_PARAGRAPH, FORM_BOLD_PARAGRAPH])
        self.assertEqual(items[0].lines, ("**A. First.** body", "- bullet one", "- **bullet two**"))
        self.assertEqual(items[1].lines, ("**B. Second.**", "- x", "**not a start: no blank line before it**"))

    def test_a_bold_paragraph_on_the_sections_first_line_is_an_item(self) -> None:
        items = items_of("**W1. First.** a", "- b")
        self.assertEqual([(item.form, item.line_start, item.line_end) for item in items], [(FORM_BOLD_PARAGRAPH, 1, 2)])

    def test_list_items_with_continuations_and_a_nested_item(self) -> None:
        items = items_of(
            "Intro.",
            "",
            "- **D1 One.** text",
            "  continued",
            "  - nested item",
            "",
            "  after a blank line",
            "3) **D2 Two.** more",
            "- plain bullet, not an item",
            "  still not an item",
            "10. **D3 Three.**",
            "",
            "Closing text.",
        )
        self.assertEqual(
            [(item.form, item.line_start, item.line_end) for item in items],
            [
                (FORM_LIST_ITEM, 3, 7),
                (FORM_LIST_ITEM, 8, 8),
                (FORM_LIST_ITEM, 11, 11),
            ],
        )

    def test_text_before_the_first_item_is_not_an_item(self) -> None:
        items = items_of("Some intro **bold** words.", "", "- **D1 One.** text")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].lines, ("- **D1 One.** text",))

    def test_h3_takes_precedence_over_bold_paragraphs(self) -> None:
        items = items_of("**Note.** before", "", "### D1 — A", "", "**Bold.** inside", "", "- **L1 List.** inside")
        self.assertEqual([(item.form, item.line_start) for item in items], [(FORM_H3, 3)])
        self.assertEqual(items[0].lines[-1], "- **L1 List.** inside")

    def test_bold_paragraphs_take_precedence_over_list_items(self) -> None:
        items = items_of("- **L1 List.** first", "", "**B1 Bold.** second")
        self.assertEqual([(item.form, item.line_start) for item in items], [(FORM_BOLD_PARAGRAPH, 3)])

    def test_fenced_lines_start_no_item(self) -> None:
        items = items_of("- **D1 One.** text", "```", "- **inside a fence**", "```")
        self.assertEqual([item.line_start for item in items], [1])

    def test_an_h3_with_a_decision_line_is_h3_adr(self) -> None:
        items = items_of(
            "### ADR-1: First",
            "**Context**: c",
            "  **decision:** lower case, colon inside",
            "### ADR-2: Second",
            "**Context**: c only",
        )
        self.assertEqual([item.form for item in items], [FORM_H3_ADR, FORM_H3])


class TitleTest(unittest.TestCase):
    """FR-005: the identifier, the trailing parenthetical, one trailing ``.`` or ``:``, the first-sentence fallback."""

    def test_the_specs_title_cases(self) -> None:
        cases = {
            "D5 Key.": "Key",
            "D-upsert-key": "",
            "S1. A wiki's identity: two tags (#80 option A).": "A wiki's identity: two tags",
            "A1 (the owner's, 2026-11-15, review of #127).": "",
            "ADR-1: MCP-first, FastAPI secondary": "MCP-first, FastAPI secondary",
            "Placement: session analytics, read-only.": "Placement: session analytics, read-only",
            "D2 — Calibration corpus source": "Calibration corpus source",
            "FR-012 The rule:": "The rule",
            "R2) Retry once": "Retry once",
            "G1.2b: Nested": "Nested",
            "API + Studio surface.": "API + Studio surface",
            "Two tags: (option A).": "Two tags:",
        }
        for label, title in cases.items():
            with self.subTest(label=label):
                self.assertEqual(title_from_label(label), title)

    def test_an_empty_title_falls_back_to_the_first_sentence_of_the_body(self) -> None:
        item = one_item("- **D-upsert-key** — Upserts on the id.  Then   more text.", "  continued.")
        self.assertEqual(item_title(item), "Upserts on the id.")
        amendment = one_item("- **A1 (the owner's, 2026-11-15, review of #127).** The cap is 10?", "  Yes.")
        self.assertEqual(item_title(amendment), "The cap is 10?")

    def test_a_body_without_a_sentence_end_gives_its_whole_first_paragraph(self) -> None:
        item = one_item("- **D7** no end", "  here", "", "  second paragraph.")
        self.assertEqual(item_title(item), "no end here")

    def test_a_label_over_several_lines_is_one_line_of_title(self) -> None:
        item = one_item(
            "1. **Placement: session analytics, read-only over E1 sets via the E2", "   loader.** New module"
        )
        self.assertEqual(item_label(item), "Placement: session analytics, read-only over E1 sets via the E2 loader.")
        self.assertEqual(item_title(item), "Placement: session analytics, read-only over E1 sets via the E2 loader")
        self.assertEqual(body_lines(item), ["New module"])

    def test_an_h3_label_is_the_heading_text(self) -> None:
        item = one_item("### D2 — Calibration corpus source", "text")
        self.assertEqual(item_title(item), "Calibration corpus source")


class BodyTest(unittest.TestCase):
    """FR-006: the four body steps; no word changed, added or reordered."""

    def test_step_1_removes_the_label_and_one_separator(self) -> None:
        self.assertEqual(body_lines(one_item("**D-x** — text")), ["text"])
        self.assertEqual(body_lines(one_item("**Foo**: text")), ["text"])
        self.assertEqual(body_lines(one_item("**Foo** - text")), ["text"])
        self.assertEqual(body_lines(one_item("- **Foo.** (text)")), ["(text)"])
        self.assertEqual(body_lines(one_item("- **Foo.**", "  text")), ["text"])
        self.assertEqual(body_lines(one_item("### D1 — Heading", "text")), ["text"])

    def test_step_2_removes_indentation_and_one_marker_per_line(self) -> None:
        item = one_item("- **A.** one", "  - two", "    3. three", "  * four", "  + five", "  - - six", "  7) seven")
        self.assertEqual(body_lines(item), ["one", "two", "three", "four", "five", "- six", "seven"])

    def test_step_2_keeps_blank_lines_where_they_were(self) -> None:
        item = one_item("**A.** p1", "- p1 bullet", "", "p2", "", "", "p3")
        self.assertEqual(body_lines(item), ["p1", "p1 bullet", "", "p2", "", "", "p3"])

    def test_step_2_copies_a_fenced_block_unchanged(self) -> None:
        item = one_item(
            "- **A.** intro", "  ```text", "    keep  indented", "  - not a marker", "  ```", "  - after the fence"
        )
        self.assertEqual(
            body_lines(item), ["intro", "```text", "    keep  indented", "  - not a marker", "```", "after the fence"]
        )
        tilde = one_item("**B.** intro", "~~~", "  - kept", "~~~")
        self.assertEqual(body_lines(tilde), ["intro", "~~~", "  - kept", "~~~"])

    def test_step_3_moves_the_adr_lines_without_labels_in_item_order(self) -> None:
        item = one_item(
            "### ADR-9: Title",
            "  Pre line.",
            "**Decision:** chosen",
            "more decision",
            "",
            "**CONTEXT**: why",
            "**Consequences**:after",
        )
        self.assertEqual(item.form, FORM_H3_ADR)
        self.assertEqual(
            item_body(item),
            "Pre line.\n\n## Decision\n\nchosen\nmore decision\n\n## Context\n\nwhy\n\n## Consequences\n\nafter",
        )

    def test_step_4_keeps_headings_tables_and_quotes(self) -> None:
        item = one_item("**A.** intro", "", "#### Sub", "| a | b |", "> quoted", "  (D6) and FR-012 stay")
        self.assertEqual(body_lines(item), ["intro", "", "#### Sub", "| a | b |", "> quoted", "(D6) and FR-012 stay"])

    def test_no_word_is_changed_added_or_reordered(self) -> None:
        for slug, spec in FIXED_ITEMS.items():
            with self.subTest(slug=slug):
                raw_lines = spec["raw"].split("\n")
                if spec["form"] == FORM_H3_ADR:
                    text = "\n".join(raw_lines[1:])
                else:
                    text = re.sub(r"\*\*.+?\*\*", "", spec["raw"], count=1, flags=re.DOTALL)
                expected: list[str] = []
                for line in text.split("\n"):
                    expected.extend(ADR_LABEL_RE.sub("", MARKER_RE.sub("", line)).split())
                words = item_body(fixed_item(slug)).split()
                headings = {index + 1 for index, word in enumerate(words) if word == "##"}
                body_words = [word for index, word in enumerate(words) if word != "##" and index not in headings]
                self.assertEqual(body_words, expected)


class PageTest(unittest.TestCase):
    """FR-006: the page bytes, the slug and the single final newline; FR-007's per-page counts."""

    def test_the_page_bytes(self) -> None:
        item = one_item("- **D2 The owner's rule.** text", "  more")
        slug = slug_for(CODE_COPILOT_TEAM, "routing-x", "plan.md", 2)
        title, page = build_page(
            item, slug=slug, spec_path="specs/routing-x/plan.md", pin=PINS[CODE_COPILOT_TEAM], commit_date=CCT_DATE
        )
        expected = (
            "---\n"
            "page_type: decision\n"
            "slug: cct-routing-x-plan-02\n"
            "title: 'The owner''s rule'\n"
            "status: stable\n"
            "last_reviewed: 2026-11-22\n"
            "sources:\n"
            "  - path: specs/routing-x/plan.md\n"
            f"    sha: {PINS[CODE_COPILOT_TEAM]}\n"
            "---\n"
            "\n"
            "## Decision\n"
            "\n"
            "text\n"
            "more\n"
        )
        self.assertEqual(title, "The owner's rule")
        self.assertEqual(page, expected)
        self.assertEqual(_title(page), "The owner's rule")
        self.assertFalse(page.endswith("\n\n"))

    def test_an_adr_page_holds_its_sections(self) -> None:
        _title_text, page = fixed_page("mk-memkernel-0-3-plan-03")
        self.assertTrue(
            page.endswith(
                "---\n\n## Context\n\n`ask` is the tenth tool; the ceiling is ten exclusive.\n\n## Decision\n\n"
                "remove the `forget_expired` tool (consolidate already purges); keep the service method.\n\n"
                "## Consequences\n\nnoted in CHANGELOG as a removal in a pre-1.0 release.\n"
            ),
            page,
        )

    def test_the_slug_form(self) -> None:
        self.assertEqual(slug_for(MEMKERNEL, "memkernel-0-3", "plan.md", 3), "mk-memkernel-0-3-plan-03")
        self.assertEqual(
            slug_for(CODE_COPILOT_TEAM, "pi-project-config", "spec.md", 12), "cct-pi-project-config-spec-12"
        )

    def test_the_input_counts_read_one_page(self) -> None:
        _title_text, page = fixed_page("cct-routing-context-limit-plan-03")
        counts = extract.input_counts(page)
        self.assertEqual(counts["title_tokens"], len(_tokenise("fail-closed only where a requirement exists")))
        self.assertEqual(counts["paragraph_tokens"], len(_tokenise(_first_paragraph(page))))
        self.assertFalse(counts["paragraph_empty"])
        _title_text, table_page = build_page(
            one_item("**T1 Table only.**", "| a | b |"), slug="s", spec_path="p", pin="x", commit_date=CCT_DATE
        )
        self.assertTrue(extract.input_counts(table_page)["paragraph_empty"])


class FixedItemsTest(unittest.TestCase):
    """FR-009: the six fixed items through the page builder; the scorer's paragraph is the first paragraph of each
    item's text after its label."""

    def test_one_per_form_in_each_repository(self) -> None:
        forms = {(spec["repository"], spec["form"]) for spec in FIXED_ITEMS.values()}
        self.assertEqual(
            forms,
            {
                (CODE_COPILOT_TEAM, FORM_LIST_ITEM),
                (CODE_COPILOT_TEAM, FORM_BOLD_PARAGRAPH),
                (CODE_COPILOT_TEAM, FORM_H3_ADR),
                (MEMKERNEL, FORM_LIST_ITEM),
                (MEMKERNEL, FORM_BOLD_PARAGRAPH),
                (MEMKERNEL, FORM_H3_ADR),
            },
        )

    def test_each_item_reads_as_its_form_and_span(self) -> None:
        for slug, spec in FIXED_ITEMS.items():
            with self.subTest(slug=slug):
                item = fixed_item(slug)
                self.assertEqual(
                    (item.form, item.line_start, item.line_end),
                    (
                        spec["form"],
                        spec["line_start"],
                        spec["line_end"],
                    ),
                )

    def test_title_label_and_the_paragraph_the_scorer_reads(self) -> None:
        for slug, spec in FIXED_ITEMS.items():
            with self.subTest(slug=slug):
                title, page = fixed_page(slug)
                self.assertEqual(title, spec["title"])
                self.assertEqual(_title(page), spec["title"])
                body = page.split("\n---\n", 1)[1]
                self.assertNotIn(item_label(fixed_item(slug)), body)
                self.assertEqual(_first_paragraph(page), spec["paragraph"])

    def test_no_fixed_item_quotes_closing_keyword_text(self) -> None:
        for slug, spec in FIXED_ITEMS.items():
            with self.subTest(slug=slug):
                self.assertIsNone(CLOSING_KEYWORD_RE.search(spec["raw"]))

    def test_the_readme_names_each_fixed_item_by_spec_path_and_line_span(self) -> None:
        readme = (DUPLICATES_DIR / "README.md").read_text(encoding="utf-8")
        for slug, spec in FIXED_ITEMS.items():
            with self.subTest(slug=slug):
                self.assertIn(f"`{spec['spec_path']}` lines {spec['line_start']}-{spec['line_end']}", readme)
                self.assertIn(f"`{slug}`", readme)


class FamiliesTest(unittest.TestCase):
    """FR-003: the prefix rule, the exclusions under every option, the extension order and cut 1."""

    CCT_NAMES = (
        "routing",
        "routing-a",
        "routingx",
        "pi-a",
        "pin-litellm",
        "session-analytics",
        "session-analytics-x",
        "benchmark-harness",
        "auto-build-loop",
        "init-permission-profiles",
        "redaction-canaries",
        "api-host",
        "llm-catalog",
        "wiki-studio-adoption",
        "wiki-audit-trail",
        "wiki-audit-flush",
        "memkernel-integration",
        "one-harness-home",
        "plugin-generate-from-sources",
        "simplest-complete-change",
    )
    MK_NAMES = (
        "copilot-memory-mvp",
        "memkernel-0-3",
        "memkernel-0-4",
        "memkernel-0-7",
        "memkernel-0-10-decision-revalidation",
        "memkernel-0-11-anti-rot-injection",
    )
    EXCLUDED = {
        "session-analytics",
        "session-analytics-x",
        "benchmark-harness",
        "auto-build-loop",
        "init-permission-profiles",
        "redaction-canaries",
        "memkernel-0-10-decision-revalidation",
        "memkernel-0-11-anti-rot-injection",
    }

    def test_the_base_families(self) -> None:
        self.assertEqual(
            family_directories(CODE_COPILOT_TEAM, self.CCT_NAMES, 0, False),
            [("routing", ["routing", "routing-a"]), ("pi", ["pi-a"])],
        )
        self.assertEqual(
            family_directories(MEMKERNEL, self.MK_NAMES, 0, False),
            [("memkernel", ["copilot-memory-mvp", "memkernel-0-3", "memkernel-0-4", "memkernel-0-7"])],
        )

    def test_the_extension_order(self) -> None:
        families = family_directories(CODE_COPILOT_TEAM, self.CCT_NAMES, len(EXTENSION_ORDER), False)
        self.assertEqual([family for family, _names in families], ["routing", "pi", *EXTENSION_ORDER])
        self.assertEqual(dict(families)["wiki-audit"], ["wiki-audit-flush", "wiki-audit-trail"])
        self.assertEqual(dict(families)["api"], ["api-host"])
        two = family_directories(CODE_COPILOT_TEAM, self.CCT_NAMES, 2, False)
        self.assertEqual([family for family, _names in two], ["routing", "pi", "api", "llm-catalog"])

    def test_cut_1(self) -> None:
        cct = family_directories(CODE_COPILOT_TEAM, self.CCT_NAMES, 1, True)
        self.assertEqual([family for family, _names in cct], ["routing", "api"])
        self.assertEqual(family_directories(MEMKERNEL, self.MK_NAMES, 0, True), [("memkernel", ["memkernel-0-7"])])

    def test_an_excluded_spec_is_never_listed_by_any_option(self) -> None:
        for extend in range(len(EXTENSION_ORDER) + 1):
            for cut_1 in (False, True):
                for repository, names in ((CODE_COPILOT_TEAM, self.CCT_NAMES), (MEMKERNEL, self.MK_NAMES)):
                    listed = {
                        name
                        for _family, group in family_directories(repository, names, extend, cut_1)
                        for name in group
                    }
                    self.assertFalse(listed & self.EXCLUDED, (extend, cut_1, repository))

    def test_an_excluded_spec_with_a_decision_section_gives_no_page(self) -> None:
        decisions = "## Decisions\n\n- **D1 One.** text\n"
        snapshot = memory_snapshot(
            MEMKERNEL,
            {
                "specs/memkernel-0-7/spec.md": decisions,
                "specs/memkernel-0-10-decision-revalidation/spec.md": decisions,
                "specs/memkernel-0-5/spec.md": "## Requirements\n\n- **R1** none\n",
            },
        )
        corpus = extract_corpus([snapshot])
        self.assertEqual(corpus.entries[0]["spec_path"], "specs/memkernel-0-7/spec.md")
        self.assertEqual(len(corpus.entries), 1)
        self.assertEqual(
            corpus.families,
            [
                {
                    "repository": MEMKERNEL,
                    "family": "memkernel",
                    "directories": ["memkernel-0-5", "memkernel-0-7"],
                    "with_decision_sections": ["memkernel-0-7"],
                }
            ],
        )


class LeftOutTest(unittest.TestCase):
    """FR-007: an item with closing-keyword text is no page and is listed by id only."""

    def test_the_item_is_listed_by_id_and_its_text_is_copied_nowhere(self) -> None:
        plan = "\n".join(
            ["# Plan", "## Decisions", "", f"- **D1 Keyword.** This {CLOSING_TEXT} on merge.", "- **D2 Kept.** text"]
        )
        snapshot = memory_snapshot(CODE_COPILOT_TEAM, {"specs/routing-a/plan.md": plan})
        corpus = extract_corpus([snapshot])
        self.assertEqual(
            corpus.left_out,
            [
                {
                    "repository": CODE_COPILOT_TEAM,
                    "spec_path": "specs/routing-a/plan.md",
                    "line_start": 4,
                    "line_end": 4,
                    "slug": "cct-routing-a-plan-01",
                    "reason": "closing-keyword text",
                }
            ],
        )
        self.assertEqual(
            [entry["page"] for entry in corpus.entries], ["code-copilot-team/routing/cct-routing-a-plan-02.md"]
        )
        document = extract.corpus_document(corpus, [snapshot], extend=0, cut_1=False)
        written = json.dumps(document) + "".join(data.decode("utf-8") for data in corpus.pages.values())
        self.assertNotIn(CLOSING_TEXT, written)
        self.assertNotIn("Keyword", written)

    def test_the_pattern_matches_the_closing_forms_only(self) -> None:
        verbs = ["clo" + "ses", "Clo" + "sed", "fix" + "ed", "re" + "solves:"]
        for verb in verbs:
            with self.subTest(verb=verb):
                self.assertIsNotNone(CLOSING_KEYWORD_RE.search(f"this {verb} #7"))
                self.assertIsNotNone(CLOSING_KEYWORD_RE.search(f"this {verb} owner/repo#7"))
        for text in ("issue 121", "review of #127", "closing #7", "the fix for #7", "fixes issue 7"):
            with self.subTest(text=text):
                self.assertIsNone(CLOSING_KEYWORD_RE.search(text))


def git_setup(cwd: Path, *argv: str) -> str:
    """A setup git call with the reading layer's clean environment and a fixed date."""
    env = {**extract.git_environment(cwd), "GIT_AUTHOR_DATE": SETUP_DATE, "GIT_COMMITTER_DATE": SETUP_DATE}
    result = subprocess.run(
        [
            GIT or "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.com",
            "-c",
            "commit.gpgsign=false",
            "-c",
            f"core.hooksPath={os.devnull}",
            *argv,
        ],
        cwd=cwd,
        env=env,
        capture_output=True,
        check=True,
    )
    return result.stdout.decode().strip()


def commit_files(repo: Path, files: dict[str, str], message: str) -> str:
    for rel, text in files.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    git_setup(repo, "add", "-A")
    git_setup(repo, "commit", "-q", "-m", message)
    return git_setup(repo, "rev-parse", "HEAD")


def make_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    git_setup(path, "init", "-q")
    return path


@unittest.skipUnless(GIT, "git is not installed")
class GitReadingTest(unittest.TestCase):
    """FR-002: reading at the pin, never the work tree; inherited GIT_ variables dropped; nothing written."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.cct = make_repo(self.tmp / "code-copilot-team")
        self.first = commit_files(
            self.cct,
            {
                "specs/routing-a/plan.md": "## Decisions\n\n- **D1 First.** at the pin\n",
                "specs/pi-b/spec.md": "## Decisions\n\n### ADR-1: Split\n**Decision**: split it.\n",
                "specs/session-analytics-x/plan.md": "## Decisions\n\n- **D1 Never.** excluded\n",
                "specs/api-z/plan.md": "## Decisions to confirm\n\n- **D1 Api.** extension\n",
                "specs/routing-c/plan.md": "## Files\n\n- **F1** no decision section\n",
            },
            "first",
        )
        self.second = commit_files(self.cct, {"specs/routing-a/plan.md": "## Decisions\n\n- **D1 Later.** x\n"}, "2")
        (self.cct / "specs/routing-a/plan.md").write_text("## Decisions\n\n- **D1 Work tree.** y\n", encoding="utf-8")
        self.mk = make_repo(self.tmp / "memkernel")
        self.mk_pin = commit_files(
            self.mk,
            {
                "specs/memkernel-0-3/plan.md": "## Architecture Decisions\n\n### ADR-1: Two\n**Decision**: two.\n",
                "specs/memkernel-0-7/spec.md": "## Decisions\n\n**G1. One setting.** one\n",
                "specs/memkernel-0-11-anti-rot-injection/spec.md": "## Decisions\n\n- **D1 No.** excluded\n",
            },
            "mk",
        )
        self.pins = {CODE_COPILOT_TEAM: self.first, MEMKERNEL: self.mk_pin}
        self.out = self.tmp / "out"

    def run_main(self, *extra: str, pins: dict[str, str] | None = None) -> int:
        argv = ["--code-copilot-team", str(self.cct), "--memkernel", str(self.mk), "--out", str(self.out), *extra]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return extract.main(argv, pins=self.pins if pins is None else pins)

    def test_show_reads_the_pin_not_the_work_tree(self) -> None:
        snapshot = extract.read_snapshot(CODE_COPILOT_TEAM, self.cct, self.first)
        self.assertEqual(snapshot.read("specs/routing-a/plan.md"), "## Decisions\n\n- **D1 First.** at the pin\n")
        self.assertEqual(snapshot.commit_date, SETUP_DATE[:10])
        self.assertIn("specs/pi-b/spec.md", snapshot.paths)

    def test_an_injected_git_dir_changes_nothing(self) -> None:
        other = make_repo(self.tmp / "other")
        commit_files(other, {"specs/routing-a/plan.md": "## Decisions\n\n- **D1 Other.** z\n"}, "other")
        injected = {
            "GIT_DIR": str(other / ".git"),
            "GIT_WORK_TREE": str(other),
            "GIT_INDEX_FILE": str(other / ".git" / "index"),
            "GIT_OBJECT_DIRECTORY": str(other / ".git" / "objects"),
            "GIT_COMMON_DIR": str(other / ".git"),
        }
        with mock.patch.dict(os.environ, injected):
            snapshot = extract.read_snapshot(CODE_COPILOT_TEAM, self.cct, self.first)
            text = snapshot.read("specs/routing-a/plan.md")
            env = extract.git_environment(self.cct)
        self.assertEqual(text, "## Decisions\n\n- **D1 First.** at the pin\n")
        self.assertFalse(
            {name for name in env if name.startswith("GIT_")}
            - {"GIT_TERMINAL_PROMPT", "GIT_CEILING_DIRECTORIES", *extract.GIT_ENV_KEPT}
        )

    def test_the_calls_are_argument_lists_with_the_prefix_and_no_shell(self) -> None:
        calls: list[tuple[list[str], dict[str, Any]]] = []
        real_run = subprocess.run

        def spy(argv: list[str], **kwargs: Any) -> Any:
            calls.append((argv, kwargs))
            return real_run(argv, **kwargs)

        with mock.patch.object(extract.subprocess, "run", spy):
            snapshot = extract.read_snapshot(CODE_COPILOT_TEAM, self.cct, self.first)
            snapshot.read("specs/routing-a/plan.md")
        self.assertEqual(
            [argv[argv.index("-C") + 2] for argv, _kwargs in calls], ["rev-parse", "log", "ls-tree", "show"]
        )
        for argv, kwargs in calls:
            self.assertEqual(argv[: len(extract.GIT_PREFIX) + 1], ["git", *extract.GIT_PREFIX])
            self.assertIn("protocol.allow=never", argv)
            self.assertNotIn("shell", kwargs)

    def test_nothing_is_written_into_either_repository(self) -> None:
        before = (tree_digest(self.cct), tree_digest(self.mk))
        self.assertEqual(self.run_main(), 0)
        self.assertEqual((tree_digest(self.cct), tree_digest(self.mk)), before)

    def test_the_run_writes_only_the_corpus_under_out(self) -> None:
        self.assertEqual(self.run_main(), 0)
        document = json.loads((self.out / "corpus.json").read_text(encoding="utf-8"))
        pages = [entry["page"] for entry in document["pages"]]
        self.assertEqual(
            pages,
            [
                "code-copilot-team/pi/cct-pi-b-spec-01.md",
                "code-copilot-team/routing/cct-routing-a-plan-01.md",
                "memkernel/memkernel/mk-memkernel-0-3-plan-01.md",
                "memkernel/memkernel/mk-memkernel-0-7-spec-01.md",
            ],
        )
        written = sorted(path.relative_to(self.out).as_posix() for path in self.out.rglob("*") if path.is_file())
        self.assertEqual(written, sorted(["corpus.json", *(f"corpus/{page}" for page in pages)]))
        for entry in document["pages"]:
            data = (self.out / "corpus" / entry["page"]).read_bytes()
            self.assertEqual(entry["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(
            document["repositories"],
            [
                {"name": CODE_COPILOT_TEAM, "pin": self.first, "commit_date": SETUP_DATE[:10]},
                {"name": MEMKERNEL, "pin": self.mk_pin, "commit_date": SETUP_DATE[:10]},
            ],
        )
        self.assertEqual(document["options"], {"extend": 0, "cut_1": False})
        self.assertEqual(document["left_out"], [])
        routing = next(row for row in document["families"] if row["family"] == "routing")
        self.assertEqual(routing["directories"], ["routing-a", "routing-c"])
        self.assertEqual(routing["with_decision_sections"], ["routing-a"])
        page = (self.out / "corpus" / pages[1]).read_text(encoding="utf-8")
        self.assertIn("at the pin", page)

    def test_extend_and_cut_1_change_the_families(self) -> None:
        self.assertEqual(self.run_main("--extend", "1", "--cut-1"), 0)
        document = json.loads((self.out / "corpus.json").read_text(encoding="utf-8"))
        self.assertEqual([row["family"] for row in document["families"]], ["routing", "api", "memkernel"])
        self.assertEqual(
            [entry["page"] for entry in document["pages"]],
            [
                "code-copilot-team/api/cct-api-z-plan-01.md",
                "code-copilot-team/routing/cct-routing-a-plan-01.md",
                "memkernel/memkernel/mk-memkernel-0-7-spec-01.md",
            ],
        )
        self.assertEqual(document["options"], {"extend": 1, "cut_1": True})

    def test_a_pin_that_does_not_resolve_writes_nothing(self) -> None:
        self.assertEqual(self.run_main(pins=dict(PINS)), extract.PIN_UNRESOLVED)
        self.assertFalse(self.out.exists())

    def test_a_stale_file_under_corpus_writes_nothing(self) -> None:
        stale = self.out / "corpus" / "code-copilot-team" / "routing" / "old.md"
        stale.parent.mkdir(parents=True)
        stale.write_text("old\n", encoding="utf-8")
        self.assertEqual(self.run_main(), extract.STALE_CORPUS)
        self.assertEqual(sorted(path.name for path in self.out.rglob("*") if path.is_file()), ["old.md"])

    def test_a_rerun_rewrites_the_same_bytes(self) -> None:
        self.assertEqual(self.run_main(), 0)
        first = tree_digest(self.out)
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(tree_digest(self.out), first)


class SampleTest(unittest.TestCase):
    """FR-008: the population, the largest-remainder split, the seeded draw."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        sizes = {"routing": 8, "pi": 3, "memkernel": 9, "api": 6}
        self.pages = {
            family: [f"x/{family}/{family}-{n:02d}.md" for n in range(size)] for family, size in sizes.items()
        }
        entries = [{"page": page, "family": family} for family, pages in self.pages.items() for page in pages]
        routing = self.pages["routing"]
        self.true_pairs = {
            (routing[0], routing[1]),
            (routing[2], routing[3]),
            (self.pages["pi"][0], self.pages["pi"][1]),
        }
        rows = [
            {"pair": list(pair), "group": "g1", "disposition": "redundant", "reason": "r"}
            for pair in sorted(self.true_pairs)
        ]
        rows.append({"pair": [routing[4], routing[5]], "group": "g2", "disposition": "companion", "reason": "r"})
        rows.append(
            {
                "pair": [self.pages["memkernel"][0], self.pages["memkernel"][1]],
                "group": "g3",
                "disposition": "supersedes",
                "reason": "r",
            }
        )
        self.true_pairs.add((self.pages["memkernel"][0], self.pages["memkernel"][1]))
        (self.tmp / "corpus.json").write_text(json.dumps({"pages": entries}), encoding="utf-8")
        (self.tmp / "labels.json").write_text(json.dumps({"pairs": rows}), encoding="utf-8")

    def run_sample(self, out: Path) -> dict[str, Any]:
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sample.main(["--out", str(out)], duplicates_dir=self.tmp), 0)
        loaded: dict[str, Any] = json.loads(out.read_text(encoding="utf-8"))
        return loaded

    def test_the_largest_remainder_split(self) -> None:
        self.assertEqual(
            sample.largest_remainder({"routing": 3486, "pi": 406, "memkernel": 5151}),
            {
                "routing": 8,
                "pi": 1,
                "memkernel": 11,
            },
        )
        self.assertEqual(
            sample.largest_remainder({"routing": 3486, "memkernel": 3828}), {"routing": 10, "memkernel": 10}
        )
        self.assertEqual(
            sample.largest_remainder({"routing": 1, "pi": 1, "memkernel": 1}),
            {
                "routing": 7,
                "pi": 7,
                "memkernel": 6,
            },
        )

    def test_only_false_within_family_base_pairs_are_drawn(self) -> None:
        document = self.run_sample(self.tmp / "review-sample.json")
        self.assertEqual(document["seed"], 121)
        self.assertEqual(document["split"], {"routing": 8, "pi": 1, "memkernel": 11})
        self.assertEqual(len(document["pairs"]), 20)
        family_of = {page: family for family, pages in self.pages.items() for page in pages}
        for row in document["pairs"]:
            left, right = row["pair"]
            self.assertEqual(family_of[left], row["family"])
            self.assertEqual(family_of[right], row["family"])
            self.assertIn(row["family"], ("routing", "pi", "memkernel"))
            self.assertNotIn((left, right), self.true_pairs)
            self.assertIn(row["label"], ("companion", "unrelated"))
        self.assertEqual(len({tuple(row["pair"]) for row in document["pairs"]}), 20)
        labels_hash = hashlib.sha256((self.tmp / "labels.json").read_bytes()).hexdigest()
        self.assertEqual(document["labels_sha256"], labels_hash)

    def test_the_draw_is_the_seeded_sample_and_repeats(self) -> None:
        first = self.run_sample(self.tmp / "one.json")
        second = self.run_sample(self.tmp / "two.json")
        self.assertEqual((self.tmp / "one.json").read_bytes(), (self.tmp / "two.json").read_bytes())
        self.assertEqual(first, second)
        routing = sorted(pair for pair in combinations(self.pages["routing"], 2) if pair not in self.true_pairs)
        expected = [list(pair) for pair in random.Random(121).sample(routing, 8)]
        self.assertEqual([row["pair"] for row in first["pairs"] if row["family"] == "routing"], expected)

    def test_too_few_false_pairs_writes_nothing(self) -> None:
        (self.tmp / "corpus.json").write_text(
            json.dumps({"pages": [{"page": "a.md", "family": "pi"}, {"page": "b.md", "family": "pi"}]}),
            encoding="utf-8",
        )
        out = self.tmp / "none.json"
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(sample.main(["--out", str(out)], duplicates_dir=self.tmp), sample.SAMPLE_FAILED)
        self.assertFalse(out.exists())


class CommandTest(unittest.TestCase):
    """``--help`` for both scripts; the closing-keyword scan of ``eval/duplicates/`` (FR-007, FR-009)."""

    def test_help_exits_zero(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(extract.main(["--help"]), 0)
            self.assertEqual(sample.main(["--help"]), 0)

    def test_every_readme_command_parses_with_its_script(self) -> None:
        parsers = {
            "eval.duplicates.extract": extract._build_arg_parser(),
            "eval.duplicates.sample": sample._build_arg_parser(),
        }
        seen = 0
        for line in (DUPLICATES_DIR / "README.md").read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if text.startswith("python -m eval.duplicates."):
                argv = shlex.split(text)
                self.assertIn(argv[2], parsers, text)
                parsers[argv[2]].parse_args(argv[3:])
                seen += 1
        self.assertGreater(seen, 0)

    def test_an_out_of_range_extend_is_refused(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(extract.main(["--extend", str(len(EXTENSION_ORDER) + 1)]), 2)

    def test_no_file_under_eval_duplicates_holds_closing_keyword_text(self) -> None:
        files = [path for path in DUPLICATES_DIR.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
        self.assertTrue(files)
        for path in files:
            with self.subTest(path=path.relative_to(REPO_ROOT).as_posix()):
                text = path.read_bytes().decode("utf-8", errors="replace")
                self.assertIsNone(CLOSING_KEYWORD_RE.search(text))


if __name__ == "__main__":
    unittest.main()
