# Origin alignment check — wiki-studio-0-9-2

Gate: the bet pitch `specs/pitches/69-one-set-of-instructions/pitch.md` was
reviewed on PR #99. Review of c86a967 found that D3 as written made
`docs/mcp-adapter.md` 178-180 and README 566 false. The owner revised D3
(the persona yields to the host; one agent name with `--by`), and the
reviewer passed 0a60a90. #99 merged as 558e0fd. The bet and cycle 06 start
merged in PR #100 as 204d568.

The spec bundle was reviewed on PR #101. Review of 6b1afec requested
changes with two P1 findings. First, a reservation was false under
`auto_approve_on_promote`. Second, the approve command was not bound to the
reviewed bytes or to every promoted page. The owner decided both on
2026-11-15, the bundle was revised at 725644e, and the reviewer passed that
head. #101 merged as ddc6492 with spec, plan and tasks still `status:
draft`, so this approval follows in its own PR. The owner approved the
bundle and this `automation.json` on 2026-11-15.

This approval commit does four things:
- sets `spec.md`, `plan.md` and the `tasks.md` marker to approved;
- adds `automation.json`, copied from 0.9.0 with this feature's branch
  (`feature/wiki-studio-0-9-2`), `max_phases: 4`, `pr.closes: [69]` and
  its title. It keeps the `pr` profile, DeepSeek as the gating reviewer
  (health check passed on 2026-11-15), the 0.9.0 gate command, two fix
  sessions per phase, and the $150 / 12 h caps;
- adds this record;
- changes nothing else.

The record was written by hand from the review record, as for 0.8.0 to
0.9.0. The automated gate runs again before the build.

Origin:
- wiki-studio issue #69, "One job, one set of instructions" (no comments on
  2026-11-14). Its acceptance: no workflow step is described in both files
  with different content, and the two issues are closed together or each
  names the other's resolving PR.
- gosha70/memkernel#86 (closed 2026-11-08, shipped in memkernel 0.8.0 by
  memkernel PRs #104 and #109, both merged 2026-11-07). memkernel's
  template at tag v0.8.0, line 46, and the Kiro steering copy, line 38,
  carry the workflow line, verified.
- the cooldown report `specs/retros/cooldown-after-05.md` (the owner picked
  #69 to shape first for cycle 06);
- the bet pitch (cycle 06, building), with the owner's decisions D1-D10 of
  2026-11-14 and the revised D3 after the #99 review.

The build PR closes #69 (`pr.closes`). The pitch PR (#99), the bet PR
(#100), the spec PR (#101) and this approval PR use no closing keyword.

Working claim:
> wiki-studio 0.9.2 makes the packaged curator persona (`WIKI_MAINTAINER.md`)
> the one home for the wiki workflow that memkernel 0.8.0's templates send
> agents to. The persona's loop runs on `wiki-studio propose`, `promote`,
> `lint` and `approve`, with one agent-identifying name on `--by`. A step
> before propose decides who approves. A host reserves approval for a person
> through its project instructions (a copyable line is given) or
> propose-only mode. Where the wiki auto-approves on promote, a reservation
> stops the agent after propose. Otherwise the agent approves each changed
> content page itself, bound to the bytes it read (`read --json`, then
> `approve --revision --by`).
>
> A short "Memory tools" section links memkernel's v0.8.0 template, as
> instructions and not a compatibility claim. It gives export, approve and
> import in memkernel's order without restating memory calls. A persona test
> parses every shown command with the CLI's own parser.
>
> `docs/mcp-adapter.md` and README stop promising what the code doesn't do,
> and the version moves to 0.9.2.
>
> Nothing else moves: no CLI verb, flag, exit code, MCP tool, page schema,
> contract fingerprint, prompt or dependency, no memkernel edit, and no
> self-approval check in cycle 06.

Origin items, mapped:
- The persona's governed loop, who approves, and one name on every record:
  FR-001 to FR-007, US1.
- The memory boundary with memkernel: FR-008 to FR-012, US2.
- The checks (command parse, `--by`, `--revision`, the reservation and
  policy markers, memkernel's pinned order): FR-013 to FR-019, US3.
- The doc corrections, CHANGELOG, the version in six places, closing #69,
  and the release: FR-020 to FR-026, US4. The compatibility row is added
  after merge, in the release PR (FR-024).

Mismatches, each deliberate and recorded (plan.md, "Departures from the
pitch"):
- **D3 refined under auto-approval.** The pitch's "stops after propose or
  promote" became "stops after propose" when the wiki auto-approves on
  promote, because promote would approve at once. The owner decided this
  on 2026-11-15 in the #101 review.
- **Approval bound to reviewed bytes, one page at a time.** The pitch's
  `approve <page> --by` became `read --json`, inspect, then
  `approve <page> --revision <sha256> --by`, once for each changed content
  page. The owner decided this on 2026-11-15 in the #101 review.
- **The approval rule is a loop step before propose.** `--promote` is
  chosen when proposing, so the decision has to come first.
- **No compatibility row in the build.** The release PR adds it, naming the
  green main run, as for 0.9.0 and 0.9.1. The owner confirmed this on
  2026-11-15 over the pitch's S4 wording.
- **Smaller corrections to the pitch, found in the code:**
  - memkernel's `promote` is named without call syntax;
  - the order check reads one paragraph;
  - line 77 is reworded as well;
  - the command check requires full flag spellings and adds self-tests;
  - the version moves in six places.

Verdict: aligned
Confidence: high
