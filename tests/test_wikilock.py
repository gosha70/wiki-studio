# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The wiki lock (0.6.0 FR-002): an OS advisory lock beside the resolved wiki, shared by every spelling of it."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.conftest import make_repo_layout, run_cli
from tests.test_cli_contract import _proposals_dir
from wiki_studio import api
from wiki_studio.errors import REASON_LOCK_TIMEOUT, PromoteApplyError
from wiki_studio.lint import list_pages
from wiki_studio.paths import DEFAULT_LOCK_TIMEOUT, ENV_LOCK_TIMEOUT, WikiPaths
from wiki_studio.wikilock import LOCK_FILE_SUFFIX, MsvcrtBackend, WikiLock, available_backends, lock_path_for

BACKENDS = available_backends()


class _HeldLock:
    """Hold the wiki lock in a background thread for ``seconds`` (or until released)."""

    def __init__(self, wiki_dir: Path, backend: object, seconds: float = 30.0) -> None:
        self.wiki_dir = wiki_dir
        self.backend = backend
        self.seconds = seconds
        self.acquired = threading.Event()
        self.release = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        with WikiLock(self.wiki_dir, timeout=5, backend=self.backend):  # type: ignore[arg-type]
            self.acquired.set()
            self.release.wait(self.seconds)

    def __enter__(self) -> _HeldLock:
        self.thread.start()
        self.acquired.wait(5)
        return self

    def __exit__(self, *exc: object) -> None:
        self.release.set()
        self.thread.join(5)


