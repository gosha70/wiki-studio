---
page_type: decision
slug: cct-routing-shadow-plan-05
title: 'Recommendation derivation v1 — positive observed-evidence dominance, per'
status: stable
last_reviewed: 2026-11-22
sources:
  - path: specs/routing-shadow/plan.md
    sha: fd05256b107889853068e81aca1cf7c60419e37e
---

## Decision

The unit is the task within
one evidence set; trials are aggregated by E1's own pipeline (the
report's per-task figures). Per task:
*actual*: the router's routing evidence as a closed structure —
per trial: the ordered selected-profile chain, whether the task
was delegated and reconciled — read from the routing-run
records with decision indices as evidence refs. Display and
evidence; never the recommendation trigger.
*candidates*: the EXECUTABLE control arms only — `always_best`
and `always_cheapest`. The oracle is a hindsight bound, shown as
the stated ceiling, never suggested (it is not a policy anyone
can run).
*the availability guard* (settled in the T1 review, before T2
builds): fixed-profile sweeps measure capability under an
availability-neutral baseline, while the router ran under the
scenario's injected outages. A `switch_profile` recommendation is
therefore ACTIONABLE only when the suggested profile appears
ADMISSIBLE in the router's own durable candidate evidence for
that task — present in the records' considered lists with a
verdict other than an availability rejection. Otherwise the
outcome is `insufficient_data` (with the availability evidence
referenced), never a claim that an unavailable profile should
have been used.
*comparison tolerance* (declared once, used everywhere): E2
declares its OWN absolute tolerance — two float64 figures are
EQUAL iff they differ by at most `1e-9`, and *strictly greater*
means exceeding by more than `1e-9`. (Attribution corrected
from rev-3: E1's cost_reader uses
`math.isclose(rel_tol=1e-9, abs_tol=1e-12)` for its value-bound
check and the oracle sorts exact floats; E2 does not borrow
those — this is E2's declared comparison rule, with boundary
tests at the tolerance edge.) Both Q and cost comparisons use
it; harmless rounding can never flip an outcome.
*the rule* (closed; positive evidence, never identity
difference): a candidate arm is *dominating* for the task iff
its per-task quality is strictly greater (per the tolerance)
than the router's and its per-task cost under the declared basis
is not greater — or its quality is equal (per the tolerance) and
its cost strictly lower. `outcome = switch_profile` iff at least
one candidate dominates (suggested = the dominating arm with the
higher quality; ties between dominating arms break by lower
cost, then arm name); `no_change_recommended` iff no candidate
dominates and every consumed figure is present and sufficient —
including when the router outperforms every control (the
counterexample this rule exists for: configured-best is not
observed-best, and identity difference alone recommends
nothing); `insufficient_data` iff the set is VALID but any
consumed figure is insufficient/withheld (arm insufficiency,
withheld Q, withheld frontier, a task absent from an arm's
table), carrying the specific insufficiency references. Invalid
sets produce no records at all (decision 4).
*divergence*: the declared subtractions (router minus candidate
per-task quality; router minus candidate per-task cost) of the
report's served figures, computed in IEEE-754 float64.
*confidence*: a closed GRADE plus its basis, both required, and
the grade measures the SAME claim the recommendation makes — per
trial, the full tolerance-aware TWO-AXIS dominance predicate,
not quality alone: for a `switch_profile` outcome, agreement =
the fraction of trials in which the suggested arm's per-trial
figures dominate the router's (quality strictly greater at cost
not greater, or quality equal at cost strictly lower); for
`no_change_recommended`, agreement = the fraction of trials in
which NO candidate's per-trial figures dominate. A trial whose
per-trial cost is unavailable under the declared basis cannot
evaluate the predicate: the grade is capped at `low` and the
basis names the unpriced trial as insufficient confidence
evidence.
Grade rule v2 (declared, deterministic): `high` iff declared
trials ≥ 5 AND the full v1 component mask AND agreement ≥ 0.8
AND every consumed trial evaluated the predicate; `moderate`
iff trials ≥ 2 AND the full mask AND agreement ≥ 0.6 AND every
trial evaluated; otherwise `low`. A single-outlier aggregate win
with majority per-trial dominance failures therefore grades
`low`, never `high` — the pinned regression for this rule. The basis names: declared
trials, the agreement fraction, the divergence deltas with the
cost basis, components_included, and the insufficiency
references consumed (empty when none). Never a bare number.
Derivation is deterministic: identical artifact bytes yield
byte-identical recommendation records.
