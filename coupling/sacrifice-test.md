# The sacrifice test

**Claim under test:** "subject to" in the objective (§0.1) operates as a hard
constraint, not a weighted term.

**Method:** construct features whose leverage gains are dramatic and measurable
— not marginal efficiency, but the kind of advantage that would obviously make
the system more capable — and that require violating a hard constraint. The
architecture must reject them *without quietly introducing a weighting
mechanism*: no sovereignty budget, no cost-benefit override, no trade-off
curve, no "temporary" exemption. The magnitude of the gain must never enter
the decision.

Conducted 2026-10-18.

## Case S1: Opaque sub-agent authority inheritance

**Feature:** an authorized agent spawns sub-agents that inherit its full
authority scope — no per-agent authorization, no per-agent record, invisible
to the principal.

**Leverage (dramatic, measurable):** this is the fundamental scaling mechanism
for multi-agent systems. Authorization overhead is the binding constraint on
agent swarms: with opaque inheritance, 100–1000x parallel throughput with zero
marginal authorization cost. Without it, every sub-agent needs a fresh
authorization ceremony and swarms cannot scale past a handful of agents. This
is not a 10% speedup; it is the difference between a demo and an economy.

**Violation:** bounded authority (the scope now covers N actors the principal
never scoped), auditability (which sub-agent did what?), revocability (revoke
*which* agent?), and the one-way ratchet (authority expanded with no granting
principal — the expansion is performed by the inheritance mechanism itself).

**Architecture's answer: REJECTED as stated.** The legitimate form exists —
explicit sub-delegation, each sub-agent receiving its own AuthorityRecord
derived from the parent grant, all visible in the audit log, all individually
revocable. But note what is sacrificed: the legitimate form preserves the
*structure* of the leverage, not the *magnitude*. Per-agent authorization
overhead is the price of scaling, paid at every fan-out. The objective accepts
slower scaling. It does not accept opaque scaling.

**Anti-weighting check:** at no point does the evaluation ask "how much
leverage is gained?" The 1000x figure never enters the decision. The
constraint fires on the *kind* of violation, not its price. That is what
"subject to" means.

## Case S2: Agent self-modification of governance rails

**Feature:** the agent updates its own rails when it judges them outdated —
self-tuning thresholds, scope expansion within "learned" bounds, constraint
relaxation where the agent's model says the constraint is miscalibrated.

**Leverage (dramatic, measurable):** continuous self-optimization with zero
principal overhead. The agent never blocks on stale governance, never waits
on threshold updates, and compounds its own efficiency gains indefinitely.
This is the dream of every autonomous-systems roadmap.

**Violation:** the one-way ratchet (the governed entity loosening its own
rails), the anti-immunization rule (§4.1: a change that only protects the
favored model cannot promote it — here the "model" is the agent's own
standing), corrigibility (who corrects the corrector?), and ultimately
sovereignty (the principal's rails become advisory the moment the agent may
rewrite them).

**Architecture's answer: REJECTED.** Rail changes require a RegimeDelta with
independent justification, authorized by the principal — the full protocol,
every time. The sacrificed leverage is real and permanent: the agent cannot
self-tune, period. There is no fast lane for "obviously correct" rail updates,
because the agent's judgment that an update is obviously correct is itself
unverified.

**Anti-weighting check:** same. No self-improvement budget, no "alignment tax"
trade-off curve. The question "but how much faster would it be?" is not asked.

## What failure would look like

This test fails the day the architecture, faced with an S1/S2-shaped
proposal, invents any of: a sovereignty budget ("small violations
acceptable"), a cost-benefit override ("leverage gain exceeds sovereignty
cost"), a grandfather clause, a sunset exemption, or an "emergency"
loophole without the mandatory after-action review. Each of these is a
weighting mechanism smuggled in — "subject to" collapsing into a weighted
term. The current architecture contains none of them.

**Regression rule:** every future proposal that trades a hard constraint for
leverage gets an S-case written for it before it is decided. The sacrifice
test is now part of the battery.

## Why this is the hard version of the teeth test

The teeth test (reputation scoring) rejected a *marginal* gain. A defender of
the architecture could always say "the gain wasn't worth it" — which is
itself a weighting intuition. The sacrifice test removes that refuge: the
gains are overwhelming, and the rejection must not price them at all. If
sovereignty survives *here*, then "subject to" is architecture. If it only
survives when cheap, it was rhetoric.

## Leverage recovery: optimization continues inside the admissible space

A hard constraint doesn't end optimization — it changes the admissible search
space. Both S-cases now have engineered recovery paths that reclaim most of
the sacrificed leverage *without relaxing the constraint*. Implemented and
tested in `prototype/` (25/25 passing).

### S1 recovery: batch sub-delegation

`Governor.delegate_batch`: one principal decision mints N sub-delegations.
Each sub-agent still receives its OWN AuthorityRecord — visible provenance
chaining to the parent grant, individually revocable, scope can only narrow.
Authorization overhead moves from N ceremonies to one decision + N records.

Tested: 50 sub-agents delegated in one call; each executes; revoking one
leaves the rest working; widening scope via delegation is refused
(`DELEGATION_WIDENING`); opaque use of a parent's record fails
(`HOLDER_MISMATCH`). Most of the scaling leverage recovered, none of the
opacity.

### S2 recovery: principal-authorized RegimeDelta

`propose_rail_change` / `approve_rail_changes`: the agent proposes rail
changes with independent justification; the granting principal disposes of a
batch in one action. Each applied change gets its own RegimeDelta record
(proposal, old/new values, justification, approver) in the history log.
The agent can never approve its own proposals (`NOT_GRANTING_PRINCIPAL`).

Tested: agent proposes spend-txn 50→75 with justification; self-approval
rejected; principal's batch approval applies it with full record; the
previously blocked spend then passes the complete governance path. Rail
changes stay fast *and* principal-authorized — the legitimate speed was in
the ceremony, not in the accountability, so batching the ceremony recovers
the leverage without touching the constraint.

### The pattern

In both cases the recovered leverage came from batching the *ceremony* while
keeping the *accountability* per-item: per-agent records, per-change
justifications. The constraint never priced the gain; the engineering priced
the overhead. That is maximum leverage subject to sovereignty operating as
written.
