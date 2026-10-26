# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.7.0 (US2): ``api.info`` and ``info --json`` describe the build and the wiki's contract (FR-010, FR-013)."""

from __future__ import annotations

import dataclasses
import inspect
import json

from tests.test_manifest import EMPTY_SHA256, ManifestCase, decision_edit
from wiki_studio import __version__, api, lint, paths, promoter, wikilock
from wiki_studio.cli import _VERBS
from wiki_studio.contract import CAPABILITIES, FORMATS, MANIFEST_INSTRUCTION
from wiki_studio.proposal import PageEdit
from wiki_studio.schema import SCHEMA_ID, SCHEMA_VERSION

# Every key ``info --json`` printed in 0.6.0, with its meaning unchanged.
KEYS_0_6_0 = (
    "layout",
    "root",
    "root_source",
    "wiki_dir",
    "wiki_dir_source",
    "wiki_dir_exists",
    "wiki_label",
    "proposals_dir",
    "proposals_dir_source",
    "proposals_dir_exists",
    "query_log",
    "audit_log",
    "schema",
    "schema_dir",
    "lock_file",
    "lock_timeout",
    "source_roots",
)
KEYS_0_7_0 = ("package_version", "schema_contract", "formats", "capabilities", "manifest")


class TestApiInfo(ManifestCase):
    def test_a_managed_wiki(self) -> None:
        api.init(self.paths)
        info = api.info(self.paths)
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(info.package_version, __version__)
        self.assertEqual(
            info.schema_contract.as_dict(),
            {
                "id": SCHEMA_ID,
                "version": SCHEMA_VERSION,
                "source": "packaged",
                "fingerprint": EMPTY_SHA256,
                "declared_fingerprint": EMPTY_SHA256,
                "drift": False,
            },
        )
        self.assertEqual(dict(info.formats), {"patch_set": 1, "receipt": 1, "ingest_log": 1, "approval": 1})
        self.assertEqual(
            info.capabilities,
            ("wiki-lock", "receipts", "base-revision", "root-manifest", "page-id", "attribution", "approval-record"),
        )
        self.assertEqual(
            info.manifest.as_dict(),
            {
                "state": "present",
                "manifest_version": 1,
                "wiki_id": manifest["wiki_id"],
                "policy": manifest["policy"],
                "mode": "managed",
            },
        )
        self.assertEqual(info.warnings, ())

    def test_a_governed_wiki_with_drift(self) -> None:
        api.init(self.paths)
        self.set_policy(approval_required=True)
        (self.wiki / "schema").mkdir()
        (self.wiki / "schema" / "citation-rules.md").write_text("# local\n", encoding="utf-8")
        info = api.info(self.paths)
        self.assertEqual(info.manifest.mode, "governed")
        self.assertTrue(info.schema_contract.drift)
        self.assertEqual(info.schema_contract.source, "project")
        self.assertEqual(len(info.warnings), 1)
        self.assertIn("init --update-schema", info.warnings[0])

    def test_a_legacy_wiki(self) -> None:
        api.init(self.paths)
        self.manifest.unlink()
        info = api.info(self.paths)
        self.assertEqual(
            info.manifest.as_dict(), {"state": "missing", "mode": "legacy", "instruction": MANIFEST_INSTRUCTION}
        )
        self.assertIn("wiki-studio init", MANIFEST_INSTRUCTION)
        self.assertIsNone(info.schema_contract.declared_fingerprint)
        self.assertFalse(info.schema_contract.drift)

    def test_info_writes_nothing(self) -> None:
        info = api.info(self.paths)
        self.assertEqual(info.manifest.state, "missing")
        self.assertFalse(self.wiki.exists())


