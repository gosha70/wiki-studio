# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
# tests/test_audit_lint.py — Phase-1 audit-format lint + .audit/ reader exclusion.

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.test_approve import ApprovalCase
from wiki_studio import api
from wiki_studio.audit_lint import (
    INGEST_LOG_MARKER,
    validate_audit_dir,
)
from wiki_studio.health_lint import _list_wiki_pages as health_pages
from wiki_studio.wiki_state import _list_wiki_pages as state_pages

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "wiki_audit"
_HEX = "a" * 64


def _valid_record(**ov: object) -> dict:
    r = {
        "v": 1,
        "ts": "2026-05-17T14:03:22Z",
        "source_path": "specs/x/spec.md",
        "source_repo_relative": True,
        "source_sha": _HEX,
        "backend": "test",
        "disposition": "accept",
        "reason": "wiki-worthy: durable cross-session lesson.",
        "proposal_dir": "2026-05-17-x",
        "target_paths": ["concepts/a.md"],
        "page_types": ["concept"],
        "proposal_hash": _HEX,
    }
    r.update(ov)
    return r


def _write_audit(root: Path, lines: list) -> Path:
    audit = root / ".audit"
    audit.mkdir(parents=True)
    body = INGEST_LOG_MARKER + "\n\n" + "\n".join(json.dumps(x) if isinstance(x, dict) else x for x in lines) + "\n"
    (audit / "ingest-log.md").write_text(body, encoding="utf-8")
    return audit


