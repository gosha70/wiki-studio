# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.7.0 (US6): ``api.findings`` and ``findings --json``: every kind, the format, no backend (FR-037, FR-038)."""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

from tests.test_approve import ApprovalCase, page_text
from wiki_studio import api
from wiki_studio.errors import BackendNotFoundError
from wiki_studio.findings import FINDING_KINDS

_GLOSSARY = (
    "---\npage_type: glossary\nslug: origin-gate\ntitle: Origin Gate\nstatus: stable\nlast_reviewed: 2026-10-16\n"
    "avoid: [a, b]\n---\n\n# Origin Gate\n\n## Definition\n\nD.\n"
)


def _no_model_check(wiki_dir: object, backend: object) -> list[object]:
    """Stand-in for the contradiction check: it must be handed no backend."""
    if backend is not None:
        raise AssertionError(f"findings handed a backend to the health pass: {backend!r}")
    return []


class FindingsCase(ApprovalCase):
    def build_fixture_wiki(self) -> dict[str, str]:
        """A managed wiki carrying one cause of every kind; returns the page each review kind names."""
        gamma = self.create("gamma")
        stale = self.create("alpha", body="Use gamma first.")
        api.approve([stale], self.paths)
        # A hand edit after approval, which also cites a source that does not exist (stale-claim).
        self.hand_edit(stale, page_text("alpha", body="Use gamma second.").replace("notes.md", "gone.md"))
        changed = self.create("beta", body="Then gamma.")
        api.approve([changed], self.paths)
        old = self.create("old", body="Gamma replaced this.", extra=f"superseded_by: {gamma}\n")
        self.create("delta", body="Gamma again.")
        (self.wiki / "glossary").mkdir()
        (self.wiki / "glossary" / "origin-gate.md").write_text(_GLOSSARY, encoding="utf-8")
        self.set_policy(approver_required=True)
        return {"unapproved": gamma, "approval-stale": stale, "approval-policy-changed": changed, "superseded": old}


class TestFindingKinds(FindingsCase):
    def test_every_kind_is_produced_on_a_fixture_wiki(self) -> None:
        pages = self.build_fixture_wiki()
        result = api.findings(self.paths)
        by_kind: dict[str, list[tuple[str, ...]]] = {}
        for finding in result.findings:
            by_kind.setdefault(finding.kind, []).append(finding.pages)
            self.assertEqual(finding.severity, "warning", finding)
            self.assertTrue(finding.description)
        self.assertEqual(set(by_kind), set(FINDING_KINDS))
        self.assertNotIn("contradiction", result.counts)
        self.assertIn((pages["unapproved"],), by_kind["unapproved"])
        self.assertEqual(by_kind["approval-stale"], [(pages["approval-stale"],)])
        self.assertEqual(by_kind["approval-policy-changed"], [(pages["approval-policy-changed"],)])
        self.assertEqual(by_kind["superseded-still-indexed"], [(pages["superseded"], "index.md")])
        self.assertIn((pages["approval-stale"],), by_kind["stale-claim"])
        self.assertEqual(by_kind["avoid-format"], [("glossary/origin-gate.md",)])
        self.assertEqual(by_kind["missing-cross-link"][0][0], pages["unapproved"])
        self.assertIn((pages["unapproved"],), by_kind["no-page-id"])
        self.assertEqual(result.counts, {kind: len(by_kind[kind]) for kind in FINDING_KINDS})

    def test_a_superseded_page_is_never_reported_as_unapproved(self) -> None:
        pages = self.build_fixture_wiki()
        unapproved = [f.pages for f in api.findings(self.paths).findings if f.kind == "unapproved"]
        self.assertNotIn((pages["superseded"],), unapproved)

    def test_an_approved_page_with_a_page_id_has_no_review_finding(self) -> None:
        rel = self.create("solo", page_id="pg-" + "a" * 32)
        api.approve([rel], self.paths)
        kinds = {f.kind for f in api.findings(self.paths).findings if rel in f.pages}
        self.assertFalse(kinds & {"unapproved", "approval-stale", "approval-policy-changed", "no-page-id"}, kinds)

    def test_a_legacy_wiki_reports_every_page_unapproved_naming_init(self) -> None:
        rel = self.create("solo")
        self.manifest.unlink()
        (finding,) = [f for f in api.findings(self.paths).findings if f.kind == "unapproved"]
        self.assertEqual(finding.pages, (rel,))
        self.assertIn("wiki-studio init", finding.description)

    def test_scoped_pages_limit_every_kind_and_paths_are_canonical(self) -> None:
        pages = self.build_fixture_wiki()
        target = pages["approval-stale"]
        result = api.findings(self.paths, pages=[f"./{target}"])
        self.assertEqual(result.pages_checked, 1)
        self.assertTrue(result.findings)
        for finding in result.findings:
            self.assertIn(target, finding.pages, finding)
        self.assertEqual(result.counts["approval-stale"], 1)
        self.assertEqual(result.counts["unapproved"], 0)


