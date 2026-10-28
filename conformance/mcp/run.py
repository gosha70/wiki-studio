# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The MCP conformance suite for a wiki-studio tool server (0.8.0, FR-043, FR-045).

Two commands:

``python -m conformance.mcp.run --server-cmd "COMMAND" [--protocol-version V]... [--trace PATH]``
    Copies ``fixture/`` into a temporary root, launches ``COMMAND`` over stdio
    through the MCP SDK's client and runs the twelve cases once per tested
    protocol version: ``2025-06-18`` and ``2025-11-25`` by the initialize
    handshake, ``2026-07-28`` by the per-request envelope (``server/discover``).
    ``{root}`` in ``COMMAND`` is replaced by the temporary project root; the
    server also starts with that root as its working directory and as
    ``WIKI_STUDIO_ROOT``. ``--trace PATH`` adds ``--trace PATH`` to every launch.
    Exit 0 when every case passes, 1 when one fails, 2 when the suite cannot run.

``python -m conformance.mcp.run check-host-run --run DIR [--record]``
    Applies cases 2-9 to a recorded host run (``conformance/runs/README.md``):
    its trace and the fixture's end state, never the transcript. Each case is
    labelled ``proved`` (by the trace's evidence lines),
    ``proved-by-end-state`` (the end state is needed too) or
    ``not-provable-from-host-run (protocol suite)`` (the trace lacks the
    scenario step that would show it; counted as skipped, never as passed),
    and the verdict names the cases the run proves. ``--record`` writes the
    verdict into the run's ``manifest.json``.

``python -m conformance.mcp.run tree-hash DIR``
    Prints the tree hash ``check-host-run`` compares with ``end_state_sha256``.

Adapter-agnostic: nothing here imports ``wiki_studio``. The end state is read
from disk, and the server is any command that speaks MCP over stdio. The
suite itself needs the ``mcp`` SDK; ``check-host-run`` needs only the
standard library.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import dataclasses
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest import mock

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Iterator

HERE = Path(__file__).resolve().parent
FIXTURE_DIR = HERE / "fixture"
FIXTURE_PROJECT = FIXTURE_DIR / "project"
VARIANT_DEFAULT = "default"
VARIANT_AUTO_APPROVE = "auto-approve"
MANIFEST_NAME = ".wiki-studio.json"
RELAY = HERE / "relay.py"
STUB_BACKEND = HERE / "stub-backend.sh"
SCENARIO = HERE / "scenario.md"

# D17: two handshake versions and one per-request ("modern") version.
HANDSHAKE_VERSIONS = ("2025-06-18", "2025-11-25")
MODERN_VERSIONS = ("2026-07-28",)
TESTED_VERSIONS = (*HANDSHAKE_VERSIONS, *MODERN_VERSIONS)

# The tool contract (FR-035, FR-036).
TOOL_FIND = "find"
TOOL_READ_PAGE = "read_page"
TOOL_PROPOSE = "propose"
TOOL_PROMOTE = "promote"
TOOL_LINT = "lint"
TOOL_INFO = "info"
TOOL_FINDINGS = "findings"
TOOL_REVIEW_STATE = "review_state"
TOOL_NAMES = (
    TOOL_FIND,
    TOOL_READ_PAGE,
    TOOL_PROPOSE,
    TOOL_PROMOTE,
    TOOL_LINT,
    TOOL_INFO,
    TOOL_FINDINGS,
    TOOL_REVIEW_STATE,
)
FORBIDDEN_PROPERTIES = frozenset(
    {
        "root",
        "wiki_dir",
        "proposals_dir",
        "backend",
        "by",
        "actor",
        "allow_out_of_repo",
        "allow_unguarded_updates",
        "entry_point",
        "lock_timeout",
        "ranker_config",
    }
)
MAX_FIND_PAGES = 5

# The fixture's layout and the facts the cases check against.
WIKI_REL = "knowledge/wiki"
PROPOSALS_REL = "doc_internal/proposals"
APPLIED_DIR = ".applied"
RECEIPT_FILE = "receipt.json"
RECEIPT_COMMITTED = "committed"
ENTRY_POINT_MCP = "mcp"
APPROVALS_REL = ".audit/approvals"
STATE_APPROVED = "approved"
# Files the server may create beside the wiki (its lock and search cache), outside the end-state comparison.
DERIVED_PREFIX = ".wiki.wiki-studio."
KNOWN_PAGE = "decisions/retry-policy.md"
KNOWN_SHA256 = "f736f09dcba9d4c1ef8b70f7e901f4fbbc2b7ff7eaeedc5acc03179e6c560304"
FIND_QUESTION = "retry backoff"
PAGE_ID_RE = re.compile(r"^page_id: pg-[0-9a-f]{32}$", re.MULTILINE)
INDEX_LINK_RE = re.compile(r"\]\(([^)\s]+\.md)\)")
EXIT_PATH_OUTSIDE_ROOT = 7
EXIT_PROMOTE_VALIDATION = 9
# A ValueError error result (FR-039's name rule among them) and the error name the trace records for it.
EXIT_VALUE_ERROR = 1
ERROR_VALUE_ERROR = "ValueError"
# How the MCP SDK refuses a call to a tool that is not registered ("Unknown tool: <name>", as an error result).
UNKNOWN_TOOL_RE = re.compile(r"unknown tool", re.IGNORECASE)

# The launch environment.
ENV_PREFIX = "WIKI_STUDIO_"
ENV_ROOT = "WIKI_STUDIO_ROOT"
ENV_ACTOR = "WIKI_STUDIO_ACTOR"
ENV_BACKEND = "WIKI_STUDIO_BACKEND"
ENV_STUB_LOG = "CONFORMANCE_STUB_LOG"
STUB_BACKEND_NAME = "claude"
LAUNCH_ACTOR = "conformance-agent"
ROOT_PLACEHOLDER = "{root}"
DISABLE_PROMOTE = ("--disable-tool", TOOL_PROMOTE)
SESSION_TIMEOUT_SECONDS = 180

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_CANNOT_RUN = 2
SDK_MISSING = "the conformance suite needs the MCP SDK: pip install 'mcp>=2.3,<3' (or 'wiki-studio[mcp]')"

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

CASES = {
    1: "negotiate",
    2: "tool surface",
    3: "find",
    4: "read_page",
    5: "propose",
    6: "promote",
    7: "guarded update",
    8: "promote name containment",
    9: "no approval by default",
    10: "auto-approval by policy",
    11: "lint makes no backend call",
    12: "clean stdout",
}
HOST_RUN_CASES = (2, 3, 4, 5, 6, 7, 8, 9)

PAGE_TEMPLATE = (
    "---\npage_type: decision\nslug: {slug}\ntitle: {title}\nstatus: stable\nlast_reviewed: 2026-10-27\n"
    'sources:\n  - url: "https://example.com/{slug}"\n    retrieved: 2026-10-27\n---\n\n# {title}\n\n'
    "## Decision\n\n{body}\n\n## Context\n\nAgreed in review.\n\n## Alternatives considered\n\nNone.\n\n"
    "## Consequences\n\nCallers wait less.\n"
)
CREATE_SLUG = "backoff-ceiling"
DECOY_SLUG = "decoy-policy"
AUTO_SLUG = "approved-by-policy"
UPDATE_MARKER = "Retry at most five times, starting at 250 ms."
HAND_EDIT_MARKER = "Changed by hand outside the server."
STALE_MARKER = "A draft from before the hand edit."


class CaseFailureError(Exception):
    """One check of a case did not hold."""


class SuiteError(Exception):
    """The suite cannot run (no SDK, a bad argument, a missing fixture)."""


def check(condition: object, message: str) -> None:
    if not condition:
        raise CaseFailureError(message)


def page_path(slug: str) -> str:
    return f"decisions/{slug}.md"


def page_text(slug: str, body: str = "Cap the backoff at 8 s.") -> str:
    return PAGE_TEMPLATE.format(slug=slug, title=slug.replace("-", " ").title(), body=body)


def create_edits(slug: str) -> list[dict[str, Any]]:
    rel = page_path(slug)
    return [
        {"path": rel, "action": "create", "content": page_text(slug)},
        {"path": "index.md", "action": "append-index", "content": f"- [{slug}]({rel})"},
    ]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def snapshot(directory: Path) -> dict[str, str]:
    """Every entry under ``directory`` by relative path: a file's sha256, a symlink's target."""
    out: dict[str, str] = {}
    if not directory.is_dir():
        return out
    for path in sorted(directory.rglob("*")):
        rel = path.relative_to(directory).as_posix()
        if path.is_symlink():
            out[rel] = "symlink:" + os.readlink(path)
        elif path.is_file():
            out[rel] = sha256_bytes(path.read_bytes())
    return out


def tree_sha256(directory: Path) -> str:
    """One sha256 over :func:`snapshot` (canonical JSON), the end-state hash of a recorded run."""
    canonical = json.dumps(snapshot(directory), sort_keys=True, separators=(",", ":"))
    return sha256_bytes(canonical.encode("utf-8"))


def index_links(index: Path) -> set[str]:
    return set(INDEX_LINK_RE.findall(index.read_text(encoding="utf-8")))


def copy_fixture(destination: Path, variant: str) -> Path:
    """The fixture project under ``destination`` with ``variant``'s manifest; returns the project root."""
    manifest = FIXTURE_DIR / "variants" / variant / MANIFEST_NAME
    if not FIXTURE_PROJECT.is_dir() or not manifest.is_file():
        raise SuiteError(f"the fixture is incomplete: {FIXTURE_PROJECT} and {manifest} are required")
    root = destination / "project"
    shutil.copytree(FIXTURE_PROJECT, root)
    shutil.copyfile(manifest, root / WIKI_REL / MANIFEST_NAME)
    return root


# ── Results ──────────────────────────────────────────────────


@dataclasses.dataclass
class CaseResult:
    version: str
    number: int
    status: str
    detail: str = ""
    proof: str = ""  # a host-run case's proof label; empty for the suite's own cases

    def line(self) -> str:
        label = f"[{self.version}] {self.number:02d} {CASES[self.number]}"
        proof = f" [{self.proof}]" if self.proof else ""
        return f"{self.status}  {label}{proof}" + (f": {self.detail}" if self.detail else "")


@dataclasses.dataclass
class ToolCall:
    """One ``tools/call``: an error result, a raised protocol error, or a result payload.

    ``text`` is the result's first text block as sent (the SDK's own errors
    are plain text, not a JSON object); ``payload`` is that text as a JSON
    object when it is one, else ``structuredContent``.
    """

    is_error: bool
    payload: dict[str, Any] | None
    raised: str | None = None
    text: str | None = None

    @property
    def exit_code(self) -> int | None:
        return None if self.payload is None else self.payload.get("exit_code")

    @property
    def refusal(self) -> str:
        """What the call gave, for a failure message."""
        return str(self.raised or self.payload or self.text)

    def ok(self, what: str) -> dict[str, Any]:
        check(not self.is_error and self.payload is not None, f"{what} failed: {self.refusal}")
        assert self.payload is not None
        return self.payload

    def is_unknown_tool_error(self) -> bool:
        """The SDK's refusal of a tool that is not registered: an error naming an unknown tool, with no payload.

        A wiki-studio error result (``{error, exit_code, message}``) means the
        tool ran, so it is not this.
        """
        return self.is_error and self.payload is None and bool(UNKNOWN_TOOL_RE.search(self.text or self.raised or ""))


# ── The SDK session ──────────────────────────────────────────


@dataclasses.dataclass
class Launch:
    """One server process: its command, root, environment and the record of its stdout."""

    argv: list[str]
    root: Path
    env: dict[str, str]
    stdout_record: Path
    stderr_log: Path


def _require_sdk() -> None:
    try:
        import mcp  # noqa: F401
    except ImportError as exc:
        raise SuiteError(SDK_MISSING) from exc


@contextlib.contextmanager
def _pinned(module: Any, name: str, version: str) -> Iterator[None]:
    """Make the SDK client propose ``version`` (it otherwise proposes its latest one)."""
    if not hasattr(module, name):
        raise CaseFailureError(f"the SDK client has no {name}; this SDK cannot be pinned to {version}")
    with mock.patch.object(module, name, version):
        yield


async def _negotiate(session: Any, version: str) -> str | None:
    from mcp.client import session as session_module

    if version in MODERN_VERSIONS:
        with _pinned(session_module, "LATEST_MODERN_VERSION", version):
            await session.discover()
    else:
        with _pinned(session_module, "LATEST_HANDSHAKE_VERSION", version):
            await session.initialize()
    negotiated = session.protocol_version
    return negotiated if isinstance(negotiated, str) else None


async def _call(session: Any, name: str, arguments: dict[str, Any]) -> ToolCall:
    try:
        result = await session.call_tool(name, arguments)
    except Exception as exc:  # an unknown tool may be a protocol error rather than an error result
        return ToolCall(is_error=True, payload=None, raised=f"{type(exc).__name__}: {exc}")
    data = result.model_dump(by_alias=True, exclude_none=True)
    payload: dict[str, Any] | None = None
    text: str | None = None
    for block in data.get("content") or []:
        if block.get("type") == "text":
            text = str(block.get("text", ""))
            with contextlib.suppress(ValueError):
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    payload = parsed
            break
    if payload is None and isinstance(data.get("structuredContent"), dict):
        payload = data["structuredContent"]
    return ToolCall(is_error=bool(data.get("isError")), payload=payload, text=text)


async def _list_tools(session: Any) -> list[dict[str, Any]]:
    return [tool.model_dump(by_alias=True, exclude_none=True) for tool in (await session.list_tools()).tools]


def _answered(record: Path) -> bool:
    """Whether the server wrote at least one JSON-RPC response (a refusal is an answer; a crash is not)."""
    if not record.exists():
        return False
    for line in record.read_bytes().split(b"\n"):
        with contextlib.suppress(ValueError):
            message = json.loads(line)
            if isinstance(message, dict) and ("result" in message or "error" in message):
                return True
    return False


class Negotiation:
    """What the handshake or discovery gave: the version, or a clean refusal, or a failure."""

    def __init__(self, negotiated: str | None = None, refused: str | None = None, failed: str | None = None) -> None:
        self.negotiated = negotiated
        self.refused = refused
        self.failed = failed


async def _session(launch: Launch, version: str, body: Callable[[Any], Coroutine[Any, Any, None]]) -> Negotiation:
    """Launch the server through the relay, negotiate ``version`` and run ``body`` when it was agreed."""
    from mcp import ClientSession, StdioServerParameters, stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=[str(RELAY), str(launch.stdout_record), "--", *launch.argv],
        env=launch.env,
        cwd=str(launch.root),
    )
    with open(launch.stderr_log, "a", encoding="utf-8") as errlog:
        async with stdio_client(params, errlog=errlog) as (read, write), ClientSession(read, write) as session:
            try:
                negotiated = await _negotiate(session, version)
            except CaseFailureError as exc:
                return Negotiation(failed=str(exc))
            except Exception as exc:  # the server refused the version with a protocol error
                return Negotiation(refused=f"{type(exc).__name__}: {exc}")
            if negotiated != version:
                return Negotiation(negotiated=negotiated, refused=f"the server offered {negotiated}")
            await body(session)
            return Negotiation(negotiated=negotiated)


