# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.7.0 (US4): the approval record — layout, path digest, verification, exclusive publication (FR-023..FR-025)."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from tests.test_approve import ApprovalCase, page_text
from wiki_studio import api, promoter
from wiki_studio.contract import FORMATS
from wiki_studio.errors import ContractViolationError, PromoteValidationError
from wiki_studio.proposal import new_page_id
from wiki_studio.review import APPROVALS_REL, RECORD_KEYS, path_digest, policy_sha256

OVERVIEW = (
    "---\npage_type: overview\nslug: {slug}\ntitle: Overview\nstatus: stable\nlast_reviewed: 2026-10-16\n{extra}"
    "sources:\n  - path: notes.md\n---\n\n# Overview\n\n## Summary\n\nA root page.\n"
)
DEFAULT_POLICY_HASH = hashlib.sha256(b'{"approver_required":false}').hexdigest()


class TestLayout(ApprovalCase):
    def test_a_path_keyed_record_lives_under_path_digest_with_every_key(self) -> None:
        rel = self.create("retry-backoff", by="carol")
        sha = api.read_page(rel, self.paths).sha256
        (written,) = api.approve([rel], self.paths, by="alice").published
        digest = hashlib.sha256(rel.encode("utf-8")).hexdigest()
        self.assertEqual(written, f"{APPROVALS_REL}/path/{digest}/{sha}/{DEFAULT_POLICY_HASH}/approved.json")
        record = self.record(written)
        self.assertEqual(tuple(record), RECORD_KEYS)
        self.assertEqual(record["approval_version"], FORMATS["approval"])
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(
            {k: record[k] for k in ("wiki_id", "page_key", "path", "sha256", "policy_sha256", "decision")},
            {
                "wiki_id": manifest["wiki_id"],
                "page_key": rel,
                "path": rel,
                "sha256": sha,
                "policy_sha256": DEFAULT_POLICY_HASH,
                "decision": "approved",
            },
        )
        self.assertEqual(record["promoter"], {"name": "carol", "source": "flag"})
        self.assertTrue(str(record["timestamp"]).endswith("Z"))

    def test_a_page_with_a_page_id_is_keyed_by_it(self) -> None:
        page_id = new_page_id()
        rel = self.create("retry-backoff", page_id=page_id)
        (written,) = api.approve([rel], self.paths).published
        self.assertTrue(written.startswith(f"{APPROVALS_REL}/id/{page_id}/"))
        self.assertEqual(self.record(written)["page_key"], page_id)

    def test_the_path_digest_is_of_the_canonical_path(self) -> None:
        self.assertEqual(path_digest("./concepts/x.md"), hashlib.sha256(b"concepts/x.md").hexdigest())
        self.assertEqual(path_digest("concepts/x.md"), path_digest("concepts//./x.md"))

    def test_the_same_bytes_under_a_changed_policy_get_their_own_record(self) -> None:
        rel = self.create("a")
        first = api.approve([rel], self.paths).published[0]
        before = (self.wiki / first).read_bytes()
        self.set_policy(approver_required=True)
        second = api.approve([rel], self.paths, by="bob").published[0]
        self.assertNotEqual(first, second)
        self.assertEqual(second.split("/")[-2], policy_sha256({"approver_required": True}))
        self.assertEqual((self.wiki / first).read_bytes(), before)


class TestCollisionAndEquivalence(ApprovalCase):
    def _root_page(self, slug: str, extra: str = "") -> str:
        rel = f"{slug}.md"
        self.hand_edit(rel, OVERVIEW.format(slug=slug, extra=extra))
        index = (self.wiki / "index.md").read_text(encoding="utf-8")
        self.hand_edit("index.md", index + f"\n- [{slug}]({rel})\n")
        return rel

    def test_a_nested_page_and_a_flattened_root_name_never_share_records(self) -> None:
        (self.wiki / "concepts").mkdir()
        nested = "concepts/x.md"
        self.hand_edit(
            nested, page_text("x").replace("page_type: decision", "page_type: concept").replace("decisions", "concepts")
        )
        self.hand_edit("index.md", (self.wiki / "index.md").read_text(encoding="utf-8") + f"\n- [x]({nested})\n")
        flat = self._root_page("concepts__x")
        self.assertEqual(api.lint(self.paths).violations, ())
        a = api.approve([nested], self.paths).published[0]
        self.assertEqual(self.state(flat).state, "unapproved")
        b = api.approve([flat], self.paths).published[0]
        self.assertNotEqual(a.split("/")[3], b.split("/")[3])
        self.assertEqual((self.state(nested).record_path, self.state(flat).record_path), (a, b))

    def test_a_page_id_equal_to_a_path_derived_name_stays_in_its_namespace(self) -> None:
        page_id = new_page_id()
        flat = self._root_page(page_id)
        keyed = self.create("keyed", page_id=page_id)
        a = api.approve([flat], self.paths).published[0]
        self.assertEqual(self.state(keyed).state, "unapproved")
        b = api.approve([keyed], self.paths).published[0]
        self.assertIn("/path/", a)
        self.assertIn(f"/id/{page_id}/", b)
        self.assertEqual((self.state(flat).record_path, self.state(keyed).record_path), (a, b))

    def test_dot_slash_and_plain_paths_locate_the_same_records(self) -> None:
        rel = self.create("x")
        written = api.approve([f"./{rel}"], self.paths).published[0]
        self.assertEqual(self.state(rel).record_path, written)
        self.assertEqual(api.approve([rel], self.paths).existing, [written])


