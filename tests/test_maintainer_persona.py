# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The packaged curator persona, checked as users receive it (0.9.2, FR-013..FR-018).

The persona is read through ``importlib.resources``: the bytes the wheel
ships. Every inline code span and every fenced-block line is a candidate
command; the CLI's own parser and the MCP server's launch parser decide
whether it parses, and every flag must be spelled in full because argparse
accepts unambiguous prefixes. The approval rule is found by its markers and
their positions, not by its sentences. No network, no memkernel: the one
memkernel line is a pinned copy (FR-018).
"""

from __future__ import annotations

import argparse
import contextlib
import io
import re
import shlex
import unittest
from importlib import resources
from pathlib import Path

from wiki_studio.cli import _build_arg_parser
from wiki_studio.mcp_adapter.config import TOOL_NAMES, build_parser

PERSONA = resources.files("wiki_studio").joinpath("schema", "WIKI_MAINTAINER.md").read_text(encoding="utf-8")
REPO_ROOT = Path(__file__).resolve().parents[1]

# FR-004's copyable line, quoted verbatim in the persona's "Who approves" step.
RESERVATION_LINE = "A person approves wiki pages here; do not run `wiki-studio approve`."

# FR-030: the label that finds the persona's paragraph on a model-drafted proposal.
NIGHTLY_LABEL = "**Proposals named `nightly-*`.**"

# Copied from gosha70/memkernel templates/claude-memory-instructions.md at tag v0.8.0,
# line 46 (citation verified 2026-11-15, see the spec FR-018). Test fixture only;
# it changes only by a deliberate re-pin to a newer memkernel tag.
MEMKERNEL_WORKFLOW = (
    "wiki_export()  → review the draft pages → (with wiki-studio) wiki-studio approve <page> → wiki_import()"
)
MEMKERNEL_MARKERS = ("wiki_export", "wiki-studio approve", "wiki_import")
MEMKERNEL_TEMPLATE_URL = "https://github.com/gosha70/memkernel/blob/v0.8.0/templates/claude-memory-instructions.md"
COMPATIBILITY_URL = "https://github.com/gosha70/wiki-studio/blob/main/docs/compatibility.md"

# FR-012: the memory call syntax and memory steps the persona must never restate.
FORBIDDEN_TOKENS = (
    "retain(",
    "recall(",
    "consolidate(",
    "checkpoint=",
    "promote(ref_id",
    "wiki_export(",
    "wiki_import(",
)

PLACEHOLDER = "PLACEHOLDER"
PLACEHOLDER_RE = re.compile(r"<[^<>\n]+>")
INLINE_SPAN_RE = re.compile(r"`([^`\n]+)`")
MEMORY_WORD_RE = re.compile(r"\b(retain|recall|consolidate|wiki_export|wiki_import)\b")
LOOP_HEADING = "## The canonical curator loop"
STEP_BOUNDARY_RE = re.compile(r"^(?:\d+\. \*\*|## )", re.MULTILINE)

# FR-014e: shapes the checker must reject -- a wrong verb, a wrong flag, an
# abbreviated flag, a missing required flag and an unknown tool.
REJECTED_SPANS = (
    "wiki-studio aprove <page>",
    "wiki-studio approve <page> --approver x",
    "wiki-studio approve <page> --b x",
    "wiki-studio approve <page> --rev <sha256> --by x",
    "wiki-studio propose --by x",
    "--disable-tool approve",
)
ACCEPTED_SPANS = (
    "wiki-studio approve <page> --revision <sha256> --by <agent-name>",
    "wiki-studio read <page> --json",
    "wiki-studio info --json",
)


def persona_candidates(text: str) -> list[tuple[int, str]]:
    """(offset, text) for every inline code span and every non-blank fenced-block line."""
    found: list[tuple[int, str]] = []
    in_fence = False
    offset = 0
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\n")
        if body.lstrip().startswith("```"):
            in_fence = not in_fence
        elif in_fence:
            if body.strip():
                found.append((offset + len(body) - len(body.lstrip()), body.strip()))
        else:
            for match in INLINE_SPAN_RE.finditer(body):
                found.append((offset + match.start(1), match.group(1)))
        offset += len(line)
    return found


def split_span(span: str) -> list[str]:
    """The span with each ``<...>`` placeholder replaced by one token, split like a shell line."""
    return shlex.split(PLACEHOLDER_RE.sub(PLACEHOLDER, span))


def flag_value(tokens: list[str], flag: str) -> str | None:
    """The value that follows ``flag`` (or after ``flag=``), or None when the flag has no value."""
    for index, token in enumerate(tokens):
        if token == flag:
            if index + 1 < len(tokens) and not tokens[index + 1].startswith("-"):
                return tokens[index + 1]
            return None
        if token.startswith(flag + "="):
            return token[len(flag) + 1 :] or None
    return None


def _subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    """The verb choices of ``_build_arg_parser()`` (FR-014a), an ``argparse._SubParsersAction``."""
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    raise AssertionError("wiki_studio.cli._build_arg_parser() has no subparsers action")


def _parse(parser: argparse.ArgumentParser, argv: list[str]) -> tuple[argparse.Namespace | None, str]:
    """The parsed namespace, or None and the stderr argparse printed before its ``SystemExit``."""
    stderr = io.StringIO()
    try:
        with contextlib.redirect_stderr(stderr):
            args = parser.parse_args(argv)
    except SystemExit:
        return None, stderr.getvalue().strip() or "the parser exited without a message"
    return args, stderr.getvalue().strip()


def _wiki_studio_failure(span: str, tokens: list[str]) -> str | None:
    """The failure of a ``wiki-studio ...`` span, or None when it is a real verb or a command that parses."""
    parser = _build_arg_parser()
    subparsers = _subparsers(parser)
    if len(tokens) == 1:
        return None
    verb = tokens[1]
    if len(tokens) == 2:
        if verb not in subparsers.choices:
            return f"{span!r}: {verb!r} is not a verb of wiki-studio's CLI"
        return None
    parsed, message = _parse(parser, tokens[1:])
    if parsed is None:
        return f"{span!r} does not parse with the CLI's own parser: {message}"
    verb = parsed.verb
    allowed = set(subparsers.choices[verb]._option_string_actions) | set(parser._option_string_actions)
    for token in tokens[1:]:
        flag = token.split("=", 1)[0]
        if flag.startswith("--") and flag not in allowed:
            return f"{span!r}: {flag} is not an option of {verb} or the top-level parser, spelled in full"
    return None


def _disable_tool_values(tokens: list[str]) -> list[str]:
    """Every value given to ``--disable-tool``, in either spelling."""
    values: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "--disable-tool":
            if index + 1 < len(tokens):
                values.append(tokens[index + 1])
            index += 2
            continue
        if token.startswith("--disable-tool="):
            values.append(token.split("=", 1)[1])
        index += 1
    return values


def _mcp_failure(span: str, tokens: list[str]) -> str | None:
    """The failure of a ``wiki-studio-mcp ...`` or ``--disable-tool ...`` span, or None when it launches."""
    parser = build_parser()
    argv = tokens[1:] if tokens[0] == "wiki-studio-mcp" else tokens
    parsed, message = _parse(parser, argv)
    if parsed is None:
        return f"{span!r} does not parse with wiki-studio-mcp's launch parser: {message}"
    for token in argv:
        flag = token.split("=", 1)[0]
        if flag.startswith("--") and flag not in parser._option_string_actions:
            return f"{span!r}: {flag} is not an option of wiki-studio-mcp, spelled in full"
    for name in _disable_tool_values(argv):
        if name not in TOOL_NAMES:
            return f"{span!r}: --disable-tool {name!r} is not a tool; tools are {', '.join(TOOL_NAMES)}"
    return None


def command_failure(span: str) -> str | None:
    """None when ``span`` is no command, or a command both parsers accept as written; else why it fails."""
    try:
        tokens = split_span(span)
    except ValueError as exc:
        return f"{span!r} does not split like a shell line: {exc}"
    if not tokens:
        return None
    if tokens[0] == "wiki-studio":
        return _wiki_studio_failure(span, tokens)
    if tokens[0] == "wiki-studio-mcp" or tokens[0].startswith("--disable-tool"):
        return _mcp_failure(span, tokens)
    return None


def parsed_commands(text: str = PERSONA) -> list[tuple[int, list[str]]]:
    """(offset, tokens) for every full ``wiki-studio <verb> ...`` command both parsers accept."""
    commands: list[tuple[int, list[str]]] = []
    for offset, raw in persona_candidates(text):
        if command_failure(raw) is not None:
            continue
        try:
            tokens = split_span(raw)
        except ValueError:
            continue
        if len(tokens) > 2 and tokens[0] == "wiki-studio":
            commands.append((offset, tokens))
    return commands


def first_command(text: str, verb: str, flag: str | None = None) -> tuple[int, list[str]] | None:
    """The first accepted ``wiki-studio <verb>`` command in ``text``, optionally carrying ``flag``."""
    for offset, tokens in parsed_commands(text):
        if tokens[1] == verb and (flag is None or flag in tokens):
            return offset, tokens
    return None


def first_promote(text: str) -> tuple[int, list[str]] | None:
    """P (FR-016): the first ``promote`` command, or ``propose`` command carrying ``--promote``."""
    for offset, tokens in parsed_commands(text):
        if tokens[1] == "promote" or (tokens[1] == "propose" and "--promote" in tokens):
            return offset, tokens
    return None


def loop_text(text: str = PERSONA) -> str:
    """The text of "The canonical curator loop", up to the next ``## `` heading."""
    start = text.index(LOOP_HEADING)
    end = text.find("\n## ", start + len(LOOP_HEADING))
    return text[start:] if end < 0 else text[start:end]


