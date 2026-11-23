# Build review — phase 3 (US3), by hand

Phase 3 was finished outside the auto-build driver (its sessions could not run
Python; see the phase 3 commit message), so the driver's gating review did not
run on it. The build session sent the phase's code diff (`7af7fd4..ae4f2ad`,
limited to `record.py`, `candidates.py`, `report.md` and
`tests/test_revisions_eval.py`; the recorded data files left out for size) to
DeepSeek (`deepseek-flash`, through code-copilot-team's
`provider-adapters/openai-compatible.sh`) on 2026-11-23.

Verdict: CHANGES SUGGESTED (advisory). Dispositions by the build session:

- **"The setup clone and checkout lack the hardened prefix"** (marked blocking).
  Partly right. `_resolve` and `_blob_sha256` go through `_git`, which carries
  the full prefix; the review misread them. The two setup calls (`git clone
  --no-hardlinks --no-checkout` of the owner's own checkout into a temporary
  directory, then `checkout --detach`) are plain local commands, as FR-012
  lists them; `checkout` sets `core.hooksPath`. The report claims the hardened
  prefix only for the call plan p1-p7. No code change; noted for the external
  review.
- **"An unexpected p3 failure silently skips a repository."** No effect on this
  record: no repository was skipped, all 28 sources were checked and 2 went to
  the exact kind.
- **"`heading_above` is off by one."** It matches FR-008's "at or above the
  hunk's first old-side line".
- **"No sensitivity note for the anchor rule, with the win at the limit."**
  Taken: the report now says that was not measured.
- **Test-strength suggestions** (golden-file scorer test, the loose process-count
  check, no unit test of `decide` and `select`): noted for the external review;
  FR-015's tests are as specified.
