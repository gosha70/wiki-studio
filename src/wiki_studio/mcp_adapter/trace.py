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
``exit_code``) and ``duration_ms``. Page content, question text, edit content
and file paths are never traced. Observing the wire rather than the SDK's
internals keeps the trace independent of the SDK version.
"""

from __future__ import annotations

import contextlib
import datetime
import json
import os
import sys
import threading
import time
from typing import IO, TYPE_CHECKING, Any

from ..paths import path_inside_dir
from .config import LaunchError

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
)
METHOD_INITIALIZE = "initialize"
METHOD_TOOLS_CALL = "tools/call"
# The outcome of a failed request that carries no wiki-studio exit code (a protocol error, an SDK refusal).
OUTCOME_UNCODED_ERROR = 1
_STDIN_FD = 0
_STDOUT_FD = 1
_READ_CHUNK = 65536


def open_trace(path: Path, paths: WikiPaths) -> IO[str]:
    """Open ``path`` append-only for the trace; a path inside the wiki or one that cannot open is a launch error."""
    if path_inside_dir(path, paths.wiki_dir):
        raise LaunchError(f"--trace {path} lies inside the wiki {paths.wiki_dir}; put the trace outside it")
    try:
        return open(path, "a", encoding="utf-8")  # noqa: SIM115 - held for the process, closed by WireObserver
    except OSError as exc:
        raise LaunchError(f"--trace {path} cannot be opened for appending: {exc}") from exc


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


def _outcome(message: dict[str, Any]) -> int:
    """0 for a successful response; the error result's ``exit_code``; 1 for an uncoded error."""
    if "error" in message:
        return OUTCOME_UNCODED_ERROR
    result = message.get("result")
    if not isinstance(result, dict) or not result.get("isError"):
        return 0
    for block in result.get("content") or []:
        if isinstance(block, dict) and block.get("type") == "text":
            with contextlib.suppress(ValueError, TypeError):
                code = json.loads(block.get("text", "")).get("exit_code")
                if isinstance(code, int):
                    return code
    return OUTCOME_UNCODED_ERROR


class WireObserver:
    """What the frames say: the negotiated protocol version, the client, and the trace lines.

    ``inbound`` is called with each line the client sent, ``outbound`` with
    each line the server sent. Thread-safe: the two relay threads call it.
    """

    def __init__(self, trace: IO[str] | None = None, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._trace = trace
        self._clock = clock
        self._lock = threading.Lock()
        self._pending: dict[str, tuple[str, str | None, float]] = {}
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
            tool = params.get("name") if method == METHOD_TOOLS_CALL and isinstance(params.get("name"), str) else None
            key = json.dumps(message["id"])
            with self._lock:
                if method == METHOD_INITIALIZE:
                    self._initialize_id = key
                    info = params.get("clientInfo")
                    if isinstance(info, dict):
                        self.client_name = info.get("name") if isinstance(info.get("name"), str) else None
                        self.client_version = info.get("version") if isinstance(info.get("version"), str) else None
                self._pending[key] = (method, tool, self._clock())

    def outbound(self, line: bytes) -> None:
        for message in _frames(line):
            if "method" in message or "id" not in message:
                continue
            key = json.dumps(message["id"])
            with self._lock:
                pending = self._pending.pop(key, None)
                if pending is None:
                    continue
                if key == self._initialize_id:
                    result = message.get("result")
                    version = result.get("protocolVersion") if isinstance(result, dict) else None
                    if isinstance(version, str):
                        self.protocol_version = version
                method, tool, started = pending
                self._write(
                    {
                        "ts": _utc_now(),
                        "method": method,
                        "tool": tool,
                        "protocol_version": self.protocol_version,
                        "client_name": self.client_name,
                        "client_version": self.client_version,
                        "outcome": _outcome(message),
                        "duration_ms": round((self._clock() - started) * 1000),
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


def _pump(source: int, sink: int, observe: Callable[[bytes], None]) -> None:
    """Copy bytes from ``source`` to ``sink`` unchanged, handing each line to ``observe``; close ``sink`` at EOF.

    The bytes are forwarded before they are observed, so an observer failure
    never holds back or alters a frame.
    """
    pending = b""
    try:
        while True:
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
    inbound = threading.Thread(target=_pump, args=(real_stdin, in_write, observer.inbound), daemon=True)
    outbound = threading.Thread(target=_pump, args=(out_read, real_stdout, observer.outbound), daemon=True)
    inbound.start()
    outbound.start()
    try:
        yield
    finally:
        with contextlib.suppress(OSError, ValueError):
            sys.stdout.flush()
        # Pointing fd 1 back at the real stdout drops the last write end of the
        # outbound pipe, so its relay reaches EOF after the final frame.
        os.dup2(real_stdout, _STDOUT_FD)
        outbound.join()
        observer.close()
