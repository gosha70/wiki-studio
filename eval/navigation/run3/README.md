# Run 3 — the development set

Run 3 measures both rankers, `fts5` and `index-first`, on run 2's frozen wiki
(`eval/navigation/run2/wiki`, read in place, never copied) and run 1's
questions, corpus and stop list (`specs/wiki-studio-0-8-0`, FR-020, FR-021).
Of its 35 questions, 21 have a gold page and carry hit numbers. It is the
development set: tuning happens here, and only after the held-out set is
frozen (`../heldout/protocol.md`). Its numbers never decide the default.

| File | What | When |
|------|------|------|
| `ranker-config-untuned.json` | The untuned configuration (`porter unicode61`, weights 4, 4, 2, 1, minimum match 1, five pages) and its hash | Committed before any tuning |
| `results-untuned.json` | Both rankers under the untuned configuration | Committed before any tuning |
| `tuning.json` | Every configuration of the closed grid with hit at 1, hit at 5, absent behaviour and hash, and the chosen one | Written by `discovery tune` after the held-out freeze |
| `ranker-config.json` | The chosen configuration and its hash, the frozen configuration | Written by `discovery tune` |
| `results.json` | Both rankers under `ranker-config.json` | After tuning |

Reproduce the untuned result (everything except `latency`, which is
machine-dependent):

```bash
python -m eval.navigation.discovery run --fixture eval/navigation/run2 --shared eval/navigation \
    --config eval/navigation/run3/ranker-config-untuned.json
```

Every results file records its configuration under `parameters`, and
`tests/test_discovery_eval.py` reproduces each one in memory under that
configuration, so it stays reproducible after the live default changes. The
`index-first` column equals run 2's published numbers (3 of 21 at 1, 10 of 21
at 5), because on a wiki with no ineligible page `find` selects exactly what
run 2's selector did. Ingest coverage is inherited from run 2 (21 of 29), not
re-measured. The search cache is kept in a temporary directory, never beside
the frozen wiki.
