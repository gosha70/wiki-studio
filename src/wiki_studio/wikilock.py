# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""WikiLock — the OS advisory lock that serialises cooperating wiki-studio writers.

Ownership is the operating system's lock on an open file descriptor:
``fcntl.flock(fd, LOCK_EX)`` on POSIX and ``msvcrt.locking`` on Windows,
behind one interface. There is no PID-file ownership and no stale-lock
reclamation: a holder that dies releases the lock with its descriptor, and
the lock file is never deleted or recreated while contenders may hold it.
PID, hostname and start time are written into the file as diagnostics only
and are never read to decide anything.

The lock file is ``<resolved-wiki-parent>/.<wiki-dir-name>.wiki-studio.lock``,
keyed to ``wiki_dir.resolve()`` so two spellings of one directory share it.
It lies outside the wiki, so staging and lint never see it.

Scope: one machine and one local filesystem. The lock is not distributed,
does not protect against direct edits of wiki files, and network
filesystems are out of scope. It is not reentrant: a second acquisition
from the same thread while the first is held waits for the timeout.
"""

from __future__ import annotations

import contextlib
import datetime
import os
import socket
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from .errors import REASON_LOCK_TIMEOUT, PromoteApplyError
from .paths import DEFAULT_LOCK_TIMEOUT

if TYPE_CHECKING:
    from types import TracebackType

__all__ = ["DEFAULT_LOCK_TIMEOUT", "LockBackend", "WikiLock", "available_backends", "lock_path_for"]

LOCK_FILE_SUFFIX = ".wiki-studio.lock"

# Interval between non-blocking acquisition attempts.
_POLL_SECONDS = 0.02
# Stable tag names for the backends (used to parametrise tests).
BACKEND_FCNTL = "fcntl"
BACKEND_MSVCRT = "msvcrt"


class LockBackend(Protocol):
    """One way to take an exclusive OS lock on an open descriptor without blocking."""

    name: str

    def try_lock(self, fd: int) -> bool:
        """Take the lock on ``fd``; False when another holder has it."""
        ...

    def unlock(self, fd: int) -> None:
        """Release the lock taken by :meth:`try_lock`."""
        ...


class FcntlBackend:
    """``fcntl.flock``: the lock belongs to the open file description (POSIX)."""

    name = BACKEND_FCNTL

    def try_lock(self, fd: int) -> bool:
        import fcntl

        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        return True

    def unlock(self, fd: int) -> None:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_UN)


class MsvcrtBackend:
    """``msvcrt.locking`` on the first byte of the file (Windows).

    The byte is locked through the holder's descriptor; the diagnostics are
    written after it so they never overlap the locked region.
    """

    name = BACKEND_MSVCRT

    def try_lock(self, fd: int) -> bool:
        if sys.platform != "win32":
            raise RuntimeError("the msvcrt lock backend runs on Windows only")
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError:
            return False
        return True

    def unlock(self, fd: int) -> None:
        if sys.platform != "win32":
            raise RuntimeError("the msvcrt lock backend runs on Windows only")
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)


def available_backends() -> tuple[LockBackend, ...]:
    """The backends this platform can run (one, in practice)."""
    if sys.platform == "win32":
        return (MsvcrtBackend(),)
    return (FcntlBackend(),)


def default_backend() -> LockBackend:
    """The backend for this platform."""
    return available_backends()[0]


def lock_path_for(wiki_dir: Path) -> Path:
    """``<resolved-wiki-parent>/.<wiki-dir-name>.wiki-studio.lock`` for ``wiki_dir``."""
    resolved = Path(wiki_dir).resolve()
    return resolved.parent / f".{resolved.name}{LOCK_FILE_SUFFIX}"


class WikiLock:
    """Context manager holding the exclusive wiki lock for its ``with`` block.

    Parameters
    ----------
    wiki_dir : Path
        The wiki directory the lock protects; the lock file is its sibling.
    timeout : float
        Seconds to wait for the lock; on expiry ``PromoteApplyError`` with
        ``reason="lock_timeout"`` (exit 10). A negative value is clamped to
        0 (one attempt, no wait); ``WikiPaths.resolve`` rejects negatives
        before they reach here. ``inf`` waits indefinitely.
    backend : LockBackend | None
        The OS lock primitive; defaults to the platform's.

    After acquisition ``wait_seconds`` records how long the acquisition took.
    """

    def __init__(
        self,
        wiki_dir: Path,
        timeout: float = DEFAULT_LOCK_TIMEOUT,
        *,
        backend: LockBackend | None = None,
    ) -> None:
        self.wiki_dir = Path(wiki_dir)
        self.lock_path = lock_path_for(self.wiki_dir)
        self.timeout = max(0.0, float(timeout))
        self.backend: LockBackend = backend if backend is not None else default_backend()
        self.wait_seconds = 0.0
        self._fd: int | None = None

    @property
    def held(self) -> bool:
        """True between a successful ``acquire`` and ``release``."""
        return self._fd is not None

    def acquire(self) -> WikiLock:
        """Take the lock, waiting up to ``timeout`` seconds."""
        if self._fd is not None:
            raise RuntimeError(f"WikiLock on {self.lock_path} is already held by this object")
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        # O_CREAT without O_EXCL: the file is shared by every contender and is
        # never removed, so opening it is never a question of ownership.
        # O_NOFOLLOW (where the platform has it): a symlink planted at the lock
        # path is refused rather than written through.
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.lock_path, flags, 0o644)
        started = time.monotonic()
        deadline = started + self.timeout
        try:
            while not self.backend.try_lock(fd):
                if time.monotonic() >= deadline:
                    raise PromoteApplyError(
                        f"could not acquire the wiki lock {self.lock_path} within {self.timeout:g}s; "
                        "another wiki-studio process is writing to this wiki. Wait for it to finish, or pass "
                        "--lock-timeout / set WIKI_STUDIO_LOCK_TIMEOUT to wait longer.",
                        reason=REASON_LOCK_TIMEOUT,
                    )
                time.sleep(_POLL_SECONDS)
        except BaseException:
            os.close(fd)
            raise
        self.wait_seconds = time.monotonic() - started
        self._fd = fd
        self._write_diagnostics(fd)
        return self

    def release(self) -> None:
        """Release the lock and close the descriptor; a no-op when not held."""
        fd = self._fd
        if fd is None:
            return
        self._fd = None
        try:
            self.backend.unlock(fd)
        finally:
            os.close(fd)

    def _write_diagnostics(self, fd: int) -> None:
        """PID, host and start time for a human reading the file; never used for ownership."""
        started = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        text = f"pid={os.getpid()}\nhost={socket.gethostname()}\nstarted={started}\n".encode()
        # The msvcrt byte lock covers offset 0; keep the diagnostics behind it.
        offset = 1 if self.backend.name == BACKEND_MSVCRT else 0
        with contextlib.suppress(OSError):  # diagnostics are best-effort
            os.lseek(fd, offset, os.SEEK_SET)
            view = memoryview(text)
            while view:  # os.write may write fewer bytes than asked
                view = view[os.write(fd, view) :]
            os.ftruncate(fd, offset + len(text))

    def __enter__(self) -> WikiLock:
        return self.acquire()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()