class TestVerification(ApprovalCase):
    def _plant(self, rel: str, record_rel: str, **changes: object) -> None:
        """Copy the record at ``record_rel`` to the location ``rel``'s live bytes would use, with ``changes``."""
        data = self.record(record_rel)
        data.update(changes)
        sha = api.read_page(rel, self.paths).sha256
        target = self.wiki / APPROVALS_REL / "path" / path_digest(rel) / sha / DEFAULT_POLICY_HASH / "approved.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        data["sha256"] = changes.get("sha256", sha)
        target.write_text(json.dumps(data), encoding="utf-8")

    def test_a_record_naming_another_page_is_skipped_and_reported(self) -> None:
        a, b = self.create("a"), self.create("b")
        written = api.approve([a], self.paths).published[0]
        self._plant(b, written)
        state = self.state(b)
        self.assertEqual(state.state, "unapproved")
        self.assertTrue(any("page_key 'decisions/a.md'" in w for w in state.warnings), state.warnings)

    def test_records_failing_verification_are_skipped(self) -> None:
        a, b = self.create("a"), self.create("b")
        written = api.approve([a], self.paths).published[0]
        cases: dict[str, dict[str, object]] = {
            "wiki_id": {"page_key": b, "wiki_id": "00000000-0000-4000-8000-000000000000"},
            "approval_version": {"page_key": b, "approval_version": 2},
            "differs from its location": {"page_key": b, "sha256": "0" * 64},
            "approver must be": {"page_key": b, "approver": {"name": "x"}},
            "timestamp": {"page_key": b, "timestamp": "yesterday"},
            "proposal must be": {"page_key": b, "proposal": {"name": 1}},
        }
        for needle, changes in cases.items():
            with self.subTest(needle):
                self._plant(b, written, **changes)
                state = self.state(b)
                self.assertEqual(state.state, "unapproved")
                self.assertTrue(any(needle in w for w in state.warnings), state.warnings)

    def test_unparseable_and_misnamed_entries_are_skipped(self) -> None:
        rel = self.create("a")
        written = api.approve([rel], self.paths).published[0]
        policy_dir = (self.wiki / written).parent
        (self.wiki / written).write_text("{not json", encoding="utf-8")
        (policy_dir / "rejected.json").write_text("{}", encoding="utf-8")
        (policy_dir.parent / "not-a-policy").mkdir()
        state = self.state(rel)
        self.assertEqual(state.state, "unapproved")
        joined = "\n".join(state.warnings)
        for needle in ("not a UTF-8 JSON document", "not an approval record", "not a policy directory"):
            self.assertIn(needle, joined)
        with self.assertRaises(PromoteValidationError):
            api.approve([rel], self.paths)