class TestFindingsFormat(FindingsCase):
    def test_the_json_has_the_versioned_keys_and_exits_zero_with_findings(self) -> None:
        self.build_fixture_wiki()
        result = self.cli("findings", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(set(data), {"findings_version", "counts", "pages_checked", "findings"})
        self.assertEqual(data["findings_version"], 1)
        self.assertEqual(set(data["counts"]), set(FINDING_KINDS))
        self.assertGreater(sum(data["counts"].values()), 0)
        self.assertEqual(sum(data["counts"].values()), len(data["findings"]))
        self.assertIsInstance(data["pages_checked"], int)
        for finding in data["findings"]:
            self.assertEqual(set(finding), {"kind", "severity", "pages", "description"})
        # Compared by key, not by property order.
        self.assertEqual(data, api.findings(self.paths).as_dict())

    def test_the_text_form_leads_with_counts_and_exits_zero(self) -> None:
        self.build_fixture_wiki()
        result = self.cli("findings")
        self.assertEqual(result.returncode, 0, result.stderr)
        first = result.stdout.splitlines()[0]
        self.assertTrue(first.startswith("findings: "), first)
        self.assertIn("approval-stale 1", first)
        self.assertIn("[superseded-still-indexed / warning]", result.stdout)

    def test_a_clean_scope_exits_zero(self) -> None:
        rel = self.create("solo", page_id="pg-" + "b" * 32)
        api.approve([rel], self.paths)
        result = self.cli("findings", "--json", "--paths", rel)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["pages_checked"], 1)
        self.assertIn("weak-orphan", {f["kind"] for f in data["findings"]})

    def test_a_missing_scoped_page_exits_5(self) -> None:
        self.assertEqual(self.cli("findings", "--paths", "decisions/nope.md").returncode, 5)


class TestNoBackend(FindingsCase):
    def test_findings_takes_no_backend_parameter(self) -> None:
        self.assertEqual(list(inspect.signature(api.findings).parameters), ["paths", "pages"])
        self.assertNotIn("--backend", self.cli("findings", "--help").stdout)

    def test_a_run_with_backend_resolution_patched_to_fail_still_succeeds(self) -> None:
        self.build_fixture_wiki()
        failing = BackendNotFoundError("backend resolution must not be reached by findings")
        with (
            patch("wiki_studio.backends.resolve_backend", side_effect=failing),
            patch("wiki_studio.api.resolve_backend", side_effect=failing),
            patch("wiki_studio.api.prepare_backend", side_effect=failing),
            patch("wiki_studio.health_lint._check_contradictions", side_effect=_no_model_check),
        ):
            result = api.findings(self.paths)
            cli = self.cli("findings", "--json")
        self.assertTrue(result.findings)
        self.assertEqual(cli.returncode, 0, cli.stderr)