def loop_step(label: str) -> str:
    """The loop item starting with ``label`` (``**Who approves.**``), up to the next step or heading."""
    loop = loop_text()
    match = re.search(rf"^\d+\. {re.escape(label)}", loop, re.MULTILINE)
    if match is None:
        raise AssertionError(f"the loop has no step labelled {label}")
    boundary = STEP_BOUNDARY_RE.search(loop, match.start() + 1)
    end = boundary.start() if boundary is not None else len(loop)
    return loop[match.start() : end]


def section_text(heading: str) -> str:
    """The persona from ``heading`` to the next ``## `` heading."""
    start = PERSONA.index(heading)
    end = PERSONA.find("\n## ", start + len(heading))
    return PERSONA[start:] if end < 0 else PERSONA[start:end]


def marker_order(text: str) -> list[str]:
    """``MEMKERNEL_MARKERS`` in the order ``text`` first mentions them, omitting absent ones."""
    found = [(text.find(marker), marker) for marker in MEMKERNEL_MARKERS]
    return [marker for position, marker in sorted(found) if position >= 0]


class TestEveryShownCommandParses(unittest.TestCase):
    def test_every_inline_span_and_fenced_line_is_accepted(self) -> None:
        failures: list[str] = []
        for _, candidate in persona_candidates(PERSONA):
            failure = command_failure(candidate)
            if failure is not None:
                failures.append(failure)
        self.assertEqual(failures, [], "\n".join(failures))

    def test_the_persona_shows_the_commands_the_loop_relies_on(self) -> None:
        commands = parsed_commands()
        self.assertTrue(commands, "the persona shows no wiki-studio command")
        for verb in ("propose", "promote", "approve"):
            self.assertTrue(any(tokens[1] == verb for _, tokens in commands), f"no {verb} command")
        for verb in ("read", "info"):
            self.assertTrue(
                any(tokens[1] == verb and "--json" in tokens for _, tokens in commands),
                f"no `{verb} --json` command",
            )

    def test_the_persona_names_no_bash_linter(self) -> None:
        self.assertNotIn("lint-wiki", PERSONA)


