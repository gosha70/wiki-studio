# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""0.7.0 (US3): who proposed and who promoted, as attribution with its source (FR-017, FR-018)."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING
from unittest.mock import patch

from tests.test_manifest import DECISION, ManifestCase, decision_edit
from wiki_studio import api, promoter
from wiki_studio.errors import PromoteValidationError
from wiki_studio.paths import ENV_ACTOR, Actor, resolve_actor

if TYPE_CHECKING:
    from pathlib import Path

# Stands in for the OS user: no audit file may ever contain it.
OS_USER = "os-user-sentinel-7f3a"
NONE = {"name": None, "source": "none"}


class AttributionCase(ManifestCase):
    """A managed wiki, ``WIKI_STUDIO_ACTOR`` unset and the OS user name a sentinel."""

    def setUp(self) -> None:
        super().setUp()
        env = {k: v for k, v in os.environ.items() if k != ENV_ACTOR}
        env.update(USER=OS_USER, LOGNAME=OS_USER, USERNAME=OS_USER)
        self.enterContext(patch.dict(os.environ, env, clear=True))
        self.enterContext(patch("getpass.getuser", return_value=OS_USER))
        api.init(self.paths)

    def plan(self, proposal: Path) -> dict:
        return json.loads((proposal / "plan.json").read_text(encoding="utf-8"))

    def receipt(self, result: api.PromoteResult) -> dict:
        assert result.archived_dir is not None
        return json.loads((result.archived_dir / promoter.RECEIPT_FILE_NAME).read_text(encoding="utf-8"))


class TestResolveActor(AttributionCase):
    def test_the_rule(self) -> None:
        self.assertEqual(resolve_actor("ada"), Actor("ada", "flag"))
        self.assertEqual(resolve_actor("ada", env={ENV_ACTOR: "bob"}), Actor("ada", "flag"), "the flag wins")
        self.assertEqual(resolve_actor(None, env={ENV_ACTOR: "bob"}), Actor("bob", "env"))
        self.assertEqual(resolve_actor("", env={ENV_ACTOR: "bob"}), Actor("bob", "env"), "an empty --by is no flag")
        self.assertEqual(resolve_actor(None, env={ENV_ACTOR: "  "}), Actor(None, "none"))
        self.assertEqual(resolve_actor(None, env={}), Actor(None, "none"))

    def test_the_os_user_is_never_captured(self) -> None:
        self.assertEqual(resolve_actor(), Actor(None, "none"))


