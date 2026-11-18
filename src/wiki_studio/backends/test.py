# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
# wiki-studio.backends.test — deterministic test backend (no LLM, no subprocess).

from __future__ import annotations

import posixpath
import re
from pathlib import Path
from typing import Any

from .. import yaml_lite
from ..errors import ContractViolationError
from ..nightly import INLINE_LINK_RE, code_regions
from ..prompt import CURATE_TASK
from ..prose_lint import find_term


def _extract_h1(content: str) -> str:
    """Return the first H1 heading text from a markdown string, or a fallback."""
    for line in content.splitlines():
        m = re.match(r"^#\s+(.+)", line)
        if m:
            return m.group(1).strip()
    return "Untitled"


def _to_kebab(title: str) -> str:
    """Convert a title string to a kebab-case slug."""
    # Lowercase, replace non-alphanumeric runs with hyphens, strip leading/trailing.
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "untitled"


def _quote_first_line(content: str) -> str:
    """The first non-blank line of ``content`` (at most 120 characters), or ''.

    A query citation must quote the cited page as it was in the prompt
    (FR-014), so the fragment is taken from the page text itself.
    """
    for line in content.splitlines():
        if line.strip():
            return line[:120]
    return ""


def _frontmatter_value(text: str, key: str) -> str | None:
    """The frontmatter ``key:`` value, or None when the page has none."""
    try:
        value = yaml_lite.parse_frontmatter(text).get(key)
    except ContractViolationError:
        return None
    return value if isinstance(value, str) else None


def _body_start(text: str) -> int:
    """The offset just past the closing frontmatter line, or 0 without frontmatter."""
    offset = 0
    for index, line in enumerate(text.splitlines(keepends=True)):
        if index == 0 and line.strip() != "---":
            return 0
        if index > 0 and line.strip() == "---":
            return offset + len(line)
        offset += len(line)
    return 0


def _link_first_mention(text: str, page_path: str, canonical: str, slug: str) -> str:
    """Link the first whole-word mention of ``slug`` outside frontmatter, code and links (FR-017)."""
    if not text:
        return text
    regions = code_regions(text)
    regions.extend((match.start(), match.end()) for match in INLINE_LINK_RE.finditer(text))
    best: re.Match[str] | None = None
    for form in (slug, slug.replace("-", " ")):
        for match in find_term(text, form):
            if match.start() < _body_start(text):
                continue
            if any(match.start() < end and start < match.end() for start, end in regions):
                continue
            if best is None or match.start() < best.start():
                best = match
    if best is None:
        return text
    target = posixpath.relpath(canonical, posixpath.dirname(page_path) or ".")
    return f"{text[: best.start()]}[{best.group(0)}]({target}){text[best.end() :]}"