class TestSymlinksAreRefused(ApprovalCase):
    """FR-025: a symlink planted at each level under ``.audit/approvals/`` is refused, its target untouched."""

    def setUp(self) -> None:
        super().setUp()
        self.rel = self.create("a")
        self.sha = api.read_page(self.rel, self.paths).sha256
        self._outside = tempfile.TemporaryDirectory(prefix="wiki_studio-outside-")
        self.outside = Path(self._outside.name)
        self.addCleanup(self._outside.cleanup)

    def _levels(self) -> list[Path]:
        root = self.wiki / APPROVALS_REL
        key = root / "path" / path_digest(self.rel)
        return [
            root,
            root / "path",
            key,
            key / self.sha,
            key / self.sha / DEFAULT_POLICY_HASH,
            key / self.sha / DEFAULT_POLICY_HASH / "approved.json",
        ]

    def test_every_level(self) -> None:
        for level in self._levels():
            with self.subTest(level=level.relative_to(self.wiki).as_posix()):
                if (self.wiki / APPROVALS_REL).exists() or (self.wiki / APPROVALS_REL).is_symlink():
                    if (self.wiki / APPROVALS_REL).is_symlink():
                        (self.wiki / APPROVALS_REL).unlink()
                    else:
                        shutil.rmtree(self.wiki / APPROVALS_REL)
                target = self.outside / level.name
                if level.name.endswith(".json"):
                    target.write_text("outside", encoding="utf-8")
                else:
                    target.mkdir(exist_ok=True)
                level.parent.mkdir(parents=True, exist_ok=True)
                level.symlink_to(target)
                before = sorted(p.name for p in self.outside.rglob("*"))
                result = self.cli("approve", self.rel)
                self.assertEqual(result.returncode, 4, result.stderr)
                self.assertIn("symlink", result.stderr)
                with self.assertRaises(ContractViolationError):
                    api.approve([self.rel], self.paths)
                self.assertEqual(sorted(p.name for p in self.outside.rglob("*")), before, "target untouched")
                if target.is_file():
                    self.assertEqual(target.read_text(encoding="utf-8"), "outside")
                state = self.state(self.rel)
                self.assertEqual(state.state, "unapproved")
                self.assertTrue(any("symlink" in w for w in state.warnings), state.warnings)
                level.unlink()

    def test_publication_refuses_a_symlinked_component_directly(self) -> None:
        record = f"{APPROVALS_REL}/path/{path_digest(self.rel)}/{self.sha}/{DEFAULT_POLICY_HASH}/approved.json"
        (self.wiki / APPROVALS_REL).parent.mkdir(parents=True, exist_ok=True)
        (self.wiki / APPROVALS_REL).symlink_to(self.outside)
        with self.assertRaises(ContractViolationError):
            promoter._publish_record(self.paths, record, b"{}")
        self.assertEqual(list(self.outside.iterdir()), [])


class TestExclusivePublication(ApprovalCase):
    def _record_rel(self, rel: str) -> str:
        sha = api.read_page(rel, self.paths).sha256
        return f"{APPROVALS_REL}/path/{path_digest(rel)}/{sha}/{DEFAULT_POLICY_HASH}/approved.json"

    def test_an_existing_record_is_never_rewritten(self) -> None:
        rel = self.create("a")
        written = api.approve([rel], self.paths).published[0]
        before = (self.wiki / written).read_bytes()
        self.assertFalse(promoter._publish_record(self.paths, written, b"replacement"))
        self.assertEqual((self.wiki / written).read_bytes(), before)
        leftovers = [p.name for p in (self.wiki / written).parent.iterdir()]
        self.assertEqual(leftovers, ["approved.json"], "the temporary name is removed")

    def test_without_hard_links_publication_falls_back_to_an_exclusive_create(self) -> None:
        rel = self.create("a")
        target = self._record_rel(rel)
        with patch.object(os, "link", side_effect=OSError(errno.EPERM, "Operation not permitted")):
            self.assertTrue(promoter._publish_record(self.paths, target, b"first"))
            self.assertFalse(promoter._publish_record(self.paths, target, b"second"))
        self.assertEqual((self.wiki / target).read_bytes(), b"first")

    def test_an_unexpected_link_failure_propagates(self) -> None:
        rel = self.create("a")
        with (
            patch.object(os, "link", side_effect=OSError(errno.EIO, "I/O error")),
            self.assertRaises(OSError),
        ):
            promoter._publish_record(self.paths, self._record_rel(rel), b"x")
        self.assertFalse((self.wiki / self._record_rel(rel)).exists())

    def test_the_path_based_fallback_publishes_and_refuses_symlinks(self) -> None:
        rel = self.create("a")
        target = self._record_rel(rel)
        with patch.object(promoter, "_DIR_FD_RECORDS", False):
            self.assertTrue(promoter._publish_record(self.paths, target, b"first"))
            self.assertFalse(promoter._publish_record(self.paths, target, b"second"))
            blocker = self.wiki / APPROVALS_REL / "id"
            blocker.write_text("not a directory", encoding="utf-8")
            with self.assertRaises(ContractViolationError):
                promoter._publish_record(self.paths, f"{APPROVALS_REL}/id/{new_page_id()}/x/y/approved.json", b"z")
        self.assertEqual((self.wiki / target).read_bytes(), b"first")

    def test_a_file_occupying_the_record_name_refuses_approve(self) -> None:
        rel = self.create("a")
        target = self.wiki / self._record_rel(rel)
        target.parent.mkdir(parents=True)
        target.write_text("{}", encoding="utf-8")
        result = self.cli("approve", rel)
        self.assertEqual(result.returncode, 9)
        self.assertIn("remove it by hand", result.stderr)
        self.assertEqual(target.read_text(encoding="utf-8"), "{}")