# ── The suite ────────────────────────────────────────────────


class VersionRun:
    """The twelve cases for one protocol version, over three fresh fixture copies."""

    def __init__(self, version: str, server_cmd: list[str], base: Path, trace: Path | None) -> None:
        self.version = version
        self.server_cmd = server_cmd
        self.base = base
        self.trace = trace
        self.results: dict[int, CaseResult] = {}
        self.records: list[Path] = []
        self.negotiated = False  # whether the server agreed to this version (a clean refusal leaves it False)
        self.stub_log = base / "stub-backend.log"
        self.stub_bin = base / "bin"
        self._install_stub()

    def _install_stub(self) -> None:
        self.stub_bin.mkdir()
        target = self.stub_bin / STUB_BACKEND_NAME
        shutil.copyfile(STUB_BACKEND, target)
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def launch(self, label: str, variant: str, *extra: str) -> Launch:
        root = copy_fixture(self.base / label, variant)
        argv = [part.replace(ROOT_PLACEHOLDER, str(root)) for part in self.server_cmd] + list(extra)
        if self.trace is not None:
            argv += ["--trace", str(self.trace)]
        env = {key: value for key, value in os.environ.items() if not key.startswith(ENV_PREFIX)}
        env.update(
            {
                ENV_ROOT: str(root),
                ENV_ACTOR: LAUNCH_ACTOR,
                ENV_BACKEND: STUB_BACKEND_NAME,
                ENV_STUB_LOG: str(self.stub_log),
                "PATH": os.pathsep.join([str(self.stub_bin), env.get("PATH", "")]),
            }
        )
        record = self.base / f"{label}.stdout"
        self.records.append(record)
        return Launch(argv=argv, root=root, env=env, stdout_record=record, stderr_log=self.base / f"{label}.stderr")

    def record(self, number: int, status: str, detail: str = "") -> None:
        self.results[number] = CaseResult(self.version, number, status, detail)

    async def run_case(self, number: int, case: Callable[[], Coroutine[Any, Any, str | None]]) -> None:
        try:
            detail = await case()
        except CaseFailureError as exc:
            self.record(number, FAIL, str(exc))
        except Exception as exc:
            self.record(number, FAIL, f"{type(exc).__name__}: {exc}")
        else:
            self.record(number, PASS, detail or "")

    async def run(self) -> list[CaseResult]:
        main = self.launch("main", VARIANT_DEFAULT)
        negotiation = await self._guarded(main, self._main_cases(main))
        if negotiation.failed is not None:
            self.record(1, FAIL, negotiation.failed)
        elif negotiation.refused is not None:
            if not _answered(main.stdout_record):
                self.record(1, FAIL, f"no response from the server ({negotiation.refused}); see {main.stderr_log}")
                return self.ordered()
            self.record(1, PASS, f"refused cleanly ({negotiation.refused})")
            for number in CASES:
                if number != 1:
                    self.record(number, SKIP, "the server does not speak this version")
            return self.ordered()
        else:
            self.negotiated = True
            propose_only = self.launch("propose-only", VARIANT_DEFAULT, *DISABLE_PROMOTE)
            second = await self._guarded(propose_only, self._propose_only_cases(propose_only))
            auto = self.launch("auto-approve", VARIANT_AUTO_APPROVE)
            third = await self._guarded(auto, self._auto_approve_cases(auto))
            failures = [n.failed or n.refused for n in (second, third) if n.failed or n.refused]
            if failures:
                self.record(1, FAIL, "; ".join(str(f) for f in failures))
            else:
                self.record(1, PASS, f"negotiated {self.version} in three sessions")
        await self.run_case(12, self.case_clean_stdout)
        for number in CASES:
            self.results.setdefault(number, CaseResult(self.version, number, FAIL, "not reached"))
        return self.ordered()

    def ordered(self) -> list[CaseResult]:
        return [self.results[number] for number in sorted(self.results)]

    async def _guarded(self, launch: Launch, body: Callable[[Any], Coroutine[Any, Any, None]]) -> Negotiation:
        try:
            return await asyncio.wait_for(_session(launch, self.version, body), SESSION_TIMEOUT_SECONDS)
        except Exception as exc:
            stderr = (
                launch.stderr_log.read_text(encoding="utf-8", errors="replace") if launch.stderr_log.exists() else ""
            )
            tail = stderr.strip().splitlines()[-3:]
            return Negotiation(failed=f"session failed: {type(exc).__name__}: {exc} {' | '.join(tail)}".strip())

    # The default-policy session: cases 2 (surface), 3-9 and 11.

    def _main_cases(self, launch: Launch) -> Callable[[Any], Coroutine[Any, Any, None]]:
        root = launch.root
        wiki = root / WIKI_REL

        async def body(session: Any) -> None:
            state: dict[str, Any] = {}

            async def surface() -> str:
                tools = await _list_tools(session)
                names = sorted(tool["name"] for tool in tools)
                check(names == sorted(TOOL_NAMES), f"tools/list is {names}, expected the eight")
                for tool in tools:
                    properties = set((tool.get("inputSchema") or {}).get("properties") or {})
                    bad = sorted(properties & FORBIDDEN_PROPERTIES)
                    check(not bad, f"{tool['name']} takes forbidden arguments {bad}")
                return "the eight tools, no forbidden argument"

            async def find() -> str:
                linked = index_links(wiki / "index.md")
                for max_pages in (MAX_FIND_PAGES, 1):
                    result = (await _call(session, TOOL_FIND, {"question": FIND_QUESTION, "max_pages": max_pages})).ok(
                        "find"
                    )
                    pages = [page["path"] for page in result.get("pages", [])]
                    check(len(pages) <= max_pages, f"find returned {len(pages)} pages for max_pages {max_pages}")
                    check(set(pages) <= linked, f"find returned pages not linked from index.md: {pages}")
                    check(
                        isinstance(result.get("bytes_loaded"), int) and result["bytes_loaded"] <= result["max_bytes"],
                        f"bytes_loaded {result.get('bytes_loaded')} exceeds max_bytes {result.get('max_bytes')}",
                    )
                    check(isinstance(result.get("ranker"), str) and result["ranker"], "find does not name its ranker")
                check(KNOWN_PAGE in pages, f"find '{FIND_QUESTION}' did not select {KNOWN_PAGE}")
                return f"ranker {result['ranker']}, {len(pages)} page(s)"

            async def read_page() -> str:
                result = (await _call(session, TOOL_READ_PAGE, {"path": KNOWN_PAGE})).ok("read_page")
                data = (wiki / KNOWN_PAGE).read_bytes()
                check(
                    result.get("sha256") == sha256_bytes(data) == KNOWN_SHA256, "read_page's sha256 is not the file's"
                )
                check(result.get("content") == data.decode("utf-8"), "read_page's content is not the file's text")
                (root / "outside.md").write_text("outside the wiki\n", encoding="utf-8")
                link = wiki / "decisions" / "escape.md"
                link.symlink_to(root / "outside.md")
                try:
                    for bad in (str(wiki / KNOWN_PAGE), "../outside.md", "decisions/escape.md"):
                        call = await _call(session, TOOL_READ_PAGE, {"path": bad})
                        check(
                            call.is_error and call.exit_code == EXIT_PATH_OUTSIDE_ROOT,
                            f"read_page {bad!r} gave {call.raised or call.payload}, expected exit 7",
                        )
                finally:
                    link.unlink()
                return "sha256 matches; absolute, ../ and symlink refused with exit 7"

            async def propose() -> str:
                before = snapshot(wiki)
                result = (
                    await _call(session, TOOL_PROPOSE, {"edits": create_edits(CREATE_SLUG), "name": "conf-create"})
                ).ok("propose")
                proposal = (root / str(result.get("proposal_dir"))).resolve()
                check(proposal.is_dir(), f"no proposal at {result.get('proposal_dir')}")
                check(
                    proposal.parent == (root / PROPOSALS_REL).resolve(), "the proposal is not under the proposals dir"
                )
                check(snapshot(wiki) == before, "propose changed the wiki")
                carriers = [
                    p for p in proposal.rglob("*") if p.is_file() and p.as_posix().endswith(page_path(CREATE_SLUG))
                ]
                check(
                    any(PAGE_ID_RE.search(p.read_text(encoding="utf-8")) for p in carriers),
                    "the create carries no page_id of the form pg-<32 hex>",
                )
                state["created"] = result["name"]
                return f"proposal {result['name']} with a page_id; wiki unchanged"

            async def promote() -> str:
                name = str(state.get("created") or "")
                check(name, "no proposal from case 5")
                result = (await _call(session, TOOL_PROMOTE, {"name": name})).ok("promote")
                check(page_path(CREATE_SLUG) in result.get("applied_paths", []), "the created page was not applied")
                archive = root / str(result.get("archived_dir"))
                receipt = json.loads((archive / RECEIPT_FILE).read_text(encoding="utf-8"))
                check(receipt.get("state") == RECEIPT_COMMITTED, f"receipt state {receipt.get('state')}")
                check(not (root / PROPOSALS_REL / name).exists(), "the proposal was not archived")
                check((wiki / page_path(CREATE_SLUG)).is_file(), "the page is not in the wiki")
                return f"committed receipt in {result['archived_dir']}"

            async def guarded_update() -> str:
                base = (await _call(session, TOOL_READ_PAGE, {"path": KNOWN_PAGE})).ok("read_page")["sha256"]
                edit = {"path": KNOWN_PAGE, "action": "update", "content": page_text("retry-policy", UPDATE_MARKER)}
                (
                    await _call(
                        session, TOOL_PROPOSE, {"edits": [{**edit, "base_sha256": base}], "name": "conf-update"}
                    )
                ).ok("propose update")
                (await _call(session, TOOL_PROMOTE, {"name": "conf-update"})).ok("promote update")
                check(UPDATE_MARKER in (wiki / KNOWN_PAGE).read_text(encoding="utf-8"), "the update did not land")
                current = (await _call(session, TOOL_READ_PAGE, {"path": KNOWN_PAGE})).ok("read_page")["sha256"]
                stale = {"path": KNOWN_PAGE, "action": "update", "content": page_text("retry-policy", STALE_MARKER)}
                (
                    await _call(
                        session, TOOL_PROPOSE, {"edits": [{**stale, "base_sha256": current}], "name": "conf-stale"}
                    )
                ).ok("propose stale update")
                (wiki / KNOWN_PAGE).write_text(page_text("retry-policy", HAND_EDIT_MARKER), encoding="utf-8")
                before = snapshot(wiki)
                call = await _call(session, TOOL_PROMOTE, {"name": "conf-stale"})
                check(
                    call.is_error and call.exit_code == EXIT_PROMOTE_VALIDATION,
                    f"the stale update gave {call.raised or call.payload}, expected exit 9",
                )
                check(snapshot(wiki) == before, "the refused promote changed the wiki")
                return "fresh update landed; stale update refused with exit 9, wiki unchanged"

            async def containment() -> str:
                (await _call(session, TOOL_PROPOSE, {"edits": create_edits(DECOY_SLUG), "name": "conf-decoy"})).ok(
                    "propose decoy"
                )
                decoy = root / PROPOSALS_REL / "conf-decoy"
                outside = (root / PROPOSALS_REL).parent / "x"
                decoy.rename(outside)
                before = snapshot(wiki)
                for name in ("../x", str(outside)):
                    call = await _call(session, TOOL_PROMOTE, {"name": name})
                    check(call.is_error, f"promote {name!r} was not refused: {call.payload}")
                check(snapshot(wiki) == before, "a refused promote changed the wiki")
                check(not (outside / RECEIPT_FILE).exists(), "the proposal outside the proposals dir was touched")
                return "../x and an absolute name refused; the decoy outside was not promoted"

            async def not_approved() -> str:
                result = (await _call(session, TOOL_REVIEW_STATE, {"pages": [page_path(CREATE_SLUG)]})).ok(
                    "review_state"
                )
                states = result.get("states", [])
                check(len(states) == 1, f"review_state returned {states}")
                check(states[0].get("state") != STATE_APPROVED, "the agent's promote approved the page")
                return f"state {states[0].get('state')}"

            async def lint_no_backend() -> str:
                result = (await _call(session, TOOL_LINT, {"health": True})).ok("lint")
                check(isinstance(result.get("passed"), bool), "lint has no passed flag")
                check(not self.stub_log.exists(), "lint with health invoked the backend")
                return "no backend invocation recorded"

            for number, case in (
                (2, surface),
                (3, find),
                (4, read_page),
                (5, propose),
                (6, promote),
                (7, guarded_update),
                (8, containment),
                (9, not_approved),
                (11, lint_no_backend),
            ):
                await self.run_case(number, case)

        return body

    def _propose_only_cases(self, launch: Launch) -> Callable[[Any], Coroutine[Any, Any, None]]:
        async def body(session: Any) -> None:
            if self.results.get(2, CaseResult(self.version, 2, FAIL)).status != PASS:
                return
            try:
                names = sorted(tool["name"] for tool in await _list_tools(session))
                expected = sorted(name for name in TOOL_NAMES if name != TOOL_PROMOTE)
                check(names == expected, f"with --disable-tool promote tools/list is {names}")
                call = await _call(session, TOOL_PROMOTE, {"name": "anything"})
                check(
                    call.is_unknown_tool_error(),
                    f"promote with --disable-tool promote gave {call.refusal}, expected the SDK's unknown-tool error",
                )
                calls: dict[str, dict[str, Any]] = {
                    TOOL_FIND: {"question": FIND_QUESTION},
                    TOOL_READ_PAGE: {"path": KNOWN_PAGE},
                    TOOL_PROPOSE: {"edits": create_edits("propose-only"), "name": "conf-propose-only"},
                    TOOL_LINT: {},
                    TOOL_INFO: {},
                    TOOL_FINDINGS: {},
                    TOOL_REVIEW_STATE: {},
                }
                for name, arguments in calls.items():
                    (await _call(session, name, arguments)).ok(f"{name} in propose-only mode")
            except CaseFailureError as exc:
                self.record(2, FAIL, f"propose-only mode: {exc}")
            else:
                self.record(2, PASS, self.results[2].detail + "; propose-only mode lacks promote, the seven work")

        return body

    def _auto_approve_cases(self, launch: Launch) -> Callable[[Any], Coroutine[Any, Any, None]]:
        wiki = launch.root / WIKI_REL

        async def body(session: Any) -> None:
            async def auto_approval() -> str:
                (await _call(session, TOOL_PROPOSE, {"edits": create_edits(AUTO_SLUG), "name": "conf-auto"})).ok(
                    "propose"
                )
                result = (await _call(session, TOOL_PROMOTE, {"name": "conf-auto"})).ok("promote")
                check(page_path(AUTO_SLUG) in result.get("approved_paths", []), "the page is not in approved_paths")
                check(
                    any("auto_approve_on_promote" in warning for warning in result.get("warnings", [])),
                    "no warning names the auto_approve_on_promote policy",
                )
                records = [
                    json.loads(p.read_text(encoding="utf-8"))
                    for p in sorted((wiki / APPROVALS_REL).rglob("*.json"))
                    if p.is_file()
                ]
                approvers = [(r.get("approver") or {}).get("name") for r in records]
                check(approvers and set(approvers) == {LAUNCH_ACTOR}, f"approval records name {approvers}")
                return f"approved by policy, approver {LAUNCH_ACTOR}"

            await self.run_case(10, auto_approval)

        return body

    async def case_clean_stdout(self) -> str:
        frames = 0
        for record in self.records:
            check(record.exists() and record.stat().st_size, f"{record.name}: the server wrote nothing to stdout")
            for line in record.read_bytes().split(b"\n"):
                if not line.strip():
                    continue
                try:
                    message = json.loads(line)
                except ValueError:
                    raise CaseFailureError(f"{record.name}: a stdout line is not JSON: {line[:80]!r}") from None
                items = message if isinstance(message, list) else [message]
                check(
                    all(isinstance(item, dict) and item.get("jsonrpc") == "2.0" for item in items),
                    f"{record.name}: a stdout line is not a JSON-RPC frame: {line[:80]!r}",
                )
                frames += len(items)
        return f"{frames} frames, nothing else"


