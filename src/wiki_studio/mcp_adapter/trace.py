# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The wire observer of ``wiki-studio-mcp`` and its opt-in trace file (FR-041).

The observer sits between the process's stdio and the SDK: two relay threads
copy every JSON-RPC line from the real stdin to the SDK and from the SDK to the
real stdout, byte for byte, and look at each frame on the way. From the frames
it learns the negotiated protocol version and the client's name and version
(``info``'s ``adapter.protocol_version``), and with ``--trace PATH`` it appends
one JSON line per request: ``ts``, ``method``, ``tool``, ``protocol_version``,
``client_name``, ``client_version``, ``outcome`` (0, or the error result's
``exit_code``), ``duration_ms``, and the non-content evidence a host-run
checker needs: ``tool_names`` (a ``tools/list`` result's names), ``arg_keys``
and ``result_keys`` (a ``tools/call``'s argument and result key names) and
``summary`` (counts and flags per tool, see :func:`_summary`). Page content,
question text, edit content and file paths are never traced, and neither is
any other string the client chooses: ``method`` and ``tool`` are recorded
only when they are a known request method and one of the eight tools (else
``"unknown"``), ``arg_keys``, ``result_keys`` and ``tool_names`` keep only
the names in the tool's own schema, and whatever else a frame carries is
counted in ``unknown_tool_names``, ``unknown_arg_keys`` and
``unknown_result_keys``. Observing the wire rather than the SDK's internals
keeps the trace independent of the SDK version.
"""

from __future__ import annotations

import contextlib
import datetime
import inspect
import json
import os
import re
import select
import stat
import sys
import threading
import time
from typing import IO, TYPE_CHECKING, Any

from ..errors import IngestError
from ..paths import path_inside_dir
from ..review import STATE_APPROVED
from .config import (
    TOOL_FIND,
    TOOL_FINDINGS,
    TOOL_INFO,
    TOOL_LINT,
    TOOL_NAMES,
    TOOL_PROMOTE,
    TOOL_PROPOSE,
    TOOL_READ_PAGE,
    TOOL_REVIEW_STATE,
    LaunchError,
)
from .tools import INTERNAL_ERROR, WikiTools

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from ..paths import WikiPaths

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
METHOD_INITIALIZE = "initialize"
METHOD_TOOLS_LIST = "tools/list"
METHOD_TOOLS_CALL = "tools/call"
# The request methods a client may send a server (MCP 2025-06-18); any other method is traced as UNKNOWN.
# The 2026-07-28 protocol has no initialize handshake: the client probes ``server/discover`` and then carries the
# protocol version and its clientInfo in every request's ``params._meta`` (the per-request envelope).
METHOD_SERVER_DISCOVER = "server/discover"
METHOD_SUBSCRIPTIONS_LISTEN = "subscriptions/listen"
META_KEY = "_meta"
META_PROTOCOL_VERSION = "io.modelcontextprotocol/protocolVersion"
META_CLIENT_INFO = "io.modelcontextprotocol/clientInfo"
KNOWN_METHODS = frozenset(
    {
        METHOD_INITIALIZE,
        METHOD_SERVER_DISCOVER,
        METHOD_SUBSCRIPTIONS_LISTEN,
        METHOD_TOOLS_LIST,
        METHOD_TOOLS_CALL,
        "ping",
        "resources/list",
        "resources/templates/list",
        "resources/read",
        "resources/subscribe",
        "resources/unsubscribe",
        "prompts/list",
        "prompts/get",
        "completion/complete",
        "logging/setLevel",
    }
)
# What the trace records in place of a client-chosen method or tool name it does not know (FR-041).
UNKNOWN = "unknown"
# A client name or version the trace copies verbatim: short and plain (letters, digits, dots, dashes, plus signs,
# underscores); anything else the client sends as its identity is recorded as UNKNOWN, like a method or tool name.
IDENTITY_PATTERN = re.compile(r"[A-Za-z0-9._+-]{1,64}")
# The outcome of a failed request that carries no wiki-studio exit code (a protocol error, an SDK refusal).
OUTCOME_UNCODED_ERROR = 1
# The keys of an error result (tools.error_payload) and the top-level keys of each tool's result (FR-035).
ERROR_RESULT_KEYS = frozenset({"error", "exit_code", "message"})
TOOL_RESULT_KEYS: dict[str, frozenset[str]] = {
    TOOL_FIND: frozenset(
        {
            "question",
            "index",
            "pages",
            "ranker",
            "fallback_reason",
            "bytes_loaded",
            "max_bytes",
            "ranker_config_hash",
            "omitted",
            "ineligible",
            "warnings",
        }
    ),
    TOOL_READ_PAGE: frozenset({"path", "sha256", "content"}),
    TOOL_PROPOSE: frozenset({"name", "proposal_dir", "warnings"}),
    TOOL_PROMOTE: frozenset(
        {"applied_paths", "archived_dir", "dry_run", "unguarded_paths", "warnings", "approved_paths"}
    ),
    TOOL_LINT: frozenset({"violations", "pages_checked", "audit_errors", "health", "prose", "passed"}),
    TOOL_INFO: frozenset(
        {"package_version", "schema_contract", "formats", "capabilities", "manifest", "discovery", "adapter"}
    ),
    TOOL_FINDINGS: frozenset({"findings_version", "counts", "pages_checked", "findings"}),
    TOOL_REVIEW_STATE: frozenset({"states"}),
}


def _argument_keys(name: str) -> frozenset[str]:
    """The argument names of one tool: its method's parameters, from which the SDK builds the input schema."""
    return frozenset(p for p in inspect.signature(getattr(WikiTools, name)).parameters if p != "self")


TOOL_ARG_KEYS: dict[str, frozenset[str]] = {name: _argument_keys(name) for name in TOOL_NAMES}


def _error_names() -> frozenset[str]:
    """The ``error`` values an error result can carry: wiki-studio's error classes, ``ValueError``, InternalError."""
    names = {INTERNAL_ERROR, ValueError.__name__}
    pending: list[type[BaseException]] = [IngestError]
    while pending:
        cls = pending.pop()
        names.add(cls.__name__)
        pending.extend(cls.__subclasses__())
    return frozenset(names)


KNOWN_ERRORS = _error_names()
_STDIN_FD = 0
_STDOUT_FD = 1
_READ_CHUNK = 65536
# How often the outbound relay checks whether the server has finished (POSIX; see _pump).
_PUMP_POLL_SECONDS = 0.05
_POSIX = os.name == "posix"
# Without select on pipes (Windows) the relay cannot poll; bound the wait instead.
_PUMP_JOIN_FALLBACK_SECONDS = 2.0
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_TRACE_MODE = 0o600
# The edit actions propose's summary counts.
_ACTION_CREATE = "create"
_ACTION_UPDATE = "update"
_PAGE_ID_LINE = "page_id:"


def open_trace(path: Path, paths: WikiPaths) -> IO[str]:
    """Open ``path`` append-only for the trace; inside the wiki, a symlink, or unopenable is a launch error.

    The containment check does not follow the final component, so the file
    itself is opened without following a symlink (``lstat`` first, then
    ``O_NOFOLLOW`` against a link raced in after it) and must be a regular file.
    """
    if path_inside_dir(path, paths.wiki_dir):
        raise LaunchError(f"--trace {path} lies inside the wiki {paths.wiki_dir}; put the trace outside it")
    try:
        if path.is_symlink():
            raise LaunchError(f"--trace {path} is a symlink; name the trace file itself")
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | _O_NOFOLLOW, _TRACE_MODE)
    except OSError as exc:
        raise LaunchError(f"--trace {path} cannot be opened for appending: {exc}") from exc
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise LaunchError(f"--trace {path} is not a regular file")
        return os.fdopen(fd, "a", encoding="utf-8")
    except (OSError, LaunchError):
        os.close(fd)
        raise


def _utc_now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _frames(line: bytes) -> list[dict[str, Any]]:
    """The JSON-RPC messages on one line (one object, or a batch); nothing for a line that is not JSON."""
    try:
        data = json.loads(line)
    except ValueError:
        return []
    items = data if isinstance(data, list) else [data]
    return [item for item in items if isinstance(item, dict)]


def _payload(message: dict[str, Any]) -> dict[str, Any] | None:
    """A ``tools/call`` response's object: the first text block's JSON, else ``structuredContent``."""
    result = message.get("result")
    if not isinstance(result, dict):
        return None
    for block in result.get("content") or []:
        if isinstance(block, dict) and block.get("type") == "text":
            with contextlib.suppress(ValueError, TypeError):
                parsed = json.loads(block.get("text", ""))
                if isinstance(parsed, dict):
                    return parsed
            break
    structured = result.get("structuredContent")
    return structured if isinstance(structured, dict) else None


def _outcome(message: dict[str, Any], payload: dict[str, Any] | None) -> int:
    """0 for a successful response; the error result's ``exit_code``; 1 for an uncoded error."""
    if "error" in message:
        return OUTCOME_UNCODED_ERROR
    result = message.get("result")
    if not isinstance(result, dict) or not result.get("isError"):
        return 0
    code = payload.get("exit_code") if payload is not None else None
    return code if isinstance(code, int) and not isinstance(code, bool) else OUTCOME_UNCODED_ERROR


def _known(names: Any, allowed: frozenset[str]) -> tuple[list[str], int]:
    """The strings of ``names`` that are in ``allowed``, sorted, and the count of everything else."""
    known = sorted(n for n in names if isinstance(n, str) and n in allowed)
    return known, len(list(names)) - len(known)


def _tool_names(message: dict[str, Any]) -> tuple[list[str] | None, int | None]:
    """The eight tools a ``tools/list`` result names and the count of other names; (None, None) without a list."""
    result = message.get("result")
    tools = result.get("tools") if isinstance(result, dict) else None
    if not isinstance(tools, list):
        return None, None
    return _known([t.get("name") for t in tools if isinstance(t, dict)], frozenset(TOOL_NAMES))


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _edits_of(arguments: dict[str, Any], action: str) -> list[dict[str, Any]]:
    edits = arguments.get("edits")
    return [e for e in edits if isinstance(e, dict) and e.get("action") == action] if isinstance(edits, list) else []


def _carries_page_id(edit: dict[str, Any]) -> bool:
    """Whether a create's submitted content already names a ``page_id`` (the content itself is never traced)."""
    content = edit.get("content")
    return isinstance(content, str) and any(line.startswith(_PAGE_ID_LINE) for line in content.splitlines())


def _summary(tool: str | None, arguments: dict[str, Any], payload: dict[str, Any] | None, outcome: int) -> Any:
    """Counts and flags per tool, from the arguments and the result; None for a tool without a summary.

    For an error result the summary is ``{"exit_code": <outcome>, "error":
    <class>}`` with the class only when it is one of wiki-studio's own error
    names (else null). Nothing here copies a value out of the arguments or
    the result except ``find``'s ranker name, which the ``info`` tool reports
    anyway.
    """
    if outcome != 0:
        name = payload.get("error") if payload is not None else None
        return {"exit_code": outcome, "error": name if isinstance(name, str) and name in KNOWN_ERRORS else None}
    result = payload or {}
    if tool == TOOL_FIND:
        pages = _list(result.get("pages"))
        max_pages = arguments.get("max_pages")
        return {
            "pages": len(pages),
            "max_pages": max_pages if isinstance(max_pages, int) and not isinstance(max_pages, bool) else None,
            "ranker": result.get("ranker") if isinstance(result.get("ranker"), str) else None,
            "has_sha256": all(isinstance(p, dict) and isinstance(p.get("sha256"), str) and p["sha256"] for p in pages),
        }
    if tool == TOOL_READ_PAGE:
        return {"has_sha256": isinstance(result.get("sha256"), str) and bool(result["sha256"])}
    if tool == TOOL_PROPOSE:
        creates = _edits_of(arguments, _ACTION_CREATE)
        updates = _edits_of(arguments, _ACTION_UPDATE)
        return {
            "creates": len(creates),
            "updates": len(updates),
            "with_base_sha256": sum(isinstance(e.get("base_sha256"), str) and bool(e["base_sha256"]) for e in updates),
            "page_id_supplied": sum(_carries_page_id(e) for e in creates),
        }
    if tool == TOOL_PROMOTE:
        return {
            "applied": len(_list(result.get("applied_paths"))),
            "dry_run": bool(result.get("dry_run")),
            "approved": len(_list(result.get("approved_paths"))),
        }
    if tool == TOOL_REVIEW_STATE:
        states = _list(result.get("states"))
        return {
            "states": len(states),
            "approved": sum(isinstance(s, dict) and s.get("state") == STATE_APPROVED for s in states),
        }
    return None


def _identity(value: Any) -> str | None:
    """A client name or version as the trace records it: the string when short and plain, else UNKNOWN."""
    if not isinstance(value, str):
        return None
    return value if IDENTITY_PATTERN.fullmatch(value) else UNKNOWN


class WireObserver:
    """What the frames say: the negotiated protocol version, the client, and the trace lines.

    ``inbound`` is called with each line the client sent, ``outbound`` with
    each line the server sent. Thread-safe: the two relay threads call it.
    """

    def __init__(self, trace: IO[str] | None = None, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._trace = trace
        self._clock = clock
        self._lock = threading.Lock()
        self._pending: dict[str, tuple[str, str | None, dict[str, Any] | None, float, str | None]] = {}
        self._initialize_id: str | None = None
        self.protocol_version: str | None = None
        self.client_name: str | None = None
        self.client_version: str | None = None

    def inbound(self, line: bytes) -> None:
        for message in _frames(line):
            method = message.get("method")
            if not isinstance(method, str) or "id" not in message:
                continue  # a notification or a response to a server request: not a request to trace
            params = message.get("params")
            if not isinstance(params, dict):
                params = {}
            # A method or tool name the trace does not know is recorded as UNKNOWN, never as the client's string.
            tool: str | None = None
            arguments: dict[str, Any] | None = None
            if method == METHOD_TOOLS_CALL:
                name = params.get("name")
                tool = name if isinstance(name, str) and name in TOOL_NAMES else UNKNOWN
                arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
            key = json.dumps(message["id"])
            # The per-request envelope (2026-07-28): the version this request proposes and the client's identity.
            meta = params.get(META_KEY)
            meta = meta if isinstance(meta, dict) else {}
            proposed = meta.get(META_PROTOCOL_VERSION)
            proposed = proposed if isinstance(proposed, str) else None
            info = params.get("clientInfo") if method == METHOD_INITIALIZE else meta.get(META_CLIENT_INFO)
            with self._lock:
                if method == METHOD_INITIALIZE:
                    self._initialize_id = key
                if isinstance(info, dict):
                    self.client_name = _identity(info.get("name"))
                    self.client_version = _identity(info.get("version"))
                recorded_method = method if method in KNOWN_METHODS else UNKNOWN
                self._pending[key] = (recorded_method, tool, arguments, self._clock(), proposed)

    def outbound(self, line: bytes) -> None:
        for message in _frames(line):
            if "method" in message or "id" not in message:
                continue
            key = json.dumps(message["id"])
            with self._lock:
                pending = self._pending.pop(key, None)
                if pending is None:
                    continue
                method, tool, arguments, started, proposed = pending
                if key == self._initialize_id:
                    result = message.get("result")
                    version = result.get("protocolVersion") if isinstance(result, dict) else None
                    if isinstance(version, str):
                        self.protocol_version = version
                elif proposed is not None and "result" in message:
                    # The server answered a request made under this version, so it is the negotiated one.
                    self.protocol_version = proposed
                payload = _payload(message) if arguments is not None else None
                outcome = _outcome(message, payload)
                tool_names, unknown_tool_names = _tool_names(message) if method == METHOD_TOOLS_LIST else (None, None)
                arg_keys: list[str] | None = None
                unknown_arg_keys: int | None = None
                result_keys: list[str] | None = None
                unknown_result_keys: int | None = None
                if arguments is not None:
                    arg_keys, unknown_arg_keys = _known(arguments, TOOL_ARG_KEYS.get(tool or "", frozenset()))
                if payload is not None:
                    allowed = TOOL_RESULT_KEYS.get(tool or "", frozenset()) | ERROR_RESULT_KEYS
                    result_keys, unknown_result_keys = _known(payload, allowed)
                self._write(
                    {
                        "ts": _utc_now(),
                        "method": method,
                        "tool": tool,
                        "protocol_version": self.protocol_version,
                        "client_name": self.client_name,
                        "client_version": self.client_version,
                        "outcome": outcome,
                        "duration_ms": round((self._clock() - started) * 1000),
                        "tool_names": tool_names,
                        "unknown_tool_names": unknown_tool_names,
                        "arg_keys": arg_keys,
                        "unknown_arg_keys": unknown_arg_keys,
                        "result_keys": result_keys,
                        "unknown_result_keys": unknown_result_keys,
                        "summary": None if arguments is None else _summary(tool, arguments, payload, outcome),
                    }
                )

    def _write(self, record: dict[str, Any]) -> None:
        if self._trace is None:
            return
        self._trace.write(json.dumps(record, separators=(",", ":")) + "\n")
        self._trace.flush()

    def close(self) -> None:
        if self._trace is not None:
            self._trace.close()


def _pump(source: int, sink: int, observe: Callable[[bytes], None], stop: threading.Event | None = None) -> None:
    """Copy bytes from ``source`` to ``sink`` unchanged, handing each line to ``observe``; close ``sink`` at the end.

    The bytes are forwarded before they are observed, so an observer failure
    never holds back or alters a frame. The relay ends at EOF on ``source``,
    or, when ``stop`` is given, once it is set and ``source`` has been drained:
    the SDK's stdio transport keeps a private duplicate of fd 1 for the rest
    of the process (``mcp.server.stdio._dup_above_std``), so the outbound pipe
    never reaches EOF on its own after ``run`` returns.
    """
    pending = b""
    try:
        while True:
            if stop is not None and _POSIX:
                readable, _, _ = select.select([source], [], [], _PUMP_POLL_SECONDS)
                if not readable:
                    if stop.is_set():
                        break
                    continue
            chunk = os.read(source, _READ_CHUNK)
            if not chunk:
                break
            _write_all(sink, chunk)
            pending += chunk
            *lines, pending = pending.split(b"\n")
            for line in lines:
                with contextlib.suppress(Exception):
                    observe(line)
    except OSError:
        pass
    finally:
        with contextlib.suppress(OSError):
            os.close(sink)


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        view = view[written:]


@contextlib.contextmanager
def observed_stdio(observer: WireObserver) -> Iterator[None]:
    """Route fd 0 and fd 1 through pipes watched by ``observer`` for the duration of the block.

    The SDK's stdio transport keeps reading fd 0 and writing fd 1; it sees the
    client's bytes and the client sees its bytes unchanged. On exit fd 1 is
    restored (which ends the outbound relay once the SDK's last frame is
    copied) and the observer is closed.
    """
    real_stdin = os.dup(_STDIN_FD)
    real_stdout = os.dup(_STDOUT_FD)
    in_read, in_write = os.pipe()
    out_read, out_write = os.pipe()
    os.dup2(in_read, _STDIN_FD)
    os.close(in_read)
    os.dup2(out_write, _STDOUT_FD)
    os.close(out_write)
    done = threading.Event()
    inbound = threading.Thread(target=_pump, args=(real_stdin, in_write, observer.inbound), daemon=True)
    outbound = threading.Thread(target=_pump, args=(out_read, real_stdout, observer.outbound, done), daemon=True)
    inbound.start()
    outbound.start()
    try:
        yield
    finally:
        with contextlib.suppress(OSError, ValueError):
            sys.stdout.flush()
        # Point fd 1 back at the real stdout, then tell the relay the server is
        # done: it drains what the SDK wrote before ``run`` returned and ends.
        # (The SDK keeps its own duplicate of fd 1 open, so EOF never comes.)
        os.dup2(real_stdout, _STDOUT_FD)
        done.set()
        outbound.join(None if _POSIX else _PUMP_JOIN_FALLBACK_SECONDS)
        observer.close()
