# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The recorder's attempt manifest on every way out (FR-014, examples/correction-loop/README.md step 4).

``record.py`` writes ``manifest.json`` with ``outcome: running`` as soon as the run directory
exists, rewrites it at each stage, and ends it as ``outcome: failed`` with ``failed_stage`` for any
exception, an interrupt included, before re-raising. These tests stub only the preflight (a clean
tree, a commit, ``poetry`` on PATH) and inject failures into the attempt; nothing is built,
downloaded or run.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest import mock

if TYPE_CHECKING:
    from types import ModuleType

RECORD = Path(__file__).resolve().parents[1] / "examples" / "correction-loop" / "record.py"
COMMIT = "a" * 40
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"


def _load_record() -> ModuleType:
    spec = importlib.util.spec_from_file_location("correction_loop_record", RECORD)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AttemptManifestTest(unittest.TestCase):
    def setUp(self) -> None:
        self.record = _load_record()
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki-studio-record-test-")
        self.out = Path(self._tmp.name) / "run"
        clean = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        patches = [
            mock.patch.object(self.record, "_run", return_value=clean),
            mock.patch.object(self.record, "_git_output", return_value=COMMIT),
            mock.patch.object(self.record.shutil, "which", return_value="/usr/bin/poetry"),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _manifest(self) -> dict[str, Any]:
        data: dict[str, Any] = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        return data

    def _fail_at_extract(self, exc: BaseException) -> None:
        def raise_it(tmp: Path, commit: str) -> Path:
            # The running marker is on disk before the first stage does any work.
            marker = self._manifest()
            self.assertEqual((marker["outcome"], marker["stage"], marker["git_commit"]), ("running", "extract", COMMIT))
            raise exc

        mock.patch.object(self.record, "_extract_commit", side_effect=raise_it).start()
        self.addCleanup(mock.patch.stopall)

    def test_a_keyboard_interrupt_leaves_a_failed_manifest_and_propagates(self) -> None:
        self._fail_at_extract(KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt):
            self.record._record(self.out, REVISION)
        manifest = self._manifest()
        self.assertEqual(manifest["outcome"], "failed")
        self.assertEqual(manifest["failed_stage"], "extract")
        self.assertEqual(manifest["error"], "KeyboardInterrupt")
        self.assertNotIn("stage", manifest)
        self.assertIn("finished_at", manifest)

    def test_a_system_exit_leaves_a_failed_manifest_and_propagates(self) -> None:
        self._fail_at_extract(SystemExit(3))
        with self.assertRaises(SystemExit) as raised:
            self.record._record(self.out, REVISION)
        self.assertEqual(raised.exception.code, 3)
        manifest = self._manifest()
        self.assertEqual((manifest["outcome"], manifest["failed_stage"]), ("failed", "extract"))
        self.assertEqual(manifest["error"], "SystemExit: 3")

    def test_an_interrupt_in_a_later_stage_names_that_stage(self) -> None:
        source = Path(self._tmp.name) / "source"
        demo_dir = source / "examples" / "correction-loop"
        demo_dir.mkdir(parents=True)
        for name in ("demo.py", "README.md"):
            (demo_dir / name).write_text(name, encoding="utf-8")
        (demo_dir / "record.py").write_bytes(RECORD.read_bytes())
        mock.patch.object(self.record, "_extract_commit", return_value=source).start()
        mock.patch.object(self.record, "_build_wheel", side_effect=KeyboardInterrupt()).start()
        self.addCleanup(mock.patch.stopall)
        with self.assertRaises(KeyboardInterrupt):
            self.record._record(self.out, REVISION)
        manifest = self._manifest()
        self.assertEqual((manifest["outcome"], manifest["failed_stage"]), ("failed", "build"))
        self.assertEqual(len(manifest["demo_sha256"]), 64)

    def test_an_ordinary_failure_exits_two_through_main_with_a_failed_manifest(self) -> None:
        self._fail_at_extract(self.record.CannotRunError("archive refused"))
        self.assertEqual(self.record.main(["--out", str(self.out)]), 2)
        manifest = self._manifest()
        self.assertEqual((manifest["outcome"], manifest["failed_stage"]), ("failed", "extract"))
        self.assertEqual(manifest["error"], "CannotRunError: archive refused")

    def test_a_preflight_refusal_creates_no_attempt(self) -> None:
        self.out.mkdir()
        with self.assertRaises(self.record.CannotRunError):
            self.record._record(self.out, REVISION)
        self.assertFalse((self.out / "manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