async def run_suite(server_cmd: list[str], versions: list[str], trace: Path | None) -> list[CaseResult]:
    """Every case for every version; a server that negotiates none of the versions fails case 1 for each of them."""
    runs: list[VersionRun] = []
    with tempfile.TemporaryDirectory(prefix="wiki-studio-conformance-") as tmp:
        for version in versions:
            base = Path(tmp).resolve() / version
            base.mkdir()
            version_run = VersionRun(version, server_cmd, base, trace)
            await version_run.run()
            runs.append(version_run)
    if not any(version_run.negotiated for version_run in runs):
        for version_run in runs:
            first = version_run.results[1]
            if first.status == PASS:
                version_run.record(1, FAIL, f"the server negotiated none of {', '.join(versions)}: {first.detail}")
    return [result for version_run in runs for result in version_run.ordered()]


# ── check-host-run ───────────────────────────────────────────

HOST_MANIFEST_KEYS = (
    "claude_code_version",
    "model",
    "wiki_studio_commit",
    "wiki_studio_version",
    "mcp_version",
    "protocol_version",
    "scenario_sha256",
    "end_state_sha256",
)
RUN_MANIFEST = "manifest.json"
RUN_TRACE = "trace.jsonl"
RUN_END_STATE = "end-state"
TRACE_KEYS = (
    "ts",
    "method",
    "tool",
    "protocol_version",
    "client_name",
    "client_version",
    "outcome",
    "duration_ms",
    "tool_names",
    "unknown_tool_names",
    "arg_keys",
    "unknown_arg_keys",
    "result_keys",
    "unknown_result_keys",
    "summary",
)
METHOD_LIST = "tools/list"
METHOD_CALL = "tools/call"
# What proves a host-run case: the trace's evidence lines, the end state as well, or nothing in the scenario.
PROOF_TRACE = "proved"
PROOF_END_STATE = "proved-by-end-state"
PROOF_NONE = "not-provable-from-host-run (protocol suite)"
PROOF_FAILED = "not proved"
INDEX_PAGES = ("index.md", "log.md")


