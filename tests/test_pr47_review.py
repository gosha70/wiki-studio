# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.7.0, PR #47 review: regressions for containment, provenance, partial publication and findings scope."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

from tests.test_approve import ApprovalCase, page_text
from wiki_studio import api, contract, health_lint, promoter, review
from wiki_studio.errors import ContractViolationError, OutputWriteError
from wiki_studio.paths import WikiPaths


class _OutsideCase(ApprovalCase):
    def setUp(self) -> None:
        super().setUp()
        self._outside_tmp = tempfile.TemporaryDirectory(prefix="wiki_studio-outside-")
        self.outside = Path(self._outside_tmp.name).resolve()

    def tearDown(self) -> None:
        self._outside_tmp.cleanup()
        super().tearDown()


class TestRecordScanNeverFollowsASwappedDirectory(_OutsideCase):
    """F2: a key directory swapped for an outside symlink after the containment check is never followed."""

    def test_a_key_directory_swapped_after_the_check_is_refused(self) -> None:
        if not review._FD_SCAN:
            self.skipTest("descriptor-relative scans are unsupported here (documented weaker binding)")
        rel = self.create("a")
        api.approve([rel], self.paths)
        [state] = api.review_state(self.paths, pages=[rel])
        self.assertEqual(state.state, "approved")
        assert state.record_path is not None
        key_dir = (self.wiki / state.record_path).parents[2]
        self.hand_edit(rel, page_text("a", body="Edited by hand."))
        live = api.read_page(rel, self.paths).sha256
        # The outside tree holds a forged record for the live bytes, laid out like the real one.
        forged = self.outside / "forged"
        shutil.copytree(key_dir, forged)
        old_rev = next(p for p in forged.iterdir() if p.is_dir())
        old_rev.rename(forged / live)
        real_contain = review.contain
        swapped = {"done": False}

        def contain_then_swap(*args: Any, **kwargs: Any) -> Any:
            result = real_contain(*args, **kwargs)
            if not swapped["done"]:
                swapped["done"] = True
                shutil.rmtree(key_dir)
                key_dir.symlink_to(forged, target_is_directory=True)
            return result

        with patch.object(review, "contain", contain_then_swap):
            [after] = api.review_state(self.paths, pages=[rel])
        self.assertTrue(swapped["done"])
        self.assertNotEqual(after.state, "approved", "a record outside the wiki never approves a page")
        self.assertTrue(any("symlink" in w for w in after.warnings))


class TestContractReadsBelowTheRoot(_OutsideCase):
    """F3: a component below the (resolved) wiki root swapped for a symlink after the check is refused."""

    def test_a_schema_directory_swapped_after_the_check_is_refused(self) -> None:
        if not contract._FD_READS:
            self.skipTest("descriptor-relative reads are unsupported here")
        schema = self.wiki / "schema"
        schema.mkdir()
        (schema / "page-types.md").write_text("project override\n", encoding="utf-8")
        elsewhere = self.outside / "schema"
        elsewhere.mkdir()
        (elsewhere / "page-types.md").write_text("outside bytes\n", encoding="utf-8")
        real_contain = contract.contain
        swapped = {"done": False}

        def contain_then_swap(*args: Any, **kwargs: Any) -> Any:
            result = real_contain(*args, **kwargs)
            if not swapped["done"] and str(args[0]).startswith("schema/"):
                swapped["done"] = True
                shutil.rmtree(schema)
                schema.symlink_to(elsewhere, target_is_directory=True)
            return result

        with patch.object(contract, "contain", contain_then_swap), self.assertRaises(ContractViolationError):
            api.info(self.paths)
        self.assertTrue(swapped["done"])

    def test_an_alias_spelling_of_the_root_still_reads(self) -> None:
        """Release A (FR-002): the root's configured spelling may be an alias; it is resolved once."""
        alias = self.root / "wiki-alias"
        alias.symlink_to(self.wiki, target_is_directory=True)
        aliased = WikiPaths.for_root(self.root, wiki_dir=alias)
        self.assertEqual(api.info(aliased).manifest.state, "present")


class TestHealthPagesStayInsideTheWiki(_OutsideCase):
    """F4: a symlinked page or directory is never read by the health checks or by findings."""

    def test_symlinked_pages_and_directories_are_not_enumerated(self) -> None:
        self.create("a")
        (self.outside / "x.md").write_text(page_text("x", body="See missing/path.md:12."), encoding="utf-8")
        (self.wiki / "decisions" / "linked.md").symlink_to(self.outside / "x.md")
        (self.wiki / "mirror").symlink_to(self.outside, target_is_directory=True)
        listed = {p.relative_to(self.wiki).as_posix() for p in health_lint._list_wiki_pages(self.wiki)}
        self.assertNotIn("decisions/linked.md", listed)
        self.assertFalse(any(rel.startswith("mirror/") for rel in listed))
        result = api.findings(self.paths)
        for finding in result.findings:
            self.assertNotIn("decisions/linked.md", finding.pages)
            self.assertFalse(any(page.startswith("mirror/") for page in finding.pages))