class TestTheCheckerBites(unittest.TestCase):
    def test_the_required_commands_pass(self) -> None:
        for span in ACCEPTED_SPANS:
            with self.subTest(span=span):
                self.assertIsNone(command_failure(span))

    def test_each_wrong_shape_fails_naming_the_span(self) -> None:
        for span in REJECTED_SPANS:
            with self.subTest(span=span):
                failure = command_failure(span)
                self.assertIsNotNone(failure, f"{span!r} passed the checker")
                assert failure is not None
                self.assertIn(span, failure)

    def test_a_system_exit_reports_argparses_message(self) -> None:
        failure = command_failure("wiki-studio aprove <page>")
        assert failure is not None
        self.assertIn("invalid choice", failure)
        failure = command_failure("wiki-studio propose --by x")
        assert failure is not None
        self.assertIn("required", failure)


class TestOneAgentNameOnEveryRecord(unittest.TestCase):
    def test_propose_promote_and_approve_carry_by_and_approve_carries_revision(self) -> None:
        writing = [
            (offset, tokens) for offset, tokens in parsed_commands() if tokens[1] in ("propose", "promote", "approve")
        ]
        self.assertTrue(writing, "the persona shows no propose, promote or approve command")
        for _, tokens in writing:
            with self.subTest(command=" ".join(tokens)):
                self.assertIsNotNone(flag_value(tokens, "--by"), f"--by is missing from {tokens}")
                if tokens[1] == "approve":
                    self.assertIsNotNone(flag_value(tokens, "--revision"), f"--revision is missing from {tokens}")