def _first(calls: list[tuple[int, dict[str, Any]]], tool: str, after: int = -1) -> int | None:
    """The trace position of the first successful call of ``tool`` after position ``after``."""
    for position, record in calls:
        if position > after and record.get("tool") == tool and record.get("outcome") == 0:
            return position
    return None


def _summary(record: dict[str, Any]) -> dict[str, Any]:
    summary = record.get("summary")
    return summary if isinstance(summary, dict) else {}


def _int(summary: dict[str, Any], key: str) -> int:
    value = summary.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise CaseFailureError(f"the trace summary lacks an integer {key}")
    return value


def check_host_run(run_dir: Path) -> list[CaseResult]:
    """Cases 2-9 on a recorded host run's trace and end state (FR-045), each labelled with what proves it.

    The trace holds no content, so a case is ``proved`` only when its evidence
    lines (``tool_names``, ``summary``, ``outcome``) establish it,
    ``proved-by-end-state`` when the fixture's end state is needed as well, and
    ``not-provable-from-host-run`` (skipped, never passed) when the trace
    lacks the scenario step that would show it: the stale-update refusal (7)
    needs a ``promote`` refused with exit 9, promote-name containment (8) one
    refused by the name rule (``ValueError``, exit 1). The detail of every
    case says what the run does not show.
    """
    manifest = json.loads((run_dir / RUN_MANIFEST).read_text(encoding="utf-8"))
    records = [json.loads(line) for line in (run_dir / RUN_TRACE).read_text(encoding="utf-8").splitlines() if line]
    end = run_dir / RUN_END_STATE
    version = str(manifest.get("protocol_version") or "host")
    results: list[CaseResult] = []
    calls = [(i, r) for i, r in enumerate(records) if r.get("method") == METHOD_CALL]

    def run(number: int, proof: str, case: Callable[[], str]) -> None:
        try:
            results.append(CaseResult(version, number, PASS, case(), proof))
        except (CaseFailureError, OSError, ValueError, KeyError, TypeError) as exc:
            results.append(CaseResult(version, number, FAIL, f"{type(exc).__name__}: {exc}", PROOF_FAILED))

    def not_provable(number: int, detail: str) -> None:
        results.append(CaseResult(version, number, SKIP, detail, PROOF_NONE))

    def recorded() -> str:
        missing = [key for key in HOST_MANIFEST_KEYS if not manifest.get(key)]
        check(not missing, f"manifest.json lacks {missing}")
        check(
            manifest["scenario_sha256"] == sha256_bytes(SCENARIO.read_bytes()), "scenario_sha256 is not scenario.md's"
        )
        check(manifest["end_state_sha256"] == tree_sha256(end), "end_state_sha256 is not the end-state tree's hash")
        check(all(tuple(r) == TRACE_KEYS for r in records), "a trace line does not have the trace keys")
        negotiated = {r["protocol_version"] for r in records if r.get("protocol_version")}
        check(negotiated == {manifest["protocol_version"]}, f"the trace negotiated {sorted(negotiated)}")
        return f"manifest, scenario and end state agree; negotiated {manifest['protocol_version']}"

    wiki = end / WIKI_REL
    applied = end / PROPOSALS_REL / APPLIED_DIR
    receipts = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(applied.glob(f"*/{RECEIPT_FILE}"))]
    fixture_wiki = FIXTURE_PROJECT / WIKI_REL
    order: dict[str, int | None] = {}

    def successful(tool: str) -> list[dict[str, Any]]:
        return [r for _, r in calls if r.get("tool") == tool and r.get("outcome") == 0]

    def surface() -> str:
        recorded()
        listed = [r for r in records if r.get("method") == METHOD_LIST and r.get("outcome") == 0]
        check(listed, "no successful tools/list")
        for record in listed:
            names = record.get("tool_names")
            check(names is not None, "the tools/list line carries no tool_names (a trace from before 0.8.0)")
            check(names == sorted(TOOL_NAMES), f"tools/list named {names}, expected the eight")
        called = sorted({str(r.get("tool")) for _, r in calls})
        check(set(called) <= set(TOOL_NAMES), f"calls outside the eight tools: {called}")
        return f"tools/list named the eight tools; called {called} (the argument schemas are the protocol suite's)"

    def find() -> str:
        order["find"] = _first(calls, TOOL_FIND)
        check(order["find"] is not None, "no successful find")
        finds = successful(TOOL_FIND)
        for summary in map(_summary, finds):
            pages = _int(summary, "pages")
            check(pages <= MAX_FIND_PAGES, f"find returned {pages} pages, more than {MAX_FIND_PAGES}")
            max_pages = summary.get("max_pages")
            if isinstance(max_pages, int) and not isinstance(max_pages, bool):
                check(pages <= max_pages, f"find returned {pages} pages for max_pages {max_pages}")
            check(isinstance(summary.get("ranker"), str) and summary["ranker"], "find did not name its ranker")
            check(summary.get("has_sha256") is True, "a page of find's result lacks its sha256")
        rankers = sorted({str(_summary(r).get("ranker")) for r in finds})
        return (
            f"{len(finds)} find(s), each within {MAX_FIND_PAGES} pages, ranker {rankers}, every page with a sha256 "
            "(index linkage and the byte budget are the protocol suite's)"
        )

    def read_page() -> str:
        order["read"] = _first(calls, TOOL_READ_PAGE)
        check(order["read"] is not None, "no successful read_page")
        for summary in map(_summary, successful(TOOL_READ_PAGE)):
            check(summary.get("has_sha256") is True, "read_page returned no sha256")
        refused = [
            r for _, r in calls if r.get("tool") == TOOL_READ_PAGE and r.get("outcome") == EXIT_PATH_OUTSIDE_ROOT
        ]
        check(
            refused,
            "containment is not provable from this run: no read_page was refused with exit 7 "
            "(the scenario's traversal step); the protocol suite covers it",
        )
        return (
            "read_page returned a sha256 (that it is the file's is the protocol suite's check); "
            f"{len(refused)} read_page refused with exit 7 (the scenario's traversal step; the trace holds no path)"
        )

    def after(step: str) -> int:
        """The trace position of an earlier step, which the next step must follow."""
        position = order.get(step)
        check(position is not None, f"no successful {step} before this step")
        assert position is not None
        return position

    def created_pages() -> list[str]:
        """The wiki-relative pages the receipts created (no previous bytes), other than the index pages."""
        pages = []
        for receipt in receipts:
            for write in receipt.get("planned_writes") or []:
                rel = str(write.get("path", ""))
                rel = rel[len(WIKI_REL) + 1 :] if rel.startswith(WIKI_REL + "/") else rel
                if write.get("pre_sha256") is None and rel.endswith(".md") and rel not in INDEX_PAGES:
                    pages.append(rel)
        return pages

    def propose() -> str:
        order["propose"] = _first(calls, TOOL_PROPOSE, after("read"))
        check(order["propose"] is not None, "no successful propose after read_page")
        assert order["propose"] is not None
        summary = _summary(records[order["propose"]])
        creates, updates = _int(summary, "creates"), _int(summary, "updates")
        with_base = _int(summary, "with_base_sha256")
        check(creates + updates, "propose carried no create and no update")
        check(with_base == updates, f"{updates - with_base} update(s) carried no base_sha256")
        plans = list(applied.glob("*/plan.json"))
        check(plans, "no proposal reached the proposals directory's archive")
        if creates:
            pages = created_pages()
            check(len(pages) >= creates, f"the receipts show {len(pages)} created page(s) for {creates} create(s)")
            for rel in pages:
                check(PAGE_ID_RE.search((wiki / rel).read_text(encoding="utf-8")), f"{rel} carries no page_id")
            page_ids = f"the {len(pages)} created page(s) carry a page_id in the end state"
        else:
            page_ids = "no create in the scenario, so page_id assignment is not exercised"
        return (
            f"{creates} create(s), {updates} update(s) each carrying base_sha256; {len(plans)} proposal(s) archived; "
            f"{page_ids} (that the wiki stayed unchanged between propose and promote is not provable from a trace)"
        )

    def promote() -> str:
        order["promote"] = _first(calls, TOOL_PROMOTE, after("propose"))
        check(order["promote"] is not None, "no successful promote after propose")
        assert order["promote"] is not None
        summary = _summary(records[order["promote"]])
        applied_count = _int(summary, "applied")
        check(applied_count, "promote applied no path")
        check(summary.get("dry_run") is False, "promote was a dry run")
        check(receipts, "no receipt in the archive")
        check(all(r.get("state") == RECEIPT_COMMITTED for r in receipts), "a receipt is not committed")
        entry_points = {(r.get("promoter") or {}).get("entry_point") for r in receipts}
        check(entry_points == {ENTRY_POINT_MCP}, f"receipt entry points {sorted(map(str, entry_points))}")
        for receipt in receipts:
            check(not receipt.get("unguarded_paths"), "an update was applied without base_sha256")
        updated = landed_updates()
        check(updated, "no fixture page was updated")
        return (
            f"applied {applied_count} path(s), not a dry run; {len(receipts)} committed receipt(s), entry_point mcp; "
            f"guarded update of {sorted(updated)} from the fixture's revision, no unguarded path"
        )

    def landed_updates() -> list[str]:
        """The fixture pages the receipts updated: each from the fixture's revision, each still as written."""
        updated = []
        for receipt in receipts:
            for write in receipt.get("planned_writes") or []:
                rel = str(write.get("path", ""))
                rel = rel[len(WIKI_REL) + 1 :] if rel.startswith(WIKI_REL + "/") else rel
                original = fixture_wiki / rel
                if rel.endswith(".md") and rel not in INDEX_PAGES and original.is_file():
                    check(
                        write.get("pre_sha256") == sha256_bytes(original.read_bytes()),
                        f"{rel} was not updated from the fixture's revision",
                    )
                    check(
                        write.get("post_sha256") == sha256_bytes((wiki / rel).read_bytes()),
                        f"{rel} in the end state is not what the promote wrote",
                    )
                    updated.append(rel)
        return updated

    def refused_promotes(exit_code: int) -> list[tuple[int, dict[str, Any]]]:
        return [(i, r) for i, r in calls if r.get("tool") == TOOL_PROMOTE and r.get("outcome") == exit_code]

    def stale_update() -> str:
        promoted = after("promote")
        stale = [i for i, _ in refused_promotes(EXIT_PROMOTE_VALIDATION) if i > promoted]
        check(stale, "no promote was refused with exit 9 after the successful promote")
        proposes = [
            r for i, r in calls if promoted < i < stale[0] and r.get("tool") == TOOL_PROPOSE and r.get("outcome") == 0
        ]
        check(proposes, "no successful propose between the successful promote and the refused one")
        updates = 0
        for summary in map(_summary, proposes):
            count = _int(summary, "updates")
            check(count, "the propose before the refused promote carried no update")
            check(_int(summary, "with_base_sha256") == count, "an update before the refused promote had no base_sha256")
            updates += count
        check(all(r.get("state") == RECEIPT_COMMITTED for r in receipts), "a receipt is not committed")
        updated = landed_updates()
        check(updated, "no fixture page was updated")
        return (
            f"after the first promote, a propose with {updates} update(s) carrying base_sha256 was refused at promote "
            f"with exit 9; {sorted(updated)} in the end state is still what the first promote wrote and every receipt "
            "is committed, so the refused promote changed nothing (that it named the same page is not in the trace)"
        )

    def name_containment() -> str:
        bad = [r for _, r in refused_promotes(EXIT_VALUE_ERROR) if _summary(r).get("error") == ERROR_VALUE_ERROR]
        check(bad, "no promote was refused by the name rule (ValueError, exit 1)")
        return (
            f"{len(bad)} promote refused by the name rule (ValueError, exit 1; the trace holds no name), so nothing "
            "was applied; that nothing was read is the protocol suite's"
        )

    def not_approved() -> str:
        position = _first(calls, TOOL_REVIEW_STATE, after("promote"))
        check(position is not None, "no successful review_state after promote")
        assert position is not None
        summary = _summary(records[position])
        check(_int(summary, "states"), "review_state returned no state")
        check(_int(summary, "approved") == 0, f"review_state reports {summary.get('approved')} approved page(s)")
        promoted = _summary(records[after("promote")])
        check(_int(promoted, "approved") == 0, f"promote approved {promoted.get('approved')} page(s)")
        approvals = (
            [p for p in (wiki / APPROVALS_REL).rglob("*") if p.is_file()] if (wiki / APPROVALS_REL).is_dir() else []
        )
        check(not approvals, f"approval records exist: {len(approvals)}")
        return "review_state after promote reports no approved page, promote approved none, no approval record"

    run(2, PROOF_TRACE, surface)
    run(3, PROOF_TRACE, find)
    run(4, PROOF_TRACE, read_page)
    run(5, PROOF_END_STATE, propose)
    run(6, PROOF_END_STATE, promote)
    if refused_promotes(EXIT_PROMOTE_VALIDATION):
        run(7, PROOF_END_STATE, stale_update)
    else:
        not_provable(
            7, "no promote was refused with exit 9 (the scenario's stale-update step), so that refusal is the suite's"
        )
    if any(_summary(r).get("error") == ERROR_VALUE_ERROR for _, r in refused_promotes(EXIT_VALUE_ERROR)):
        run(8, PROOF_TRACE, name_containment)
    else:
        not_provable(
            8, "no promote was refused by the name rule (the scenario's ../x step), so that refusal is the suite's"
        )
    run(9, PROOF_END_STATE, not_approved)
    return sorted(results, key=lambda r: r.number)