class TestInfoJson(ManifestCase):
    def test_new_keys_beside_every_0_6_0_key(self) -> None:
        api.init(self.paths)
        result = self.cli("info", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        for key in (*KEYS_0_6_0, *KEYS_0_7_0):
            self.assertIn(key, data)
        self.assertEqual(data["schema"], "packaged", "still judged by the schema directory's existence")
        self.assertEqual(data["schema_dir"], str(self.paths.schema_dir))
        self.assertEqual(data["manifest"]["state"], "present")
        self.assertEqual(data["manifest"]["mode"], "managed")
        self.assertFalse(data["schema_contract"]["drift"])
        self.assertEqual(data["capabilities"], list(CAPABILITIES))
        self.assertEqual(data["formats"], dict(FORMATS))

    def test_the_old_schema_key_keeps_its_meaning(self) -> None:
        api.init(self.paths)
        (self.wiki / "schema").mkdir()
        (self.wiki / "schema" / "lint-rules.md").write_text("# lint\n", encoding="utf-8")
        data = json.loads(self.cli("info", "--json").stdout)
        self.assertEqual(data["schema"], "project", "a schema directory exists")
        self.assertEqual(data["schema_contract"]["source"], "packaged", "but no prompt document is overridden")

    def test_the_text_form_prints_the_contract_and_drift_on_stderr(self) -> None:
        api.init(self.paths)
        (self.wiki / "schema").mkdir()
        (self.wiki / "schema" / "page-types.md").write_text("# local\n", encoding="utf-8")
        result = self.cli("info")
        self.assertEqual(result.returncode, 0, result.stderr)
        for needle in ("package-version:", "schema-contract:", "capabilities: wiki-lock", "manifest: present"):
            self.assertIn(needle, result.stdout)
        self.assertIn("drift: yes", result.stdout)
        self.assertIn("schema drift", result.stderr)

    def test_a_legacy_wiki_is_told_how_to_add_a_manifest(self) -> None:
        api.init(self.paths)
        self.manifest.unlink()
        result = self.cli("info")
        self.assertIn("manifest: missing, mode legacy", result.stdout)
        self.assertIn("wiki-studio init", result.stdout)
        self.assertEqual(json.loads(self.cli("info", "--json").stdout)["manifest"]["mode"], "legacy")


class TestAdvertisedContract(ManifestCase):
    """Every capability and format ``info`` advertises exists in this build."""

    def test_every_capability_resolves(self) -> None:
        api.init(self.paths)
        data = json.loads(self.cli("info", "--json").stdout)
        edit_fields = {f.name for f in dataclasses.fields(PageEdit)}
        propose_params = inspect.signature(api.propose).parameters
        promote_params = inspect.signature(api.promote).parameters
        resolvers = {
            "wiki-lock": lambda: callable(wikilock.WikiLock) and "lock_file" in data,
            "receipts": lambda: bool(promoter.RECEIPT_FILE_NAME) and "receipt" in data["formats"],
            "base-revision": lambda: callable(api.read_page) and "base_sha256" in edit_fields,
            "root-manifest": lambda: "init" in _VERBS and callable(api.init) and "manifest" in data,
            "page-id": lambda: "assign_page_ids" in propose_params and callable(lint.lint_wiki),
            "attribution": lambda: "by" in propose_params and "by" in promote_params and bool(paths.ENV_ACTOR),
            "approval-record": lambda: (
                "approve" in _VERBS
                and callable(api.approve)
                and callable(api.review_state)
                and "approval" in data["formats"]
            ),
        }
        for capability in CAPABILITIES:
            with self.subTest(capability):
                self.assertIn(capability, resolvers, "an advertised capability needs a resolver here")
                self.assertTrue(resolvers[capability]())

    def test_the_formats_are_the_versions_written(self) -> None:
        api.init(self.paths)
        prop = api.propose(decision_edit(), self.paths, name="p")
        self.assertEqual(json.loads((prop / "plan.json").read_text(encoding="utf-8"))["version"], FORMATS["patch_set"])
        result = api.promote(prop, self.paths)
        assert result.archived_dir is not None
        receipt = json.loads((result.archived_dir / promoter.RECEIPT_FILE_NAME).read_text(encoding="utf-8"))
        self.assertEqual(receipt["receipt_version"], FORMATS["receipt"])
