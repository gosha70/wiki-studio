# Origin alignment check — wiki-studio-patterns-54

Gate: the bet pitch `specs/pitches/54-reusable-patterns/pitch.md` was
reviewed and merged in PR #110 (9178147). The owner decided D1-D8 on
2026-11-17, every default. Cycle 07 was closed in PR #113, and the bet and
cycle 08 start merged in PR #114 (f30e4b6).

The spec bundle was reviewed on PR #115:
- The first review (41e62d8) requested changes:
  - opening summaries too long for prose lint;
  - superseded pages that search could never see;
  - a circular link signal.
  The owner chose on 2026-11-18 to keep the two superseded pages in
  `index.md`, and the rest was fixed as the reviewer asked.
- The reviewer approved 4e1780d.

#115 merged as 95a6daf with the files still `status: draft`, so this
approval follows in its own PR, as for 0.9.2 and 0.10.0. The owner approved
the bundle for an automatic build on 2026-11-18, kept "pass with a warning
flag" for a verdict that rests only on annotation links, and asked that the
DeepSeek reviewer be confirmed working. It was checked on 2026-11-19:
- the health check's authenticated call to `api.deepseek.com/v1/models`
  passed;
- a one-word chat request through
  `scripts/provider-adapters/openai-compatible.sh` with model
  `deepseek-flash` answered "OK" (exit 0).

This approval commit does four things:
- sets `spec.md`, `plan.md` and the `tasks.md` marker to approved;
- adds `automation.json`, copied from 0.10.0 with four fields changed: the
  branch (`feature/wiki-studio-patterns-54`), `max_phases: 7`,
  `pr.closes: [54]` and the title. It keeps the `pr` profile, DeepSeek as
  the gating reviewer, the same gate command, two fix sessions per phase
  and the $150 / 12 h caps;
- adds this record;
- changes nothing else.

Origin:
- wiki-studio issue #54, "Govern reusable engineering patterns and assess
  duplicate knowledge" (no comments). It is a research spike whose
  deliverable is a recommendation: docs and templates only, a separately
  specified enhancement, or no change.
- the cooldown reports `cooldown-after-05.md` (the owner's order: issue
  69, then 70, then 54), `cooldown-after-06.md` and `cooldown-after-07.md`;
- memkernel's #57 corpus at tag `v0.9.0` (commit 7f26012, sha256
  10e61af7…ca503), and code-copilot-team's wiki at `00d49c0`.

The evidence PR closes issue 54 (`pr.closes`) when the report is published.
Each enhancement it recommends becomes a new issue. The pitch PR (#110),
the bet PR (#114), the spec PR (#115) and this approval PR use no closing
keyword.

Working claim:
> An `eval/patterns/` study, with no change under `src/wiki_studio/`, tests
> whether the existing `decision` page type can hold a reusable engineering
> pattern. The pattern uses an optional convention inside its four
> sections: a summary of one sentence, or of three where needed, then
> "Applies when / Does not apply when", "Revisit when", and evidence as
> `sources:` with `sha:`.
>
> The study:
> - copies memkernel's labelled corpus (pinned by tag and sha256), plus two
>   successor pages and code-copilot-team's wiki as background;
> - labels all 91 pattern pairs and freezes the retrieval gold in their own
>   phase, before any signal code exists;
> - traces a pattern's lifecycle with no model;
> - measures retrieval, with the `fts5` comparison skipped where SQLite
>   lacks FTS5;
> - measures three model-free near-duplicate signals against the frozen
>   labels. Each verdict states its counts, a verdict that rests only on
>   annotation links is flagged, and a pass is grounds to draft an issue,
>   nothing more;
> - checks `path:` + `sha:` revisit signals against what `stale-claim`
>   reports;
> - publishes `report.md` with a recommendation, plus `docs/patterns.md`
>   only if the study recommends a template.
>
> It makes no schema, findings, lint, exit-code or MCP change, has no
> release, and doesn't touch memkernel or code-copilot-team.

Origin items, mapped:
- Inventory and the fit map: FR-001 to FR-004, US1.
- The pinned corpus, the successors and the background: FR-005 to FR-011,
  US2.
- The frozen labels, gold and protocol: FR-012 to FR-016, US3.
- The lifecycle trace and retrieval: FR-017 to FR-021, US4.
- The duplicate run: FR-022 to FR-025, US5.
- The revisit signals: FR-026 to FR-029, US6.
- The report, the recommendation and closure: FR-030 to FR-035, US7.

Mismatches, each deliberate and recorded in plan.md's twenty "Departures
from the pitch":
- Labelling is its own phase. All 91 pairs are labelled, and background
  pairs count as false unless a corpus record names them.
- The pass bar states its counts and can come out "not testable".
- The corpus is copied in with a manifest, so CI can check the pin.
- After review:
  - three-sentence summaries;
  - the superseded pages stay indexed (owner);
  - signal (a)'s shared-path part reported on its own;
  - annotation-linked pairs flagged.

Verdict: aligned
Confidence: high