# The cases a recorded host run must prove for FR-045's exit evidence: every one of 2..9.
HOST_RUN_CASES = tuple(range(2, 10))


def host_verdict(results: list[CaseResult]) -> dict[str, Any]:
    """The recorded verdict: which cases the run proves, which it cannot, and which failed.

    ``passed`` is true only when every case in :data:`HOST_RUN_CASES` is
    proved: a run with no failure but an unprovable case (a skipped scenario
    step) is not exit evidence.
    """
    proved = [r.number for r in results if r.status == PASS]
    not_provable = [r.number for r in results if r.status == SKIP]
    failed = [r.number for r in results if r.status == FAIL]
    return {
        "passed": not failed and all(number in proved for number in HOST_RUN_CASES),
        "cases": {str(r.number): r.status for r in results},
        "proof": {str(r.number): r.proof for r in results},
        "proved": proved,
        "not_provable": not_provable,
        "failed": failed,
    }


def host_verdict_line(verdict: dict[str, Any]) -> str:
    def cases(numbers: list[int]) -> str:
        return ", ".join(str(n) for n in numbers) or "none"

    text = f"verdict: the host run proves case(s) {cases(verdict['proved'])}"
    if verdict["not_provable"]:
        text += f"; not provable from a host run, the protocol suite's: {cases(verdict['not_provable'])}"
    if verdict["failed"]:
        text += f"; failed: {cases(verdict['failed'])}"
    missing = [n for n in HOST_RUN_CASES if n not in verdict["proved"]]
    text += "; passed" if verdict["passed"] else f"; not passed: case(s) {cases(missing)} unproved"
    return text


