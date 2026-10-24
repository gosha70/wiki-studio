# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
# wiki-studio.querier — Phase-3 query operation.
#
# Karpathy's pattern: the wiki is queryable. The querier reads
# index.md FIRST (the navigation primitive), follows links to a
# bounded set of relevant pages, synthesises an answer from those
# pages, and returns it with (page, fragment) citations. Pages not
# linked from index.md are unreachable through query — that's by
# design (the index is the wiki's table of contents; orphans are
# already flagged by the structural linter).
#
# The pages-loaded list is appended to
# the query log (``WikiPaths.query_log``) so curators can audit the
# index-first navigation: did the query open the right pages? did
# it load too many? did it open pages NOT linked from the index
# (which would be a bug)?
#
# ``--file-back`` synthesises a source from the question+answer
# text and runs the multi-page ingest over it, producing a patch-set
# that captures the answer back into the wiki. The curator reviews
# and runs ``wiki promote`` to land it.

from __future__ import annotations

import datetime
import json
import posixpath
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from .errors import (
    BackendInvocationError,
    ContractViolationError,
    SourceMissingError,
)
from .ingestor_multi import DefaultMultiIngestor
from .lint import NON_FILESYSTEM_SCHEMES
from .paths import ContainmentError, contain, is_absolute_path
from .prompt import load_schema_files
from .proposal import Citation, IngestRequest, QueryAnswer, WikiPatchSet
from .wiki_state import _read_text_or_empty, _tokenise

if TYPE_CHECKING:
    from .ingestor import Backend
    from .paths import WikiPaths

# Default cap on candidate pages loaded into the query prompt. Index-
# first navigation typically needs only 1–5 pages; the default of 5 is
# generous, configurable via Querier(max_pages=N).
DEFAULT_MAX_QUERY_PAGES = 5

# Pattern for [text](path.md) inside index.md. Used to extract the
# wiki's link graph before scoring pages.
_MD_LINK_RE = re.compile(r"\]\(([^)]+\.md)(?:#[^)]*)?\)")


def _index_entry_inside_wiki(target: str, wiki_dir: Path | None) -> bool:
    """The index-entry rule of the structural linter, applied as a defence (FR-013).

    A target is kept only when it is a relative ``.md`` path that stays
    inside the wiki: no web URL, no absolute path, no ``..`` escape and, when
    ``wiki_dir`` is given, no symlink on the way and no resolution outside the
    wiki directory. Lint reports such entries first; this keeps ``find``,
    ``query`` and the eval selector from reading a file outside the wiki when
    it has not run.
    """
    if target.startswith(NON_FILESYSTEM_SCHEMES) or is_absolute_path(target):
        return False
    normalised = posixpath.normpath(target)
    if normalised == ".." or normalised.startswith("../"):
        return False
    if wiki_dir is None:
        return True
    try:
        contain(target, wiki_dir)
    except ContainmentError:
        return False
    return True


def _extract_index_links(index_md: str, wiki_dir: Path | None = None) -> list[str]:
    """Return the list of wiki-relative .md paths linked from index.md.

    Keeps only entries that stay inside the wiki (:func:`_index_entry_inside_wiki`);
    with ``wiki_dir`` the check resolves each target on disk. Order is
    significant — first-occurrence wins for relevance ranking ties.
    """
    paths: list[str] = []
    seen: set[str] = set()
    for m in _MD_LINK_RE.finditer(index_md):
        target = m.group(1).strip()
        if not target or not _index_entry_inside_wiki(target, wiki_dir):
            continue
        if target in seen:
            continue
        seen.add(target)
        paths.append(target)
    return paths


def _select_query_candidates(
    paths: WikiPaths,
    question: str,
    max_pages: int,
) -> tuple[str, list[str], dict[str, str]]:
    """Read index.md first, then select top-N relevant linked pages.

    Returns
    -------
    (index_md, pages_loaded, pages_content)
        index_md      — verbatim contents of index.md (for the prompt)
        pages_loaded  — ordered list of wiki-relative paths actually
                        loaded into the prompt
        pages_content — map from path to content for the loaded pages
    """
    wiki_dir = paths.wiki_dir
    index_md = _read_text_or_empty(wiki_dir / "index.md")
    if not index_md:
        return "", [], {}

    # Score each index-linked page by token overlap with the question.
    # Pages not in the index are unreachable.
    question_tokens = _tokenise(question)
    candidate_paths = _extract_index_links(index_md, wiki_dir)

    # One read per page: the text scored here is the text the prompt carries
    # and the text the reply's citations are checked against (FR-014).
    scored: list[tuple[int, str]] = []
    contents: dict[str, str] = {}
    for rel in candidate_paths:
        page_path = wiki_dir / rel
        if not page_path.exists():
            continue
        content = _read_text_or_empty(page_path)
        if not content:
            continue
        # Score = |question_tokens ∩ (slug + path + first-400 tokens)|
        signal: set[str] = {Path(rel).stem.lower()}
        signal |= _tokenise(rel.replace("/", " ").replace("-", " "))
        signal |= _tokenise(content[:400])
        score = len(question_tokens & signal)
        if score > 0:
            scored.append((score, rel))
            contents[rel] = content

    # Stable: highest score first, then path order in the index.
    index_position = {rel: i for i, rel in enumerate(candidate_paths)}
    scored.sort(key=lambda pair: (-pair[0], index_position.get(pair[1], 1_000_000)))

    selected = scored[:max_pages]
    pages_loaded = [rel for _score, rel in selected]
    pages_content = {rel: contents[rel] for rel in pages_loaded}
    return index_md, pages_loaded, pages_content


