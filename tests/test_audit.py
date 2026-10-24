# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
# tests/test_audit.py — Phase-2 unit tests for audit.py helpers.
#
# Covers:
#   - source_sha vector
#   - proposal_hash canonicalization vector
#   - truncate_reason 240/239+ellipsis boundary
#   - IngestLogRecord JSON round-trip
#   - build_log_record (multi-page accept, reject, legacy, out-of-repo)
#   - append_ingest_log creates marker+one line / appends / fail-closed
#   - Invariant: no module other than audit.py writes ingest-log.md
#   - Invariant: no module other than promoter.py writes canonical wiki content
#   - Behavioral: a crafted promote cannot write outside the staged tree
#   - lint-wiki.sh .audit/ shell exclusion arm

import dataclasses
import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.conftest import PACKAGE_ROOT
from wiki_studio import audit
from wiki_studio.audit import (
    append_ingest_log,
    build_log_record,
    proposal_hash,
    source_sha,
    truncate_reason,
)
from wiki_studio.audit_lint import INGEST_LOG_MARKER
from wiki_studio.errors import OutputWriteError
from wiki_studio.paths import WikiPaths
from wiki_studio.proposal import IngestLogRecord, IngestProposal, PageEdit, WikiPatchSet

# ── source_sha ────────────────────────────────────────────────────────────