# ── Command line ─────────────────────────────────────────────


def _print(results: list[CaseResult]) -> int:
    for result in results:
        print(result.line())
    failed = [r for r in results if r.status == FAIL]
    passed = sum(r.status == PASS for r in results)
    print(f"{passed} passed, {len(failed)} failed, {sum(r.status == SKIP for r in results)} skipped")
    return EXIT_FAIL if failed else EXIT_PASS


def _suite_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m conformance.mcp.run", description=__doc__.splitlines()[0])
    parser.add_argument("--server-cmd", required=True, help="The server command; {root} becomes the fixture root.")
    parser.add_argument(
        "--protocol-version",
        action="append",
        choices=TESTED_VERSIONS,
        default=None,
        help="A protocol version to test; repeatable (default: all tested versions).",
    )
    parser.add_argument("--trace", type=Path, default=None, help="Pass --trace PATH to every server launch.")
    args = parser.parse_args(argv)
    server_cmd = shlex.split(args.server_cmd)
    if not server_cmd:
        raise SuiteError("--server-cmd is empty")
    _require_sdk()
    versions = list(dict.fromkeys(args.protocol_version or TESTED_VERSIONS))
    trace = None if args.trace is None else args.trace.resolve()
    return _print(asyncio.run(run_suite(server_cmd, versions, trace)))


