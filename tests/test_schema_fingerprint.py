# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.7.0 (US2): the one contained schema loader, the fingerprint recipe and drift (FR-007, FR-008, FR-009, FR-013)."""

from __future__ import annotations

import hashlib
import os
import warnings
from unittest.mock import patch

from tests.test_manifest import DECISION, EMPTY_SHA256, ManifestCase, decision_edit
from wiki_studio import api, contract
from wiki_studio.contract import load_schema, schema_fingerprint
from wiki_studio.errors import ContractViolationError, DriftWarning
from wiki_studio.prompt import load_schema_files


def _recipe(files: dict[str, bytes]) -> str:
    """FR-008 spelled out: sorted by name, each as UTF-8 name, NUL, raw bytes."""
    digest = hashlib.sha256()
    for name in sorted(files):
        digest.update(name.encode("utf-8") + b"\0" + files[name])
    return digest.hexdigest()


class TestFingerprintRecipe(ManifestCase):
    def setUp(self) -> None:
        super().setUp()
        self.schema = self.wiki / "schema"
        self.schema.mkdir(parents=True)

    def test_no_override_is_the_sha256_of_empty_input(self) -> None:
        self.assertEqual(schema_fingerprint({}), hashlib.sha256(b"").hexdigest())
        self.assertEqual(load_schema(self.paths).fingerprint, EMPTY_SHA256)
        self.assertEqual(load_schema(self.paths).source, "packaged")

    def test_the_recipe_over_the_present_overrides(self) -> None:
        files = {"page-types.md": b"# page types\r\n", "citation-rules.md": b"# citations\n"}
        for name, data in files.items():
            (self.schema / name).write_bytes(data)
        loaded = load_schema(self.paths)
        self.assertEqual(dict(loaded.overrides), files, "the exact bytes read")
        self.assertEqual(loaded.fingerprint, _recipe(files))
        self.assertEqual(loaded.source, "project")
        self.assertEqual(loaded.texts["page-types"], "# page types\r\n", "the prompt sees what is hashed")

    def test_one_changed_byte_changes_it(self) -> None:
        (self.schema / "ingest-rules.md").write_bytes(b"# rules\n")
        first = load_schema(self.paths).fingerprint
        (self.schema / "ingest-rules.md").write_bytes(b"# rulez\n")
        self.assertNotEqual(load_schema(self.paths).fingerprint, first)

    def test_a_line_ending_change_is_a_schema_change(self) -> None:
        (self.schema / "ingest-rules.md").write_bytes(b"# rules\n")
        first = load_schema(self.paths).fingerprint
        (self.schema / "ingest-rules.md").write_bytes(b"# rules\r\n")
        self.assertNotEqual(load_schema(self.paths).fingerprint, first)

    def test_it_does_not_depend_on_order(self) -> None:
        a, b = {"page-types.md": b"x"}, {"ingest-rules.md": b"y"}
        self.assertEqual(schema_fingerprint({**a, **b}), schema_fingerprint({**b, **a}))
        # Created in the reverse of the sorted order: the loader looks names up, it never lists the directory.
        (self.schema / "page-types.md").write_bytes(b"x")
        (self.schema / "ingest-rules.md").write_bytes(b"y")
        self.assertEqual(load_schema(self.paths).fingerprint, _recipe({**a, **b}))

    def test_unloaded_files_and_packaged_documents_never_enter_it(self) -> None:
        (self.schema / "lint-rules.md").write_text("# lint\n", encoding="utf-8")
        (self.schema / "notes.txt").write_text("x\n", encoding="utf-8")
        self.assertEqual(load_schema(self.paths).fingerprint, EMPTY_SHA256)
        self.assertEqual(load_schema(self.paths).source, "packaged")
        with patch.object(contract, "read_packaged_schema", return_value="# a newer packaged document\n"):
            self.assertEqual(load_schema(self.paths).fingerprint, EMPTY_SHA256)


class TestContainedLoader(ManifestCase):
    """FR-007: a symlinked override or schema directory is refused (exit 4) with its target unread."""

    def setUp(self) -> None:
        super().setUp()
        api.init(self.paths)
        self.outside = self.root / "outside"
        self.outside.mkdir()
        self.secret = self.outside / "page-types.md"
        self.secret.write_text("# not the wiki's\n", encoding="utf-8")

    def assert_refused_unread(self) -> None:
        opened: list[str] = []
        real_open = os.open

        def spy(path, *args, **kwargs):  # noqa: ANN001, ANN202 - test spy
            opened.append(os.fspath(path))
            return real_open(path, *args, **kwargs)

        with patch("wiki_studio.contract.os.open", spy):
            for call in (load_schema, load_schema_files, api.info):
                with self.subTest(call.__name__), self.assertRaises(ContractViolationError):
                    call(self.paths)
        self.assertFalse([p for p in opened if os.path.realpath(p).startswith(str(self.outside))], opened)
        self.assertEqual(self.cli("info").returncode, ContractViolationError.exit_code)

    def test_an_override_symlink_pointing_outside_the_wiki(self) -> None:
        (self.wiki / "schema").mkdir()
        (self.wiki / "schema" / "page-types.md").symlink_to(self.secret)
        self.assert_refused_unread()
        with self.assertRaises(ContractViolationError):
            api.propose(decision_edit(), self.paths, name="p")

    def test_a_symlinked_schema_directory(self) -> None:
        (self.wiki / "schema").symlink_to(self.outside, target_is_directory=True)
        self.assert_refused_unread()

    def test_load_schema_files_keeps_its_shape(self) -> None:
        texts = load_schema_files(self.paths)
        self.assertEqual(set(texts), {"ingest-rules", "page-types", "citation-rules"})
        self.assertTrue(all(isinstance(v, str) and v for v in texts.values()))


