# Ceremony batching: stress test

**Principle:** batch the ceremony, preserve atomic accountability. When a hard
sovereignty constraint creates operational overhead, optimize the ceremony
surrounding the constraint before considering any relaxation of it.

**Status:** engineering protocol (GOVERNANCE.md §12), not Lexicon doctrine.
This document is the stress test for generalization. If the principle fails
here, it stays a description of two cases, not a rule.

## Demonstrated cases

- **S1 (sub-delegation):** one principal decision → N individually-visible,
  individually-revocable AuthorityRecords. Ceremony batched (one decision);
  accountability atomic (per-agent records, provenance, revocation).
- **S2 (rail changes):** one principal action disposes of N proposals. Ceremony
  batched (one review); accountability atomic (per-change RegimeDelta with its
  own justification).

## Stress test 1: the rubber-stamping objection

*Objection:* batching 50 rail changes makes per-item review implausible; the
principal will rubber-stamp, and atomic accountability becomes fiction.

*Response:* the architecture cannot force attention, but it makes inattention
visible and reviewable. Per-item justification records are mandatory; the
batch approval enumerates exact proposal IDs (there is deliberately no
"approve all pending" path — the API requires enumeration); the batch
decision itself is logged as covering precisely those items; batch size is
visible in the audit trail. A principal who routinely batch-approves
50-item batches with thin justifications produces an auditable pattern, and
that pattern trips the same review as bypass behavior.

*Honest limit:* this mitigates, it does not solve. The residual is epistemic
(the principal's actual attention), which no record-keeping can verify. The
risk is documented in the protocol rather than hand-waved. If a future case
shows batching *systematically* degrading review quality below the
per-item baseline, the principle's condition (3) — no skipped substantive
evaluation — fails, and batching is refused for that case.

## Stress test 2: where the timing is load-bearing

*Case:* safety-state reassessment after a trigger fires. Could the principal
batch-clear all YELLOW states in one action?

*Result:* refused. Each trigger demands its own reassessment against current
evidence; a blanket clear would skip substantive evaluation per item,
violating condition (3). The ceremony here *is* the accountability — there is
nothing to batch without discarding. The principle constrains itself correctly.

*Case:* fresh assent (challenge-response liveness). Could future assents be
pre-batched?

*Result:* refused. The challenge must be fresh per moment; pre-batching would
issue authorizations against challenges never presented. Timing is
load-bearing.

## Stress test 3: does batching reintroduce opacity by another door?

*Objection:* S1's batch delegation looks uncomfortably close to the rejected
opaque inheritance — 50 sub-agents from one decision.

*Response:* the difference is structural, not quantitative. Opaque inheritance
produces sub-agents with *no* records, *no* individual revocability, and *no*
visibility. Batch delegation produces 50 records, 50 revocation handles, and
an audit trail enumerating all of them. An auditor asking "who acted under
what authority?" gets 50 precise answers in the batch case and silence in the
opaque case. If batching ever merges items such that the question stops having
per-item answers, condition (1) fails and the batching is illegitimate —
regardless of how convenient it is.

## Third domain: retrospective review (structurally different)

S1 (sub-delegation) and S2 (rail changes) batch *prospective authorization*.
S3 (standing delegations, `test_s3_envelope_expansion`) batches the same
ceremony *across time* and adds the learning recursion — related to S2, not
independent. The structurally different domain is **batched retrospective
review** (`Governor.submit_review`, `prototype/tests/test_review.py`): one
review session covers N executed actions, each item receiving its own
disposition (acknowledged / flagged / escalated), individually recorded.

The same mechanical test applies — from the audit trail alone, an auditor
reconstructs exactly what the principal decided about each item — and the
abuse tests are the interesting part:

- Items without dispositions cannot pass through silently
  (`REVIEW_DISPOSITION_MISMATCH`); non-execution entries cannot be smuggled
  in (`REVIEW_UNKNOWN_ITEM`); dispositions are a closed set.
- **Review is observation only.** An escalated disposition revokes nothing,
  changes no rail, and grants no power. Review cannot substitute for control
  actions (revocation, reassessment) — the batch never becomes a backdoor.

This is the principle surviving in a domain with reversed temporal direction
(looking back instead of authorizing forward) and a different failure mode
(oversight degrading into theater rather than authorization degrading into
rubber-stamping). Three domains, same reconstructibility test.

## Generalization claim (current)

The principle holds across three structurally distinct domains (prospective
delegation, prospective rail change, retrospective review), survives the
rubber-stamping objection (with the attention residual documented, not
solved), refuses the timing-load-bearing cases, and distinguishes itself
from the rejected opaque alternative structurally. That justifies an
engineering pattern worth actively testing; Lexicon-doctrine promotion still
waits on Caleb's explicit word (open decision #6 covers the neighboring
autonomy-envelope claim).

## The deeper result

If the pattern generalizes, the architecture scales not by weakening human
sovereignty but by **amortizing the cost of exercising it**. The expensive
part was never the constraint — it was the ceremony around the constraint.
That reframes the engineering program: every sovereignty-induced bottleneck
is a candidate for ceremony-batching analysis, and the analysis has a fixed
form (can per-item provenance/scope/revocability/accountability survive the
batch? if yes, batch; if no, the bottleneck stands).
