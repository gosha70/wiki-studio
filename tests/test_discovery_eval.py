# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""Discovery evidence (0.8.0 US3): reproduction, the tuning and held-out guards, the decision rule, the protocol order.

Every committed results file reproduces in memory under the configuration it
records, whatever the live default is. ``tune`` and the one held-out run
refuse out of order; ``heldout_protocol.py`` refuses every step out of order.
All held-out cases run on synthetic fixtures in temporary directories; no
backend is invoked and nothing is written beside a frozen fixture.
"""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import io
import json
import posixpath
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from eval.navigation import discovery, heldout_protocol
from eval.navigation.run2_protocol import _tree_hash
from wiki_studio import api
from wiki_studio import discovery as wiki_discovery
from wiki_studio.discovery import RANKER_FTS5, RANKER_INDEX_FIRST, RankerConfig, ranker_config_hash
from wiki_studio.paths import WikiPaths
from wiki_studio.querier import _extract_index_links

NAVIGATION = Path(__file__).resolve().parents[1] / "eval" / "navigation"
RUN2 = NAVIGATION / "run2"
RUN3 = NAVIGATION / "run3"
HELDOUT = NAVIGATION / "heldout"
UNTUNED = RUN3 / "ranker-config-untuned.json"
UNTUNED_RESULTS = RUN3 / "results-untuned.json"

# Every committed results file and the fixture it was produced over (each checked once it exists).
COMMITTED_RESULTS: list[tuple[Path, Path, Path]] = [
    (UNTUNED_RESULTS, RUN2, NAVIGATION),
    (RUN3 / "results.json", RUN2, NAVIGATION),
    (HELDOUT / "results.json", HELDOUT, NAVIGATION),
]

ALPHA = "concepts/alpha.md"
BETA = "concepts/beta.md"
PAGE = "---\npage_type: concept\nslug: {slug}\ntitle: {title}\nstatus: stable\n---\n\n# {title}\n\n{body}\n"
INDEX = (
    "---\npage_type: index\nslug: index\ntitle: Index\n---\n\n# Index\n\n"
    "- [Alpha](concepts/alpha.md)\n- [Beta](concepts/beta.md)\n"
)
QUESTIONS = [
    {"id": "h01", "kind": "single", "question": "How are alpha tiles cached offline?"},
    {"id": "h02", "kind": "competing", "question": "Which recorder writes beta storage?"},
    {"id": "h03", "kind": "absent", "question": "What does the gamma licence cost?"},
]
GOLD: list[dict[str, Any]] = [
    {"id": "h01", "gold": ALPHA, "distractors": [], "reason": "alpha caches tiles"},
    {"id": "h02", "gold": BETA, "distractors": [ALPHA], "reason": "beta holds the recorder"},
    {"id": "h03", "gold": None, "distractors": [], "reason": "not in the corpus"},
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _quiet(func: Any, *args: Any) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = func(*args)
    return code, out.getvalue(), err.getvalue()


def _manifest(heldout: Path) -> dict[str, Any]:
    return json.loads((heldout / "manifest.json").read_text(encoding="utf-8"))


def _set_manifest(heldout: Path, **fields: Any) -> None:
    manifest = _manifest(heldout) if (heldout / "manifest.json").exists() else {"set": "heldout"}
    manifest.update(fields)
    (heldout / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _synthetic_heldout(root: Path) -> Path:
    """A held-out set in state ``ingested``: two pages, three questions, gold, one corpus file."""
    heldout = root / "heldout"
    _write(heldout / "wiki" / "index.md", INDEX)
    _write(heldout / "wiki" / "log.md", "---\npage_type: log\nslug: log\ntitle: Log\n---\n\n# Log\n")
    _write(
        heldout / "wiki" / ALPHA,
        PAGE.format(slug="alpha", title="Alpha tiles", body="Alpha caches map tiles offline in a store."),
    )
    _write(
        heldout / "wiki" / BETA,
        PAGE.format(slug="beta", title="Beta recorder", body="The beta recorder writes sessions to storage."),
    )
    _write(heldout / "corpus" / "README.md", "Alpha tiles are cached offline. The beta recorder writes storage.\n")
    _write(heldout / "questions.json", json.dumps(QUESTIONS))
    _write(heldout / "gold.json", json.dumps(GOLD))
    _set_manifest(
        heldout,
        state=heldout_protocol.STATE_INGESTED,
        history=[],
        questions_sha256=_sha256(heldout / "questions.json"),
        corpus_files=[
            {"path": "README.md", "corpus_file": "README.md", "sha256": _sha256(heldout / "corpus" / "README.md")}
        ],
        ingest={"summary": {"documents_ingested": 1, "promoted": 1}},
    )
    return heldout


def _corpus_entry(heldout: Path) -> list[dict[str, Any]]:
    """One recorded corpus file under ``heldout/corpus/`` (written if absent), as the sources step records it."""
    source = heldout / "corpus" / "README.md"
    if not source.is_file():
        _write(source, "Alpha tiles are cached offline. The beta recorder writes storage.\n")
    return [{"path": "README.md", "corpus_file": "README.md", "sha256": _sha256(source)}]


def _frozen_heldout(root: Path) -> Path:
    heldout = _synthetic_heldout(root)
    heldout_protocol.step_freeze_wiki(heldout)
    heldout_protocol.step_freeze(heldout)
    return heldout


def _run3_with_untuned(root: Path) -> Path:
    run3 = root / "run3"
    run3.mkdir()
    shutil.copy(UNTUNED, run3 / UNTUNED.name)
    shutil.copy(UNTUNED_RESULTS, run3 / UNTUNED_RESULTS.name)
    return run3


# ── Reproduction of the committed results ─────────────────────


class TestCommittedResultsReproduce(unittest.TestCase):
    def test_results_untuned_is_committed(self) -> None:
        self.assertTrue(UNTUNED.is_file())
        self.assertTrue(UNTUNED_RESULTS.is_file())

    def test_every_committed_results_file_reproduces_and_writes_nothing(self) -> None:
        for results, fixture, shared in COMMITTED_RESULTS:
            if not results.is_file():
                continue
            with self.subTest(results=results.name, fixture=fixture.name):
                before = (_tree_hash(fixture), _tree_hash(RUN3))
                self.assertTrue(discovery.reproduce(results, fixture, shared))
                self.assertEqual((_tree_hash(fixture), _tree_hash(RUN3)), before)

    def test_reproduction_survives_a_changed_live_default(self) -> None:
        changed = RankerConfig(tokenizer="unicode61", weights=(1.0, 1.0, 1.0, 1.0), min_match_tokens=2, max_pages=5)
        with (
            mock.patch.object(wiki_discovery, "DEFAULT_RANKER_CONFIG", changed),
            mock.patch.object(wiki_discovery, "DEFAULT_RANKER", RANKER_FTS5),
        ):
            self.assertTrue(discovery.reproduce(UNTUNED_RESULTS, RUN2, NAVIGATION))

    def test_a_changed_number_does_not_reproduce(self) -> None:
        committed = json.loads(UNTUNED_RESULTS.read_text(encoding="utf-8"))
        committed["navigation"][RANKER_FTS5]["hits_at_1"] += 1
        with tempfile.TemporaryDirectory() as tmp:
            stale = Path(tmp) / "results.json"
            stale.write_text(json.dumps(committed), encoding="utf-8")
            self.assertFalse(discovery.reproduce(stale, RUN2, NAVIGATION))

    def test_latency_and_environment_are_not_compared(self) -> None:
        committed = json.loads(UNTUNED_RESULTS.read_text(encoding="utf-8"))
        committed["latency"] = {"cold_cache": {"median_ms": 1e9}}
        committed["parameters"]["sqlite_version"] = "0.0.0"
        committed["parameters"]["wiki_studio_version"] = "0.0.0"
        with tempfile.TemporaryDirectory() as tmp:
            edited = Path(tmp) / "results.json"
            edited.write_text(json.dumps(committed), encoding="utf-8")
            self.assertTrue(discovery.reproduce(edited, RUN2, NAVIGATION))

    def test_the_untuned_configuration_is_fr006s(self) -> None:
        config = discovery.load_config(UNTUNED)
        self.assertEqual(config, RankerConfig("porter unicode61", (4.0, 4.0, 2.0, 1.0), 1, 5))
        recorded = json.loads(UNTUNED_RESULTS.read_text(encoding="utf-8"))["parameters"]
        self.assertEqual(recorded["ranker_config_hash"], ranker_config_hash(config))

    def test_index_first_on_the_development_set_is_run2s_published_baseline(self) -> None:
        run3 = json.loads(UNTUNED_RESULTS.read_text(encoding="utf-8"))["navigation"][RANKER_INDEX_FIRST]
        run2 = json.loads((RUN2 / "results.json").read_text(encoding="utf-8"))["navigation"]
        self.assertEqual((run3["hits_at_1"], run3["hits_at_5"], run3["evaluated"]), (3, 10, 21))
        self.assertEqual(run3["hit_at_1"], run2["hit_at_1"])
        self.assertEqual(run3["hit_at_5"], run2["hit_at_max"])
        self.assertEqual(run3["random_hit_at_1"], run2["random_hit_at_1"])
        self.assertEqual(run3["random_hit_at_5"], run2["random_hit_at_max"])

    def test_every_hit_rate_has_the_eligible_pages_and_the_random_baseline(self) -> None:
        for results, _fixture, _shared in COMMITTED_RESULTS:
            if not results.is_file():
                continue
            document = json.loads(results.read_text(encoding="utf-8"))
            for ranker in (RANKER_FTS5, RANKER_INDEX_FIRST):
                block = document["navigation"][ranker]
                with self.subTest(results=results.name, ranker=ranker):
                    for key in ("hit_at_1", "hit_at_5", "random_hit_at_1", "random_hit_at_5"):
                        self.assertIn(key, block)
                    self.assertEqual(block["eligible_pages"], document["eligible_pages"])
            for key in ("counts", "absent", "context", "ingest_coverage", "latency", "parameters", "discordant"):
                self.assertIn(key, document)
            entry = document["per_question"][0]
            for key in ("selected", "hit_at_1", "hit_at_5", "distractor_outranks", "bytes_loaded", "words_loaded"):
                self.assertIn(key, entry[RANKER_FTS5])
            self.assertIn("grep_words", entry)

    def test_the_heldout_result_ran_under_the_frozen_configuration(self) -> None:
        results = HELDOUT / "results.json"
        if not results.is_file():
            self.skipTest("no held-out run yet (the evidence PR, FR-028)")
        tuned = json.loads((RUN3 / "ranker-config.json").read_text(encoding="utf-8"))
        recorded = json.loads(results.read_text(encoding="utf-8"))["parameters"]["ranker_config_hash"]
        self.assertEqual(tuned["ranker_config_hash"], recorded)


class TestHeldOutSources(unittest.TestCase):
    def test_the_corpus_is_the_pinned_mapatlas_readmes(self) -> None:
        manifest = _manifest(HELDOUT)
        self.assertEqual(manifest["corpus_commit"], "7c3a8de609fb8e2173a74a884afdc4029ff18ca5")
        self.assertEqual(len(manifest["corpus_files"]), 8)
        self.assertEqual(sum(f["bytes"] for f in manifest["corpus_files"]), manifest["corpus_bytes"])
        self.assertEqual(manifest["corpus_bytes"], 30554)
        on_disk = sorted(p.name for p in (HELDOUT / "corpus").iterdir())
        self.assertEqual(on_disk, sorted(f["corpus_file"] for f in manifest["corpus_files"]))
        for entry in manifest["corpus_files"]:
            with self.subTest(path=entry["path"]):
                self.assertEqual(entry["corpus_file"], entry["path"].replace("/", "__"))
                data = (HELDOUT / "corpus" / entry["corpus_file"]).read_bytes()
                self.assertEqual((hashlib.sha256(data).hexdigest(), len(data)), (entry["sha256"], entry["bytes"]))


# ── tune ──────────────────────────────────────────────────────


class TestTuneGuards(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _tune(self, heldout: Path, run3: Path, configurations: list[RankerConfig] | None = None) -> RankerConfig:
        return discovery.tune(
            run3_dir=run3, heldout_dir=heldout, dev_fixture=RUN2, shared_dir=NAVIGATION, configurations=configurations
        )

    def test_tune_refuses_before_the_heldout_freeze(self) -> None:
        heldout = _synthetic_heldout(self.root)
        run3 = _run3_with_untuned(self.root)
        with self.assertRaisesRegex(discovery.RunnerError, "not frozen"):
            self._tune(heldout, run3)
        self.assertFalse((run3 / discovery.TUNING_NAME).exists())

    def test_tune_refuses_when_the_frozen_set_was_edited(self) -> None:
        heldout = _frozen_heldout(self.root)
        _write(heldout / "gold.json", json.dumps(GOLD[:2] + [dict(GOLD[2], reason="edited")]))
        with self.assertRaisesRegex(discovery.RunnerError, "gold.json"):
            self._tune(heldout, _run3_with_untuned(self.root))

    def test_tune_refuses_when_results_untuned_is_missing(self) -> None:
        heldout = _frozen_heldout(self.root)
        run3 = _run3_with_untuned(self.root)
        (run3 / UNTUNED_RESULTS.name).unlink()
        with self.assertRaisesRegex(discovery.RunnerError, "committed first"):
            self._tune(heldout, run3)

    def test_tune_refuses_when_results_untuned_is_stale(self) -> None:
        heldout = _frozen_heldout(self.root)
        run3 = _run3_with_untuned(self.root)
        stale = json.loads((run3 / UNTUNED_RESULTS.name).read_text(encoding="utf-8"))
        stale["navigation"][RANKER_FTS5]["hit_at_1"] = 1.0
        (run3 / UNTUNED_RESULTS.name).write_text(json.dumps(stale), encoding="utf-8")
        with self.assertRaisesRegex(discovery.RunnerError, "does not reproduce"):
            self._tune(heldout, run3)

    def test_tune_chooses_by_hit_at_1_and_freezes_the_choice(self) -> None:
        heldout = _frozen_heldout(self.root)
        run3 = _run3_with_untuned(self.root)
        untuned = discovery.load_config(UNTUNED)
        other = dataclasses.replace(untuned, min_match_tokens=2)
        chosen = self._tune(heldout, run3, [other, untuned])
        tuning = json.loads((run3 / discovery.TUNING_NAME).read_text(encoding="utf-8"))
        self.assertEqual(len(tuning["configurations"]), 2)
        best = max(tuning["configurations"], key=lambda r: (r["hit_at_1"], r["hit_at_5"]))
        self.assertEqual(ranker_config_hash(chosen), tuning["chosen"]["ranker_config_hash"])
        self.assertEqual(
            (tuning["chosen"]["hit_at_1"], tuning["chosen"]["hit_at_5"]), (best["hit_at_1"], best["hit_at_5"])
        )
        written = json.loads((run3 / discovery.TUNED_CONFIG_NAME).read_text(encoding="utf-8"))
        self.assertEqual(written["ranker_config_hash"], ranker_config_hash(chosen))
        with self.assertRaisesRegex(discovery.RunnerError, "frozen"):
            self._tune(heldout, run3, [untuned])

    def test_tune_refuses_candidates_without_the_untuned_configuration(self) -> None:
        heldout = _frozen_heldout(self.root)
        run3 = _run3_with_untuned(self.root)
        other = dataclasses.replace(discovery.load_config(UNTUNED), min_match_tokens=2)
        with self.assertRaisesRegex(discovery.RunnerError, "tie-break"):
            self._tune(heldout, run3, [other])
        self.assertFalse((run3 / discovery.TUNED_CONFIG_NAME).exists())

    def test_the_grid_is_closed(self) -> None:
        grid = discovery.grid()
        self.assertEqual(len(grid), 108)
        self.assertEqual(len({ranker_config_hash(c) for c in grid}), 108)
        self.assertIn(discovery.load_config(UNTUNED), grid)
        self.assertTrue(all(c.weights[3] == 1.0 and c.max_pages == 5 for c in grid))

    def test_tune_through_main_refuses_while_not_frozen(self) -> None:
        heldout = _synthetic_heldout(self.root)
        with mock.patch.object(discovery, "HELDOUT_DIR", heldout):
            code, _out, err = _quiet(discovery.main, ["tune"])
        self.assertEqual(code, 1)
        self.assertIn("not frozen", err)


# ── The one held-out run ──────────────────────────────────────


class TestHeldOutRunGuards(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.run3 = self.root / "run3"
        self.run3.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_tuning(self, chosen_hash: str) -> None:
        """``run3/tuning.json`` as ``tune`` leaves it, reduced to the chosen entry the run checks."""
        discovery._write_json(self.run3 / discovery.TUNING_NAME, {"chosen": {"ranker_config_hash": chosen_hash}})

    def _freeze_config(self, config: RankerConfig) -> None:
        """``tune``'s outcome for ``config``: the frozen configuration file and the tuning record that chose it."""
        discovery._write_json(self.run3 / discovery.TUNED_CONFIG_NAME, discovery.config_document(config))
        self._write_tuning(ranker_config_hash(config))

    def _freeze_live_config(self) -> None:
        self._freeze_config(discovery._live_config())

    def _main_run(self, heldout: Path, *extra: str) -> tuple[int, str, str]:
        argv = ["run", "--fixture", str(heldout), "--shared", str(NAVIGATION), *extra]
        with mock.patch.object(discovery, "RUN3_DIR", self.run3):
            return _quiet(discovery.main, argv)

    def _assert_no_attempt(self, heldout: Path) -> None:
        self.assertFalse((heldout / heldout_protocol.RUN_ATTEMPT_NAME).exists(), "no attempt was consumed")
        self.assertFalse((heldout / "results.json").exists())
        self.assertEqual(_manifest(heldout)["state"], heldout_protocol.STATE_FROZEN)

    def test_run_refuses_a_configuration_tune_did_not_choose(self) -> None:
        """``ranker-config.json`` must be ``tuning.json``'s chosen entry: the configuration came from ``tune``."""
        heldout = _frozen_heldout(self.root)
        self._freeze_live_config()
        self._write_tuning("0" * 64)
        code, _out, err = self._main_run(heldout)
        self.assertEqual(code, 1)
        self.assertIn("run: refusing", err)
        self.assertIn(discovery.TUNING_NAME, err)
        self._assert_no_attempt(heldout)
        (self.run3 / discovery.TUNING_NAME).unlink()
        code, _out, err = self._main_run(heldout)
        self.assertEqual(code, 1)
        self.assertIn("run: refusing", err)
        self.assertIn(f"{discovery.TUNING_NAME} does not exist", err)
        self._assert_no_attempt(heldout)
        self._write_tuning(ranker_config_hash(discovery._live_config()))
        code, _out, err = self._main_run(heldout)
        self.assertEqual(code, 0, err)
        self.assertTrue((heldout / heldout_protocol.RUN_ATTEMPT_NAME).is_file())

    def test_a_copy_without_the_set_field_is_still_the_heldout_set(self) -> None:
        """Recognition by content: the copy's questions, gold and corpus hash to what the committed manifest records."""
        heldout = _frozen_heldout(self.root)
        copy = self.root / "elsewhere" / "fixture"
        shutil.copytree(heldout, copy)
        manifest = _manifest(copy)
        del manifest["set"]
        (copy / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with mock.patch.object(discovery, "HELDOUT_DIR", self.root / "absent"):
            self.assertEqual(discovery._heldout_content_hashes(), frozenset())
            self.assertFalse(discovery.is_heldout(copy), "with no committed manifest nothing is recognised")
        with mock.patch.object(discovery, "HELDOUT_DIR", heldout):
            self.assertTrue(discovery.is_heldout(copy))
            self.assertFalse(discovery.is_heldout(RUN2))
            code, _out, err = self._main_run(copy)
            self.assertEqual(code, 1, "the held-out guards apply to the copy")
            self.assertIn("does not exist (tune first", err)
            self._assert_no_attempt(copy)
            self._freeze_live_config()
            code, _out, err = self._main_run(copy)
            self.assertEqual(code, 0, err)
        self.assertTrue((copy / heldout_protocol.RUN_ATTEMPT_NAME).is_file(), "the attempt is recorded")
        self.assertTrue((copy / "results.json").is_file())
        self.assertEqual(_manifest(copy)["state"], heldout_protocol.STATE_RUN)
        self.assertEqual(_manifest(heldout)["state"], heldout_protocol.STATE_FROZEN, "the original is untouched")

    def test_a_missing_input_file_is_a_refusal_not_a_traceback(self) -> None:
        shared = self.root / "shared"
        shutil.copytree(NAVIGATION / "corpus", shared / "corpus")
        shutil.copy(NAVIGATION / "questions.json", shared / "questions.json")
        fixture = self.root / "dev"
        shutil.copytree(RUN2 / "wiki", fixture / "wiki")
        shutil.copy(RUN2 / "gold.json", fixture / "gold.json")
        shutil.copy(RUN2 / "results.json", fixture / "results.json")
        argv = ["run", "--fixture", str(fixture), "--shared", str(shared), "--config", str(UNTUNED)]
        code, _out, err = _quiet(discovery.main, argv)
        self.assertEqual(code, 1)
        self.assertIn(f"{shared / 'stopwords.txt'} not found", err)
        shutil.copy(NAVIGATION / "stopwords.txt", shared / "stopwords.txt")
        (fixture / "gold.json").unlink()
        code, _out, err = _quiet(discovery.main, argv)
        self.assertEqual(code, 1)
        self.assertIn(f"{fixture / 'gold.json'} not found", err)
        shutil.copy(RUN2 / "gold.json", fixture / "gold.json")
        (shared / "questions.json").unlink()
        code, _out, err = _quiet(discovery.main, argv)
        self.assertEqual(code, 1)
        self.assertIn(f"{shared / 'questions.json'} not found", err)
        shutil.copy(NAVIGATION / "questions.json", shared / "questions.json")
        code, out, err = _quiet(discovery.main, argv)
        self.assertEqual(code, 0, err)
        self.assertIn('"navigation"', out)

    def test_run_refuses_before_the_freeze(self) -> None:
        heldout = _synthetic_heldout(self.root)
        self._freeze_live_config()
        code, _out, err = self._main_run(heldout)
        self.assertEqual(code, 1)
        self.assertIn("not frozen", err)
        self.assertFalse((heldout / "results.json").exists())

    def test_run_refuses_a_config_for_the_heldout_set(self) -> None:
        heldout = _frozen_heldout(self.root)
        self._freeze_live_config()
        code, _out, err = self._main_run(heldout, "--config", str(UNTUNED))
        self.assertEqual(code, 1)
        self.assertIn("--config is refused", err)

    def test_run_refuses_without_the_frozen_configuration(self) -> None:
        heldout = _frozen_heldout(self.root)
        code, _out, err = self._main_run(heldout)
        self.assertEqual((code, "does not exist" in err), (1, True))
        other = RankerConfig("unicode61", (1.0, 2.0, 4.0, 1.0), 2, 5)
        discovery._write_json(self.run3 / discovery.TUNED_CONFIG_NAME, discovery.config_document(other))
        code, _out, err = self._main_run(heldout)
        self.assertEqual(code, 1)
        self.assertIn("differs from the live ranker_config_hash", err)

    def test_the_one_run_is_written_once_and_later_runs_are_post_hoc(self) -> None:
        heldout = _frozen_heldout(self.root)
        self._freeze_live_config()
        code, _out, err = self._main_run(heldout)
        self.assertEqual(code, 0, err)
        results = heldout / "results.json"
        written = results.read_bytes()
        manifest = _manifest(heldout)
        self.assertEqual(manifest["state"], heldout_protocol.STATE_RUN)
        self.assertEqual(manifest["history"][-1]["state"], heldout_protocol.STATE_RUN)
        document = json.loads(written)
        self.assertEqual(document["ingest_coverage"]["basis"], "measured")
        self.assertEqual(document["eligible_pages"], 2)
        self.assertEqual(document["parameters"]["ranker_config_hash"], ranker_config_hash(discovery._live_config()))

        code, _out, err = self._main_run(heldout)
        self.assertEqual(code, 1)
        self.assertIn("--post-hoc", err)
        self.assertEqual(results.read_bytes(), written)

        code, _out, err = self._main_run(heldout, "--post-hoc", "../x")
        self.assertEqual(code, 1)
        code, _out, err = self._main_run(heldout, "--post-hoc", "rerun-1")
        self.assertEqual(code, 0, err)
        self.assertTrue((heldout / "results-post-hoc-rerun-1.json").is_file())
        self.assertEqual(results.read_bytes(), written)
        code, _out, _err = self._main_run(heldout, "--post-hoc", "rerun-1")
        self.assertEqual(code, 1)

        self.assertTrue(discovery.reproduce(results, heldout, NAVIGATION))

    def test_the_one_run_leaves_an_immutable_attempt_marker(self) -> None:
        heldout = _frozen_heldout(self.root)
        self._freeze_live_config()
        code, _out, err = self._main_run(heldout)
        self.assertEqual(code, 0, err)
        marker = json.loads((heldout / heldout_protocol.RUN_ATTEMPT_NAME).read_text(encoding="utf-8"))
        self.assertEqual(marker["ranker_config_hash"], ranker_config_hash(discovery._live_config()))
        self.assertEqual(marker["wiki_studio_version"], discovery.__version__)
        self.assertTrue(marker["started_at"] and marker["wiki_studio_commit"])
        manifest = _manifest(heldout)
        visited = [h["state"] for h in manifest["history"][-2:]]
        self.assertEqual(visited, [heldout_protocol.STATE_RUN_STARTED, heldout_protocol.STATE_RUN])
        document = json.loads((heldout / "results.json").read_text(encoding="utf-8"))
        self.assertEqual(document[discovery.ATTEMPT_KEY], marker)
        self.assertEqual(manifest[discovery.ATTEMPT_KEY], marker)
        with self.assertRaises(discovery.RunnerError):
            discovery._write_attempt_marker(heldout, {"started_at": "later"})

    def test_an_input_error_is_refused_before_the_attempt_is_recorded(self) -> None:
        """Inputs are checked first: a bad input is an ordinary refusal and never consumes the one attempt."""
        heldout = _frozen_heldout(self.root)
        self._freeze_live_config()
        code, _out, err = self._main_run(heldout, "--search-cache", str(heldout / "cache.sqlite"))
        self.assertEqual(code, 1)
        self.assertIn("inside a frozen evaluation directory", err)
        self.assertFalse((heldout / heldout_protocol.RUN_ATTEMPT_NAME).exists(), "no attempt was recorded")
        self.assertFalse((heldout / "results.json").exists())
        self.assertEqual(_manifest(heldout)["state"], heldout_protocol.STATE_FROZEN)
        code, _out, err = self._main_run(heldout)
        self.assertEqual(code, 0, err)
        self.assertTrue((heldout / heldout_protocol.RUN_ATTEMPT_NAME).exists())

    def test_a_crash_between_the_marker_and_the_manifest_is_still_recoverable(self) -> None:
        """A marker with no results is an interrupted attempt even when the manifest never reached run-started."""
        heldout = _frozen_heldout(self.root)
        self._freeze_live_config()
        marker = heldout / heldout_protocol.RUN_ATTEMPT_NAME
        with (
            mock.patch.object(discovery, "save_manifest", side_effect=RuntimeError("the disk went away")),
            self.assertRaises(RuntimeError),
        ):
            discovery.run(heldout, NAVIGATION, config_path=None, search_cache=None, post_hoc=None, run3_dir=self.run3)
        self.assertTrue(marker.exists())
        self.assertEqual(_manifest(heldout)["state"], heldout_protocol.STATE_FROZEN, "the transition never landed")
        code, _out, err = self._main_run(heldout)
        self.assertEqual(code, 1)
        self.assertIn("--post-hoc", err)
        code, _out, err = self._main_run(heldout, "--post-hoc", "recovery")
        self.assertEqual(code, 0, err)
        self.assertTrue((heldout / "results-post-hoc-recovery.json").exists())
        self.assertFalse((heldout / "results.json").exists(), "the original is never produced after a crash")

    def test_a_missing_or_edited_held_out_corpus_is_refused_before_the_attempt(self) -> None:
        """The held-out corpus is an input of its own: it is verified first and never borrowed from the shared set."""
        heldout = _frozen_heldout(self.root)
        self._freeze_live_config()
        corpus = heldout / "corpus"
        kept = (corpus / "README.md").read_bytes()
        (corpus / "README.md").write_bytes(kept + b"edited after the freeze\n")
        code, _out, err = self._main_run(heldout)
        self.assertEqual(code, 1)
        self.assertIn("corpus files missing or differing", err)
        shutil.rmtree(corpus)
        code, _out, err = self._main_run(heldout)
        self.assertEqual(code, 1)
        self.assertIn("corpus files missing or differing", err)
        self.assertFalse((heldout / heldout_protocol.RUN_ATTEMPT_NAME).exists(), "no attempt was consumed")
        self.assertEqual(_manifest(heldout)["state"], heldout_protocol.STATE_FROZEN)
        _write(corpus / "README.md", kept.decode("utf-8"))
        code, _out, err = self._main_run(heldout)
        self.assertEqual(code, 0, err)

    def test_an_interrupted_attempt_is_never_repeated_as_the_original(self) -> None:
        heldout = _frozen_heldout(self.root)
        self._freeze_live_config()
        results = heldout / "results.json"
        marker = heldout / heldout_protocol.RUN_ATTEMPT_NAME
        compute = discovery.compute
        with (
            mock.patch.object(discovery, "compute", side_effect=RuntimeError("the machine went away")),
            self.assertRaisesRegex(RuntimeError, "the machine went away"),
        ):
            self._main_run(heldout)
        self.assertTrue(marker.is_file())
        self.assertFalse(results.exists())
        manifest = _manifest(heldout)
        self.assertEqual(manifest["state"], heldout_protocol.STATE_RUN_STARTED)
        self.assertTrue(manifest[discovery.ATTEMPT_KEY]["failed_at"])
        self.assertIn("RuntimeError", manifest[discovery.ATTEMPT_KEY]["error"])
        marker_bytes = marker.read_bytes()
        started = json.loads(marker_bytes)["started_at"]

        code, _out, err = self._main_run(heldout)
        self.assertEqual(code, 1)
        self.assertIn(f"started at {started}", err)
        self.assertIn("--post-hoc", err)
        self.assertFalse(results.exists())
        self.assertEqual(marker.read_bytes(), marker_bytes)
        self.assertEqual(_manifest(heldout)["state"], heldout_protocol.STATE_RUN_STARTED)

        with mock.patch.object(discovery, "compute", wraps=compute):
            code, _out, err = self._main_run(heldout, "--post-hoc", "recovery")
        self.assertEqual(code, 0, err)
        self.assertTrue((heldout / "results-post-hoc-recovery.json").is_file())
        self.assertFalse(results.exists())
        self.assertEqual(marker.read_bytes(), marker_bytes)
        self.assertEqual(_manifest(heldout)["state"], heldout_protocol.STATE_RUN_STARTED)

    def test_a_crashed_attempt_without_a_failure_record_is_post_hoc_only(self) -> None:
        # The process was killed after the marker: no failed_at, run-started, no results.json.
        heldout = _frozen_heldout(self.root)
        self._freeze_live_config()
        with (
            mock.patch.object(discovery, "compute", side_effect=KeyboardInterrupt),
            self.assertRaises(KeyboardInterrupt),
        ):
            discovery.run(heldout, NAVIGATION, config_path=None, search_cache=None, post_hoc=None, run3_dir=self.run3)
        manifest = _manifest(heldout)
        manifest[discovery.ATTEMPT_KEY].pop("failed_at")
        manifest[discovery.ATTEMPT_KEY].pop("error")
        (heldout / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        code, _out, err = self._main_run(heldout)
        self.assertEqual((code, "--post-hoc" in err), (1, True))
        code, _out, err = self._main_run(heldout, "--post-hoc", "after-kill")
        self.assertEqual(code, 0, err)
        self.assertFalse((heldout / "results.json").exists())

    def test_post_hoc_after_a_failed_attempt_checks_the_markers_configuration(self) -> None:
        heldout = _frozen_heldout(self.root)
        self._freeze_live_config()
        with mock.patch.object(discovery, "compute", side_effect=RuntimeError("boom")), self.assertRaises(RuntimeError):
            self._main_run(heldout)
        other = RankerConfig("unicode61", (1.0, 2.0, 4.0, 1.0), 2, 5)
        with mock.patch.object(wiki_discovery, "DEFAULT_RANKER_CONFIG", other):
            self._freeze_config(other)
            code, _out, err = self._main_run(heldout, "--post-hoc", "retuned")
        self.assertEqual(code, 1)
        self.assertIn("not produced under the current", err)
        self.assertFalse((heldout / "results-post-hoc-retuned.json").exists())

    def test_post_hoc_refuses_when_the_original_ran_under_another_configuration(self) -> None:
        heldout = _frozen_heldout(self.root)
        self._freeze_live_config()
        code, _out, err = self._main_run(heldout)
        self.assertEqual(code, 0, err)
        results = heldout / "results.json"
        document = json.loads(results.read_text(encoding="utf-8"))
        document["parameters"]["ranker_config_hash"] = "0" * 64
        results.write_text(json.dumps(document), encoding="utf-8")
        code, _out, err = self._main_run(heldout, "--post-hoc", "rerun-1")
        self.assertEqual(code, 1)
        self.assertIn("not produced under the current", err)
        self.assertFalse((heldout / "results-post-hoc-rerun-1.json").exists())

    def test_inherited_ingest_coverage_needs_the_fixtures_results(self) -> None:
        fixture = self.root / "dev"
        shutil.copytree(RUN2 / "wiki", fixture / "wiki")
        shutil.copy(RUN2 / "gold.json", fixture / "gold.json")
        with self.assertRaisesRegex(discovery.RunnerError, "inherited"):
            discovery.compute(
                fixture,
                NAVIGATION,
                config=discovery.load_config(UNTUNED),
                search_cache=self.root / "c.sqlite",
                latency=False,
            )

    def test_post_hoc_needs_the_original_run(self) -> None:
        heldout = _frozen_heldout(self.root)
        self._freeze_live_config()
        code, _out, err = self._main_run(heldout, "--post-hoc", "early")
        self.assertEqual(code, 1)
        self.assertIn("has not happened", err)

    def test_post_hoc_is_for_the_heldout_set_only(self) -> None:
        code, _out, err = _quiet(
            discovery.main, ["run", "--fixture", str(RUN2), "--shared", str(NAVIGATION), "--post-hoc", "x"]
        )
        self.assertEqual(code, 1)
        self.assertIn("held-out set only", err)


# ── decide ────────────────────────────────────────────────────


def _results(fts5: tuple[float, float], index_first: tuple[float, float], ran_as: str = RANKER_FTS5) -> dict[str, Any]:
    return {
        "navigation": {
            RANKER_FTS5: {"hit_at_1": fts5[0], "hit_at_5": fts5[1], "ran_as": [ran_as]},
            RANKER_INDEX_FIRST: {
                "hit_at_1": index_first[0],
                "hit_at_5": index_first[1],
                "ran_as": [RANKER_INDEX_FIRST],
            },
        }
    }


FLOORS_MET = {"gold_questions": 15, "eligible_pages": 10}


class TestDecisionRule(unittest.TestCase):
    def test_pass(self) -> None:
        decision = discovery.decide(_results((0.5, 0.8), (0.5, 0.8)), FLOORS_MET)
        self.assertEqual(decision.default_ranker, RANKER_FTS5)
        self.assertIn("held-out measurement", decision.basis)

    def test_fail_at_1(self) -> None:
        decision = discovery.decide(_results((0.4, 0.9), (0.5, 0.8)), FLOORS_MET)
        self.assertEqual(decision.default_ranker, RANKER_INDEX_FIRST)
        self.assertIn("hit at 1", decision.basis)

    def test_fail_at_5(self) -> None:
        decision = discovery.decide(_results((0.6, 0.7), (0.5, 0.8)), FLOORS_MET)
        self.assertEqual(decision.default_ranker, RANKER_INDEX_FIRST)
        self.assertIn("hit at 5", decision.basis)

    def test_gold_question_floor(self) -> None:
        decision = discovery.decide(_results((0.9, 0.9), (0.1, 0.1)), {"gold_questions": 14, "eligible_pages": 10})
        self.assertEqual(decision.default_ranker, RANKER_INDEX_FIRST)
        self.assertIn("fewer than 15 gold questions (14", decision.basis)
        self.assertIn("want of evidence", decision.basis)

    def test_eligible_page_floor(self) -> None:
        decision = discovery.decide(_results((0.9, 0.9), (0.1, 0.1)), {"gold_questions": 15, "eligible_pages": 9})
        self.assertEqual(decision.default_ranker, RANKER_INDEX_FIRST)
        self.assertIn("fewer than 10 eligible pages (9", decision.basis)

    def test_a_fallback_is_not_a_pass(self) -> None:
        results = _results((0.5, 0.8), (0.5, 0.8), ran_as=RANKER_INDEX_FIRST)
        decision = discovery.decide(results, FLOORS_MET)
        self.assertEqual(decision.default_ranker, RANKER_INDEX_FIRST)
        self.assertIn("fell back on at least one", decision.basis)
        results["per_question"] = [
            {RANKER_FTS5: {"ran_as": RANKER_FTS5}},
            {RANKER_FTS5: {"ran_as": RANKER_INDEX_FIRST}},
        ]
        self.assertIn("1 of 2 questions", discovery.decide(results, FLOORS_MET).basis)

    def test_decide_without_a_heldout_run_says_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(discovery, "HELDOUT_DIR", Path(tmp)):
            code, out, err = _quiet(discovery.main, ["decide"])
        self.assertEqual(code, 1)
        self.assertIn("rule:", out)
        self.assertIn("pending", err)

    def test_decide_prints_the_basis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            heldout = Path(tmp)
            (heldout / "results.json").write_text(json.dumps(_results((0.5, 0.8), (0.4, 0.8))), encoding="utf-8")
            (heldout / "manifest.json").write_text(json.dumps(FLOORS_MET), encoding="utf-8")
            with mock.patch.object(discovery, "HELDOUT_DIR", heldout):
                code, out, _err = _quiet(discovery.main, ["decide"])
        self.assertEqual(code, 0)
        self.assertIn("default ranker: fts5", out)
        self.assertIn("basis: held-out measurement", out)


# ── heldout_protocol.py ───────────────────────────────────────


def _valid_questions() -> list[dict[str, str]]:
    kinds = ["single"] * 29 + ["competing"] * 6 + ["absent"] * 6
    return [{"id": f"h{n:02d}", "kind": kind, "question": f"question {n}?"} for n, kind in enumerate(kinds, start=1)]


class TestHeldOutProtocolOrder(unittest.TestCase):
    STEPS: tuple[tuple[str, str], ...] = (
        ("questions", heldout_protocol.STATE_SOURCES),
        ("pin", heldout_protocol.STATE_QUESTIONS),
        ("probe", heldout_protocol.STATE_PINNED),
        ("ingest", heldout_protocol.STATE_PINNED),
        ("freeze-wiki", heldout_protocol.STATE_INGESTED),
        ("freeze", heldout_protocol.STATE_WIKI_FROZEN),
    )

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.heldout = Path(self._tmp.name) / "heldout"
        self.heldout.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _main(self, *argv: str) -> tuple[int, str, str]:
        return _quiet(heldout_protocol.main, ["--heldout-dir", str(self.heldout), *argv])

    def test_every_step_refuses_out_of_order(self) -> None:
        for step, expected in self.STEPS:
            for state in heldout_protocol.STATES:
                if state == expected:
                    continue
                with self.subTest(step=step, state=state):
                    _set_manifest(self.heldout, state=state)
                    code, _out, err = self._main(step)
                    self.assertEqual(code, 1)
                    self.assertIn(f"expected state {expected!r}", err)
                    self.assertEqual(_manifest(self.heldout)["state"], state)

    def test_the_committed_manifest_moved_through_the_states_in_order(self) -> None:
        # The build ships the sources only; every later state is the owner's (the evidence PR), taken in order.
        manifest = _manifest(HELDOUT)
        visited = [h["state"] for h in manifest["history"]]
        # A re-pin before the ingest (`pin --again`) repeats `pinned` once per entry in pins_history.
        repins = len(manifest.get("pins_history", []))
        self.assertEqual(
            visited.count(heldout_protocol.STATE_PINNED),
            1 + repins if repins else visited.count(heldout_protocol.STATE_PINNED),
        )
        collapsed = [s for i, s in enumerate(visited) if i == 0 or s != visited[i - 1]]
        self.assertEqual(collapsed, list(heldout_protocol.STATES[: len(collapsed)]))
        self.assertEqual(manifest["state"], visited[-1])
        if not (HELDOUT / "wiki").exists():
            self.assertIn(
                manifest["state"],
                heldout_protocol.STATES[: heldout_protocol.STATES.index(heldout_protocol.STATE_INGESTED)],
            )

    def test_questions_records_the_committed_set(self) -> None:
        _set_manifest(self.heldout, state=heldout_protocol.STATE_SOURCES)
        _write(self.heldout / "questions.json", json.dumps(_valid_questions()))
        data = (self.heldout / "questions.json").read_bytes()
        with (
            mock.patch.object(heldout_protocol, "_committed_bytes", return_value=data),
            mock.patch.object(heldout_protocol, "_git", return_value="a" * 40),
        ):
            code, _out, err = self._main("questions", "--commit", "abc")
        self.assertEqual(code, 0, err)
        manifest = _manifest(self.heldout)
        self.assertEqual(manifest["state"], heldout_protocol.STATE_QUESTIONS)
        self.assertEqual(manifest["questions_sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(manifest["questions_commit"], "a" * 40)
        self.assertEqual(manifest["history"][-1]["state"], heldout_protocol.STATE_QUESTIONS)

    def test_questions_refuses_a_sha256_mismatch(self) -> None:
        _set_manifest(self.heldout, state=heldout_protocol.STATE_SOURCES)
        _write(self.heldout / "questions.json", json.dumps(_valid_questions()))
        with mock.patch.object(heldout_protocol, "_committed_bytes", return_value=b"[]"):
            code, _out, err = self._main("questions")
        self.assertEqual(code, 1)
        self.assertIn("differs from its committed version", err)
        self.assertEqual(_manifest(self.heldout)["state"], heldout_protocol.STATE_SOURCES)

    def test_questions_refuses_a_set_below_the_floor(self) -> None:
        _set_manifest(self.heldout, state=heldout_protocol.STATE_SOURCES)
        _write(self.heldout / "questions.json", json.dumps(_valid_questions()[1:]))
        code, _out, err = self._main("questions")
        self.assertEqual(code, 1)
        self.assertIn("at least 35 answerable", err)

    def test_pin_refuses_questions_edited_after_they_were_recorded(self) -> None:
        _write(self.heldout / "questions.json", json.dumps(_valid_questions()))
        _set_manifest(
            self.heldout,
            state=heldout_protocol.STATE_QUESTIONS,
            corpus_files=_corpus_entry(self.heldout),
            questions_sha256="0" * 64,
        )
        code, _out, err = self._main("pin", "--model", "claude-opus-5-5")
        self.assertEqual(code, 1)
        self.assertIn("questions.json's sha256 differs", err)

    def _git_stub(self, status: str, head: str, *, tree_of: Any = None) -> Any:
        """``status`` for git status, ``head`` for rev-parse, and a listing per commit for ls-tree."""

        def fake(*args: str) -> str:
            if args[0] == "status":
                return status
            if args[0] == "ls-tree":
                commit = args[2]
                return tree_of(commit) if tree_of else f"100644 blob {commit}\tsrc/wiki_studio/x.py"
            return head

        return fake

    def test_pin_refuses_a_dirty_tree(self) -> None:
        _write(self.heldout / "questions.json", json.dumps(_valid_questions()))
        _set_manifest(
            self.heldout,
            state=heldout_protocol.STATE_QUESTIONS,
            corpus_files=_corpus_entry(self.heldout),
            questions_sha256=_sha256(self.heldout / "questions.json"),
        )
        with (
            mock.patch.object(heldout_protocol, "_git", self._git_stub(" M src/wiki_studio/discovery.py", "a" * 40)),
            mock.patch.object(heldout_protocol.shutil, "which", return_value="/usr/local/bin/claude"),
        ):
            code, _out, err = self._main("pin", "--model", "claude-opus-5-5")
        self.assertEqual(code, 1)
        self.assertIn("uncommitted changes", err)
        self.assertIn("src/wiki_studio/discovery.py", err)
        manifest = _manifest(self.heldout)
        self.assertEqual(manifest["state"], heldout_protocol.STATE_QUESTIONS)
        self.assertNotIn("pins", manifest)

    def test_pin_records_the_executed_source(self) -> None:
        _write(self.heldout / "questions.json", json.dumps(_valid_questions()))
        _set_manifest(
            self.heldout,
            state=heldout_protocol.STATE_QUESTIONS,
            corpus_files=_corpus_entry(self.heldout),
            questions_sha256=_sha256(self.heldout / "questions.json"),
        )
        with (
            mock.patch.object(heldout_protocol, "_git", self._git_stub("", "a" * 40)),
            mock.patch.object(heldout_protocol.shutil, "which", return_value="/usr/local/bin/claude"),
            mock.patch.object(heldout_protocol, "_version", return_value="2.0.0 (Claude Code)"),
        ):
            code, _out, err = self._main("pin", "--model", "claude-opus-5-5")
        self.assertEqual(code, 0, err)
        pins = _manifest(self.heldout)["pins"]
        self.assertEqual(pins["wiki_studio_commit"], "a" * 40)
        self.assertEqual(pins["wiki_studio_version"], heldout_protocol.__version__)
        self.assertEqual(pins["claude_path"], "/usr/local/bin/claude")
        self.assertEqual(pins["claude_code_version"], "2.0.0 (Claude Code)")
        self.assertIs(pins["tree_clean"], True)

    def _pinned_for_ingest(self, commit: str) -> None:
        _write(self.heldout / "questions.json", json.dumps(_valid_questions()))
        _set_manifest(
            self.heldout,
            state=heldout_protocol.STATE_PINNED,
            corpus_files=_corpus_entry(self.heldout),
            questions_sha256=_sha256(self.heldout / "questions.json"),
            isolation_probe={"passed": True},
            pins={
                "wiki_studio_commit": commit,
                "wiki_studio_version": heldout_protocol.__version__,
                "claude_path": "/usr/local/bin/claude",
                "tree_clean": True,
                "model": "claude-opus-5-5",
            },
        )

    def test_ingest_refuses_source_that_differs_from_the_pins(self) -> None:
        self._pinned_for_ingest("b" * 40)

        def never(*_args: Any, **_kwargs: Any) -> Any:
            self.fail("the ingest runner was called although the source check failed")

        with (
            mock.patch.object(heldout_protocol, "_git", self._git_stub("", "a" * 40)),
            mock.patch.object(heldout_protocol.shutil, "which", return_value="/usr/local/bin/claude"),
            mock.patch.object(heldout_protocol, "_run_logged", never),
        ):
            code, _out, err = self._main("ingest")
        self.assertEqual(code, 1)
        self.assertIn(heldout_protocol.SOURCE_TREE_KEY, err)
        self.assertNotIn("claude_path", err)
        manifest = _manifest(self.heldout)
        self.assertEqual(manifest["state"], heldout_protocol.STATE_PINNED)
        self.assertNotIn("ingest", manifest)
        self.assertFalse((self.heldout / "wiki").exists())

    def test_pin_can_be_retaken_before_the_ingest_and_never_after(self) -> None:
        """A tool fix merged after the pin needs a re-pin; the old pins stay on record and the probe must rerun."""
        self._pinned_for_ingest("b" * 40)
        _set_manifest(self.heldout, **{**_manifest(self.heldout), "isolation_probe": {"passed": True}})
        with (
            mock.patch.object(heldout_protocol, "_git", self._git_stub("", "c" * 40)),
            mock.patch.object(heldout_protocol.shutil, "which", return_value="/usr/local/bin/claude"),
            mock.patch.object(heldout_protocol, "_version", return_value="2.1.312 (Claude Code)"),
        ):
            code, _out, err = self._main("pin", "--again", "--model", "claude-opus-5-5")
        self.assertEqual(code, 0, err)
        manifest = _manifest(self.heldout)
        self.assertEqual(manifest["state"], heldout_protocol.STATE_PINNED)
        self.assertEqual(manifest["pins"]["wiki_studio_commit"], "c" * 40)
        self.assertEqual([h["wiki_studio_commit"] for h in manifest["pins_history"]], ["b" * 40])
        self.assertTrue(manifest["pins_history"][0]["replaced_at"])
        self.assertNotIn("isolation_probe", manifest, "the probe must run again under the new pins")
        self.assertEqual(manifest["history"][-1]["state"], heldout_protocol.STATE_PINNED)
        _set_manifest(self.heldout, **{**_manifest(self.heldout), "ingest": {"started_at": "now"}})
        with (
            mock.patch.object(heldout_protocol, "_git", self._git_stub("", "d" * 40)),
            mock.patch.object(heldout_protocol.shutil, "which", return_value="/usr/local/bin/claude"),
        ):
            code, _out, err = self._main("pin", "--again", "--model", "claude-opus-5-5")
        self.assertEqual(code, 1)
        self.assertIn("the ingest has started", err)

    def test_a_manifest_only_commit_after_the_pin_does_not_refuse_the_ingest(self) -> None:
        """Committing the pin and the probe moves HEAD; the ingest compares the source tree, not the commit."""
        self._pinned_for_ingest("b" * 40)
        same_tree = "100644 blob 0123\tsrc/wiki_studio/x.py\n100644 blob 4567\teval/navigation/heldout/manifest.json"

        def stop_at_init(*_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("reached the ingest runner")

        with (
            mock.patch.object(heldout_protocol, "_git", self._git_stub("", "a" * 40, tree_of=lambda _c: same_tree)),
            mock.patch.object(heldout_protocol.shutil, "which", return_value="/usr/local/bin/claude"),
            mock.patch.object(heldout_protocol, "_run_logged", stop_at_init),
            self.assertRaises(RuntimeError),
        ):
            heldout_protocol.step_ingest(self.heldout)

    def test_ingest_refuses_a_dirty_tree_before_the_first_attempt(self) -> None:
        self._pinned_for_ingest("a" * 40)

        def never(*_args: Any, **_kwargs: Any) -> Any:
            self.fail("the ingest runner was called although the tree is dirty")

        with (
            mock.patch.object(heldout_protocol, "_git", self._git_stub(" M eval/navigation/discovery.py", "a" * 40)),
            mock.patch.object(heldout_protocol.shutil, "which", return_value="/usr/local/bin/claude"),
            mock.patch.object(heldout_protocol, "_run_logged", never),
        ):
            code, _out, err = self._main("ingest")
        self.assertEqual(code, 1)
        self.assertIn("uncommitted changes", err)
        self.assertNotIn("ingest", _manifest(self.heldout))

    def test_ingest_records_the_recomputed_source_check(self) -> None:
        self._pinned_for_ingest("a" * 40)

        def runner(cmd: list[str], _env: dict[str, str], log_prefix: Path) -> tuple[int, float, str, str]:
            log_prefix.parent.mkdir(parents=True, exist_ok=True)
            return 0, 0.0, "", ""

        with (
            mock.patch.object(heldout_protocol, "_git", self._git_stub("", "a" * 40)),
            mock.patch.object(heldout_protocol.shutil, "which", return_value="/usr/local/bin/claude"),
            mock.patch.object(heldout_protocol, "_run_logged", runner),
        ):
            code, _out, err = self._main("ingest")
        self.assertEqual(code, 0, err)
        manifest = _manifest(self.heldout)
        self.assertEqual(manifest["state"], heldout_protocol.STATE_INGESTED)
        check = manifest["ingest_source_check"]
        self.assertTrue(check.pop("checked_at"))
        self.assertRegex(check.pop(heldout_protocol.SOURCE_TREE_KEY), r"^[0-9a-f]{64}$")
        self.assertEqual(
            check,
            {
                "wiki_studio_commit": "a" * 40,
                "wiki_studio_version": heldout_protocol.__version__,
                "claude_path": "/usr/local/bin/claude",
                "tree_clean": True,
            },
        )

    def test_ingest_refuses_without_a_passed_probe(self) -> None:
        _set_manifest(self.heldout, state=heldout_protocol.STATE_PINNED, isolation_probe={"passed": False})
        code, _out, err = self._main("ingest")
        self.assertEqual(code, 1)
        self.assertIn("probe", err)

    def test_nothing_is_rerun_once_the_ingest_started(self) -> None:
        _set_manifest(
            self.heldout,
            state=heldout_protocol.STATE_PINNED,
            isolation_probe={"passed": True},
            ingest={"started_at": "t", "documents": []},
        )
        for step in ("probe", "ingest"):
            with self.subTest(step=step):
                code, _out, err = self._main(step)
                self.assertEqual(code, 1)
                self.assertIn("ingest", err)
                self.assertRegex(err, "never|nothing is re-run")

    def test_freeze_wiki_then_freeze_record_the_floors(self) -> None:
        heldout = _synthetic_heldout(Path(self._tmp.name) / "fixture")
        code, _out, err = _quiet(heldout_protocol.main, ["--heldout-dir", str(heldout), "freeze-wiki"])
        self.assertEqual(code, 0, err)
        self.assertEqual(_manifest(heldout)["state"], heldout_protocol.STATE_WIKI_FROZEN)
        code, _out, err = _quiet(heldout_protocol.main, ["--heldout-dir", str(heldout), "freeze"])
        self.assertEqual(code, 0, err)
        manifest = _manifest(heldout)
        self.assertEqual(manifest["state"], heldout_protocol.STATE_FROZEN)
        self.assertEqual((manifest["gold_questions"], manifest["eligible_pages"]), (2, 2))
        self.assertEqual(manifest["gold_sha256"], _sha256(heldout / "gold.json"))
        self.assertEqual(manifest["wiki_tree_sha256"], _tree_hash(heldout / "wiki"))
        self.assertEqual(
            [h["state"] for h in manifest["history"]],
            [heldout_protocol.STATE_WIKI_FROZEN, heldout_protocol.STATE_FROZEN],
        )

    def test_freeze_refuses_a_wiki_edited_after_freeze_wiki(self) -> None:
        heldout = _synthetic_heldout(Path(self._tmp.name) / "fixture")
        heldout_protocol.step_freeze_wiki(heldout)
        _write(heldout / "wiki" / ALPHA, "edited\n")
        with self.assertRaisesRegex(heldout_protocol.ProtocolError, "never edited"):
            heldout_protocol.step_freeze(heldout)

    def test_freeze_refuses_gold_for_a_missing_page(self) -> None:
        heldout = _synthetic_heldout(Path(self._tmp.name) / "fixture")
        heldout_protocol.step_freeze_wiki(heldout)
        _write(heldout / "gold.json", json.dumps([dict(GOLD[0], gold="concepts/none.md"), *GOLD[1:]]))
        with self.assertRaisesRegex(heldout_protocol.ProtocolError, "names no page"):
            heldout_protocol.step_freeze(heldout)

    def test_freeze_refuses_gold_outside_the_wiki(self) -> None:
        heldout = _synthetic_heldout(Path(self._tmp.name) / "fixture")
        heldout_protocol.step_freeze_wiki(heldout)
        _write(heldout / "gold.json", json.dumps([dict(GOLD[0], gold="../questions.json"), *GOLD[1:]]))
        with self.assertRaisesRegex(heldout_protocol.ProtocolError, "names no page"):
            heldout_protocol.step_freeze(heldout)

    def test_questions_checks_the_bytes_of_the_resolved_commit(self) -> None:
        _set_manifest(self.heldout, state=heldout_protocol.STATE_SOURCES)
        _write(self.heldout / "questions.json", json.dumps(_valid_questions()))
        data = (self.heldout / "questions.json").read_bytes()
        with (
            mock.patch.object(heldout_protocol, "_committed_bytes", return_value=data) as committed,
            mock.patch.object(heldout_protocol, "_git", return_value="b" * 40),
        ):
            code, _out, err = self._main("questions", "--commit", "HEAD")
        self.assertEqual(code, 0, err)
        self.assertEqual(committed.call_args.args[0], "b" * 40)

    def test_the_eligible_pages_are_the_ones_find_considers(self) -> None:
        # read_eligible_pages reimplements find's eligibility loop; on the development wiki they agree.
        wiki_dir = RUN2 / "wiki"
        links = _extract_index_links((wiki_dir / "index.md").read_text(encoding="utf-8"), wiki_dir)
        with tempfile.TemporaryDirectory() as tmp:
            paths = WikiPaths.for_root(
                RUN2, wiki_dir=wiki_dir, proposals_dir=RUN2 / "proposals", search_cache=Path(tmp) / "c.sqlite"
            )
            result = api.find("anything", paths, ranker=RANKER_INDEX_FIRST)
        candidates = {rel for rel in links if posixpath.normpath(rel) not in wiki_discovery._NEVER_CANDIDATES}
        expected = candidates - {page.path for page in result.ineligible}
        self.assertEqual(set(heldout_protocol.read_eligible_pages(wiki_dir)), expected)


if __name__ == "__main__":
    unittest.main()