class TestBackend:
    """Deterministic in-process backend for unit and integration tests.

    Rules:
    - page_type is always "incident".
    - slug is derived from the source H1 (kebab-case).
    - title is the source H1 verbatim.
    - sources is a single fixed entry (the source path).
    - draft_markdown is constructed to satisfy ALL semantic-validation rules so
      the test backend round-trips clean through parse_response().
    - disposition is always "accept".

    This backend must NOT be selected by auto-detect; use --backend test explicitly.
    """

    def call(self, prompt: dict[str, Any]) -> dict[str, Any]:
        # Phase 1: dispatch on task. The default ("ingest" / "gate-only")
        # returns the v1 single-page IngestProposal shape; "ingest-multi"
        # returns a deterministic WikiPatchSet shape. Other tasks added
        # in later phases (query, lint-health) extend this dispatch.
        task = prompt.get("task", "ingest")
        if task == "ingest-multi":
            return self._call_multi(prompt)
        if task == "query":
            return self._call_query(prompt)
        if task == CURATE_TASK:
            return self._call_curate(prompt)
        return self._call_single(prompt)

    def _call_curate(self, prompt: dict[str, Any]) -> dict[str, Any]:
        """A deterministic draft that passes FR-019: links only, one log line (FR-017).

        For a ``missing-cross-link`` it links the first whole-word mention of
        the canonical page (its slug or the slug with spaces for hyphens,
        outside frontmatter, code and existing links) in every editable page,
        returning a page with no such mention unchanged, so FR-019 refuses the
        whole draft. For a ``weak-orphan`` it appends the fixed index line.
        """
        finding = prompt.get("finding", {}) or {}
        kind = str(finding.get("kind", ""))
        editable = [str(page) for page in finding.get("editable", []) or []]
        canonical = finding.get("canonical")
        orphan = finding.get("orphan")
        run_date = str(finding.get("date", ""))
        wiki_state = prompt.get("wiki_state", {}) or {}
        shown = wiki_state.get("candidate_pages", {}) or {}
        edits: list[dict[str, str]] = []
        if canonical is not None:
            slug = Path(str(canonical)).stem
            for page in editable:
                edits.append(
                    {
                        "path": page,
                        "action": "update",
                        "new_content": _link_first_mention(str(shown.get(page, "")), page, str(canonical), slug),
                        "rationale": f"Link the first mention of {slug!r} to its canonical page.",
                    }
                )
            named = editable[0] if editable else str(canonical)
        else:
            orphan_path = str(orphan or "")
            orphan_text = str(shown.get(orphan_path, ""))
            title = _frontmatter_value(orphan_text, "title") or Path(orphan_path).stem
            edits.append(
                {
                    "path": "index.md",
                    "action": "append-index",
                    "new_content": f"- [{title}]({orphan_path})",
                    "rationale": f"Link the weak orphan {orphan_path!r} from index.md.",
                }
            )
            named = orphan_path
        named_text = str(shown.get(named, ""))
        slug = _frontmatter_value(named_text, "slug") or Path(named).stem
        page_type = _frontmatter_value(named_text, "page_type") or ""
        edits.append(
            {
                "path": "log.md",
                "action": "append-log",
                "new_content": f"- {run_date} — link {slug} ({page_type}): nightly {kind} draft",
                "rationale": "Append one log line for the link the draft adds.",
            }
        )
        return {
            "version": 1,
            "rationale": f"Test backend deterministic curate draft for {kind}.",
            "edits": edits,
        }

    def _call_query(self, prompt: dict[str, Any]) -> dict[str, Any]:
        """Deterministic query response for Phase-3 tests.

        Returns an answer derived from the question + cites every
        candidate page that was loaded into the prompt. Idempotent
        and stable — useful for index-first navigation tests. Every
        fragment is quoted from the prompt's own text (the first
        non-blank line of the page, or of index.md for the abstention
        form), so the reply satisfies the citation-evidence rule.
        """
        question = prompt.get("source", {}).get("content", "")
        wiki_state = prompt.get("wiki_state", {})
        candidates = wiki_state.get("candidate_pages", {}) or {}

        # Synthesise a stable answer from the question + page paths.
        if candidates:
            citations = [{"page": rel, "fragment": _quote_first_line(content)} for rel, content in candidates.items()]
            answer = f"Test backend deterministic answer to: {question.strip()!r}. Consulted {len(candidates)} page(s)."
        else:
            citations = [{"page": "index.md", "fragment": _quote_first_line(wiki_state.get("index_md", ""))}]
            answer = ""  # empty signals "not enough info"

        return {
            "version": 1,
            "answer": answer,
            "citations": citations,
        }

    def _call_single(self, prompt: dict[str, Any]) -> dict[str, Any]:
        source = prompt.get("source", {})
        content = source.get("content", "")
        source_path = source.get("path", "unknown-source.md")

        h1 = _extract_h1(content)
        slug = _to_kebab(h1)
        page_type = "incident"
        title = h1
        today = "2026-05-04"

        sources = [{"path": source_path, "sha": "abc1234"}]

        # Build a draft_markdown that passes semantic validation:
        #   - frontmatter page_type, slug, title, sources match the structured fields exactly.
        #   - page_type == "incident" → directory is incidents/ (validated at lint time).
        sources_yaml = "\n".join(f"  - path: {s['path']}\n    sha: {s['sha']}" for s in sources)
        draft_markdown = (
            f"---\n"
            f"page_type: {page_type}\n"
            f"slug: {slug}\n"
            f"title: {title}\n"
            f"status: draft\n"
            f"last_reviewed: {today}\n"
            f"sources:\n"
            f"{sources_yaml}\n"
            f"---\n"
            f"\n"
            f"# {title}\n"
            f"\n"
            f"## What happened\n"
            f"\n"
            f"(Test backend placeholder — replace with real content.)\n"
            f"\n"
            f"## Why it happened\n"
            f"\n"
            f"(Root cause placeholder.)\n"
            f"\n"
            f"## What we changed\n"
            f"\n"
            f"(Remediation placeholder.)\n"
            f"\n"
            f"## How to recognize a recurrence\n"
            f"\n"
            f"(Recurrence signals placeholder.)\n"
        )

        return {
            "version": 1,
            "disposition": "accept",
            "reason": "Test backend always accepts; deterministic output for CI.",
            "page_type": page_type,
            "slug": slug,
            "title": title,
            "draft_markdown": draft_markdown,
            "sources": sources,
        }

    def _call_multi(self, prompt: dict[str, Any]) -> dict[str, Any]:
        """Deterministic multi-page WikiPatchSet response for Phase-1 tests.

        Returns a fixed set of edits derived from the source H1:
          1. create  incidents/<slug>.md  — main page
          2. append-log  log.md            — one-line log entry
          3. append-index  index.md       — entry under "Incidents"

        This mirrors the canonical "atomic cluster" pattern from
        workflows/promote-lesson-to-wiki.md: one source
        produces one main page, one log line, one index link.
        """
        source = prompt.get("source", {})
        content = source.get("content", "")
        source_path = source.get("path", "unknown-source.md")

        h1 = _extract_h1(content)
        slug = _to_kebab(h1)
        title = h1
        today = "2026-05-04"

        page_path = f"incidents/{slug}.md"
        page_md = (
            f"---\n"
            f"page_type: incident\n"
            f"slug: {slug}\n"
            f"title: {title}\n"
            f"status: draft\n"
            f"last_reviewed: {today}\n"
            f"sources:\n"
            f"  - path: {source_path}\n"
            f"    sha: abc1234\n"
            f"---\n"
            f"\n"
            f"# {title}\n"
            f"\n"
            f"(Test backend placeholder — multi-page ingest path.)\n"
        )

        edits = [
            {
                "path": page_path,
                "action": "create",
                "new_content": page_md,
                "rationale": "Main incident page derived from the source H1.",
            },
            {
                "path": "log.md",
                "action": "append-log",
                "new_content": f"- {today} — promote {slug} (incident): test backend.",
                "rationale": "Append a dated log entry per the canonical loop.",
            },
            {
                "path": "index.md",
                "action": "append-index",
                "new_content": f"- [{title}](incidents/{slug}.md) — test backend placeholder.",
                "rationale": "Link the new incident from index.md under the Incidents section.",
            },
        ]
        return {
            "version": 1,
            "rationale": (
                "Test backend deterministic multi-page response: create main incident page + append-log + append-index."
            ),
            "edits": edits,
        }
