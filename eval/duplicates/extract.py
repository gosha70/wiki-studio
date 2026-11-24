# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The near-duplicate study's corpus: decision items extracted verbatim at two pins (issue 121, FR-002-FR-007).

``python -m eval.duplicates.extract [--code-copilot-team PATH] [--memkernel PATH] [--extend N] [--cut-1]
[--out DIR]`` reads the local code-copilot-team and memkernel checkouts at the pinned commits and writes one
decision page per extracted item under ``<out>/corpus/<repository>/<family>/`` plus ``<out>/corpus.json``.

Reading (FR-002): each repository is read only with ``git -C <checkout>`` and the read-only commands
``rev-parse --verify <pin>^{commit}``, ``ls-tree -r --name-only <pin> -- specs``, ``show <pin>:<path>`` and
``log -1 --format=%cs <pin>``, as argument lists through ``subprocess.run`` (never a shell), with the prefix
``--no-pager -c core.fsmonitor=false -c core.hooksPath=<devnull> -c protocol.allow=never`` and an environment
built from ``os.environ`` without any inherited ``GIT_`` variable except the three config-location ones. Nothing
is fetched, no working tree is read and nothing is written to either repository; the script writes only under
``--out``. A pin that does not resolve exits 2, a failing git call exits 3, and a file under ``<out>/corpus/``
that this run would not rewrite exits 4; in each case nothing is written.

The rule (families and exclusions FR-003, sections and forms FR-004, the title FR-005, the body and the page
FR-006, ``corpus.json`` and the left-out items FR-007) is fixed here before any page is read; the pure functions
``decision_sections``, ``section_items``, ``item_title``, ``item_body`` and ``build_page`` apply it to text, so
the tests call them on raw section text. No similarity is computed: the per-page input counts read one page
each and compare none.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from eval.patterns.duplicates import _first_paragraph, _title
from wiki_studio.wiki_state import _tokenise

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping, Sequence

DUPLICATES_DIR = Path(__file__).resolve().parent
REPO_ROOT = DUPLICATES_DIR.parents[1]
STUDY = "issue 121 near-duplicate study: the extracted corpus"
CORPUS_DIR_NAME = "corpus"
CORPUS_JSON_NAME = "corpus.json"

# FR-002: the two repositories, their sibling checkouts and their pins (resolved by hand with rev-parse).
CODE_COPILOT_TEAM = "code-copilot-team"
MEMKERNEL = "memkernel"
REPOSITORIES = (CODE_COPILOT_TEAM, MEMKERNEL)
DEFAULT_CHECKOUTS = {
    CODE_COPILOT_TEAM: REPO_ROOT.parent / CODE_COPILOT_TEAM,
    MEMKERNEL: REPO_ROOT.parent / MEMKERNEL,
}
PINS = {
    CODE_COPILOT_TEAM: "fd05256b107889853068e81aca1cf7c60419e37e",
    MEMKERNEL: "8279d7631851584a939a03d6243df57a4cc25c31",
}
SLUG_PREFIXES = {CODE_COPILOT_TEAM: "cct", MEMKERNEL: "mk"}

# FR-003: the families. A code-copilot-team directory is in family F when its name is F or starts with "F-".
BASE_FAMILIES = ("routing", "pi")
MEMKERNEL_FAMILY = MEMKERNEL
EXTENSION_ORDER = (
    "api",
    "llm-catalog",
    "wiki-studio-adoption",
    "wiki-audit",
    "memkernel-integration",
    "one-harness-home",
    "plugin-generate-from-sources",
    "simplest-complete-change",
)
CUT_1_FAMILIES = ("routing",)
CUT_1_MEMKERNEL_LEFT_OUT = frozenset({"copilot-memory-mvp", "memkernel-0-3", "memkernel-0-4"})
FAMILY_SEPARATOR = "-"