class TestLockPath(unittest.TestCase):
    def test_lock_file_is_a_sibling_of_the_resolved_wiki(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "knowledge" / "wiki"
            wiki.mkdir(parents=True)
            self.assertEqual(lock_path_for(wiki), wiki.resolve().parent / f".wiki{LOCK_FILE_SUFFIX}")
            self.assertFalse(lock_path_for(wiki).is_relative_to(wiki.resolve()))

    def test_two_spellings_of_one_wiki_share_the_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wiki = root / "knowledge" / "wiki"
            wiki.mkdir(parents=True)
            alias = root / "alias"
            alias.symlink_to(wiki, target_is_directory=True)
            dotted = root / "knowledge" / "." / "wiki"
            self.assertEqual(lock_path_for(alias), lock_path_for(wiki))
            self.assertEqual(lock_path_for(dotted), lock_path_for(wiki))


class TestAcquireRelease(unittest.TestCase):
    def test_diagnostics_are_written_and_the_file_is_never_removed(self) -> None:
        for backend in BACKENDS:
            with self.subTest(backend=backend.name), tempfile.TemporaryDirectory() as tmp:
                wiki = Path(tmp) / "wiki"
                wiki.mkdir()
                lock = WikiLock(wiki, timeout=1, backend=backend)
                self.assertFalse(lock.held)
                with lock:
                    self.assertTrue(lock.held)
                    text = lock.lock_path.read_text(encoding="utf-8")
                    self.assertIn(f"pid={os.getpid()}", text)
                    self.assertIn("host=", text)
                    self.assertIn("started=", text)
                self.assertFalse(lock.held)
                self.assertTrue(lock.lock_path.is_file(), "the lock file is never deleted")
                lock.release()  # idempotent

    def test_lock_file_parent_is_created_for_a_wiki_that_does_not_exist_yet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "new" / "wiki"
            with WikiLock(wiki, timeout=1) as lock:
                self.assertTrue(lock.lock_path.is_file())
            self.assertFalse(wiki.exists())

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "O_NOFOLLOW is a POSIX flag")
    def test_a_symlink_at_the_lock_path_is_refused_not_written_through(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            wiki.mkdir()
            target = Path(tmp) / "victim"
            target.write_text("keep\n", encoding="utf-8")
            lock_path_for(wiki).symlink_to(target)
            with self.assertRaises(OSError):
                WikiLock(wiki, timeout=1).acquire()
            self.assertEqual(target.read_text(encoding="utf-8"), "keep\n")

    def test_double_acquire_on_one_object_is_an_error(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmp,
            WikiLock(Path(tmp) / "wiki", timeout=1) as lock,
            self.assertRaises(RuntimeError),
        ):
            lock.acquire()


class TestContention(unittest.TestCase):
    def test_timeout_is_exit_10_with_reason_lock_timeout(self) -> None:
        for backend in BACKENDS:
            with self.subTest(backend=backend.name), tempfile.TemporaryDirectory() as tmp:
                wiki = Path(tmp) / "wiki"
                wiki.mkdir()
                with _HeldLock(wiki, backend):
                    started = time.monotonic()
                    with self.assertRaises(PromoteApplyError) as ctx:
                        WikiLock(wiki, timeout=0.2, backend=backend).acquire()
                    self.assertGreaterEqual(time.monotonic() - started, 0.2)
                self.assertEqual(ctx.exception.reason, REASON_LOCK_TIMEOUT)
                self.assertEqual(ctx.exception.exit_code, 10)
                self.assertIn("--lock-timeout", str(ctx.exception))

    def test_second_holder_waits_and_records_the_wait(self) -> None:
        for backend in BACKENDS:
            with self.subTest(backend=backend.name), tempfile.TemporaryDirectory() as tmp:
                wiki = Path(tmp) / "wiki"
                wiki.mkdir()
                with _HeldLock(wiki, backend, seconds=0.3), WikiLock(wiki, timeout=5, backend=backend) as second:
                    self.assertGreater(second.wait_seconds, 0.2)
                    self.assertTrue(second.held)

    def test_the_msvcrt_backend_refuses_to_run_off_windows(self) -> None:
        if sys.platform == "win32":
            self.skipTest("Windows runs the msvcrt backend")
        backend = MsvcrtBackend()
        self.assertEqual(backend.name, "msvcrt")
        with self.assertRaises(RuntimeError):
            backend.try_lock(0)
        with self.assertRaises(RuntimeError):
            backend.unlock(0)

    def test_an_exception_inside_the_block_releases_the_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            wiki.mkdir()
            with self.assertRaises(ValueError), WikiLock(wiki, timeout=1):
                raise ValueError("boom")
            with WikiLock(wiki, timeout=0.1) as again:
                self.assertLess(again.wait_seconds, 0.1)

    def test_a_failed_acquisition_closes_its_descriptor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            wiki.mkdir()
            with _HeldLock(wiki, BACKENDS[0]), patch("wiki_studio.wikilock.os.close") as close:
                with self.assertRaises(PromoteApplyError):
                    WikiLock(wiki, timeout=0.05).acquire()
                close.assert_called_once()


class TestLockIsInvisibleToTheWiki(unittest.TestCase):
    def test_promote_leaves_the_lock_outside_the_wiki_and_lint_never_sees_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo_layout(Path(tmp), with_schema=True, with_sample=False)
            paths = WikiPaths.for_root(root)
            api.promote(_proposals_dir(root), paths)
            lock_file = lock_path_for(paths.wiki_dir)
            self.assertTrue(lock_file.is_file())
            self.assertEqual(lock_file.parent, paths.wiki_dir.parent)
            self.assertFalse(any(p.name.endswith(LOCK_FILE_SUFFIX) for p in paths.wiki_dir.rglob("*")))
            self.assertFalse(any(p.name.endswith(LOCK_FILE_SUFFIX) for p in list_pages(paths.wiki_dir)))
            self.assertTrue(api.lint(paths).passed)
            # A second promote stages a copy of the wiki: the staged tree has no lock file either.
            second = _proposals_dir(root, slug="second")
            with patch("wiki_studio.promoter._validate_staged_tree", side_effect=_assert_no_lock_in_stage):
                api.promote(second, paths)


def _assert_no_lock_in_stage(stage_dir: Path, *_: object, **__: object) -> None:
    offenders = [p for p in stage_dir.rglob("*") if p.name.endswith(LOCK_FILE_SUFFIX)]
    if offenders:
        raise AssertionError(f"lock file staged: {offenders}")


class TestTimeoutConfiguration(unittest.TestCase):
    def test_default_flag_and_environment_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(WikiPaths.for_root(root).lock_timeout, DEFAULT_LOCK_TIMEOUT)
            self.assertEqual(WikiPaths.resolve(root=root, env={ENV_LOCK_TIMEOUT: "2.5"}).lock_timeout, 2.5)
            self.assertEqual(WikiPaths.resolve(root=root, lock_timeout=1, env={ENV_LOCK_TIMEOUT: "9"}).lock_timeout, 1)
            with self.assertRaises(ValueError):
                WikiPaths.resolve(root=root, env={ENV_LOCK_TIMEOUT: "soon"})
            with self.assertRaises(ValueError):
                WikiPaths.resolve(root=root, lock_timeout=-1)

    def test_cli_flag_before_and_after_the_verb_and_info(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo_layout(Path(tmp), with_schema=True, with_sample=False)
            before = run_cli("--lock-timeout", "3", "info", "--json", cwd=root)
            after = run_cli("info", "--json", "--lock-timeout", "4", cwd=root)
            self.assertEqual(before.returncode, 0, before.stderr)
            self.assertEqual(json.loads(before.stdout)["lock_timeout"], 3)
            self.assertEqual(json.loads(after.stdout)["lock_timeout"], 4)
            self.assertEqual(json.loads(after.stdout)["lock_file"], str(lock_path_for(root / "knowledge" / "wiki")))
            with patch.dict(os.environ, {ENV_LOCK_TIMEOUT: "7"}):
                env = run_cli("info", cwd=root)
            self.assertIn("timeout 7s", env.stdout)

    def test_cli_promote_times_out_with_exit_10(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo_layout(Path(tmp), with_schema=True, with_sample=False)
            prop = _proposals_dir(root)
            with _HeldLock(root / "knowledge" / "wiki", BACKENDS[0]):
                result = run_cli("promote", str(prop), "--lock-timeout", "0.1", cwd=root)
            self.assertEqual(result.returncode, 10, result.stderr)
            self.assertIn("[reason=lock_timeout]", result.stderr)
            self.assertFalse((root / "knowledge" / "wiki" / "incidents").exists())
            self.assertFalse((prop / "receipt.json").exists())


if __name__ == "__main__":
    unittest.main()