class TestTheApprovalRuleComesFirst(unittest.TestCase):
    def test_who_approves_states_the_rule_before_any_promote_or_approve(self) -> None:
        loop = loop_text()
        step = loop_step("**Who approves.**")
        promote = first_promote(loop)
        approve = first_command(loop, "approve")
        self.assertIsNotNone(promote, "the loop shows no promote command")
        self.assertIsNotNone(approve, "the loop shows no approve command")
        assert promote is not None and approve is not None
        for marker in (
            "project's instructions",
            "`--disable-tool promote`",
            RESERVATION_LINE,
            "auto_approve_on_promote",
            "stop after propose",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, step)
                self.assertLess(loop.index(marker), promote[0])
                self.assertLess(loop.index(marker), approve[0])
        info = first_command(loop, "info", "--json")
        self.assertIsNotNone(info, "the loop shows no `wiki-studio info --json` command")
        self.assertIsNotNone(
            first_command(step, "info", "--json"), "the Who approves step shows no `wiki-studio info --json`"
        )
        assert info is not None
        self.assertLess(info[0], promote[0])
        self.assertLess(info[0], approve[0])

    def test_approve_reads_and_names_each_changed_page_before_it_approves(self) -> None:
        step = loop_step("**Approve.**")
        approve = first_command(step, "approve")
        self.assertIsNotNone(approve, "the Approve step shows no approve command")
        assert approve is not None
        self.assertIsNotNone(flag_value(approve[1], "--revision"), f"--revision is missing from {approve[1]}")
        self.assertIsNotNone(flag_value(approve[1], "--by"), f"--by is missing from {approve[1]}")
        self.assertIn("each changed content page", step)
        self.assertLess(step.index("each changed content page"), approve[0])
        read = first_command(step, "read", "--json")
        self.assertIsNotNone(read, "the Approve step shows no `wiki-studio read --json` command")
        assert read is not None
        self.assertLess(read[0], approve[0])

    def test_the_cli_comes_before_the_no_shell_fallback(self) -> None:
        step = loop_step("**Approve.**")
        bullet = step[step.index("- **Through MCP.**") :]
        approve = first_command(bullet, "approve")
        self.assertIsNotNone(approve, "the MCP sub-bullet shows no approve command")
        assert approve is not None
        self.assertIn("without a shell", bullet)
        self.assertLess(approve[0], bullet.index("without a shell"))


class TestTheApprovalSafeguards(unittest.TestCase):
    """FR-003 (d), (f) and outcome (4), amended after the #103 review."""

    def test_draft_and_superseded_pages_are_skipped_not_forced(self) -> None:
        step = loop_step("**Approve.**")
        approve = first_command(step, "approve")
        assert approve is not None
        skip = step.index("Skip a changed page")
        for marker in ("`status: draft`", "`superseded_by`", "report it", "never edit a page's"):
            with self.subTest(marker=marker):
                self.assertIn(marker, step[skip:])
        self.assertLess(skip, approve[0])

    def test_a_changed_revision_is_reported_never_approved(self) -> None:
        step = loop_step("**Approve.**")
        bullet = step[step.index("If `approve` refuses because the live page differs") :]
        bullet = bullet[: bullet.index("\n    - ")]
        self.assertIn("Do not\n      approve it: report the page and stop.", bullet)
        self.assertNotIn("Approve the", bullet)
        self.assertNotIn("still what you drafted", bullet)

    def test_auto_approval_is_checked_against_every_eligible_page(self) -> None:
        step = loop_step("**Who approves.**")
        outcome = step[step.index("4. Approval is not reserved and the policy approves on promote") :]
        outcome = outcome[: outcome.index("\n   5. ")]
        for marker in (
            "`approved <wiki-label>/<path>`",
            "`approved_paths`",
            "every eligible page",
            "report each missing page",
            "and stop",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, outcome)
        self.assertLess(outcome.index("every eligible page"), outcome.index("skip step 13"))
        self.assertLess(outcome.index("report each missing page"), outcome.index("skip step 13"))