# FR-003: the exclusions (pitch finding 11). An excluded spec is never extracted, by any option.
EXCLUDED_FAMILIES = {
    CODE_COPILOT_TEAM: ("session-analytics", "benchmark", "auto-build"),
    MEMKERNEL: (),
}
EXCLUDED_SPECS = {
    CODE_COPILOT_TEAM: frozenset({"init-permission-profiles", "redaction-canaries"}),
    MEMKERNEL: frozenset({"memkernel-0-10-decision-revalidation", "memkernel-0-11-anti-rot-injection"}),
}

# FR-004: the files read, plan before spec, and what a decision section and an item are.
SPECS_DIR = "specs"
SPEC_FILES = ("plan.md", "spec.md")
H2_PREFIX = "## "
H3_PREFIX = "### "
BOLD_PREFIX = "**"
DECISION_WORD = "decision"
FENCE_MARKERS = ("```", "~~~")
LIST_ITEM_RE = re.compile(r"^(?:[-*+]|\d+[.)]) \*\*")
ADR_DECISION_LINE_RE = re.compile(r"^\s*\*\*decision(?:\*\*:|:\*\*)", re.IGNORECASE)
FORM_H3 = "h3"
FORM_H3_ADR = "h3-adr"
FORM_BOLD_PARAGRAPH = "bold-paragraph"
FORM_LIST_ITEM = "list-item"

# FR-005: the title rule.
BOLD_SPAN_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
IDENTIFIER_RE = re.compile(
    r"^(?:ADR-\d+|D-[a-z0-9]+(?:-[a-z0-9]+)*|[A-Z]{1,3}-?\d+(?:\.\d+)*[a-z]?)(?:[.:)])?(?:\s+[—–-])?\s*"
)
TRAILING_PARENTHETICAL_RE = re.compile(r"\s*\([^()]*\)\s*$")
TRAILING_PUNCTUATION = (".", ":")
FIRST_SENTENCE_RE = re.compile(r".*?[.?!](?=\s|$)")
PARAGRAPH_SPLIT_RE = re.compile(r"\n[ \t]*\n")

# FR-006: the body rule and the page.
LABEL_SEPARATOR_RE = re.compile(r"[ \t]*(?:[:—–-][ \t]*)?")
LIST_MARKER_RE = re.compile(r"^(?:[-*+]|\d+[.)]) ")
ADR_LABEL_RE = re.compile(r"^\*\*(context|decision|consequences)(?:\*\*:|:\*\*) ?", re.IGNORECASE)
DECISION_SECTION = "Decision"
ADR_SECTIONS = {"context": "Context", "decision": DECISION_SECTION, "consequences": "Consequences"}
PAGE_TYPE = "decision"
PAGE_STATUS = "stable"

# FR-007: the closing-keyword pattern; a matching item is left out and listed by id only.
CLOSING_KEYWORD_RE = re.compile(r"(?i)\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b:?\s+(?:[\w.-]+/[\w.-]+)?#\d+")
LEFT_OUT_REASON = "closing-keyword text"