class TestDrift(ManifestCase):
    """FR-009: exit 4 on a governed wiki, a warning on a managed one, through propose and promote."""

    def setUp(self) -> None:
        super().setUp()
        api.init(self.paths)
        self.declared = EMPTY_SHA256

    def drift(self) -> str:
        (self.wiki / "schema").mkdir(exist_ok=True)
        (self.wiki / "schema" / "page-types.md").write_text("# local page types\n", encoding="utf-8")
        return load_schema(self.paths).fingerprint

    def draft(self) -> str:
        draft = self.root / "draft"
        (draft / "decisions").mkdir(parents=True, exist_ok=True)
        (draft / "decisions" / "retry-backoff.md").write_text(DECISION.format(slug="retry-backoff"), encoding="utf-8")
        (draft / "index.md").write_text("- [Retry backoff](decisions/retry-backoff.md)\n", encoding="utf-8")
        return str(draft)

    def test_managed_drift_warns_through_api_propose_and_still_writes(self) -> None:
        current = self.drift()
        with self.assertWarns(DriftWarning) as ctx:
            prop = api.propose(decision_edit(), self.paths, name="p")
        message = str(ctx.warning)
        for needle in (self.declared, current, "init --update-schema"):
            self.assertIn(needle, message)
        self.assertTrue((prop / "plan.json").is_file())
        result = api.promote(prop, self.paths)
        self.assertEqual(result.warnings, [message])
        self.assertTrue((self.wiki / "decisions" / "retry-backoff.md").is_file())

    def test_managed_drift_can_be_escalated_by_the_warnings_filter(self) -> None:
        self.drift()
        with warnings.catch_warnings():
            warnings.simplefilter("error", DriftWarning)
            with self.assertRaises(DriftWarning):
                api.propose(decision_edit(), self.paths, name="p")
        self.assertFalse((self.paths.proposals_dir / "p").exists())

    def test_managed_drift_is_on_stderr_for_cli_propose_and_promote(self) -> None:
        prop = api.propose(decision_edit("first"), self.paths, name="first")
        self.drift()
        dry = self.cli("promote", "--dry-run", str(prop))
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn("schema drift", dry.stderr)
        promoted = self.cli("promote", str(prop))
        self.assertEqual(promoted.returncode, 0, promoted.stderr)
        self.assertEqual(promoted.stderr.count("schema drift"), 1)
        proposed = self.cli("propose", "--from", self.draft(), "--name", "second", "--promote")
        self.assertEqual(proposed.returncode, 0, proposed.stderr)
        self.assertEqual(proposed.stderr.count("schema drift"), 1, "printed once, not again by the promote")

    def test_governed_drift_is_exit_4_through_propose_and_promote(self) -> None:
        prop = api.propose(decision_edit(), self.paths, name="first")
        self.set_policy(approval_required=True)
        current = self.drift()
        for label, call in {
            "api.propose": lambda: api.propose(decision_edit("other"), self.paths, name="second"),
            "api.promote": lambda: api.promote(prop, self.paths),
            "api.promote dry run": lambda: api.promote(prop, self.paths, dry_run=True),
        }.items():
            with self.subTest(label), self.assertRaises(ContractViolationError) as ctx:
                call()
            for needle in (self.declared, current, "init --update-schema"):
                self.assertIn(needle, str(ctx.exception))
        for argv in (("promote", str(prop)), ("promote", "--dry-run", str(prop)), ("propose", "--from", self.draft())):
            result = self.cli(*argv)
            self.assertEqual(result.returncode, ContractViolationError.exit_code, argv)
            self.assertIn(current, result.stderr)
        self.assertFalse((self.wiki / "decisions" / "retry-backoff.md").exists())
        self.assertFalse((self.paths.proposals_dir / "second").exists())

    def test_update_schema_acknowledges_the_change(self) -> None:
        self.set_policy(approval_required=True)
        current = self.drift()
        self.assertEqual(api.init(self.paths, update_schema=True).manifest, "updated")
        self.assertEqual(api.info(self.paths).schema_contract.declared_fingerprint, current)
        api.promote(api.propose(decision_edit(), self.paths, name="p"), self.paths)

    def test_a_changed_packaged_document_alone_never_trips_drift(self) -> None:
        self.set_policy(approval_required=True)
        with patch.object(contract, "read_packaged_schema", return_value="# the next release's rules\n"):
            self.assertFalse(api.info(self.paths).schema_contract.drift)
            api.promote(api.propose(decision_edit(), self.paths, name="p"), self.paths)

    def test_update_schema_after_the_first_override_is_added_and_the_last_removed(self) -> None:
        self.drift()
        self.assertEqual(api.info(self.paths).schema_contract.source, "project")
        self.assertTrue(api.info(self.paths).schema_contract.drift)
        api.init(self.paths, update_schema=True)
        info = api.info(self.paths).schema_contract
        self.assertEqual((info.source, info.drift), ("project", False))
        (self.wiki / "schema" / "page-types.md").unlink()
        self.assertTrue(api.info(self.paths).schema_contract.drift)
        api.init(self.paths, update_schema=True)
        info = api.info(self.paths).schema_contract
        self.assertEqual((info.source, info.drift, info.fingerprint), ("packaged", False, EMPTY_SHA256))