class TestAuditFixtures(unittest.TestCase):
    def test_valid_fixture_is_clean(self) -> None:
        self.assertEqual(validate_audit_dir(_FIXTURES / "valid"), [])

    def test_each_invalid_fixture_flags_its_defect(self) -> None:
        expected = {
            "invalid-missing-marker": "line 1 must be exactly",
            "invalid-malformed-json": "not valid JSON",
            "invalid-missing-key": "missing keys ['proposal_hash']",
            "invalid-bad-enum": "disposition 'maybe' not in",
            "invalid-reason-too-long": "reason is 241 codepoints",
            "invalid-malformed-ts": "is not ISO-8601 UTC",
        }
        for case, needle in expected.items():
            errs = validate_audit_dir(_FIXTURES / case)
            self.assertTrue(errs, f"{case}: expected a violation, got none")
            self.assertTrue(
                any(needle in e for e in errs),
                f"{case}: no violation matched {needle!r}; got {errs}",
            )

    def test_absent_audit_tree_is_clean(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(validate_audit_dir(Path(td) / "nope"), [])


class TestAuditNestedConstraints(unittest.TestCase):
    def test_unsupported_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            audit = _write_audit(Path(td), [_valid_record(v=2)])
            errs = validate_audit_dir(audit)
            self.assertTrue(any("unsupported schema version" in e for e in errs))

    def test_array_items_must_be_strings(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            audit = _write_audit(
                Path(td),
                [_valid_record(target_paths=[123], page_types=[False])],
            )
            errs = validate_audit_dir(audit)
            self.assertTrue(
                any("'target_paths' must be an array of strings" in e for e in errs),
                errs,
            )

    def test_stray_top_level_entry_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            audit = _write_audit(Path(td), [_valid_record()])
            (audit / "notes.md").write_text("stray\n", encoding="utf-8")
            errs = validate_audit_dir(audit)
            self.assertTrue(
                any("unexpected entry under .audit/" in e for e in errs),
                errs,
            )

    def test_plan_json_as_directory_is_violation_not_exception(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            audit = _write_audit(Path(td), [_valid_record()])
            pdir = audit / "proposals" / "2026-05-17-x"
            pdir.mkdir(parents=True)
            (pdir / "plan.json").mkdir()  # a directory, not a file
            (pdir / "proposal.md").write_text("body\n", encoding="utf-8")
            errs = validate_audit_dir(audit)  # must not raise
            self.assertTrue(
                any("plan.json: must be a regular file" in e for e in errs),
                errs,
            )


class TestAuditReaderExclusion(unittest.TestCase):
    """`.audit/` must be invisible to the wiki-page readers."""

    def _wiki_with_audit(self, root: Path) -> Path:
        wiki = root / "knowledge" / "wiki"
        (wiki / "concepts").mkdir(parents=True)
        (wiki / "index.md").write_text("# index\n", encoding="utf-8")
        (wiki / "concepts" / "real.md").write_text("# real page\n", encoding="utf-8")
        adir = wiki / ".audit" / "proposals" / "2026-05-17-x"
        adir.mkdir(parents=True)
        (adir / "proposal.md").write_text("# archived\n", encoding="utf-8")
        (wiki / ".audit" / "ingest-log.md").write_text(INGEST_LOG_MARKER + "\n\n", encoding="utf-8")
        return wiki

    def test_wiki_state_skips_audit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            wiki = self._wiki_with_audit(Path(td))
            pages = state_pages(wiki)
            self.assertFalse(
                any(".audit" in p.parts for p in pages),
                [str(p) for p in pages],
            )

    def test_health_lint_skips_audit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            wiki = self._wiki_with_audit(Path(td))
            pages = health_pages(wiki)
            self.assertFalse(
                any(".audit" in p.parts for p in pages),
                [str(p) for p in pages],
            )


class TestAuditApprovals(ApprovalCase):
    """0.7.0 (FR-031): ``approvals/`` is admitted in ``.audit/``'s closed set and its tree is validated."""

    def setUp(self) -> None:
        super().setUp()
        self.rel = self.create("a")
        self.written = api.approve([self.rel], self.paths).published[0]
        self.audit = self.wiki / ".audit"
        self.record = self.wiki / self.written

    def errors(self) -> list[str]:
        return validate_audit_dir(self.audit)

    def test_a_tree_written_by_approve_is_clean(self) -> None:
        self.assertEqual(self.errors(), [])
        self.assertEqual(api.lint(self.paths).audit_errors, ())

    def test_unexpected_names_at_each_level_are_reported(self) -> None:
        approvals = self.audit / "approvals"
        (approvals / "other").mkdir()
        (approvals / "path" / "not-hex").mkdir()
        (approvals / "id" / "pg-short").mkdir(parents=True)
        (self.record.parent.parent / "not-a-policy").mkdir()
        (self.record.parent.parent.parent / "not-a-revision").mkdir()
        (self.record.parent / "rejected.json").write_text("{}", encoding="utf-8")
        joined = "\n".join(self.errors())
        for needle in (
            "only id/ and path/",
            "64 lowercase hex",
            "a page_id",
            "policy entries",
            "revision entries",
            "<decision>.json",
        ):
            self.assertIn(needle, joined)

    def test_a_record_invalid_for_its_location_is_reported(self) -> None:
        data = json.loads(self.record.read_text(encoding="utf-8"))
        data["decision"] = "rejected"
        self.record.write_text(json.dumps(data), encoding="utf-8")
        self.assertTrue(any("invalid approval record" in e for e in self.errors()), self.errors())
        data["decision"], data["page_key"] = "approved", "decisions/b.md"
        self.record.write_text(json.dumps(data), encoding="utf-8")
        self.assertTrue(any("page_key is not a canonical path" in e for e in self.errors()), self.errors())

    def test_symlinks_and_stray_temporary_files_are_reported(self) -> None:
        (self.record.parent / ".approved.json.123.abcd.tmp").write_text("{", encoding="utf-8")
        (self.record.parent.parent / ("b" * 64)).symlink_to(self.root)
        joined = "\n".join(self.errors())
        self.assertIn("stray temporary file", joined)
        self.assertIn("symlink in the approval tree", joined)

    def test_records_without_a_manifest_are_reported(self) -> None:
        self.manifest.unlink()
        self.assertTrue(any("need the wiki's manifest" in e for e in self.errors()), self.errors())

    def test_approvals_must_be_a_directory(self) -> None:
        shutil.rmtree(self.audit / "approvals")
        (self.audit / "approvals").write_text("x", encoding="utf-8")
        self.assertTrue(any("approvals must be a directory" in e for e in self.errors()))


if __name__ == "__main__":
    unittest.main()
