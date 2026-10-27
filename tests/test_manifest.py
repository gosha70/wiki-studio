# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.7.0 (US2): the root manifest ``init`` writes, how every writer reads it, and the legacy wiki (FR-006, FR-011)."""

from __future__ import annotations

import json
import tempfile
import unittest
import uuid
import warnings
from pathlib import Path
from unittest.mock import patch

from tests.conftest import run_cli
from wiki_studio import __version__, api, promoter
from wiki_studio.contract import (
    MANIFEST_VERSION,
    MODE_MANAGED,
    POLICY_KEYS,
    read_manifest,
)
from wiki_studio.errors import ContractViolationError, DriftWarning, OutputWriteError
from wiki_studio.lint import lint_wiki
from wiki_studio.paths import MANIFEST_NAME, WikiPaths
from wiki_studio.proposal import PageEdit
from wiki_studio.schema import SCHEMA_ID, SCHEMA_VERSION

DECISION = (
    "---\npage_type: decision\nslug: {slug}\ntitle: Retry backoff\nstatus: draft\nlast_reviewed: 2026-10-16\n"
    "sources:\n  - path: notes.md\n---\n\n# Retry backoff\n\n"
    "## Decision\n\nStart at 250 ms, double each attempt, cap at 8 s.\n\n"
    "## Context\n\nAgreed with the platform team.\n\n## Alternatives considered\n\nFixed 1 s delay.\n\n"
    "## Consequences\n\nLong outages wait at most 8 s between tries.\n"
)

EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def decision_edit(slug: str = "retry-backoff") -> list[PageEdit]:
    """One valid ``create`` edit and its index line."""
    return [
        PageEdit(f"decisions/{slug}.md", "create", DECISION.format(slug=slug), "why"),
        PageEdit("index.md", "append-index", f"- [Retry backoff](decisions/{slug}.md)", "why"),
    ]