class TestTheReservationLineInTheDocs(unittest.TestCase):
    """FR-021: README and docs/mcp-adapter.md quote R verbatim, as the persona does."""

    def test_the_reservation_line_appears_verbatim_in_both_pages(self) -> None:
        for page in (REPO_ROOT / "README.md", REPO_ROOT / "docs" / "mcp-adapter.md"):
            with self.subTest(page=str(page.relative_to(REPO_ROOT))):
                self.assertIn(RESERVATION_LINE, page.read_text(encoding="utf-8"))


class TestNightlyProposals(unittest.TestCase):
    """FR-030: a ``nightly-*`` proposal is the agent's to review, a person's to approve."""

    def nightly_paragraph(self) -> str:
        """The loop's one paragraph that starts with ``NIGHTLY_LABEL``."""
        paragraphs = [block.strip() for block in loop_text().split("\n\n") if block.strip()]
        matching = [block for block in paragraphs if block.startswith(NIGHTLY_LABEL)]
        self.assertEqual(len(matching), 1, f"the loop must carry one paragraph labelled {NIGHTLY_LABEL}")
        return matching[0]

    def test_the_paragraph_names_the_rule_and_shows_no_promote_or_approve_command(self) -> None:
        paragraph = self.nightly_paragraph()
        self.assertIn("nightly-*", paragraph)
        self.assertIn("a person", paragraph)
        self.assertIsNotNone(re.search(r"\bapprov\w*", paragraph), "the paragraph never says who approves")
        self.assertIn("Who approves", paragraph)
        self.assertIsNone(first_promote(paragraph), "the paragraph shows a promote command")
        self.assertIsNone(first_command(paragraph, "approve"), "the paragraph shows an approve command")


class TestTheMemoryBoundary(unittest.TestCase):
    def test_the_memory_call_syntax_and_steps_are_absent(self) -> None:
        for token in FORBIDDEN_TOKENS:
            with self.subTest(token=token):
                self.assertNotIn(token, PERSONA)

    def test_the_memory_words_stay_inside_the_memory_tools_section(self) -> None:
        section = section_text("## Memory tools")
        outside = PERSONA.replace(section, "", 1)
        self.assertIsNone(MEMORY_WORD_RE.search(outside), "a memory word appears outside the Memory tools section")
        self.assertIn(MEMKERNEL_TEMPLATE_URL, section)
        self.assertIn(COMPATIBILITY_URL, section)


class TestMemkernelsOrder(unittest.TestCase):
    def test_the_constant_is_the_copied_line_without_its_indentation(self) -> None:
        self.assertEqual(MEMKERNEL_WORKFLOW, MEMKERNEL_WORKFLOW.strip())
        self.assertTrue(MEMKERNEL_WORKFLOW.startswith("wiki_export()"))
        self.assertTrue(MEMKERNEL_WORKFLOW.endswith("wiki_import()"))
        self.assertEqual(marker_order(MEMKERNEL_WORKFLOW), ["wiki_export", "wiki-studio approve", "wiki_import"])

    def test_the_first_paragraph_naming_all_three_follows_memkernels_order(self) -> None:
        paragraphs = [block.strip() for block in section_text("## Memory tools").split("\n\n") if block.strip()]
        naming = [block for block in paragraphs if all(marker in block for marker in MEMKERNEL_MARKERS)]
        self.assertTrue(naming, "no paragraph of Memory tools names wiki_export, wiki-studio approve and wiki_import")
        self.assertEqual(marker_order(naming[0]), marker_order(MEMKERNEL_WORKFLOW))


if __name__ == "__main__":
    unittest.main()
