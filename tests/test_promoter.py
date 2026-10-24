# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""wiki_studio.promoter: patch-set loading, apply-time guards, the audit archive and idempotency."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.conftest import make_repo_layout
from tests.test_cli_contract import _proposals_dir
from wiki_studio.errors import PromoteApplyError, PromoteValidationError
from wiki_studio.paths import WikiPaths
from wiki_studio.promoter import promote


def _plan(prop: Path) -> dict:
    return json.loads((prop / "plan.json").read_text(encoding="utf-8"))


def _write_plan(prop: Path, plan: dict) -> None:
    (prop / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")


class _LayoutCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-promoter-")
        self.root = make_repo_layout(Path(self._tmp.name), with_schema=True, with_sample=False)
        self.paths = WikiPaths.for_root(self.root)
        self.wiki = self.paths.wiki_dir

    def tearDown(self) -> None:
        self._tmp.cleanup()


class TestLoadPatch(_LayoutCase):
    def test_missing_plan_json(self) -> None:
        # A non-empty directory without plan.json (or receipt.json) is not a proposal.
        prop = self.paths.proposals_dir / "2026-05-06-no-plan"
        (prop / "preview").mkdir(parents=True)
        (prop / "preview" / "stray.md").write_text("x\n", encoding="utf-8")
        with self.assertRaises(PromoteValidationError) as ctx:
            promote(prop, self.paths)
        self.assertIn("plan.json not found", str(ctx.exception))
        self.assertTrue(prop.is_dir())

    def test_empty_leftover_directory_is_removed(self) -> None:
        # The remains of an interrupted cleanup: neither receipt.json nor plan.json, and empty.
        prop = self.paths.proposals_dir / "2026-05-06-leftover"
        prop.mkdir(parents=True)
        result = promote(prop, self.paths)
        self.assertEqual(result.applied_paths, [])
        self.assertIsNone(result.archived_dir)
        self.assertFalse(prop.exists())

    def test_invalid_json(self) -> None:
        prop = _proposals_dir(self.root)
        (prop / "plan.json").write_text("{not json", encoding="utf-8")
        with self.assertRaises(PromoteValidationError) as ctx:
            promote(prop, self.paths)
        self.assertIn("not valid JSON", str(ctx.exception))

    def test_edit_without_preview_pointer(self) -> None:
        prop = _proposals_dir(self.root)
        plan = _plan(prop)
        del plan["edits"][0]["preview"]
        _write_plan(prop, plan)
        with self.assertRaises(PromoteValidationError) as ctx:
            promote(prop, self.paths)
        self.assertIn("missing 'preview' pointer", str(ctx.exception))

    def test_missing_preview_file(self) -> None:
        prop = _proposals_dir(self.root)
        (prop / "preview" / "log.md").unlink()
        with self.assertRaises(PromoteValidationError) as ctx:
            promote(prop, self.paths)
        self.assertIn("preview file referenced by plan.json missing", str(ctx.exception))


class TestApplyGuards(_LayoutCase):
    """Apply-time checks on the staged tree, reached before validation."""

    def _with_action(self, action: str, path: str) -> Path:
        prop = _proposals_dir(self.root)
        plan = _plan(prop)
        plan["edits"] = [{"path": path, "action": action, "rationale": "r", "preview": "preview/log.md"}]
        _write_plan(prop, plan)
        return prop

    def test_create_over_existing_page_is_a_validation_error(self) -> None:
        prop = _proposals_dir(self.root)
        (self.wiki / "incidents").mkdir()
        (self.wiki / "incidents" / "cli-fixture.md").write_text("# existing\n", encoding="utf-8")
        with self.assertRaises(PromoteValidationError) as ctx:
            promote(prop, self.paths)
        self.assertEqual(ctx.exception.exit_code, 9)
        self.assertIn("create target already exists", str(ctx.exception))

    def test_update_of_missing_page_is_a_validation_error(self) -> None:
        prop = _proposals_dir(self.root)
        plan = _plan(prop)
        plan["edits"] = [
            {
                "path": "incidents/nope.md",
                "action": "update",
                "rationale": "r",
                "preview": "preview/incidents/cli-fixture.md",
            }
        ]
        _write_plan(prop, plan)
        with self.assertRaises(PromoteValidationError) as ctx:
            promote(prop, self.paths)
        self.assertIn("update target does not exist", str(ctx.exception))

    def test_path_escape_is_rejected_before_anything_is_written(self) -> None:
        for bad in ("../escape.md", "/tmp/wiki_studio-escape.md"):
            with self.subTest(path=bad):
                prop = _proposals_dir(self.root, slug=f"esc-{len(bad)}")
                plan = _plan(prop)
                plan["edits"][0]["path"] = bad
                _write_plan(prop, plan)
                with self.assertRaises(PromoteValidationError) as ctx:
                    promote(prop, self.paths)
                self.assertIn("path must be relative", str(ctx.exception))
        self.assertFalse((self.wiki.parent / "escape.md").exists())
        self.assertFalse(Path("/tmp/wiki_studio-escape.md").exists())

    def test_apply_time_containment_guard(self) -> None:
        from wiki_studio.promoter import _apply_edit
        from wiki_studio.proposal import PageEdit

        with self.assertRaises(PromoteValidationError):
            _apply_edit(self.wiki, PageEdit(path="../x.md", action="create", new_content="x", rationale="r"))
        self.assertFalse((self.wiki.parent / "x.md").exists())

    def test_malformed_plan_edit_is_a_validation_error(self) -> None:
        prop = _proposals_dir(self.root)
        plan = _plan(prop)
        del plan["edits"][0]["action"]
        _write_plan(prop, plan)
        with self.assertRaises(PromoteValidationError) as ctx:
            promote(prop, self.paths)
        self.assertIn("'path' and 'action'", str(ctx.exception))

    def test_append_log_without_log(self) -> None:
        (self.wiki / "log.md").unlink()
        with self.assertRaises(PromoteApplyError) as ctx:
            promote(self._with_action("append-log", "log.md"), self.paths)
        self.assertIn("log.md does not exist", str(ctx.exception))

    def test_append_index_without_index(self) -> None:
        (self.wiki / "index.md").unlink()
        with self.assertRaises(PromoteApplyError) as ctx:
            promote(self._with_action("append-index", "index.md"), self.paths)
        self.assertIn("index.md does not exist", str(ctx.exception))

    def test_unknown_action_is_a_validation_error(self) -> None:
        with self.assertRaises(PromoteValidationError) as ctx:
            promote(self._with_action("rename", "log.md"), self.paths)
        self.assertIn("unknown action", str(ctx.exception))

    def test_missing_wiki_cannot_be_staged(self) -> None:
        prop = _proposals_dir(self.root)
        shutil.rmtree(self.wiki)
        with self.assertRaises(PromoteApplyError) as ctx:
            promote(prop, self.paths)
        self.assertIn("wiki source not found", str(ctx.exception))

    def test_set_level_validation_rejects_duplicate_create(self) -> None:
        prop = _proposals_dir(self.root)
        plan = _plan(prop)
        plan["edits"].append(dict(plan["edits"][0], path="incidents/other.md"))
        plan["edits"][-1]["path"] = plan["edits"][0]["path"]
        _write_plan(prop, plan)
        with self.assertRaises(PromoteValidationError) as ctx:
            promote(prop, self.paths)
        self.assertIn("duplicate create", str(ctx.exception))


class TestAuditArchive(_LayoutCase):
    def test_archive_has_plan_and_rendered_proposal(self) -> None:
        prop = _proposals_dir(self.root)
        promote(prop, self.paths)
        archive = self.wiki / ".audit" / "proposals" / "2026-05-06-cli-fixture"
        self.assertTrue((archive / "plan.json").is_file())
        rendered = (archive / "proposal.md").read_text(encoding="utf-8")
        self.assertIn("# Proposal: 2026-05-06-cli-fixture", rendered)
        self.assertIn("## incidents/cli-fixture.md", rendered)
        self.assertFalse((archive / "curator-delta.md").exists())

    def test_curator_delta_records_edits_since_the_snapshot(self) -> None:
        prop = _proposals_dir(self.root)
        snapshot = prop / ".ingest-snapshot" / "preview" / "incidents"
        snapshot.mkdir(parents=True)
        original = (prop / "preview" / "incidents" / "cli-fixture.md").read_text(encoding="utf-8")
        (snapshot / "cli-fixture.md").write_text(original.replace("Body.", "Draft body."), encoding="utf-8")
        (prop / ".ingest-snapshot" / "preview" / "removed.md").write_text("gone\n", encoding="utf-8")
        promote(prop, self.paths)
        delta = (self.wiki / ".audit" / "proposals" / "2026-05-06-cli-fixture" / "curator-delta.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("--- a/incidents/cli-fixture.md", delta)
        self.assertIn("-Draft body.", delta)
        self.assertIn("+Body.", delta)
        self.assertIn("--- a/removed.md", delta)

    def test_archive_name_collision_gets_a_numeric_suffix(self) -> None:
        promote(_proposals_dir(self.root), self.paths)
        second = _proposals_dir(self.root, slug="second")
        renamed = second.parent / "2026-05-06-cli-fixture"
        second.rename(renamed)
        promote(renamed, self.paths)
        self.assertTrue((self.wiki / ".audit" / "proposals" / "2026-05-06-cli-fixture-2" / "plan.json").is_file())
        self.assertTrue((self.wiki / "incidents" / "second.md").is_file())


class TestIdempotency(_LayoutCase):
    def test_empty_patch_set_is_archived_without_changes(self) -> None:
        prop = _proposals_dir(self.root)
        plan = _plan(prop)
        plan["edits"] = []
        _write_plan(prop, plan)
        before = (self.wiki / "index.md").read_text(encoding="utf-8")
        result = promote(prop, self.paths)
        self.assertEqual(result.applied_paths, [])
        self.assertEqual(result.archived_dir, self.paths.applied_dir / prop.name)
        self.assertEqual((self.wiki / "index.md").read_text(encoding="utf-8"), before)
        dry = promote(_proposals_dir(self.root, slug="empty-dry"), self.paths, dry_run=True)
        self.assertTrue(dry.dry_run)

    def test_identical_content_is_a_no_op_write(self) -> None:
        prop = _proposals_dir(self.root)
        first = promote(prop, self.paths)
        self.assertIn("incidents/cli-fixture.md", first.applied_paths)
        # The same page again as an update with identical content: nothing to write for it.
        again = _proposals_dir(self.root, slug="cli-fixture-again")
        plan = _plan(again)
        plan["edits"] = [
            {"path": "incidents/cli-fixture.md", "action": "update", "rationale": "r", "preview": "preview/same.md"}
        ]
        (again / "preview" / "same.md").write_text(
            (self.wiki / "incidents" / "cli-fixture.md").read_text(encoding="utf-8"), encoding="utf-8"
        )
        _write_plan(again, plan)
        result = promote(again, self.paths)
        self.assertNotIn("incidents/cli-fixture.md", result.applied_paths)
        self.assertTrue(any(p.startswith(".audit/proposals/") for p in result.applied_paths))


class TestValidationAndFailures(_LayoutCase):
    def test_set_level_validation_rejects_append_log_to_another_page(self) -> None:
        prop = _proposals_dir(self.root)
        plan = _plan(prop)
        plan["edits"] = [{"path": "index.md", "action": "append-log", "rationale": "r", "preview": "preview/log.md"}]
        _write_plan(prop, plan)
        with self.assertRaises(PromoteValidationError) as ctx:
            promote(prop, self.paths)
        self.assertIn("append-log targets must be log.md", str(ctx.exception))

    def test_structural_lint_rejects_a_broken_link_in_the_staged_tree(self) -> None:
        prop = _proposals_dir(self.root)
        page = prop / "preview" / "incidents" / "cli-fixture.md"
        page.write_text(page.read_text(encoding="utf-8") + "\nSee [gone](gone.md).\n", encoding="utf-8")
        with self.assertRaises(PromoteValidationError) as ctx:
            promote(prop, self.paths)
        self.assertIn("Structural linter rejected staged tree", str(ctx.exception))
        self.assertIn("broken intra-wiki link → gone.md", str(ctx.exception))
        self.assertFalse((self.wiki / "incidents").exists())

    def test_archive_failure_after_commit_is_not_a_promote_failure(self) -> None:
        prop = _proposals_dir(self.root)
        with patch("wiki_studio.promoter._publish_archive", side_effect=OSError("disk full")):
            result = promote(prop, self.paths)
        self.assertEqual(len(result.applied_paths), 5)
        self.assertIsNone(result.archived_dir)
        self.assertTrue(prop.exists())
        self.assertTrue((self.wiki / "incidents" / "cli-fixture.md").is_file())
        # The receipt records the outcome; no partial archive sits at an applied name.
        receipt = json.loads((prop / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["state"], "committed")
        self.assertFalse((self.paths.applied_dir / prop.name).exists())

    def test_unreadable_live_page_aborts_before_any_write(self) -> None:
        prop = _proposals_dir(self.root)
        real_read = Path.read_bytes

        def failing_read(self_: Path, *args, **kwargs):  # noqa: ANN001, ANN202
            if self_.name == "log.md" and "knowledge/wiki" in str(self_):
                raise OSError("permission denied")
            return real_read(self_, *args, **kwargs)

        index_before = (self.wiki / "index.md").read_text(encoding="utf-8")
        with patch.object(Path, "read_bytes", failing_read), self.assertRaises(PromoteApplyError) as ctx:
            promote(prop, self.paths)
        self.assertIn("could not read existing wiki file for backup", str(ctx.exception))
        self.assertEqual((self.wiki / "index.md").read_text(encoding="utf-8"), index_before)
        self.assertFalse((self.wiki / "incidents").exists())


if __name__ == "__main__":
    unittest.main()
