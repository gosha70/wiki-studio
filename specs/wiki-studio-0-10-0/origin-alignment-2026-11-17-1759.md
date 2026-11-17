# Origin alignment check — wiki-studio-0-10-0

Gate: the bet pitch `specs/pitches/70-propose-only-curation-pass/pitch.md`
was reviewed on PR #104 over two rounds. The owner decided D1-D16 and, after
the review, D5's link-only rule, D21 (a person approves a `nightly-*`
proposal) and D9's precedence. #104 merged as 51114b5. Cycle 06 closed
after the 0.9.2 release (PR #105, merged as cfe1ebe). The bet and cycle 07
start merged in PR #107 as 8185680.

The spec bundle was reviewed on PR #108:
- The first review (db1a904) raised four points. The owner decided them on
  2026-11-17: the link-only check keeps link text and nesting unconstrained,
  against the reviewer's recommendation; the index and log lines get fixed
  forms; FR-030 is reworded.
- The second review (822bc69) offered one optional tightening, which the
  owner took: an added link with empty text is refused.
- The reviewer passed fc4ca2a.

#108 merged as 2301028 with the files still `status: draft`, so this
approval follows in its own PR, as for 0.9.2 (#102). The owner approved the
bundle and this `automation.json` on 2026-11-17.

This approval commit does four things:
- sets `spec.md`, `plan.md` and the `tasks.md` marker to approved, and
  fixes a doubled word in task 12 that the reviewer noted;
- adds `automation.json`, copied from 0.9.2 with four fields changed: the
  branch (`feature/wiki-studio-0-10-0`), `max_phases: 6`, `pr.closes: [70]`
  and the title. It keeps the `pr` profile, DeepSeek as the gating
  reviewer, the 0.9.2 gate command (coverage 92 included), two fix
  sessions per phase, and the $150 / 12 h caps;
- adds this record;
- changes nothing else.

The reviewer health check (`providers-health.sh --provider deepseek`)
failed on 2026-11-17. code-copilot-team now reads `~/.cct/providers.toml`,
and that file is empty. It must pass before the driver runs. This doesn't
affect the bundle.

The record was written by hand from the review record, as for 0.8.0 to
0.9.2. The automated gate runs again before the build.

Origin:
- wiki-studio issue #70, "A scheduled, propose-only curation pass" (no
  comments on 2026-11-17). Its acceptance:
  - without a backend, the report lists lint and health findings and
    creates no proposal;
  - with a backend, proposals exist and the wiki is byte-identical before
    and after;
  - a second run on an unchanged wiki creates no duplicate proposals.
- the cooldown reports `specs/retros/cooldown-after-05.md` (the owner's
  order: #69, then #70, then #54) and `cooldown-after-06.md`;
- the bet pitch (cycle 07, building), with the owner's decisions;
- the reviewer's two notes from the #104 review: an unwritable report
  always exits 6, and a failed proposal write stops drafting.

The build PR closes #70 (`pr.closes`), unless the last-resort cut drops
drafting (D16): then it names issue 70 without a closing keyword, and a
follow-up issue carries drafting. The pitch PR (#104), the bet PR (#107),
the spec PR (#108) and this approval PR use no closing keyword.

Working claim:
> wiki-studio 0.10.0 adds `nightly`, a propose-only curation pass. It runs
> structural lint and the model-free findings over the whole wiki and writes
> one report (markdown, or `--json`) outside the wiki.
>
> With an explicit `--backend`, it drafts proposals:
> - for missing-cross-link findings, it updates every unlinked page;
> - for weak orphans whose one link is not from `index.md`, it adds one
>   index line.
>
> Each draft passes a syntactic link-only check against the `api.read_page`
> bytes behind each update's `base_sha256`:
> - the page must equal the original once the new links are stripped back
>   to their text;
> - no link may sit inside code, and none may have empty text;
> - the index and log lines have fixed forms.
>
> Proposal directories are named per finding, so a rerun never duplicates
> one. Proposals created are capped at N and backend calls at 2×N.
>
> It never promotes or approves, holds no lock across a backend call, and
> writes nothing under the wiki directory. A person approves every
> `nightly-*` proposal. The exit codes keep their meanings, with a stated
> precedence. It ships with a checked cron/CI recipe and two guidance edits.

Origin items, mapped:
- The pass and its report, model-free: FR-001 to FR-008, US1.
- The verb, its exit codes and precedence: FR-009 to FR-012, US2.
- Drafting, the link-only check, the two bounds, failures and the manual
  real-backend check: FR-013 to FR-024, US3.
- No duplicate on a rerun: FR-025 to FR-027, US4.
- The recipe, the persona paragraph (D21) and the `ingest-rules.md`
  amendment: FR-028 to FR-031, US5.
- The README, the knowledge contract, the `info` capability, the
  CHANGELOG, version 0.10.0 and closing #70: FR-032 to FR-038, US6. The
  compatibility row is added after merge, in the release PR.

Mismatches, each deliberate and recorded in plan.md's "Departures from the
pitch":
- Docs and contract claims move to the last phase (US6). Each flag lands in
  the phase that builds it, and the precedence tests move to US3.
- D9 extended by the reviewer's notes: an unwritable report always exits 6,
  and a failed write stops drafting. "Already proposed" needs the directory
  to exist after the error (owner).
- One draft shows and must update every unlinked page. The code lists all
  of them, not five as the pitch assumed (owner).
- A proposals directory inside the wiki is refused (owner).
- D7 changed to two bounds: proposals created, and attempts at 2×N
  (owner).
- Links inside code are refused, and aliases are linked as they stand.
- Departure 16: the link text and nesting stay unconstrained, as the owner
  decided against the reviewer's recommendation, with D21 review as the
  mitigation. One exception: empty link text is refused (owner, after the
  re-review).
- The index and log lines have fixed forms. FR-030 says the agent does not
  promote a `nightly-*` proposal on an auto-approving wiki.

Verdict: aligned
Confidence: high