class ManifestCase(unittest.TestCase):
    """A project root with ``notes.md`` (the pages' source) and the default layout, no wiki yet."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-manifest-")
        self.root = Path(self._tmp.name).resolve()
        (self.root / "notes.md").write_text("# notes\n", encoding="utf-8")
        self.paths = WikiPaths.for_root(self.root)
        self.wiki = self.paths.wiki_dir
        self.manifest = self.wiki / MANIFEST_NAME

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def cli(self, *argv: str):  # noqa: ANN201 - test helper
        return run_cli(*argv, cwd=self.root)

    def edit_manifest(self, **changes: object) -> None:
        """Rewrite top-level manifest keys by hand, as a host would."""
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data.update(changes)
        self.manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def set_policy(self, **policy: bool) -> None:
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["policy"].update(policy)
        self.manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def tree(self) -> dict[str, bytes]:
        """Every regular file under the wiki, by wiki-relative path."""
        return {p.relative_to(self.wiki).as_posix(): p.read_bytes() for p in self.wiki.rglob("*") if p.is_file()}


class TestInitWritesTheManifest(ManifestCase):
    def test_init_creates_the_manifest_with_every_key(self) -> None:
        result = api.init(self.paths)
        self.assertEqual(result.manifest, "created")
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(data["manifest_version"], MANIFEST_VERSION)
        uuid.UUID(data["wiki_id"])
        self.assertEqual(data["schema"], {"id": SCHEMA_ID, "version": SCHEMA_VERSION})
        self.assertEqual(data["schema_fingerprint"], EMPTY_SHA256)
        self.assertEqual(data["policy"], dict.fromkeys(POLICY_KEYS, False))
        self.assertEqual(data["created_by"], {"package": "wiki-studio", "version": __version__})
        self.assertNotIn("schema_source", data, "derived on read, never persisted")
        self.assertEqual(read_manifest(self.paths).mode, MODE_MANAGED)  # type: ignore[union-attr]
        self.assertEqual(lint_wiki(self.wiki), [], "the manifest is not a page")

    def test_the_manifest_is_created_once_and_never_overwritten(self) -> None:
        api.init(self.paths)
        self.set_policy(approval_required=True)
        before = self.manifest.read_bytes()
        again = api.init(self.paths)
        self.assertEqual(again.manifest, "existing")
        self.assertEqual(self.manifest.read_bytes(), before)
        cli = self.cli("init")
        self.assertEqual(cli.returncode, 0, cli.stderr)
        self.assertIn("manifest: existing", cli.stdout)
        self.assertEqual(self.manifest.read_bytes(), before)

    def test_init_on_a_legacy_wiki_adds_the_manifest_and_touches_nothing_else(self) -> None:
        api.init(self.paths)
        api.promote(api.propose(decision_edit(), self.paths, name="first"), self.paths)
        self.manifest.unlink()
        before = self.tree()
        result = api.init(self.paths)
        self.assertEqual(result.created, [])
        self.assertEqual(result.manifest, "created")
        after = self.tree()
        self.assertEqual(after.pop(MANIFEST_NAME)[:1], b"{")
        self.assertEqual(after, before)


class TestManifestContainment(ManifestCase):
    def setUp(self) -> None:
        super().setUp()
        self.outside = self.root / "outside"
        self.outside.mkdir()

    def test_a_symlink_at_the_manifest_path_is_refused_and_its_target_untouched(self) -> None:
        self.wiki.mkdir(parents=True)
        target = self.outside / "target.json"
        target.write_text("victim\n", encoding="utf-8")
        self.manifest.symlink_to(target)
        with self.assertRaises(ContractViolationError) as ctx:
            api.init(self.paths)
        self.assertIn(MANIFEST_NAME, str(ctx.exception))
        self.assertEqual(target.read_text(encoding="utf-8"), "victim\n")
        self.assertFalse((self.wiki / "index.md").exists(), "refused before anything is written")
        self.assertEqual(self.cli("init").returncode, ContractViolationError.exit_code)

    def test_a_dangling_symlink_at_the_manifest_path_is_refused_and_nothing_is_created(self) -> None:
        self.wiki.mkdir(parents=True)
        target = self.outside / "absent.json"
        self.manifest.symlink_to(target)
        with self.assertRaises(ContractViolationError):
            api.init(self.paths)
        self.assertFalse(target.exists())

    def test_an_alias_spelling_of_the_wiki_directory_reaches_the_real_wiki(self) -> None:
        """Release A (FR-002) keeps alias spellings: the root is resolved once, then nothing below it is followed."""
        self.wiki.parent.mkdir(parents=True)
        real = self.outside / "real-wiki"
        real.mkdir()
        self.wiki.symlink_to(real, target_is_directory=True)
        api.init(self.paths)
        self.assertTrue(self.wiki.is_symlink(), "the alias stays a link")
        self.assertTrue((real / ".wiki-studio.json").is_file(), "the manifest lands in the real wiki")
        self.assertEqual(api.info(self.paths).manifest.state, "present", "contract reads through the alias succeed")

    def test_every_writer_refuses_a_symlinked_manifest_unread(self) -> None:
        api.init(self.paths)
        prop = api.propose(decision_edit(), self.paths, name="first")
        target = self.outside / "target.json"
        target.write_bytes(self.manifest.read_bytes())
        self.manifest.unlink()
        self.manifest.symlink_to(target)
        with self.assertRaises(ContractViolationError):
            api.propose(decision_edit("other"), self.paths, name="second")
        with self.assertRaises(ContractViolationError):
            api.promote(prop, self.paths)
        with self.assertRaises(ContractViolationError):
            api.info(self.paths)
        self.assertFalse((self.wiki / "decisions" / "retry-backoff.md").exists())


class TestMalformedManifest(ManifestCase):
    def setUp(self) -> None:
        super().setUp()
        api.init(self.paths)

    def assert_refused(self, *names: str) -> None:
        with self.assertRaises(ContractViolationError) as ctx:
            api.propose(decision_edit(), self.paths, name="p")
        for name in names:
            self.assertIn(name, str(ctx.exception))
        self.assertFalse((self.paths.proposals_dir / "p").exists())
        for argv in (("init",), ("info", "--json")):
            result = self.cli(*argv)
            self.assertEqual(result.returncode, ContractViolationError.exit_code, argv)
            for name in names:
                self.assertIn(name, result.stderr)

    def test_not_json(self) -> None:
        self.manifest.write_text("{not json", encoding="utf-8")
        self.assert_refused("malformed manifest")

    def test_a_missing_key_is_named(self) -> None:
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        del data["wiki_id"]
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        self.assert_refused("wiki_id", "missing")

    def test_a_wrong_type_is_named(self) -> None:
        self.set_policy(approval_required="yes")  # type: ignore[arg-type]
        self.assert_refused("policy.approval_required")

    def test_a_missing_policy_key_is_named(self) -> None:
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        del data["policy"]["auto_approve_on_promote"]
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        self.assert_refused("policy.auto_approve_on_promote")

    def test_a_bad_fingerprint_is_named(self) -> None:
        self.edit_manifest(schema_fingerprint="")
        self.assert_refused("schema_fingerprint")


class TestCompatibility(ManifestCase):
    """FR-011: a newer manifest or schema, or another schema identity, is exit 4 for every writer and init."""

    def setUp(self) -> None:
        super().setUp()
        api.init(self.paths)
        self.prop = api.propose(decision_edit(), self.paths, name="first")

    def assert_every_writer_refuses(self, *needles: str) -> None:
        checks = {
            "api.propose": lambda: api.propose(decision_edit("other"), self.paths, name="second"),
            "api.promote": lambda: api.promote(self.prop, self.paths),
            "api.promote dry run": lambda: api.promote(self.prop, self.paths, dry_run=True),
            "api.init": lambda: api.init(self.paths),
        }
        for label, call in checks.items():
            with self.subTest(label), self.assertRaises(ContractViolationError) as ctx:
                call()
            for needle in needles:
                self.assertIn(needle, str(ctx.exception), label)
        for argv in (("promote", str(self.prop)), ("init",), ("init", "--update-schema")):
            result = self.cli(*argv)
            self.assertEqual(result.returncode, ContractViolationError.exit_code, argv)
        self.assertFalse((self.wiki / "decisions" / "retry-backoff.md").exists())

    def test_a_newer_manifest_version_names_both_versions_and_the_upgrade(self) -> None:
        self.edit_manifest(manifest_version=MANIFEST_VERSION + 1)
        self.assert_every_writer_refuses(f"manifest_version {MANIFEST_VERSION + 1}", str(MANIFEST_VERSION), "upgrade")

    def test_a_newer_schema_version_names_both_versions_and_the_upgrade(self) -> None:
        self.edit_manifest(schema={"id": SCHEMA_ID, "version": SCHEMA_VERSION + 1})
        self.assert_every_writer_refuses(f"schema.version {SCHEMA_VERSION + 1}", str(SCHEMA_VERSION), "upgrade")

    def test_an_unknown_schema_id_with_a_supported_version_is_named(self) -> None:
        self.edit_manifest(schema={"id": "someone-else/page-schema", "version": SCHEMA_VERSION})
        self.assert_every_writer_refuses("someone-else/page-schema")


class TestLegacyWiki(ManifestCase):
    """A wiki without a manifest behaves as in 0.6.0."""

    def setUp(self) -> None:
        super().setUp()
        api.init(self.paths)
        self.manifest.unlink()

    def test_propose_and_promote_work_without_warnings_or_a_manifest(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            prop = api.propose(decision_edit(), self.paths, name="first")
        self.assertEqual([w for w in caught if issubclass(w.category, DriftWarning)], [])
        result = api.promote(prop, self.paths)
        self.assertEqual(result.warnings, [])
        self.assertTrue((self.wiki / "decisions" / "retry-backoff.md").is_file())
        self.assertFalse(self.manifest.exists(), "only init writes a manifest")

    def test_the_cli_verbs_work_and_say_nothing_about_a_contract(self) -> None:
        draft = self.root / "draft"
        (draft / "decisions").mkdir(parents=True)
        (draft / "decisions" / "retry-backoff.md").write_text(DECISION.format(slug="retry-backoff"), encoding="utf-8")
        (draft / "index.md").write_text("- [Retry backoff](decisions/retry-backoff.md)\n", encoding="utf-8")
        result = self.cli("propose", "--from", str(draft), "--name", "legacy", "--promote")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("warning", result.stderr)
        self.assertFalse(self.manifest.exists())


class TestUpdateSchema(ManifestCase):
    def setUp(self) -> None:
        super().setUp()
        api.init(self.paths)
        self.set_policy(approval_required=True)
        self.before = json.loads(self.manifest.read_text(encoding="utf-8"))

    def test_only_the_fingerprint_is_rewritten(self) -> None:
        (self.wiki / "schema").mkdir()
        (self.wiki / "schema" / "page-types.md").write_text("# local page types\n", encoding="utf-8")
        result = api.init(self.paths, update_schema=True)
        self.assertEqual(result.manifest, "updated")
        after = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertNotEqual(after.pop("schema_fingerprint"), self.before.pop("schema_fingerprint"))
        self.assertEqual(after, self.before, "wiki_id, policy and every other key are unchanged")
        self.assertEqual(sorted(p.name for p in self.wiki.iterdir() if p.name.startswith(".wiki")), [MANIFEST_NAME])

    def test_an_unchanged_schema_rewrites_nothing(self) -> None:
        before = self.manifest.read_bytes()
        result = self.cli("init", "--update-schema")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("manifest: existing", result.stdout)
        self.assertEqual(self.manifest.read_bytes(), before)

    def test_the_rewrite_replaces_the_manifest_and_never_writes_through_a_symlink(self) -> None:
        outside = self.root / "outside.json"
        outside.write_bytes(self.manifest.read_bytes())
        self.manifest.unlink()
        self.manifest.symlink_to(outside)
        (self.wiki / "schema").mkdir()
        (self.wiki / "schema" / "page-types.md").write_text("# local\n", encoding="utf-8")
        before = outside.read_bytes()
        with self.assertRaises(ContractViolationError):
            api.init(self.paths, update_schema=True)
        self.assertEqual(outside.read_bytes(), before)

    def test_update_schema_on_a_legacy_wiki_creates_the_manifest(self) -> None:
        self.manifest.unlink()
        self.assertEqual(api.init(self.paths, update_schema=True).manifest, "created")

    def test_the_path_based_fallback_creates_and_replaces_the_same_way(self) -> None:
        """Without dir_fd (Windows) the manifest is written by path, still exclusive and never in place."""
        self.manifest.unlink()
        with patch.object(promoter, "_DIR_FD_MANIFEST", False):
            self.assertEqual(api.init(self.paths).manifest, "created")
            (self.wiki / "schema").mkdir()
            (self.wiki / "schema" / "page-types.md").write_text("# local\n", encoding="utf-8")
            self.assertEqual(api.init(self.paths, update_schema=True).manifest, "updated")
        self.assertFalse(api.info(self.paths).schema_contract.drift)
        self.assertEqual(sorted(p.name for p in self.wiki.iterdir() if p.name.startswith(".wiki")), [MANIFEST_NAME])

    def test_a_failed_write_leaves_no_partial_manifest(self) -> None:
        self.manifest.unlink()
        with patch.object(promoter.os, "fsync", side_effect=OSError("disk full")), self.assertRaises(OutputWriteError):
            api.init(self.paths)
        self.assertFalse(self.manifest.exists())

    def test_a_failed_replace_keeps_the_manifest_and_leaves_no_temporary_file(self) -> None:
        (self.wiki / "schema").mkdir()
        (self.wiki / "schema" / "page-types.md").write_text("# local\n", encoding="utf-8")
        before = self.manifest.read_bytes()
        with patch.object(promoter.os, "replace", side_effect=OSError("no")), self.assertRaises(OutputWriteError):
            api.init(self.paths, update_schema=True)
        self.assertEqual(self.manifest.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in self.wiki.iterdir() if p.name.startswith(".wiki")), [MANIFEST_NAME])


class TestUnusualEntries(ManifestCase):
    def test_a_directory_at_the_manifest_path_is_malformed(self) -> None:
        api.init(self.paths)
        self.manifest.unlink()
        self.manifest.mkdir()
        with self.assertRaises(ContractViolationError) as ctx:
            api.info(self.paths)
        self.assertIn("not a regular file", str(ctx.exception))

    def test_an_override_that_is_not_utf8_is_refused(self) -> None:
        (self.wiki / "schema").mkdir(parents=True)
        (self.wiki / "schema" / "ingest-rules.md").write_bytes(b"\xff\xfe rules")
        with self.assertRaises(ContractViolationError) as ctx:
            api.info(self.paths)
        self.assertIn("UTF-8", str(ctx.exception))

    def test_a_directory_at_an_override_name_falls_back_to_the_packaged_copy(self) -> None:
        (self.wiki / "schema" / "page-types.md").mkdir(parents=True)
        self.assertEqual(api.info(self.paths).schema_contract.source, "packaged")


if __name__ == "__main__":
    unittest.main()