# FR-002: the hardened read-only git call.
GIT_ENV_PREFIX = "GIT_"
GIT_ENV_KEPT = frozenset({"GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "GIT_CONFIG_NOSYSTEM"})
GIT_ENV_SET = {"GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"}
GIT_CEILING = "GIT_CEILING_DIRECTORIES"
GIT_PREFIX = (
    "--no-pager",
    "-c",
    "core.fsmonitor=false",
    "-c",
    f"core.hooksPath={os.devnull}",
    "-c",
    "protocol.allow=never",
)
GIT_CALL_TIMEOUT_SECONDS = 120
COMMIT_PEEL = "^{commit}"
COMMIT_DATE_FORMAT = "--format=%cs"

PIN_UNRESOLVED = 2
GIT_FAILED = 3
STALE_CORPUS = 4


class PinError(RuntimeError):
    """A pin does not resolve to a commit in its checkout."""


class GitReadError(RuntimeError):
    """A read-only git call failed."""


class StaleCorpusError(RuntimeError):
    """A file under ``<out>/corpus/`` would not be rewritten by this run."""


@dataclass(frozen=True)
class Item:
    """One decision item: its form, its 1-based line span in the file and its raw lines."""

    form: str
    line_start: int
    line_end: int
    lines: tuple[str, ...]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


@dataclass(frozen=True)
class Snapshot:
    """One repository at its pin: the paths its tree lists under ``specs`` and a reader for a file's text."""

    repository: str
    pin: str
    commit_date: str
    paths: frozenset[str]
    read: Callable[[str], str]


@dataclass
class Corpus:
    """The extracted pages (path under ``corpus/`` to bytes), their entries, the left-out items and the families."""

    pages: dict[str, bytes] = field(default_factory=dict)
    entries: list[dict[str, Any]] = field(default_factory=list)
    left_out: list[dict[str, Any]] = field(default_factory=list)
    families: list[dict[str, Any]] = field(default_factory=list)


# --- reading (FR-002) ---------------------------------------------------------------------------------------


def git_environment(checkout: Path) -> dict[str, str]:
    """``os.environ`` without inherited ``GIT_`` variables (three kept), no prompt, C locale, ceiling above."""
    env = {
        name: value for name, value in os.environ.items() if not name.startswith(GIT_ENV_PREFIX) or name in GIT_ENV_KEPT
    }
    env.update(GIT_ENV_SET)
    env[GIT_CEILING] = str(checkout.resolve().parent)
    return env


def _git(checkout: Path, args: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
    """One hardened, read-only git call: argument list, no shell, clean environment, timeout."""
    return subprocess.run(
        ["git", *GIT_PREFIX, "-C", str(checkout), *args],
        capture_output=True,
        env=git_environment(checkout),
        timeout=GIT_CALL_TIMEOUT_SECONDS,
        check=False,
    )


def _git_text(checkout: Path, args: Sequence[str]) -> str:
    result = _git(checkout, args)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise GitReadError(f"git {' '.join(args)} failed in {checkout}: {detail}")
    return result.stdout.decode("utf-8")


def verify_pin(checkout: Path, pin: str) -> None:
    """Stop unless ``pin`` resolves, in ``checkout``, to exactly that commit."""
    result = _git(checkout, ["rev-parse", "--verify", f"{pin}{COMMIT_PEEL}"])
    resolved = result.stdout.decode("utf-8", errors="replace").strip()
    if result.returncode != 0 or resolved != pin:
        raise PinError(f"pin {pin} does not resolve to exactly that commit in {checkout} (got {resolved or 'nothing'})")


def read_snapshot(repository: str, checkout: Path, pin: str) -> Snapshot:
    """The repository at ``pin``: its commit date, its ``specs`` paths and a reader by ``git show``."""
    verify_pin(checkout, pin)
    commit_date = _git_text(checkout, ["log", "-1", COMMIT_DATE_FORMAT, pin]).strip()
    listing = _git_text(checkout, ["ls-tree", "-r", "--name-only", pin, "--", SPECS_DIR])
    paths = frozenset(line for line in listing.split("\n") if line)
    texts: dict[str, str] = {}

    def read(path: str) -> str:
        if path not in texts:
            texts[path] = _git_text(checkout, ["show", f"{pin}:{path}"])
        return texts[path]

    return Snapshot(repository=repository, pin=pin, commit_date=commit_date, paths=paths, read=read)


# --- families and exclusions (FR-003) -----------------------------------------------------------------------


def in_family(family: str, name: str) -> bool:
    """FR-003's prefix rule: ``name`` equals ``family`` or starts with ``family-``."""
    return name == family or name.startswith(family + FAMILY_SEPARATOR)


def is_excluded(repository: str, name: str) -> bool:
    """True for a spec of an excluded family or an excluded spec; such a spec is never extracted."""
    if name in EXCLUDED_SPECS[repository]:
        return True
    return any(in_family(family, name) for family in EXCLUDED_FAMILIES[repository])


def spec_names(paths: Iterable[str]) -> list[str]:
    """The spec directories that hold a ``plan.md`` or ``spec.md``, sorted."""
    names = set()
    for path in paths:
        parts = path.split("/")
        if len(parts) == 3 and parts[0] == SPECS_DIR and parts[2] in SPEC_FILES:
            names.add(parts[1])
    return sorted(names)


def code_copilot_team_families(extend: int, cut_1: bool) -> list[str]:
    """The base families (``routing`` alone under cut 1), then the first ``extend`` extension steps."""
    base = CUT_1_FAMILIES if cut_1 else BASE_FAMILIES
    return [*base, *EXTENSION_ORDER[:extend]]


def family_directories(repository: str, names: Iterable[str], extend: int, cut_1: bool) -> list[tuple[str, list[str]]]:
    """Each family of ``repository`` with its directories as listed, exclusions removed (decision sections not yet
    checked); memkernel is one family, less its three pre-0.7 plans under cut 1."""
    candidates = [name for name in sorted(names) if not is_excluded(repository, name)]
    if repository == MEMKERNEL:
        if cut_1:
            candidates = [name for name in candidates if name not in CUT_1_MEMKERNEL_LEFT_OUT]
        return [(MEMKERNEL_FAMILY, candidates)]
    return [
        (family, [name for name in candidates if in_family(family, name)])
        for family in code_copilot_team_families(extend, cut_1)
    ]


# --- decision sections and items (FR-004) -------------------------------------------------------------------


def _fence_opener(line: str) -> str | None:
    stripped = line.lstrip()
    return next((marker for marker in FENCE_MARKERS if stripped.startswith(marker)), None)


def fenced_lines(lines: Sequence[str]) -> list[bool]:
    """Per line, True when it opens, sits inside or closes a fenced block (three backticks or three tildes)."""
    flags: list[bool] = []
    fence: str | None = None
    for line in lines:
        if fence is None:
            fence = _fence_opener(line)
            flags.append(fence is not None)
        else:
            flags.append(True)
            if line.lstrip().startswith(fence):
                fence = None
    return flags


def decision_sections(lines: Sequence[str]) -> list[tuple[int, int]]:
    """Each decision section as ``(first, end)`` 0-based indexes of its content lines (the H2 line excluded): an
    H2 line outside fenced code whose text contains "decision" (any case), up to the next H2 line or the end."""
    fenced = fenced_lines(lines)
    h2 = [index for index, line in enumerate(lines) if not fenced[index] and line.startswith(H2_PREFIX)]
    sections = []
    for position, index in enumerate(h2):
        if DECISION_WORD in lines[index][len(H2_PREFIX) :].lower():
            end = h2[position + 1] if position + 1 < len(h2) else len(lines)
            sections.append((index + 1, end))
    return sections


def _blank(line: str) -> bool:
    return line.strip() == ""


def _trimmed(lines: Sequence[str]) -> list[str]:
    """``lines`` without leading and trailing blank lines."""
    start, end = 0, len(lines)
    while start < end and _blank(lines[start]):
        start += 1
    while end > start and _blank(lines[end - 1]):
        end -= 1
    return list(lines[start:end])


def _bold_paragraph_starts(lines: Sequence[str], fenced: Sequence[bool]) -> list[int]:
    first_non_blank = next((index for index, line in enumerate(lines) if not _blank(line)), None)
    return [
        index
        for index, line in enumerate(lines)
        if not fenced[index]
        and line.startswith(BOLD_PREFIX)
        and (index == first_non_blank or (index > 0 and _blank(lines[index - 1])))
    ]


def _list_item_end(lines: Sequence[str], start: int) -> int:
    for index in range(start + 1, len(lines)):
        if not _blank(lines[index]) and not lines[index][0].isspace():
            return index
    return len(lines)


def section_items(lines: Sequence[str], first_line: int) -> list[Item]:
    """The items of one decision section by FR-004's precedence; ``first_line`` is the 1-based file line number
    of ``lines[0]``. Text before the first item is not an item; trailing blank lines are not part of an item."""
    fenced = fenced_lines(lines)
    spans: list[tuple[int, int]] = []
    h3 = [index for index, line in enumerate(lines) if not fenced[index] and line.startswith(H3_PREFIX)]
    bold = [] if h3 else _bold_paragraph_starts(lines, fenced)
    if h3 or bold:
        form = FORM_H3 if h3 else FORM_BOLD_PARAGRAPH
        starts = h3 or bold
        spans = [(start, starts[i + 1] if i + 1 < len(starts) else len(lines)) for i, start in enumerate(starts)]
    else:
        form = FORM_LIST_ITEM
        starts = [index for index, line in enumerate(lines) if not fenced[index] and LIST_ITEM_RE.match(line)]
        spans = [(start, _list_item_end(lines, start)) for start in starts]
    items = []
    for start, end in spans:
        body = list(lines[start:end])
        while body and _blank(body[-1]):
            body.pop()
        item_form = form
        if form == FORM_H3 and any(ADR_DECISION_LINE_RE.match(line) for line in body):
            item_form = FORM_H3_ADR
        items.append(Item(item_form, first_line + start, first_line + start + len(body) - 1, tuple(body)))
    return items


def file_items(text: str) -> list[Item]:
    """Every item of every decision section of one file, in document order."""
    lines = text.split("\n")
    items: list[Item] = []
    for first, end in decision_sections(lines):
        items.extend(section_items(lines[first:end], first + 1))
    return items


# --- the title (FR-005) and the body (FR-006) ---------------------------------------------------------------


def _is_h3(form: str) -> bool:
    return form in (FORM_H3, FORM_H3_ADR)


def item_label(item: Item) -> str:
    """The H3 line's text, or the text inside the item's first ``**…**`` span (whitespace collapsed)."""
    if _is_h3(item.form):
        return item.lines[0][len(H3_PREFIX) :].strip()
    match = BOLD_SPAN_RE.search(item.text)
    return " ".join(match.group(1).split()) if match else ""


def title_from_label(label: str) -> str:
    """FR-005: the leading identifier, then a trailing parenthetical (a trailing ``.`` or ``:`` set aside meanwhile),
    then one trailing ``.`` or ``:``, then surrounding whitespace, each removed once."""
    text = IDENTIFIER_RE.sub("", label, count=1).rstrip()
    aside = text[-1] if text.endswith(TRAILING_PUNCTUATION) else ""
    if aside:
        text = text[:-1]
    text = TRAILING_PARENTHETICAL_RE.sub("", text, count=1) + aside
    if text.endswith(TRAILING_PUNCTUATION):
        text = text[:-1]
    return text.strip()


def first_sentence(body: str) -> str:
    """The shortest prefix of the first non-empty paragraph (whitespace collapsed) ending in ``.``, ``?`` or ``!``
    followed by whitespace or the end; the whole paragraph when there is none."""
    for paragraph in PARAGRAPH_SPLIT_RE.split(body):
        collapsed = " ".join(paragraph.split())
        if collapsed:
            match = FIRST_SENTENCE_RE.match(collapsed)
            return match.group(0) if match else collapsed
    return ""


def item_title(item: Item) -> str:
    """The title from the label, or the first sentence of the body when nothing of the label is left."""
    title = title_from_label(item_label(item))
    return title if title else first_sentence(body_text(item))


def _without_label(item: Item) -> list[str]:
    """Step 1: the H3 line, or the opening bold span with the whitespace and one separator after it, removed."""
    if _is_h3(item.form):
        return list(item.lines[1:])
    text = item.text
    match = BOLD_SPAN_RE.search(text)
    if match is None:
        return list(item.lines)
    separator = LABEL_SEPARATOR_RE.match(text, match.end())
    end = separator.end() if separator else match.end()
    return (text[: match.start()] + text[end:]).split("\n")


def _unindented(lines: Sequence[str]) -> list[str]:
    """Step 2: outside fenced code each line loses its leading whitespace, then one list marker; lines inside a
    fenced block are copied unchanged (its closing line loses its leading whitespace, as the opening one did)."""
    out: list[str] = []
    fence: str | None = None
    for line in lines:
        if fence is not None:
            if line.lstrip().startswith(fence):
                out.append(line.lstrip())
                fence = None
            else:
                out.append(line)
            continue
        stripped = LIST_MARKER_RE.sub("", line.lstrip(), count=1)
        fence = _fence_opener(stripped)
        out.append(stripped)
    return out


def _adr_sections(lines: Sequence[str]) -> list[tuple[str | None, list[str]]]:
    """Step 3: the Context, Decision and Consequences lines lose their labels and go under their own H2, in the
    order the labels appear; lines before the first label stay above the first section (heading None)."""
    blocks: list[tuple[str | None, list[str]]] = [(None, [])]
    fenced = fenced_lines(lines)
    for index, line in enumerate(lines):
        match = None if fenced[index] else ADR_LABEL_RE.match(line)
        if match is not None:
            blocks.append((ADR_SECTIONS[match.group(1).lower()], [line[match.end() :]]))
        else:
            blocks[-1][1].append(line)
    return blocks


def _body_blocks(item: Item) -> list[tuple[str | None, list[str]]]:
    """Steps 1-3: each block's H2 name (None for the lines above the first ADR section) and its trimmed lines."""
    lines = _unindented(_without_label(item))
    blocks = _adr_sections(lines) if item.form == FORM_H3_ADR else [(DECISION_SECTION, lines)]
    return [(name, _trimmed(content)) for name, content in blocks if name is not None or _trimmed(content)]


def body_text(item: Item) -> str:
    """The item's text after steps 1-3, without the page's section headings (the first-sentence fallback reads it)."""
    return "\n\n".join("\n".join(content) for _name, content in _body_blocks(item) if content)


def item_body(item: Item) -> str:
    """FR-006: the page body below the frontmatter, without the final newline. No word is changed, added or
    reordered; headings, tables, fences and blockquotes inside an item stay as written after step 2."""
    rendered = []
    for name, content in _body_blocks(item):
        text = "\n".join(content)
        rendered.append(text if name is None else (f"## {name}\n\n{text}" if content else f"## {name}"))
    return "\n\n".join(rendered)


def slug_for(repository: str, spec_name: str, file_name: str, ordinal: int) -> str:
    """``<cct|mk>-<spec name>-<plan|spec>-<nn>``, ``nn`` the item's 1-based ordinal in its file, two digits."""
    return f"{SLUG_PREFIXES[repository]}-{spec_name}-{Path(file_name).stem}-{ordinal:02d}"


def _single_quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def build_page(item: Item, *, slug: str, spec_path: str, pin: str, commit_date: str) -> tuple[str, str]:
    """The page's title and text (FR-006): the frontmatter, a blank line, the body, one final newline."""
    title = item_title(item)
    frontmatter = "\n".join(
        [
            "---",
            f"page_type: {PAGE_TYPE}",
            f"slug: {slug}",
            f"title: {_single_quoted(title)}",
            f"status: {PAGE_STATUS}",
            f"last_reviewed: {commit_date}",
            "sources:",
            f"  - path: {spec_path}",
            f"    sha: {pin}",
            "---",
        ]
    )
    return title, f"{frontmatter}\n\n{item_body(item)}\n"


def input_counts(page: str) -> dict[str, Any]:
    """FR-007's per-page counts: tokens of the title and of the paragraph the scorer reads; compares no pages."""
    paragraph = _first_paragraph(page)
    return {
        "title_tokens": len(_tokenise(_title(page))),
        "paragraph_tokens": len(_tokenise(paragraph)),
        "paragraph_empty": paragraph == "",
    }


# --- the corpus (FR-003, FR-007) ----------------------------------------------------------------------------


def _spec_paths(snapshot: Snapshot, name: str) -> list[str]:
    """The directory's ``plan.md`` and ``spec.md`` paths that exist at the pin, plan first."""
    return [path for path in (f"{SPECS_DIR}/{name}/{file}" for file in SPEC_FILES) if path in snapshot.paths]


def _family_rows(snapshot: Snapshot, extend: int, cut_1: bool) -> list[tuple[str, list[str], list[str]]]:
    """Each family with its listed directories and those holding a decision section."""
    rows = []
    for family, names in family_directories(snapshot.repository, spec_names(snapshot.paths), extend, cut_1):
        with_sections = [
            name
            for name in names
            if any(decision_sections(snapshot.read(path).split("\n")) for path in _spec_paths(snapshot, name))
        ]
        rows.append((family, names, with_sections))
    return rows


def extract_corpus(snapshots: Sequence[Snapshot], *, extend: int = 0, cut_1: bool = False) -> Corpus:
    """Every page and left-out item of the families, read from the snapshots by the rule above."""
    corpus = Corpus()
    for snapshot in snapshots:
        for family, names, with_sections in _family_rows(snapshot, extend, cut_1):
            corpus.families.append(
                {
                    "repository": snapshot.repository,
                    "family": family,
                    "directories": names,
                    "with_decision_sections": with_sections,
                }
            )
            for name in with_sections:
                for spec_path in _spec_paths(snapshot, name):
                    for ordinal, item in enumerate(file_items(snapshot.read(spec_path)), start=1):
                        _add_item(corpus, snapshot, family, spec_path, ordinal, item)
    corpus.entries.sort(key=lambda entry: str(entry["page"]))
    corpus.left_out.sort(key=lambda entry: (str(entry["repository"]), str(entry["slug"])))
    return corpus


def _add_item(corpus: Corpus, snapshot: Snapshot, family: str, spec_path: str, ordinal: int, item: Item) -> None:
    _specs, name, file_name = spec_path.split("/")
    slug = slug_for(snapshot.repository, name, file_name, ordinal)
    span = {"line_start": item.line_start, "line_end": item.line_end}
    if CLOSING_KEYWORD_RE.search(item.text):
        corpus.left_out.append(
            {"repository": snapshot.repository, "spec_path": spec_path, **span, "slug": slug, "reason": LEFT_OUT_REASON}
        )
        return
    title, page = build_page(item, slug=slug, spec_path=spec_path, pin=snapshot.pin, commit_date=snapshot.commit_date)
    data = page.encode("utf-8")
    rel = f"{snapshot.repository}/{family}/{slug}.md"
    corpus.pages[rel] = data
    corpus.entries.append(
        {
            "page": rel,
            "repository": snapshot.repository,
            "family": family,
            "spec_path": spec_path,
            **span,
            "form": item.form,
            "title": title,
            "sha256": hashlib.sha256(data).hexdigest(),
            **input_counts(page),
        }
    )


def corpus_document(corpus: Corpus, snapshots: Sequence[Snapshot], *, extend: int, cut_1: bool) -> dict[str, Any]:
    """``corpus.json``'s content (FR-007)."""
    return {
        "study": STUDY,
        "repositories": [
            {"name": snapshot.repository, "pin": snapshot.pin, "commit_date": snapshot.commit_date}
            for snapshot in snapshots
        ],
        "options": {"extend": extend, "cut_1": cut_1},
        "families": corpus.families,
        "pages": corpus.entries,
        "left_out": corpus.left_out,
    }


def write_corpus(out: Path, corpus: Corpus, document: Mapping[str, Any]) -> None:
    """Write the pages and ``corpus.json`` under ``out``; refuse, writing nothing, when ``out/corpus/`` holds a
    file this run would not rewrite."""
    corpus_dir = out / CORPUS_DIR_NAME
    if corpus_dir.exists():
        stale = sorted(
            path.relative_to(corpus_dir).as_posix()
            for path in corpus_dir.rglob("*")
            if path.is_file() and path.relative_to(corpus_dir).as_posix() not in corpus.pages
        )
        if stale:
            raise StaleCorpusError(f"{corpus_dir} holds files this run would not write: {', '.join(stale)}")
    out.mkdir(parents=True, exist_ok=True)
    for rel, data in sorted(corpus.pages.items()):
        target = corpus_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    text = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    (out / CORPUS_JSON_NAME).write_bytes(text.encode("utf-8"))


# --- the command --------------------------------------------------------------------------------------------


def _extend_steps(value: str) -> int:
    steps = int(value)
    if not 0 <= steps <= len(EXTENSION_ORDER):
        raise argparse.ArgumentTypeError(f"--extend takes 0 to {len(EXTENSION_ORDER)}, got {steps}")
    return steps


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m eval.duplicates.extract",
        description="Extract the issue 121 corpus: decision items of two repositories at their pins, verbatim.",
    )
    parser.add_argument(
        "--code-copilot-team",
        type=Path,
        default=DEFAULT_CHECKOUTS[CODE_COPILOT_TEAM],
        metavar="PATH",
        help=f"The code-copilot-team checkout, read at {PINS[CODE_COPILOT_TEAM]} (default: the sibling checkout).",
    )
    parser.add_argument(
        "--memkernel",
        type=Path,
        default=DEFAULT_CHECKOUTS[MEMKERNEL],
        metavar="PATH",
        help=f"The memkernel checkout, read at {PINS[MEMKERNEL]} (default: the sibling checkout).",
    )
    parser.add_argument(
        "--extend",
        type=_extend_steps,
        default=0,
        metavar="N",
        help="Add the first N steps of the extension order, each its own family (default 0).",
    )
    parser.add_argument(
        "--cut-1",
        action="store_true",
        help="The circuit breaker's first cut: routing only, and memkernel without its three pre-0.7 plans.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DUPLICATES_DIR,
        metavar="DIR",
        help="Write corpus/ and corpus.json under DIR (default: eval/duplicates/).",
    )
    return parser


def main(argv: Sequence[str] | None = None, *, pins: Mapping[str, str] | None = None) -> int:
    """Extract and write the corpus; return 0, or 2 (a pin does not resolve), 3 (git failed), 4 (stale files)."""
    parser = _build_arg_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    pin_for = dict(PINS if pins is None else pins)
    checkouts = {CODE_COPILOT_TEAM: args.code_copilot_team, MEMKERNEL: args.memkernel}
    try:
        for repository in REPOSITORIES:
            verify_pin(checkouts[repository], pin_for[repository])
        snapshots = [
            read_snapshot(repository, checkouts[repository], pin_for[repository]) for repository in REPOSITORIES
        ]
        corpus = extract_corpus(snapshots, extend=args.extend, cut_1=args.cut_1)
        document = corpus_document(corpus, snapshots, extend=args.extend, cut_1=args.cut_1)
        write_corpus(args.out, corpus, document)
    except PinError as exc:
        sys.stderr.write(f"{exc}; nothing was written\n")
        return PIN_UNRESOLVED
    except (GitReadError, subprocess.TimeoutExpired) as exc:
        sys.stderr.write(f"{exc}; nothing was written\n")
        return GIT_FAILED
    except StaleCorpusError as exc:
        sys.stderr.write(f"{exc}; nothing was written\n")
        return STALE_CORPUS
    sys.stdout.write(
        f"{len(corpus.entries)} pages, {len(corpus.left_out)} left out, written under {args.out / CORPUS_DIR_NAME}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