class TestApiAttribution(AttributionCase):
    def test_flag(self) -> None:
        proposal = api.propose(decision_edit(), self.paths, name="p", by="ada")
        self.assertEqual(self.plan(proposal)["proposer"], {"name": "ada", "source": "flag"})
        result = api.promote(proposal, self.paths, by="bob")
        self.assertEqual(self.receipt(result)["actor"], {"name": "bob", "source": "flag"})
        self.assertEqual(self.receipt(result)["receipt_version"], 1)

    def test_env(self) -> None:
        with patch.dict(os.environ, {ENV_ACTOR: "ci-bot"}):
            proposal = api.propose(decision_edit(), self.paths, name="p")
            result = api.promote(proposal, self.paths)
        assert result.archived_dir is not None
        self.assertEqual(self.plan(result.archived_dir)["proposer"], {"name": "ci-bot", "source": "env"})
        self.assertEqual(self.receipt(result)["actor"], {"name": "ci-bot", "source": "env"})

    def test_none(self) -> None:
        proposal = api.propose(decision_edit(), self.paths, name="p")
        self.assertEqual(self.plan(proposal)["proposer"], NONE)
        self.assertEqual(self.receipt(api.promote(proposal, self.paths))["actor"], NONE)

    def test_the_archived_plan_keeps_the_proposer(self) -> None:
        proposal = api.propose(decision_edit(), self.paths, name="p", by="ada")
        api.promote(proposal, self.paths)
        archived = self.wiki / ".audit" / "proposals" / "p" / "plan.json"
        self.assertEqual(
            json.loads(archived.read_text(encoding="utf-8"))["proposer"], {"name": "ada", "source": "flag"}
        )

    def test_no_os_user_name_anywhere_in_the_audit_files_by_default(self) -> None:
        api.promote(api.propose(decision_edit(), self.paths, name="p"), self.paths)
        written = [p for root in (self.wiki, self.paths.proposals_dir) for p in root.rglob("*") if p.is_file()]
        self.assertTrue(any(p.name == promoter.RECEIPT_FILE_NAME for p in written))
        for path in written:
            with self.subTest(path=str(path)):
                self.assertNotIn(OS_USER.encode(), path.read_bytes())

    def test_a_malformed_proposer_is_refused_at_promote(self) -> None:
        for bad in ({"name": "ada"}, {"name": None, "source": "flag"}, {"name": "x", "source": "none"}, "ada"):
            with self.subTest(bad=bad):
                proposal = api.propose(decision_edit(), self.paths, name=f"p-{len(str(bad))}-{type(bad).__name__}")
                plan = self.plan(proposal)
                plan["proposer"] = bad
                (proposal / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
                with self.assertRaises(PromoteValidationError):
                    api.promote(proposal, self.paths)
                self.assertFalse((self.wiki / "decisions" / "retry-backoff.md").exists())

    def test_a_plan_without_a_proposer_still_promotes(self) -> None:
        proposal = api.propose(decision_edit(), self.paths, name="p")
        plan = self.plan(proposal)
        del plan["proposer"]
        (proposal / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        self.assertEqual(self.receipt(api.promote(proposal, self.paths))["actor"], NONE)


class TestCliAttribution(AttributionCase):
    def setUp(self) -> None:
        super().setUp()
        self.draft = self.root / "draft"
        (self.draft / "decisions").mkdir(parents=True)
        (self.draft / "decisions" / "retry-backoff.md").write_text(
            DECISION.format(slug="retry-backoff"), encoding="utf-8"
        )
        (self.draft / "index.md").write_text("- [Retry backoff](decisions/retry-backoff.md)\n", encoding="utf-8")

    def archived(self, name: str) -> tuple[dict, dict]:
        base = self.paths.applied_dir / name
        return (
            json.loads((base / "plan.json").read_text(encoding="utf-8")),
            json.loads((base / promoter.RECEIPT_FILE_NAME).read_text(encoding="utf-8")),
        )

    def test_flag_on_propose_and_promote(self) -> None:
        proposed = self.cli("propose", "--from", str(self.draft), "--name", "p", "--by", "ada")
        self.assertEqual(proposed.returncode, 0, proposed.stderr)
        promoted = self.cli("promote", str(self.paths.proposals_dir / "p"), "--by", "bob")
        self.assertEqual(promoted.returncode, 0, promoted.stderr)
        plan, receipt = self.archived("p")
        self.assertEqual(plan["proposer"], {"name": "ada", "source": "flag"})
        self.assertEqual(receipt["actor"], {"name": "bob", "source": "flag"})

    def test_propose_promote_records_one_name_twice(self) -> None:
        result = self.cli("propose", "--from", str(self.draft), "--name", "p", "--promote", "--by", "ada")
        self.assertEqual(result.returncode, 0, result.stderr)
        plan, receipt = self.archived("p")
        self.assertEqual(plan["proposer"], {"name": "ada", "source": "flag"})
        self.assertEqual(receipt["actor"], {"name": "ada", "source": "flag"})

    def test_env(self) -> None:
        with patch.dict(os.environ, {ENV_ACTOR: "ci-bot"}):
            result = self.cli("propose", "--from", str(self.draft), "--name", "p", "--promote")
        self.assertEqual(result.returncode, 0, result.stderr)
        plan, receipt = self.archived("p")
        self.assertEqual(plan["proposer"], {"name": "ci-bot", "source": "env"})
        self.assertEqual(receipt["actor"], {"name": "ci-bot", "source": "env"})

    def test_none(self) -> None:
        result = self.cli("propose", "--from", str(self.draft), "--name", "p", "--promote")
        self.assertEqual(result.returncode, 0, result.stderr)
        plan, receipt = self.archived("p")
        self.assertEqual((plan["proposer"], receipt["actor"]), (NONE, NONE))

    def test_help_says_attribution_not_authentication(self) -> None:
        for verb in ("propose", "promote"):
            with self.subTest(verb=verb):
                text = " ".join(self.cli(verb, "--help").stdout.split())
                self.assertIn("--by NAME", text)
                self.assertIn("Attribution, not authentication", text)