def _normalise_whitespace(text: str) -> str:
    """Collapse every whitespace run to one space and trim: the comparison form of FR-014."""
    return " ".join(text.split())


def validate_citation_evidence(
    answer: QueryAnswer,
    *,
    index_md: str,
    pages_loaded: list[str],
    pages_content: dict[str, str],
) -> None:
    """Check a reply's citations against the prompt snapshot (FR-014).

    ``index_md`` and ``pages_content`` are the texts that went into the
    prompt. Nothing is reread from disk here, so a page that changed while
    the backend ran can neither fail a quotation of the text the model saw
    nor pass a quotation of text it never saw. Each citation must name
    ``index.md`` or a loaded page and quote text that occurs in that page
    after whitespace normalisation; a non-empty answer needs at least one
    citation; the abstention form (empty answer, one citation quoting
    ``index.md``) passes. The check verifies that the quotation is real,
    not that it supports the answer.

    Raises :class:`ContractViolationError` (exit 4) naming the page.
    """
    if answer.answer.strip() and not answer.citations:
        raise ContractViolationError(
            "query response has a non-empty answer and no citations; an answer "
            "must cite at least one page loaded into the prompt (or index.md) "
            "with a fragment quoted from it."
        )
    snapshot = dict(pages_content)
    snapshot["index.md"] = index_md
    for c in answer.citations:
        if c.page not in snapshot:
            raise ContractViolationError(
                f"query response cites {c.page!r}, which was not in "
                f"the index-first selection. Allowed citations are "
                f"index.md and the pages loaded into the prompt: "
                f"{sorted(pages_loaded)}. The backend may have "
                f"hallucinated this page."
            )
        fragment = _normalise_whitespace(c.fragment)
        if not fragment:
            raise ContractViolationError(
                f"query response cites {c.page!r} with an empty "
                f"fragment; every citation must include a supporting "
                f"text excerpt from the cited page."
            )
        if fragment not in _normalise_whitespace(snapshot[c.page]):
            raise ContractViolationError(
                f"query response cites {c.page!r} with a fragment that does "
                f"not occur in the text of that page as supplied to the "
                f"backend: {c.fragment[:120]!r}. A citation must quote the "
                f"cited page (whitespace runs are collapsed before comparing); "
                f"the backend may have fabricated this evidence."
            )


def compose_query_prompt(
    question: str,
    index_md: str,
    pages_content: dict[str, str],
    schema_files: dict[str, str],
) -> dict[str, Any]:
    """Compose a wiki-aware query prompt.

    The backend is told to:
      - answer using ONLY the pages provided (no fabrication, no
        outside knowledge)
      - return ``answer`` plus ``citations`` (page-path + supporting
        fragment) per page actually consulted
      - return an empty answer with citation to index.md if the wiki
        doesn't contain enough info
    """
    system_instructions = (
        "You are answering a question against a curated project wiki. "
        "Use ONLY the index and pages provided below — do not fabricate "
        "wiki contents, do not draw on outside knowledge. If the "
        "answer is not in the provided material, say so explicitly and "
        "return an empty answer string with one citation pointing at "
        "index.md. Always cite the pages you used; quote a short "
        "fragment from each cited page."
    )
    response_schema = {
        "type": "object",
        "required": ["version", "answer", "citations"],
        "properties": {
            "version": {"type": "integer", "const": 1},
            "answer": {"type": "string"},
            "citations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["page", "fragment"],
                    "properties": {
                        "page": {"type": "string"},
                        "fragment": {"type": "string"},
                    },
                },
            },
        },
    }
    return {
        "version": 1,
        "system_instructions": system_instructions,
        "task": "query",
        "schema_excerpts": {
            "ingest_rules": schema_files.get("ingest-rules", ""),
            "page_types": schema_files.get("page-types", ""),
            "citation_rules": schema_files.get("citation-rules", ""),
        },
        "source": {
            "kind": "query",
            "path": "(question)",
            "content": question,
        },
        "wiki_state": {
            "index_md": index_md,
            "log_md": "",  # query doesn't need the log
            "candidate_pages": dict(pages_content),
        },
        "response_schema": json.dumps(response_schema),
    }


