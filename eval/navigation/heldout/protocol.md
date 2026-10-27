# Held-out discovery evaluation — protocol

Preregistered for wiki-studio 0.8.0 (`specs/wiki-studio-0-8-0`, FR-022..FR-030).
This set decides whether `fts5` becomes the default ranker. The order below is
fixed and enforced by the tools: `manifest.json` carries `state` through
`sources` → `questions` → `pinned` → `ingested` → `wiki-frozen` → `frozen` →
`run`, with a timestamp per transition, and every `heldout_protocol.py`
subcommand refuses to run in any other state (exit 1, naming the expected
state). Commands run from the repository root; the tools never commit, so
commit after each step as written.

## Steps

| # | Step | Command | State after | Who |
|---|------|---------|-------------|-----|
| 1 | Sources: the eight mapatlas READMEs at commit `7c3a8de609fb8e2173a74a884afdc4029ff18ca5`, copied byte for byte into `corpus/` (`/` → `__`), sha256 and bytes in `manifest.json` (30,554 bytes), attributed in `NOTICE` | — (done in the build) | `sources` | build |
| 2 | Questions: written into `questions.json` (below), reviewed by the owner, committed; then recorded | `python -m eval.navigation.heldout_protocol questions --commit <sha>` | `questions` | owner |
| 3 | Pins: wiki-studio commit and version, backend `claude`, the model by full name, the Claude Code version, the backend timeout, the run's environment | `python -m eval.navigation.heldout_protocol pin --model <full model name>` | `pinned` | owner |
| 4 | Isolation probe (run 2's form): one trivial backend call that must change nothing under `heldout/` and start no hook test run; a failure is fixed and the probe re-run | `HOOK_SKIP=1 python -m eval.navigation.heldout_protocol probe` | `pinned` | owner's account |
| 5 | The one ingest: a fresh `init` under `heldout/wiki/`, then for each document in manifest order one `ingest` attempt and `promote` when the gate accepts it; disposition, wall time and model call count per document; logs under `ingest-logs/`. Commit `wiki/`, `proposals/`, `ingest-logs/` and the manifest | `HOOK_SKIP=1 python -m eval.navigation.heldout_protocol ingest` | `ingested` | owner's account |
| 6 | Freeze the wiki: tree hashes of the wiki and the archived proposals, the ingest summary. Commit | `python -m eval.navigation.heldout_protocol freeze-wiki` | `wiki-frozen` | owner |
| 7 | Gold: `gold.json` assigned by reading the frozen wiki (below), reviewed by the owner with the questions; then freeze questions, gold and wiki, recording `gold_questions` and `eligible_pages`. Commit, and add the sha256 pins of `wiki/`, `proposals/` and the manifest to `tests/test_frozen_runs.py` | `python -m eval.navigation.heldout_protocol freeze` | `frozen` | owner |
| 8 | Tune on the development set only (run 2's wiki, 21 gold questions): refuses unless the held-out set is `frozen` and unchanged and `run3/results-untuned.json` reproduces under `run3/ranker-config-untuned.json`; writes `run3/tuning.json` and `run3/ranker-config.json` | `python -m eval.navigation.discovery tune` | `frozen` | owner |
| 9 | Freeze the configuration: set `DEFAULT_RANKER_CONFIG` in `src/wiki_studio/discovery.py` to `run3/ranker-config.json`; produce `run3/results.json`. Commit | `python -m eval.navigation.discovery run --fixture eval/navigation/run2 --shared eval/navigation --config eval/navigation/run3/ranker-config.json > eval/navigation/run3/results.json` | `frozen` | owner |
| 10 | The one held-out run: refuses unless `frozen` and `run3/ranker-config.json`'s hash equals the live `ranker_config_hash()`; `--config` is refused; writes `results.json` only if absent. Commit | `python -m eval.navigation.discovery run --fixture eval/navigation/heldout --shared eval/navigation` | `run` | owner |
| 11 | Decide (below); set `DEFAULT_RANKER` accordingly; the CHANGELOG states the basis and the README Evidence section gains the run 3 and held-out columns | `python -m eval.navigation.discovery decide` | `run` | owner |

Steps 4 and 5 need the owner's Claude account and a model; they run outside
CI. Steps 2 to 11 land in the evidence PR on `evidence/wiki-studio-0-8-0`,
reviewed on its own and merged before the v0.8.0 tag.

## No retries

A failure before the first ingest attempt (the probe, backend access) is fixed
and the probe re-run. Once `ingest` has recorded its start, nothing is re-run:
one attempt per document, nothing edited by hand, and a poor ingest is
reported as measured. `probe` and `ingest` refuse once an ingest is recorded.
A second ingest, should the owner ever decide one, is a new labelled
directory, never this one. The held-out run happens once; any later run needs
`--post-hoc LABEL` and writes `results-post-hoc-<label>.json`, never
`results.json`. No tuning happens after the run.

## Writing the questions (D9)

A separate agent session writes `questions.json` from the source documents.
It sees only `eval/navigation/heldout/corpus/`: not the ranker code, not the
development results, not the tuning section of the spec. The set has at least
35 answerable questions (`single` and `competing`, at least six `competing`)
and at least six `absent` questions the corpus cannot answer, in
`eval/navigation/questions.json`'s shape (`id`, `kind`, `question`). The
owner reviews the set and commits it before the ingest; `questions` records
its sha256 and commit, and `pin`, `ingest` and `freeze` refuse a changed file.

## Gold

`gold.json` is assigned after `freeze-wiki`, by reading the frozen wiki, in
run 2's shape: one entry per question with `gold` (a wiki path, `index.md`,
or null), `distractors` (pages a ranker might confuse with gold) and a
`reason`. An `absent` question's gold is null; a question whose answer landed
in no page has null gold. Scoring follows run 2's preregistered rule: hit at 1
when gold is the first selected page, hit at 5 when it is among the selected
pages; questions with null gold or gold `index.md` (always loaded) carry no
hit; a distractor outranks gold when it is selected above it. The owner
reviews the questions and the gold together. `freeze` records `gold_questions`
(questions whose gold is a page other than `index.md`) and `eligible_pages`
(index-linked, regular, UTF-8, not superseded pages of the frozen wiki).

## Floors and the decision rule (D5, D8b, D8c)

`fts5` becomes `DEFAULT_RANKER` only if, in `results.json`, its hit at 1 and
its hit at 5 are each no lower than `index-first`'s, **and** `gold_questions`
is at least 15 (D8b), **and** `eligible_pages` is at least 10 (D8c).
Otherwise the default stays `index-first` and `fts5` ships opt-in. When a
floor holds, the CHANGELOG says `fts5` stays opt-in for want of evidence, not
from a measured loss, and names the floor with the counts; otherwise it states
the held-out numbers. `discovery decide` prints the rule, the decision and its
basis from the committed files.