def _host_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m conformance.mcp.run check-host-run")
    parser.add_argument("--run", type=Path, required=True, help="A recorded run directory under conformance/runs/.")
    parser.add_argument("--record", action="store_true", help="Write the verdict into the run's manifest.json.")
    args = parser.parse_args(argv)
    for name in (RUN_MANIFEST, RUN_TRACE, RUN_END_STATE):
        if not (args.run / name).exists():
            raise SuiteError(f"{args.run / name} is missing (see conformance/runs/README.md)")
    results = check_host_run(args.run)
    code = _print(results)
    verdict = host_verdict(results)
    print(host_verdict_line(verdict))
    if args.record:
        manifest_path = args.run / RUN_MANIFEST
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["verdict"] = verdict
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return code if verdict["passed"] else EXIT_FAIL


def _tree_hash_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m conformance.mcp.run tree-hash")
    parser.add_argument("dir", type=Path, help="A directory, such as a recorded run's end-state/.")
    args = parser.parse_args(argv)
    if not args.dir.is_dir():
        raise SuiteError(f"{args.dir} is not a directory")
    print(tree_sha256(args.dir))
    return EXIT_PASS


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    try:
        if args[:1] == ["check-host-run"]:
            return _host_main(args[1:])
        if args[:1] == ["tree-hash"]:
            return _tree_hash_main(args[1:])
        return _suite_main(args)
    except SuiteError as exc:
        print(f"conformance: {exc}", file=sys.stderr)
        return EXIT_CANNOT_RUN


if __name__ == "__main__":
    sys.exit(main())