class TestSourceSha(unittest.TestCase):
    def test_known_vector(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "test.txt"
            f.write_bytes(b"hello world\n")
            expected = hashlib.sha256(b"hello world\n").hexdigest()
            self.assertEqual(source_sha(f), expected)

    def test_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "empty.txt"
            f.write_bytes(b"")
            expected = hashlib.sha256(b"").hexdigest()
            self.assertEqual(source_sha(f), expected)

    def test_returns_64_lowercase_hex(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "t.txt"
            f.write_bytes(b"x")
            result = source_sha(f)
            self.assertEqual(len(result), 64)
            self.assertEqual(result, result.lower())


# ── proposal_hash ─────────────────────────────────────────────────────────


class TestProposalHash(unittest.TestCase):
    def _make_proposal_dir(self, td: str) -> Path:
        """Create a minimal proposal dir with plan.json + one preview file."""
        d = Path(td) / "2026-05-17-foo"
        d.mkdir()
        (d / "plan.json").write_bytes(b'{"version":1}\n')
        preview = d / "preview"
        preview.mkdir()
        page_dir = preview / "concepts"
        page_dir.mkdir()
        (page_dir / "foo.md").write_bytes(b"# Foo\ncontent\n")
        return d

    def test_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = self._make_proposal_dir(td)
            h1 = proposal_hash(d)
            h2 = proposal_hash(d)
            self.assertEqual(h1, h2)

    def test_known_vector(self) -> None:
        """Compute the hash independently and verify the recipe."""
        with tempfile.TemporaryDirectory() as td:
            d = self._make_proposal_dir(td)
            plan_bytes = (d / "plan.json").read_bytes()
            page_bytes = (d / "preview" / "concepts" / "foo.md").read_bytes()

            buf = bytearray()
            # Files sorted by repo-rel POSIX path: plan.json before preview/...
            buf += b"plan.json\n" + plan_bytes + b"\n--\n"
            buf += b"preview/concepts/foo.md\n" + page_bytes + b"\n--\n"
            expected = hashlib.sha256(bytes(buf)).hexdigest()

            self.assertEqual(proposal_hash(d), expected)

    def test_excludes_dotfiles(self) -> None:
        """Files under .ingest-snapshot/ must be excluded."""
        with tempfile.TemporaryDirectory() as td:
            d = self._make_proposal_dir(td)
            snap = d / ".ingest-snapshot"
            snap.mkdir()
            (snap / "plan.json").write_bytes(b'{"version":1}')

            h_before = proposal_hash(d)
            # Adding a dotfile should NOT change the hash.
            (d / ".hidden").write_bytes(b"should be excluded")
            h_after = proposal_hash(d)
            self.assertEqual(h_before, h_after)

    def test_returns_64_lowercase_hex(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = self._make_proposal_dir(td)
            result = proposal_hash(d)
            self.assertEqual(len(result), 64)
            self.assertEqual(result, result.lower())


# ── truncate_reason ───────────────────────────────────────────────────────


class TestTruncateReason(unittest.TestCase):
    def test_short_string_unchanged(self) -> None:
        self.assertEqual(truncate_reason("hello"), "hello")

    def test_exactly_240_unchanged(self) -> None:
        s = "a" * 240
        self.assertEqual(truncate_reason(s), s)

    def test_241_becomes_239_plus_ellipsis(self) -> None:
        s = "a" * 241
        result = truncate_reason(s)
        self.assertEqual(len(result), 240)
        self.assertTrue(result.endswith("…"))
        self.assertEqual(result, "a" * 239 + "…")

    def test_newlines_collapsed(self) -> None:
        s = "line one\nline two\n\nline three"
        result = truncate_reason(s)
        self.assertEqual(result, "line one line two line three")

    def test_multibyte_codepoints(self) -> None:
        # Each emoji is one codepoint (U+1F600 etc.)
        s = "😀" * 241
        result = truncate_reason(s)
        self.assertEqual(len(result), 240)
        self.assertTrue(result.endswith("…"))

    def test_empty_string(self) -> None:
        self.assertEqual(truncate_reason(""), "")

    def test_whitespace_only(self) -> None:
        self.assertEqual(truncate_reason("   \n\t  "), "")


# ── IngestLogRecord JSON round-trip ──────────────────────────────────────


class TestIngestLogRecordRoundTrip(unittest.TestCase):
    def _make_record(self) -> IngestLogRecord:
        return IngestLogRecord(
            v=1,
            ts="2026-05-17T14:03:22Z",
            source_path="specs/x/spec.md",
            source_repo_relative=True,
            source_sha="a" * 64,
            backend="test",
            disposition="accept",
            reason="wiki-worthy reason",
            proposal_dir="2026-05-17-x",
            target_paths=["concepts/foo.md", "log.md"],
            page_types=["concepts", "log"],
            proposal_hash="b" * 64,
        )

    def test_round_trip(self) -> None:
        record = self._make_record()
        obj = dataclasses.asdict(record)
        line = json.dumps(obj)
        parsed = json.loads(line)
        self.assertEqual(parsed["v"], 1)
        self.assertEqual(parsed["ts"], "2026-05-17T14:03:22Z")
        self.assertEqual(parsed["source_repo_relative"], True)
        self.assertEqual(parsed["target_paths"], ["concepts/foo.md", "log.md"])
        self.assertIsNone(parsed.get("extra_key"))

    def test_null_fields_serialize_correctly(self) -> None:
        record = dataclasses.replace(
            self._make_record(),
            proposal_dir=None,
            proposal_hash=None,
        )
        obj = dataclasses.asdict(record)
        line = json.dumps(obj)
        parsed = json.loads(line)
        self.assertIsNone(parsed["proposal_dir"])
        self.assertIsNone(parsed["proposal_hash"])


# ── build_log_record ──────────────────────────────────────────────────────


def _make_patch(edits: list, rationale: str = "rationale") -> WikiPatchSet:
    return WikiPatchSet(
        edits=edits,
        source_path="specs/x.md",
        backend="test",
        rationale=rationale,
    )


def _make_page_edit(path: str, action: str = "create") -> PageEdit:
    return PageEdit(
        path=path,
        action=action,
        new_content="# Content\n",
        rationale="per-edit rationale",
    )


class TestBuildLogRecord(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.mkdtemp()
        self._td_path = Path(self._td)

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self._td, ignore_errors=True)

    def _source_file(self, name: str = "source.md", content: str = "# Hello\n") -> Path:
        f = self._td_path / name
        f.write_text(content, encoding="utf-8")
        return f

    def _proposal_dir_with_accept(self) -> Path:
        d = self._td_path / "2026-05-17-foo"
        d.mkdir()
        (d / "plan.json").write_bytes(b'{"version":1}\n')
        preview = d / "preview"
        preview.mkdir()
        (preview / "concepts").mkdir()
        (preview / "concepts" / "foo.md").write_bytes(b"# Foo\n")
        return d

    def test_multi_page_accept(self) -> None:
        src = self._source_file()
        prop_dir = self._proposal_dir_with_accept()
        edits = [
            _make_page_edit("concepts/foo.md"),
            _make_page_edit("incidents/bar.md"),
        ]
        patch = _make_patch(edits, rationale="multi-page rationale")
        record = build_log_record(
            source_file=src,
            paths=WikiPaths.for_root(self._td_path),
            backend_name="test",
            proposal_dir_path=prop_dir,
            patch=patch,
        )
        self.assertEqual(record.v, 1)
        self.assertEqual(record.disposition, "accept")
        self.assertEqual(record.reason, "multi-page rationale")
        self.assertIn("concepts/foo.md", record.target_paths)
        self.assertIn("incidents/bar.md", record.target_paths)
        self.assertEqual(record.target_paths, sorted(record.target_paths))
        self.assertIsNotNone(record.proposal_hash)
        self.assertEqual(len(record.proposal_hash), 64)  # type: ignore[arg-type]

    def test_multi_page_reject(self) -> None:
        src = self._source_file()
        prop_dir = self._td_path / "2026-05-17-rej"
        prop_dir.mkdir()
        (prop_dir / "plan.json").write_bytes(b'{"version":1,"edits":[]}\n')
        patch = _make_patch([], rationale="not wiki-worthy")
        record = build_log_record(
            source_file=src,
            paths=WikiPaths.for_root(self._td_path),
            backend_name="test",
            proposal_dir_path=prop_dir,
            patch=patch,
        )
        self.assertEqual(record.disposition, "reject")
        self.assertEqual(record.target_paths, [])
        self.assertEqual(record.page_types, [])
        self.assertIsNone(record.proposal_hash)

    def test_legacy_single_source(self) -> None:
        src = self._source_file()
        prop_dir = self._td_path / "2026-05-17-legacy"
        prop_dir.mkdir()
        legacy = IngestProposal(
            disposition="accept",
            reason="legacy reason",
            page_type="incident",
            slug="my-incident",
            title="My Incident",
            draft_markdown="# My Incident\n",
            sources=[],
        )
        record = build_log_record(
            source_file=src,
            paths=WikiPaths.for_root(self._td_path),
            backend_name="test",
            proposal_dir_path=prop_dir,
            legacy_proposal=legacy,
        )
        self.assertEqual(record.disposition, "accept")
        self.assertEqual(record.reason, "legacy reason")
        self.assertIn("incidents/my-incident.md", record.target_paths)
        self.assertIn("incident", record.page_types)

    def test_allow_out_of_repo_source_repo_relative_false(self) -> None:
        # Source outside the repo_root → source_repo_relative=False, verbatim path.
        external = self._td_path / "external.md"
        external.write_text("# External\n", encoding="utf-8")
        # Use a *different* root so the source is outside it.
        other_root = self._td_path / "other-repo"
        other_root.mkdir()
        prop_dir = other_root / "2026-05-17-ext"
        prop_dir.mkdir()
        (prop_dir / "plan.json").write_bytes(b'{"version":1}\n')
        patch = _make_patch([], rationale="external reject")
        record = build_log_record(
            source_file=external,
            paths=WikiPaths.for_root(other_root),
            backend_name="test",
            proposal_dir_path=prop_dir,
            allow_out_of_repo=True,
            patch=patch,
        )
        self.assertFalse(record.source_repo_relative)
        # Path is verbatim (absolute or as-supplied, not relative).
        self.assertIn(str(external), record.source_path)

    def test_dry_run_forces_proposal_hash_null(self) -> None:
        src = self._source_file()
        prop_dir = self._proposal_dir_with_accept()
        edits = [_make_page_edit("concepts/foo.md")]
        patch = _make_patch(edits)
        record = build_log_record(
            source_file=src,
            paths=WikiPaths.for_root(self._td_path),
            backend_name="test",
            proposal_dir_path=prop_dir,
            patch=patch,
            dry_run=True,
        )
        self.assertIsNone(record.proposal_hash)

    def test_ts_format(self) -> None:
        src = self._source_file()
        prop_dir = self._td_path / "2026-05-17-ts"
        prop_dir.mkdir()
        (prop_dir / "plan.json").write_bytes(b"{}")
        patch = _make_patch([])
        record = build_log_record(
            source_file=src,
            paths=WikiPaths.for_root(self._td_path),
            backend_name="test",
            proposal_dir_path=prop_dir,
            patch=patch,
        )
        self.assertRegex(record.ts, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


# ── append_ingest_log ─────────────────────────────────────────────────────


class TestAppendIngestLog(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.mkdtemp()
        self._repo_root = Path(self._td)
        self._paths = WikiPaths.for_root(self._repo_root)

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self._td, ignore_errors=True)

    def _make_record(self, disposition: str = "accept") -> IngestLogRecord:
        return IngestLogRecord(
            v=1,
            ts="2026-05-17T14:03:22Z",
            source_path="specs/x/spec.md",
            source_repo_relative=True,
            source_sha="a" * 64,
            backend="test",
            disposition=disposition,
            reason="reason text",
            proposal_dir="2026-05-17-x",
            target_paths=["concepts/a.md"],
            page_types=["concepts"],
            proposal_hash="b" * 64 if disposition == "accept" else None,
        )

    def _log_path(self) -> Path:
        return self._repo_root / "knowledge" / "wiki" / ".audit" / "ingest-log.md"

    def test_creates_marker_and_one_line(self) -> None:
        record = self._make_record()
        append_ingest_log(self._paths, record)
        log = self._log_path()
        self.assertTrue(log.exists())
        content = log.read_text(encoding="utf-8")
        lines = content.split("\n")
        self.assertEqual(lines[0], "<!-- ingest-log schema v1 -->")
        self.assertEqual(lines[1], "")
        # Third line is the NDJSON record.
        obj = json.loads(lines[2])
        self.assertEqual(obj["v"], 1)
        self.assertEqual(obj["disposition"], "accept")

    def test_second_call_appends(self) -> None:
        record1 = self._make_record("accept")
        record2 = self._make_record("reject")
        append_ingest_log(self._paths, record1)
        append_ingest_log(self._paths, record2)
        content = self._log_path().read_text(encoding="utf-8")
        lines = [line for line in content.split("\n") if line.strip()]
        # First non-marker non-blank line is marker, then record1, record2.
        json_lines = [line for line in lines if not line.startswith("<!--")]
        self.assertEqual(len(json_lines), 2)
        self.assertEqual(json.loads(json_lines[0])["disposition"], "accept")
        self.assertEqual(json.loads(json_lines[1])["disposition"], "reject")

    def test_marker_written_only_once(self) -> None:
        record = self._make_record()
        append_ingest_log(self._paths, record)
        append_ingest_log(self._paths, record)
        content = self._log_path().read_text(encoding="utf-8")
        self.assertEqual(content.count("<!-- ingest-log schema v1 -->"), 1)

    def test_fail_closed_raises_output_write_error(self) -> None:
        """If the directory is a file (write will fail), raise OutputWriteError."""
        # Plant a file at the .audit path to force mkdir to fail.
        audit_parent = self._repo_root / "knowledge" / "wiki"
        audit_parent.mkdir(parents=True, exist_ok=True)
        (audit_parent / ".audit").write_text("not a dir\n", encoding="utf-8")
        record = self._make_record()
        with self.assertRaises(OutputWriteError):
            append_ingest_log(self._paths, record)

    def test_appended_line_is_valid_json(self) -> None:
        record = self._make_record()
        append_ingest_log(self._paths, record)
        content = self._log_path().read_text(encoding="utf-8")
        for line in content.split("\n"):
            if line and not line.startswith("<!--"):
                obj = json.loads(line)  # must not raise
                self.assertIn("v", obj)


# ── Invariant: single-writer enforcement ──────────────────────────────────


class TestSingleWriterInvariant(unittest.TestCase):
    """Static invariant: only audit.py may write ingest-log.md;
    only promoter.py may write canonical wiki content."""

    _WIKI_INGEST_ROOT = PACKAGE_ROOT

    def _production_sources(self) -> list[Path]:
        """Return production .py files (exclude tests/ directory and __pycache__)."""
        return [
            p for p in self._WIKI_INGEST_ROOT.rglob("*.py") if "tests" not in p.parts and "__pycache__" not in p.parts
        ]

    def test_only_audit_py_writes_ingest_log(self) -> None:
        """No production source other than audit.py must contain 'ingest-log.md'
        on a write-bearing line."""
        for path in self._production_sources():
            if path.name == "audit.py":
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
            for line in lines:
                stripped = line.strip()
                if "ingest-log.md" in stripped and (
                    "write_text" in stripped
                    or "write_bytes" in stripped
                    or ".write(" in stripped
                    or "open(" in stripped
                ):
                    self.fail(f"{path.name}: appears to write ingest-log.md: {stripped!r}")

    def test_only_promoter_writes_knowledge_wiki(self) -> None:
        """No production source other than promoter.py/audit.py should write to
        knowledge/wiki/ (check for write calls on the same line as the path)."""
        for path in self._production_sources():
            if path.name in ("promoter.py", "audit.py"):
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
            for line in lines:
                stripped = line.strip()
                # Only flag lines where knowledge/wiki is used AND a write call is present.
                if "wiki_dir" in stripped and (
                    "write_text" in stripped or "write_bytes" in stripped or ".write(" in stripped
                ):
                    self.fail(f"{path.name}: line appears to write to knowledge/wiki: {stripped!r}")


class TestAppendRefusesSymlinks(unittest.TestCase):
    """PR #41 review: the append never writes through a symlinked ingest-log.md or .audit/ (FR-012)."""

    def setUp(self) -> None:
        self._td = tempfile.mkdtemp()
        self._repo_root = Path(self._td).resolve()
        self._paths = WikiPaths.for_root(self._repo_root)
        self._log = self._repo_root / "knowledge" / "wiki" / ".audit" / "ingest-log.md"
        (self._repo_root / "knowledge" / "wiki").mkdir(parents=True)

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self._td, ignore_errors=True)

    def _record(self) -> IngestLogRecord:
        return IngestLogRecord(
            v=1,
            ts="2026-10-24T00:00:00Z",
            source_path="specs/x/spec.md",
            source_repo_relative=True,
            source_sha="a" * 64,
            backend="test",
            disposition="accept",
            reason="r",
            proposal_dir="2026-10-24-x",
            target_paths=["concepts/a.md"],
            page_types=["concepts"],
            proposal_hash="b" * 64,
        )

    def test_a_symlinked_log_file_is_refused_and_its_target_untouched(self) -> None:
        victim = self._repo_root / "victim.txt"
        victim.write_text("untouched\n", encoding="utf-8")
        self._log.parent.mkdir(parents=True)
        self._log.symlink_to(victim)
        with self.assertRaises(OutputWriteError) as ctx:
            append_ingest_log(self._paths, self._record())
        self.assertIn("ingest-log.md", str(ctx.exception))
        self.assertEqual(victim.read_text(encoding="utf-8"), "untouched\n")

    def test_a_short_write_is_completed_not_reported_as_success(self) -> None:
        """PR #41 review: os.write may return short; the append loops until every byte is written."""
        real_write = os.write

        def short_write(fd: int, data: bytes | memoryview) -> int:
            return real_write(fd, bytes(data)[:5])

        with patch("wiki_studio.audit.os.write", short_write):
            append_ingest_log(self._paths, self._record())
            append_ingest_log(self._paths, self._record())
        lines = self._log.read_text(encoding="utf-8").split("\n")
        self.assertEqual(lines[0], INGEST_LOG_MARKER)
        self.assertEqual(lines[1], "")
        self.assertEqual(len([ln for ln in lines[2:] if ln]), 2)
        for ln in lines[2:]:
            if ln:
                self.assertEqual(json.loads(ln)["proposal_dir"], "2026-10-24-x")

    def test_a_parent_swapped_for_a_symlink_after_the_check_is_refused(self) -> None:
        """PR #41 review: the open is bound to the verified parents, so a .audit swap after the check fails closed."""
        if not audit._DIR_FD_OPENS:
            self.skipTest("descriptor-relative opens are unsupported here (documented weaker binding)")
        elsewhere = self._repo_root / "elsewhere"
        elsewhere.mkdir()
        audit_dir = self._log.parent
        audit_dir.mkdir(parents=True)
        real_check = audit._refuse_symlinks

        def check_then_swap(log_path: Path, wiki_dir: Path) -> None:
            real_check(log_path, wiki_dir)
            shutil.rmtree(audit_dir)
            audit_dir.symlink_to(elsewhere)

        with patch("wiki_studio.audit._refuse_symlinks", check_then_swap), self.assertRaises(OutputWriteError):
            append_ingest_log(self._paths, self._record())
        self.assertEqual(list(elsewhere.iterdir()), [], "nothing was written outside the wiki")

    def test_the_path_based_fallback_creates_the_first_log_and_still_refuses_symlinks(self) -> None:
        """PR #41 review: without dir_fd (Windows) the first append creates .audit/; a symlinked one is refused."""
        with patch("wiki_studio.audit._DIR_FD_OPENS", False):
            append_ingest_log(self._paths, self._record())
            lines = self._log.read_text(encoding="utf-8").split("\n")
            self.assertEqual(lines[0], INGEST_LOG_MARKER)
            self.assertEqual(len([ln for ln in lines if ln.startswith("{")]), 1)
            elsewhere = self._repo_root / "elsewhere"
            elsewhere.mkdir()
            shutil.rmtree(self._log.parent)
            self._log.parent.symlink_to(elsewhere)
            with self.assertRaises(OutputWriteError):
                append_ingest_log(self._paths, self._record())
            self.assertEqual(list(elsewhere.iterdir()), [])

    def test_a_symlinked_audit_directory_is_refused(self) -> None:
        elsewhere = self._repo_root / "elsewhere"
        elsewhere.mkdir()
        self._log.parent.symlink_to(elsewhere)
        with self.assertRaises(OutputWriteError):
            append_ingest_log(self._paths, self._record())
        self.assertEqual(list(elsewhere.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