def parse_query_response(raw: str | dict) -> QueryAnswer:
    """Parse a backend's query response into a QueryAnswer."""
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ContractViolationError(
                f"query response not valid JSON: {exc}\n  stdout (first 500 chars): {raw[:500]!r}"
            ) from exc
    else:
        data = raw

    if not isinstance(data, dict):
        raise ContractViolationError(f"query response must be an object, got {type(data).__name__}")
    for required in ("version", "answer", "citations"):
        if required not in data:
            raise ContractViolationError(f"query response missing required key: {required!r}")
    if data["version"] != 1:
        raise ContractViolationError(f"query response.version must be 1, got {data['version']!r}")
    if not isinstance(data["answer"], str):
        raise ContractViolationError("query response.answer must be a string")
    if not isinstance(data["citations"], list):
        raise ContractViolationError("query response.citations must be an array")
    citations: list[Citation] = []
    for c in data["citations"]:
        if not isinstance(c, dict) or "page" not in c or "fragment" not in c:
            raise ContractViolationError(f"query response citation missing keys: {c!r}")
        citations.append(Citation(page=str(c["page"]), fragment=str(c["fragment"])))
    return QueryAnswer(
        answer=data["answer"],
        citations=citations,
        pages_loaded=[],  # filled in by the orchestrator from selection
    )


@runtime_checkable
class Querier(Protocol):
    def query(self, question: str) -> QueryAnswer: ...
    def query_with_file_back(self, question: str) -> tuple[QueryAnswer, WikiPatchSet]: ...


@dataclass
class DefaultQuerier:
    """Default index-first querier.

    Reads index.md, selects top-N relevant linked pages, composes a
    query prompt, invokes the backend, parses the response, logs the
    pages-loaded set for audit.
    """

    backend: Backend
    paths: WikiPaths
    max_pages: int = DEFAULT_MAX_QUERY_PAGES

    def query(self, question: str) -> QueryAnswer:
        index_md, pages_loaded, pages_content = _select_query_candidates(
            paths=self.paths,
            question=question,
            max_pages=self.max_pages,
        )
        if not index_md:
            raise SourceMissingError(
                f"{self.paths.wiki_label}/index.md not found; cannot run query (index is the navigation primitive)."
            )

        schema_files = load_schema_files(self.paths)
        prompt = compose_query_prompt(
            question=question,
            index_md=index_md,
            pages_content=pages_content,
            schema_files=schema_files,
        )

        try:
            response = self.backend.call(prompt)
        except BackendInvocationError:
            raise
        except Exception as exc:
            raise BackendInvocationError(f"query backend raised an unexpected error: {exc}") from exc

        answer = parse_query_response(response)

        # The evidence check runs against the snapshot the prompt carried
        # (index_md, pages_content), never against files reread now: a
        # fabricated page, a fabricated quotation or an answer with no
        # citation is rejected fail-fast (FR-014).
        validate_citation_evidence(
            answer,
            index_md=index_md,
            pages_loaded=pages_loaded,
            pages_content=pages_content,
        )

        # Re-pack with the pages_loaded list filled in by selection.
        answer = QueryAnswer(
            answer=answer.answer,
            citations=answer.citations,
            pages_loaded=pages_loaded,
        )
        self._append_query_log(question, answer)
        return answer

    def query_with_file_back(self, question: str) -> tuple[QueryAnswer, WikiPatchSet]:
        """Query and additionally generate a patch-set capturing the answer.

        Synthesises a source from the question + answer text, then
        runs the multi-page ingestor over it. Curator reviews the
        patch-set and runs ``wiki promote`` to land it.
        """
        answer = self.query(question)
        if not answer.answer:
            # Empty answer — nothing to file back. Return an empty
            # patch-set so the caller can no-op gracefully.
            empty = WikiPatchSet(
                edits=[],
                source_path="(query)",
                backend="(query)",
                rationale="Query returned no answer; nothing to file back.",
            )
            return answer, empty

        synthetic_source = (
            "# " + question + "\n\n"
            "Answer (synthesised from a `wiki query --file-back` invocation):\n\n" + answer.answer + "\n\n"
            "Citations:\n" + "\n".join(f"- `{c.page}` — {c.fragment}" for c in answer.citations) + "\n"
        )
        # Write the synthetic source to a tempfile so the multi-ingestor
        # treats it as a real file path.
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            prefix="wiki-query-fileback-",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(synthetic_source)
            synthetic_path = Path(f.name)

        try:
            multi = DefaultMultiIngestor(backend=self.backend, paths=self.paths)
            req = IngestRequest(
                source_path=synthetic_path,
                source_kind="file",
                backend_name="(query --file-back)",
            )
            patch = multi.ingest_multi(req)
        finally:
            synthetic_path.unlink(missing_ok=True)

        return answer, patch

    def _append_query_log(self, question: str, answer: QueryAnswer) -> None:
        """Append one JSONL line to the query log (``paths.query_log``)."""
        log_path = self.paths.query_log
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "ts": datetime.datetime.now().isoformat(timespec="seconds"),
                "question": question,
                "pages_loaded": answer.pages_loaded,
                "citations": [{"page": c.page, "fragment": c.fragment} for c in answer.citations],
                "answer_chars": len(answer.answer),
            }
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            # Logging is best-effort — never block a query on a log
            # failure (the answer has already been computed).
            pass