class TestProvenanceIsBoundToTheWiki(_OutsideCase):
    """F5: an explicit approve never copies provenance from a receipt written for another wiki."""

    def test_a_shared_proposals_directory_lends_no_provenance_across_wikis(self) -> None:
        rel = self.create("shared", by="alice")
        wiki_b = self.root / "other" / "wiki"
        shutil.copytree(self.wiki, wiki_b, ignore=shutil.ignore_patterns(".audit", ".wiki-studio.json"))
        paths_b = WikiPaths.for_root(self.root, wiki_dir=wiki_b, proposals_dir=self.paths.proposals_dir)
        api.init(paths_b)
        result = api.approve([rel], paths_b, by="bob")
        self.assertEqual(len(result.published), 1)
        record = json.loads((wiki_b / result.published[0]).read_text(encoding="utf-8"))
        self.assertIsNone(record["proposal"], "wiki A's proposal is not wiki B's provenance")
        self.assertIsNone(record["proposer"])
        self.assertIsNone(record["promoter"])

    def test_the_own_wiki_still_gets_its_provenance(self) -> None:
        rel = self.create("own", by="alice")
        result = api.approve([rel], self.paths, by="bob")
        record = json.loads((self.wiki / result.published[0]).read_text(encoding="utf-8"))
        self.assertIsNotNone(record["proposal"])
        self.assertEqual(record["promoter"], {"name": "alice", "source": "flag"})


class TestPartialPublicationContract(ApprovalCase):
    """F6: once a record is published, any later publication failure is OutputWriteError (exit 6) with both lists."""

    def test_a_contract_error_after_the_first_record_is_partial_publication(self) -> None:
        first, second = self.create("p1"), self.create("p2")
        real = promoter._publish_record
        calls = {"n": 0}

        def second_fails(*args: Any, **kwargs: Any) -> Any:
            calls["n"] += 1
            if calls["n"] == 2:
                raise ContractViolationError("record path refused")
            return real(*args, **kwargs)

        with patch.object(promoter, "_publish_record", second_fails), self.assertRaises(OutputWriteError) as ctx:
            api.approve([first, second], self.paths)
        self.assertIn("partly published", str(ctx.exception))
        self.assertIn(first, str(ctx.exception))
        self.assertIn(second, str(ctx.exception))

    def test_a_contract_error_before_any_record_keeps_its_own_contract(self) -> None:
        rel = self.create("p3")
        with (
            patch.object(promoter, "_publish_record", side_effect=ContractViolationError("refused")),
            self.assertRaises(ContractViolationError),
        ):
            api.approve([rel], self.paths)


class TestFindingsScope(ApprovalCase):
    """F7: one scope for every finding's pages and for pages_checked."""

    def test_scoped_findings_report_only_in_scope_pages(self) -> None:
        """A missing-cross-link spans the canonical page and three mentioners; scoped, only the scope is reported."""
        hub = self.create("gamma")
        mentioners = [self.create(slug, body="Use gamma first.") for slug in ("m1", "m2", "m3")]
        unscoped = [f for f in api.findings(self.paths).findings if f.kind == "missing-cross-link"]
        self.assertTrue(any(len(f.pages) > 1 for f in unscoped), "the fixture yields a multi-page finding")
        result = api.findings(self.paths, pages=[mentioners[0]])
        self.assertEqual(result.pages_checked, 1)
        cross = [f for f in result.findings if f.kind == "missing-cross-link"]
        self.assertTrue(cross, "the finding touching the scope is kept")
        for finding in result.findings:
            self.assertEqual(set(finding.pages), {mentioners[0]}, finding)
        self.assertNotIn(hub, {p for f in result.findings for p in f.pages})

    def test_the_unscoped_denominator_is_the_default_review_set(self) -> None:
        self.create("fc")
        result = api.findings(self.paths)
        self.assertEqual(result.pages_checked, len(review.default_review_pages(self.paths)))
        for finding in result.findings:
            self.assertNotIn("index.md", finding.pages)
            self.assertNotIn("log.md", finding.pages)


class TestPathBasedScanFallback(_OutsideCase):
    """Without ``dir_fd`` (Windows) the scan is path-based and lstat-checked: same results, symlinks skipped."""

    def test_the_fallback_finds_verified_records_and_skips_symlinks_and_junk(self) -> None:
        rel = self.create("fallback")
        api.approve([rel], self.paths)
        with patch.object(review, "_FD_SCAN", False):
            [state] = api.review_state(self.paths, pages=[rel])
        self.assertEqual(state.state, "approved")
        assert state.record_path is not None
        record = self.wiki / state.record_path
        policy_dir, rev_dir, key_dir = record.parent, record.parents[1], record.parents[2]
        (policy_dir / "notes.txt").write_text("junk", encoding="utf-8")
        (rev_dir / "not-a-policy").mkdir()
        (key_dir / "not-a-revision").mkdir()
        (policy_dir / "approved-link.json").symlink_to(self.outside)
        forged_policy = self.outside / "policy"
        forged_policy.mkdir()
        (rev_dir / ("f" * 64)).symlink_to(forged_policy, target_is_directory=True)
        for fd_scan in (False, True):
            with patch.object(review, "_FD_SCAN", fd_scan):
                [again] = api.review_state(self.paths, pages=[rel])
            self.assertEqual(again.state, "approved")
            joined = " ".join(again.warnings)
            self.assertIn("symlink", joined)
            self.assertIn("not a policy directory", joined)
            self.assertIn("not an approval record", joined)

    def test_a_corrupt_record_is_skipped_by_both_scans(self) -> None:
        rel = self.create("corrupt")
        result = api.approve([rel], self.paths)
        (self.wiki / result.published[0]).write_text("{not json", encoding="utf-8")
        for fd_scan in (False, True):
            with patch.object(review, "_FD_SCAN", fd_scan):
                [state] = api.review_state(self.paths, pages=[rel])
            self.assertNotEqual(state.state, "approved")
            self.assertTrue(any("approval record skipped" in w for w in state.warnings), state.warnings)
